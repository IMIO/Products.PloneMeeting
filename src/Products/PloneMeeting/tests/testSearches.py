# -*- coding: utf-8 -*-
#
# File: testMeetingConfig.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from DateTime import DateTime

from zope.component import getAdapter
from Products.CMFCore.permissions import ModifyPortalContent
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from eea.facetednavigation.interfaces import ICriteria
from collective.compoundcriterion.interfaces import ICompoundCriterionFilter
from collective.eeafaceted.collectionwidget.widgets.widget import CollectionWidget
from imio.helpers.cache import cleanRamCacheFor

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger

from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations


class testSearches(PloneMeetingTestCase):
    '''Tests the adapters used for searches.'''

    def test_pm_DefaultSelectedSearch(self):
        '''Test that the 'meetingAppDefaultView' defined in the MeetingConfig data
           is correctly applied to the collection-link widget on the facetednavigation view.'''
        # selected meetingAppDefaultView is 'searchallitems'
        cfg = self.meetingConfig
        searchallitems = cfg.searches.searches_items.searchallitems
        for criterion in ICriteria(cfg.searches).values():
            if criterion.widget == CollectionWidget.widget_type:
                collectionCriterion = criterion
                break
        self.assertEquals(collectionCriterion.default, searchallitems.UID())

    def test_pm_SearchItemsOfMyGroups(self):
        '''Test the 'items-of-my-groups' adapter that returns items using proposingGroup
           the current user is in.'''
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        # siteadmin is not member of any PloneMeeting groups
        adapter = getAdapter(cfg, ICompoundCriterionFilter, name='items-of-my-groups')
        self.changeUser('siteadmin')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': []},
                          'portal_type':  {'query': itemTypeName}})

        # pmManager is member of 'developers' and 'vendors'
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsofmygroups')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': ['developers', 'vendors']},
                          'portal_type':  {'query': itemTypeName}})

        # pmCreator1 is member of 'developers'
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsofmygroups')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': ['developers']},
                          'portal_type':  {'query': itemTypeName}})

        # a deactivated group is still listed
        self.changeUser('siteadmin')
        self.do(self.tool.developers, 'deactivate')
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsofmygroups')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': ['developers', 'vendors']},
                          'portal_type':  {'query': itemTypeName}})

    def test_pm_SearchItemsToAdviceAdapter(self):
        '''Test the 'search-items-to-advice' adapter that should return a list of items
           a user has to give an advice for.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'delay': '5', }, ])
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-advice')
        # admin is not adviser
        self.assertEquals(adapter.query,
                          {'indexAdvisers':  {'query': []},
                           'portal_type':  {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEquals(
            adapter.query,
            {'indexAdvisers': {
                'query': ['developers_advice_not_given',
                          'delay__developers_advice_not_given',
                          'developers_advice_asked_again',
                          'delay__developers_advice_asked_again',
                          'developers_advice_hidden_during_redaction',
                          'delay__developers_advice_hidden_during_redaction']},
                'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchallitemstoadvice"
        collection = cfg.searches.searches_items.searchallitemstoadvice
        # by default, no item to advice...
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.getQuery())
        # an advice can be given when an item is 'proposed'
        self.assertEquals(cfg.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', 'vendors__rowid__unique_id_123'))
        # as the item is "itemcreated", advices are not givable
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.getQuery())
        # now propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        # only advisers can give an advice, so a creator for example will not see it
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.getQuery())
        # now test as advisers
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmAdviser1 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.tool.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.getQuery())
        # pmReviewer2 is adviser for 'vendors', delay-aware advices are also returned
        self.changeUser('pmReviewer2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmReviewer2 gives his advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.tool.vendors.getId(),
                                             'advice_type': u'negative',
                                             'advice_comment': RichTextValue(u'My comment')})
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.getQuery())

        # ask advice again, it will appear to 'pmReviewer2' in the query
        self.backToState(item, 'itemcreated')
        self.changeUser('pmCreator1')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())

        # a given advice that is 'hidden_during_redaction' is also found by this search
        advice.advice_type = u'positive'
        changeView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeView()
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())

    def test_pm_SearchAdvisedItems(self):
        '''Test the 'search-advised-items' adapter.  This should return a list of items
           a user has already give an advice for.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='advised-items')
        # admin is not adviser
        self.assertEquals(adapter.query,
                          {'indexAdvisers': {'query': []},
                           'portal_type': {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        groupIds = []
        adviceStates = []
        for portal_type in self.tool.getAdvicePortalTypes():
            adviceWF = self.wfTool.getWorkflowsFor(portal_type.id)[0]
            adviceStates += adviceWF.states.keys()
        # remove duplicates
        adviceStates = tuple(set(adviceStates))
        for adviceState in adviceStates:
            groupIds.append('developers_%s' % adviceState)
            groupIds.append('delay__developers_%s' % adviceState)

        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.assertEquals(adapter.query,
                          {'indexAdvisers': {'query': groupIds},
                           'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchalladviseditems"
        collection = cfg.searches.searches_items.searchalladviseditems
        # by default, no advised item...
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failIf(collection.getQuery())
        # an advice can be given when an item is 'proposed'
        self.assertEquals(cfg.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers',))
        self.proposeItem(item1)
        # give an advice
        self.changeUser('pmAdviser1')
        advice = createContentInContainer(item1,
                                          'meetingadvice',
                                          **{'advice_group': self.tool.developers.getId(),
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(collection.getQuery())
        # another user will not see given advices
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failIf(collection.getQuery())
        # other advisers of the same group will also see advised items
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(collection.getQuery())
        # now create a second item and ask advice to the vendors (pmManager)
        # it will be returned for pmManager but not for pmAdviser1
        self.changeUser('pmCreator1')
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('vendors',))
        self.proposeItem(item2)
        self.changeUser('pmManager')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.tool.vendors.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(len(collection.getQuery()) == 2)
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(len(collection.getQuery()) == 1)
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failIf(collection.getQuery())

        # ask advice again to 'pmAdviser1'
        # if an advice is asked again, it stiil appears in the given advice
        # this way, if advice is asked again but no directly giveable, it is
        # still found in proposed search
        self.backToState(item1, 'itemcreated')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.proposeItem(item1)
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(len(collection.getQuery()) == 1)
        self.assertEquals(collection.getQuery()[0].UID, item1.UID())

    def test_pm_SearchAdvisedItemsWithDelay(self):
        '''Test the 'search-advised-items-with-delay' adapter.  This should return a list
           of items a user has already give a delay-aware advice for.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='advised-items-with-delay')
        # admin is not adviser
        self.assertEquals(adapter.query,
                          {'indexAdvisers': {'query': []},
                           'portal_type':  {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        adviceStates = []
        for portal_type in self.tool.getAdvicePortalTypes():
            adviceWF = self.wfTool.getWorkflowsFor(portal_type.id)[0]
            adviceStates += adviceWF.states.keys()
        # remove duplicates
        adviceStates = tuple(set(adviceStates))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.assertEquals(adapter.query,
                          {'indexAdvisers':  {'query':
                           ['delay__developers_%s' % adviceState for adviceState in adviceStates]},
                           'portal_type':  {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchalladviseditemswithdelay"
        collection = cfg.searches.searches_items.searchalladviseditemswithdelay
        # by default, no advised item...
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failIf(collection.getQuery())
        # an advice can be given when an item is 'proposed'
        self.assertEquals(cfg.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers',))
        self.proposeItem(item1)
        # give a non delay-aware advice
        self.changeUser('pmAdviser1')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.tool.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # non delay-aware advices are not found
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failIf(collection.getQuery())
        # now create a second item and ask a delay-aware advice
        self.changeUser('admin')
        originalCustomAdvisers = {'row_id': 'unique_id_123',
                                  'group': 'developers',
                                  'gives_auto_advice_on': '',
                                  'for_item_created_from': '2012/01/01',
                                  'for_item_created_until': '',
                                  'gives_auto_advice_on_help_message': '',
                                  'delay': '10',
                                  'delay_left_alert': '',
                                  'delay_label': 'Delay label', }
        cfg.setCustomAdvisers([originalCustomAdvisers, ])
        self.changeUser('pmCreator1')
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('developers__rowid__unique_id_123',))
        self.proposeItem(item2)
        self.changeUser('pmAdviser1')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failUnless(len(collection.getQuery()) == 1)
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failIf(collection.getQuery())

    def test_pm_SearchItemsInCopy(self):
        '''Test the 'search-items-in-copy' adapter.  This should return a list of items
           a user is in copy of.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))

        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-in-copy')
        # admin is just member of 'AuthenticatedUsers'
        self.assertEquals(adapter.query,
                          {'getCopyGroups': {'query': ['AuthenticatedUsers']},
                           'portal_type':  {'query': itemTypeName}})
        # as creator, query is correct
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.assertEquals(adapter.query,
                          {'getCopyGroups':  {'query': ['AuthenticatedUsers', 'developers_creators']},
                           'portal_type':  {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchallitemsincopy"
        collection = cfg.searches.searches_items.searchallitemsincopy
        # create an item and set another proposing group in copy of
        item = self.create('MeetingItem')
        # give a view access to members of vendors, like pmReviewer2
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.failIf(collection.getQuery())
        # connect as a member of 'developers_reviewers'
        self.changeUser('pmReviewer2')
        # the item is not proposed so not listed
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.failIf(collection.getQuery())
        # propose the item, it will be listed
        self.proposeItem(item)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.failUnless(collection.getQuery())

    def test_pm_SearchItemsInCopyWithAutoCopyGroups(self):
        '''Test the 'search-items-in-copy' adapter when using auto copyGroups.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))
        # configure an auto copyGroup, vendors_reviewers will be set
        # as auto copyGroup for every items
        self.tool.vendors.setAsCopyGroupOn("python: ['reviewers']")

        # this adapter is used by the "searchallitemsincopy"
        collection = cfg.searches.searches_items.searchallitemsincopy
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getAllCopyGroups(auto_real_group_ids=True),
                         ('vendors_reviewers', ))
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.failUnless(collection.getQuery())

    def test_pm_SearchMyItemsTakenOver(self):
        '''Test the 'search-my-items-taken-over' method.  This should return
           a list of items a user has taken over.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))

        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='my-items-taken-over')
        # query is correct
        self.changeUser('pmManager')
        self.assertEquals(adapter.query,
                          {'portal_type': {'query': itemTypeName},
                           'getTakenOverBy': {'query': 'pmManager'}})

        # now do the query
        # this adapter is used by the "searchmyitemstakenover"
        collection = cfg.searches.searches_items.searchmyitemstakenover
        item = self.create('MeetingItem')
        # by default nothing is returned
        self.failIf(collection.getQuery())
        # now take item over
        item.setTakenOverBy(self.member.getId())
        item.reindexObject(idxs=['getTakenOverBy', ])
        # now it is returned
        self.failUnless(collection.getQuery())
        # takenOverBy is set back to '' on each transition
        self.proposeItem(item)
        self.assertTrue(not item.getTakenOverBy())
        self.failIf(collection.getQuery())

    def test_pm_SearchItemsToValidateOfHighestHierarchicLevel(self):
        '''Test the searchItemsToValidateOfHighestHierarchicLevel method.
           This should return a list of items a user ***really*** has to validate.
           Items to validate are items for which user is a reviewer and only regarding
           his higher hierarchic level.
           So a reviewer level 1 and level 2 will only see items in level 2, a reviewer in level
           1 (only) will only see items in level 1.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-highest-hierarchic-level')
        # if user si not a reviewer, we want the search to return
        # nothing so the query uses an unknown review_state
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        # for a reviewer, query is correct
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.assertEquals(adapter.query,
                          {'getProposingGroup': {'query': ['developers']},
                           'portal_type': {'query': itemTypeName},
                           'review_state': {'query': self.WF_STATE_NAME_MAPPINGS['proposed']}})

        # activate 'prevalidation' if necessary
        if 'prereviewers' in MEETINGREVIEWERS and \
           not 'pre_validation' in cfg.getWorkflowAdaptations():
            cfg.setWorkflowAdaptations('pre_validation')
            performWorkflowAdaptations(cfg, logger=pm_logger)
        # now do the query
        # this adapter is used by the "searchitemstovalidate"
        collection = cfg.searches.searches_items.searchitemstovalidate
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # jump to first level of validation
        self.do(item, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.getQuery())
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failUnless(collection.getQuery())
        # now as 'pmReviewerLevel2', the item should not be returned
        # as he only see items of his highest hierarchic level
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.getQuery())
        # pass the item to second last level of hierarchy, where 'pmReviewerLevel2' is reviewer for
        self.changeUser('pmReviewerLevel1')
        # jump to last level of validation
        self.proposeItem(item)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.getQuery())
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failUnless(collection.getQuery())

        # now give a view on the item by 'pmReviewer2' and check if, as a reviewer,
        # the search does returns him the item, it should not as he is just a reviewer
        # but not able to really validate the new item
        cfg.setUseCopies(True)
        review_states = MEETINGREVIEWERS[MEETINGREVIEWERS.keys()[0]]
        if 'prereviewers' in MEETINGREVIEWERS:
            review_states = ('prevalidated',)
        cfg.setItemCopyGroupsStates(review_states)
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        self.changeUser('pmReviewer2')
        # the user can see the item
        self.failUnless(self.hasPermission('View', item))
        # but the search will not return it
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.getQuery())
        # if the item is validated, it will not appear for pmReviewer1 anymore
        self.changeUser('pmReviewer1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failUnless(collection.getQuery())
        self.validateItem(item)
        self.failIf(collection.getQuery())

    def test_pm_SearchItemsToValidateOfMyReviewerGroups(self):
        '''Test the 'items-to-validate-of-my-reviewer-groups' adapter.
           This should return a list of items a user could validate at any level,
           so not only his highest hierarchic level.  This will return finally every items
           corresponding to Plone reviewer groups the user is in.'''
        cfg = self.meetingConfig
        self.changeUser('admin')
        # activate the 'pre_validation' wfAdaptation if it exists in current profile...
        # if not, then MEETINGREVIEWERS must be at least 2 elements long
        if not len(MEETINGREVIEWERS) > 1:
            pm_logger.info("Could not launch test 'test_pm_SearchItemsToValidateOfMyReviewerGroups' because "
                           "we need at least 2 levels of item validation.")
        if 'pre_validation' in cfg.listWorkflowAdaptations():
            cfg.setWorkflowAdaptations('pre_validation')
            performWorkflowAdaptations(cfg, logger=pm_logger)

        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-my-reviewer-groups')
        # if user si not a reviewer, we want the search to return
        # nothing so the query uses an unknown review_state
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        # for a reviewer, query is correct
        self.changeUser('pmManager')
        # keep relevant reviewer states
        res = []
        for grp in self.member.getGroups():
            for reviewer_suffix, reviewer_state in MEETINGREVIEWERS.items():
                if grp.endswith('_' + reviewer_suffix):
                    if reviewer_suffix == 'reviewers' and 'pre_validation' in cfg.listWorkflowAdaptations():
                        res.append('prevalidated')
                    else:
                        res.append(reviewer_state)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.assertEquals(adapter.query,
                          {'portal_type': {'query': itemTypeName},
                           'reviewProcessInfo': {'query': ['developers__reviewprocess__%s' % st for st in res]}})

        # now do the query
        # this adapter is not used by default, but is intended to be used with
        # the "searchitemstovalidate" collection so use it with it
        collection = cfg.searches.searches_items.searchitemstovalidate
        patchedQuery = list(collection.query)
        patchedQuery[0]['v'] = 'items-to-validate-of-my-reviewer-groups'
        collection.query = patchedQuery

        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failIf(collection.getQuery())
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failUnless(len(collection.getQuery()) == 2)
        # as second level user, he will not see items of first level also
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failIf(collection.getQuery())

        # define 'pmReviewerLevel2' as a prereviewer (first validation level reviewer)
        self._turnUserIntoPrereviewer(self.member)
        # change again to 'pmReviewerLevel2' so changes in his groups are taken into account
        self.changeUser('pmReviewerLevel2')
        # he can access first validation level items
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failUnless(len(collection.getQuery()) == 2)
        # move item1 to last validation level
        self.proposeItem(item1)
        # both items still returned by the search for 'pmReviewerLevel2'
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failUnless(len(collection.getQuery()) == 2)
        # but now, the search only returns item2 to 'pmReviewerLevel1'
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failUnless(len(collection.getQuery()) == 1)
        self.failUnless(collection.getQuery()[0].UID == item2.UID())

    def runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest(self):
        '''
          Helper method for activating the test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels
          test when called from a subplugin.
        '''
        return False

    def test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels(self):
        '''Test the searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels method.
           This will return items to validate of his highest hierarchic level and every levels
           under, even if user is not in the corresponding Plone reviewer groups.'''
        cfg = self.meetingConfig
        # by default we use the 'pre_validation_keep_reviewer_permissions' to check
        # this, but if a subplugin has the right workflow behaviour, this can works also
        # so if we have 'pre_validation_keep_reviewer_permissions' apply it, either,
        # check if self.runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest() is True
        if not 'pre_validation_keep_reviewer_permissions' in cfg.listWorkflowAdaptations() and \
           not self.runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest():
            pm_logger.info("Could not launch test 'test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels' "
                           "because we need a correctly configured workflow.")
            return
        if 'pre_validation_keep_reviewer_permissions' in cfg.listWorkflowAdaptations():
            cfg.setWorkflowAdaptations(('pre_validation_keep_reviewer_permissions', ))
            performWorkflowAdaptations(cfg, logger=pm_logger)
        itemTypeName = cfg.getItemTypeName()
        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-every-reviewer-levels-and-lower-levels')
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        # now do the query
        # this adapter is not used by default, but is intended to be used with
        # the "searchitemstovalidate" collection so use it with it
        collection = cfg.searches.searches_items.searchitemstovalidate
        patchedQuery = list(collection.query)
        patchedQuery[0]['v'] = 'items-to-validate-of-every-reviewer-levels-and-lower-levels'
        collection.query = patchedQuery
        self.failIf(collection.getQuery())
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        # find state to use for current reviewer
        reviewer_state = MEETINGREVIEWERS[cfg._highestReviewerLevel(self.member.getGroups())]
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.assertEquals(adapter.query,
                          {'portal_type': {'query': itemTypeName},
                           'reviewProcessInfo': {'query': ['developers__reviewprocess__%s' % reviewer_state]}})

        self.failUnless(len(collection.getQuery()) == 2)
        # as second level user, he will also see items because items are from lower reviewer levels
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.failUnless(len(collection.getQuery()) == 2)

        # now propose item1, both items are still viewable to 'pmReviewerLevel2', but 'pmReviewerLevel1'
        # will only see item of 'his' highest hierarchic level
        self.proposeItem(item1)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.failUnless(len(collection.getQuery()) == 2)
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.failUnless(len(collection.getQuery()) == 1)
        self.failUnless(collection.getQuery()[0].UID == item2.UID())

    def test_pm_SearchItemsToCorrect(self):
        '''Test the 'items-to-correct' CompoundCriterion adapter.  This should return
           a list of items in state 'returned_to_proposing_group' the current user is able to edit.'''
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        if not 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            pm_logger.info("Bypassing test test_pm_SearchItemsToCorrect because it "
                           "needs the 'return_to_proposing_group' wfAdaptation.")
            return

        itemTypeName = cfg.getItemTypeName()
        self.changeUser('siteadmin')
        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-correct')
        # wfAdaptation 'return_to_proposing_group' is not enabled
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if not 'return_to_proposing_group' in wfAdaptations:
            wfAdaptations.append('return_to_proposing_group')
        cfg.setWorkflowAdaptations(wfAdaptations)
        performWorkflowAdaptations(cfg, logger=pm_logger)

        # normally this search is not available to users that are not able to correct items
        # nevertheless, if a user is in not able to edit items to correct, the special
        # query 'return nothing' is returned
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')

        self.assertEquals(adapter.query, {
                          'portal_type': {'query': itemTypeName},
                          'reviewProcessInfo': {'query': ['developers__reviewprocess__returned_to_proposing_group']}})

        # it returns only items the current user is able to correct
        # create an item for developers and one for vendors and 'return' it to proposingGroup
        self.create('Meeting', date=DateTime())
        developersItem = self.create('MeetingItem')
        self.assertEquals(developersItem.getProposingGroup(), 'developers')
        self.presentItem(developersItem)
        self.changeUser('pmCreator2')
        vendorsItem = self.create('MeetingItem')
        self.assertEquals(vendorsItem.getProposingGroup(), 'vendors')
        self.changeUser('pmManager')
        self.presentItem(vendorsItem)
        collection = cfg.searches.searches_items.searchitemstocorrect
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        self.failIf(collection.getQuery())
        self.do(developersItem, 'return_to_proposing_group')
        self.do(vendorsItem, 'return_to_proposing_group')

        # pmManager may only edit developersItem
        self.assertTrue(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        res = collection.getQuery()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == developersItem.UID())

        # pmCreator2 may only edit vendorsItem
        self.changeUser('pmCreator2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        res = collection.getQuery()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == vendorsItem.UID())

    def test_pm_SearchItemsToCorrectToValidateHighestHierarchicLevel(self):
        '''Test the 'items-to-correct-to-validate-of-highest-hierarchic-level'
           CompoundCriterion adapter. This should return a list of items in state
           'returned_to_proposing_group_proposed' the current user is able to edit.'''
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        if not 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            pm_logger.info(
                "Bypassing test test_pm_SearchItemsToCorrectToValidateHighestHierarchicLevel because it "
                "needs the 'return_to_proposing_group_with_last_validation' wfAdaptation.")
            return

        itemTypeName = cfg.getItemTypeName()
        self.changeUser('siteadmin')
        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-correct-to-validate-of-highest-hierarchic-level')
        # wfAdaptation 'return_to_proposing_group_with_last_validation' is not enabled
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if not 'return_to_proposing_group_with_last_validation' in wfAdaptations:
            wfAdaptations.append('return_to_proposing_group_with_last_validation')
        # desactivate simple return to proposing group wf
        if 'return_to_proposing_group' in wfAdaptations:
            wfAdaptations.remove('return_to_proposing_group')
        cfg.setWorkflowAdaptations(wfAdaptations)
        performWorkflowAdaptations(cfg, logger=pm_logger)

        # normally this search is not available to users that are not able to review items
        # nevertheless, if a user is in not able to edit items to correct in proposed, the special
        # query 'return nothing' is returned
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        self.assertEquals(adapter.query, {
            'getProposingGroup': {'query': ['developers']},
            'portal_type': {'query': itemTypeName},
            'review_state': {'query': 'returned_to_proposing_group_proposed'}})

        # it returns only items the current user is able to correct
        # create an item for developers and one for vendors and 'return' it to proposingGroup
        self.create('Meeting', date=DateTime())
        developersItem = self.create('MeetingItem')
        self.assertEquals(developersItem.getProposingGroup(), 'developers')
        self.presentItem(developersItem)
        self.changeUser('pmCreator2')
        vendorsItem = self.create('MeetingItem')
        self.assertEquals(vendorsItem.getProposingGroup(), 'vendors')
        self.changeUser('pmManager')
        self.presentItem(vendorsItem)
        collection = cfg.searches.searches_items.searchitemstocorrecttovalidate
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        self.failIf(collection.getQuery())
        self.do(developersItem, 'return_to_proposing_group')
        self.do(vendorsItem, 'return_to_proposing_group')

        self.changeUser('pmCreator1')
        self.do(developersItem, 'goTo_returned_to_proposing_group_proposed')
        self.changeUser('pmCreator2')
        self.do(vendorsItem, 'goTo_returned_to_proposing_group_proposed')
        self.changeUser('pmManager')

        # pmManager may only edit developersItem
        self.assertTrue(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        res = collection.getQuery()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == developersItem.UID())

        # pmCreator2 can't edit vendorsItem
        self.changeUser('pmCreator2')
        self.assertTrue(not self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        res = collection.getQuery()
        self.failUnless(len(res) == 0)

        # pmReviewer2 may only edit vendorsItem
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        res = collection.getQuery()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == vendorsItem.UID())

    def test_pm_SearchItemsToCorrectToValidateOfEveryReviewerGroups(self):
        '''Test the 'items-to-correct-to-validate-of-every-reviewer-groups'
           CompoundCriterion adapter.  This should return a list of items in state
           'returned_to_proposing_group_proposed' the current user is able to edit.'''
        # specify that copyGroups can see the item when it is proposed or prevalidated
        cfg = self.meetingConfig
        if not 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            pm_logger.info(
                "Bypassing test test_pm_SearchItemsToCorrectToValidateOfEveryReviewerGroups because it "
                "needs the 'return_to_proposing_group_with_all_validations' wfAdaptation.")
            return

        itemTypeName = cfg.getItemTypeName()

        self.changeUser('siteadmin')
        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-correct-to-validate-of-every-reviewer-groups')
        # wfAdaptation 'return_to_proposing_group_with_last_validation' is not enabled
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if not 'pre_validation' in wfAdaptations:
            wfAdaptations.append('pre_validation')
        if not 'return_to_proposing_group_with_all_validations' in wfAdaptations:
            wfAdaptations.append('return_to_proposing_group_with_all_validations')
        # desactivate simple return to proposing group wf
        if 'return_to_proposing_group' in wfAdaptations:
            wfAdaptations.remove('return_to_proposing_group')
        cfg.setWorkflowAdaptations(wfAdaptations)
        performWorkflowAdaptations(cfg, logger=pm_logger)

        # normally this search is not available to users that are not able to review items
        # nevertheless, if a user is in not able to edit items to correct in proposed, the special
        # query 'return nothing' is returned
        self.assertEquals(adapter.query,
                          {'review_state': {'query': ['unknown_review_state']}})
        self.changeUser('pmManager')
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        self.assertEquals(adapter.query, {
            'portal_type': {'query': itemTypeName},
            'reviewProcessInfo':
            {'query': ['developers__reviewprocess__returned_to_proposing_group_prevalidated',
                       'developers__reviewprocess__returned_to_proposing_group_proposed']}})

        # it returns only items the current user is able to correct
        # create an item for developers and one for vendors and 'return' it to proposingGroup
        self.create('Meeting', date=DateTime())
        developersItem = self.create('MeetingItem')
        self.assertEquals(developersItem.getProposingGroup(), 'developers')
        self.changeUser('pmCreator2')
        vendorsItem = self.create('MeetingItem')
        self.assertEquals(vendorsItem.getProposingGroup(), 'vendors')
        self.changeUser('admin')
        # presenting item :
        for tr in ('propose', 'prevalidate', 'validate', 'present'):
            self.do(developersItem, tr)
            self.do(vendorsItem, tr)
        self.changeUser('pmManager')
        collection = cfg.searches.searches_items.searchitemstocorrecttovalidateoffeveryreviewergroups
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        self.failIf(collection.getQuery())

        self.do(developersItem, 'return_to_proposing_group')
        self.do(vendorsItem, 'return_to_proposing_group')

        self.changeUser('pmCreator1')
        self.do(developersItem, 'goTo_returned_to_proposing_group_proposed')
        self.changeUser('pmCreator2')
        self.do(vendorsItem, 'goTo_returned_to_proposing_group_proposed')

        self.changeUser('pmCreator1')
        # pmManager can't edit developersItem
        self.assertTrue(not self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        res = collection.getQuery()
        self.failUnless(len(res) == 0)

        # pmCreator2 can't edit vendorsItem
        self.changeUser('pmCreator2')
        self.assertTrue(not self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        res = collection.getQuery()
        self.failUnless(len(res) == 0)

        self.changeUser('admin')
        self.do(developersItem, 'goTo_returned_to_proposing_group_prevalidated')
        self.do(vendorsItem, 'goTo_returned_to_proposing_group_prevalidated')

        # pmReviewer1 may only edit developersItem
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        res = collection.getQuery()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == developersItem.UID())

        # pmReviewer2 may only edit vendorsItem
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        res = collection.getQuery()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == vendorsItem.UID())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSearches, prefix='test_pm_'))
    return suite
