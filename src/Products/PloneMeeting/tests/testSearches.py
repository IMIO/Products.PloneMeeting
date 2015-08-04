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

import logging

from zope.component import getAdapter
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from eea.facetednavigation.interfaces import ICriteria
from collective.compoundcriterion.interfaces import ICompoundCriterionFilter
from collective.eeafaceted.collectionwidget.widgets.widget import CollectionWidget

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations


class testSearches(PloneMeetingTestCase):
    '''Tests the adapters used for searches.'''

    def test_pm_DefaultSelectedSearch(self):
        '''Test that the 'meetingAppDefaultView' defined in the MeetingConfig data
           is correctly applied to the collection-link widget on the facetednavigation view.'''
        # selected meetingAppDefaultView is 'searchallitems'
        searchallitems = self.meetingConfig.searches.searches_items.searchallitems
        for criterion in ICriteria(self.meetingConfig.searches).values():
            if criterion.widget == CollectionWidget.widget_type:
                collectionCriterion = criterion
                break
        self.assertEquals(collectionCriterion.default, searchallitems.UID())

    def test_pm_SearchItemsToAdviceAdapter(self):
        '''Test the 'search-items-to-advice' adapter that should return a list of items
           a user has to give an advice for.'''
        self.changeUser('admin')
        self.meetingConfig.setUsedAdviceTypes(self.meetingConfig.getUsedAdviceTypes() + ('asked_again', ))
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'delay': '5', }, ])
        itemTypeName = self.meetingConfig.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='items-to-advice')
        # admin is not adviser
        self.assertEquals(adapter.query,
                          {'indexAdvisers': [],
                           'portal_type': itemTypeName})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        self.assertEquals(adapter.query,
                          {'indexAdvisers': ['developers_advice_not_given',
                                             'delay__developers_advice_not_given',
                                             'developers_advice_asked_again',
                                             'delay__developers_advice_asked_again'],
                           'portal_type': itemTypeName})

        # now do the query
        # this adapter is used by the "searchallitemstoadvice"
        collection = self.meetingConfig.searches.searches_items.searchallitemstoadvice
        # by default, no item to advice...
        self.failIf(collection.getQuery())
        # an advice can be given when an item is 'proposed'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', 'vendors__rowid__unique_id_123'))
        # as the item is "itemcreated", advices are not givable
        self.changeUser('pmAdviser1')
        self.failIf(collection.getQuery())
        # now propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        # only advisers can give an advice, so a creator for example will not see it
        self.failIf(collection.getQuery())
        # now test as advisers
        self.changeUser('pmAdviser1')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmAdviser1 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.tool.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.failIf(collection.getQuery())
        # pmReviewer2 is adviser for 'vendors', delay-aware advices are also returned
        self.changeUser('pmReviewer2')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmReviewer2 gives his advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.tool.vendors.getId(),
                                             'advice_type': u'negative',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.failIf(collection.getQuery())

        # ask advice again, it will appear to 'pmReviewer2' in the query
        self.backToState(item, 'itemcreated')
        self.changeUser('pmCreator1')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.assertEquals(len(collection.getQuery()), 1)
        self.assertEquals(collection.getQuery()[0].UID, item.UID())

    def test_pm_SearchAdvisedItems(self):
        '''Test the 'search-advised-items' adapter.  This should return a list of items
           a user has already give an advice for.'''
        self.changeUser('admin')
        itemTypeName = self.meetingConfig.getItemTypeName()
        self.meetingConfig.setUsedAdviceTypes(self.meetingConfig.getUsedAdviceTypes() + ('asked_again', ))

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='advised-items')
        # admin is not adviser
        self.assertEquals(adapter.query,
                          {'indexAdvisers': [],
                           'portal_type': itemTypeName})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        adviceWF = self.wfTool.getWorkflowsFor('meetingadvice')[0]
        adviceStates = adviceWF.states.keys()
        groupIds = []
        for adviceState in adviceStates:
            groupIds.append('developers_%s' % adviceState)
            groupIds.append('delay__developers_%s' % adviceState)
        import ipdb; ipdb.set_trace()
        self.assertEquals(adapter.query,
                          {'indexAdvisers': groupIds,
                           'portal_type': itemTypeName})

        # now do the query
        # this adapter is used by the "searchalladviseditems"
        collection = self.meetingConfig.searches.searches_items.searchalladviseditems
        # by default, no advised item...
        self.changeUser('pmAdviser1')
        self.failIf(collection.getQuery())
        # an advice can be given when an item is 'proposed'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
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
                                          **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.failUnless(collection.getQuery())
        # another user will not see given advices
        self.changeUser('pmCreator1')
        self.failIf(collection.getQuery())
        # other advisers of the same group will also see advised items
        self.changeUser('pmManager')
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
                                 **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        self.failUnless(len(collection.getQuery()) == 2)
        self.changeUser('pmAdviser1')
        self.failUnless(len(collection.getQuery()) == 1)
        self.changeUser('pmCreator1')
        self.failIf(collection.getQuery())

        # ask advice again to 'pmAdviser1'
        # if an advice is asked again, it is no more considered given
        self.backToState(item1, 'itemcreated')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.proposeItem(item1)
        self.changeUser('pmAdviser1')
        self.failIf(collection.getQuery())

    def test_pm_SearchAdvisedItemsWithDelay(self):
        '''Test the 'search-advised-items-with-delay' adapter.  This should return a list
           of items a user has already give a delay-aware advice for.'''
        self.changeUser('admin')
        itemTypeName = self.meetingConfig.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='advised-items-with-delay')
        # admin is not adviser
        self.assertEquals(adapter.query,
                          {'indexAdvisers': [],
                           'portal_type': itemTypeName})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        self.assertEquals(adapter.query,
                          {'indexAdvisers': ['delay__developers_advice_given',
                                             'delay__developers_advice_under_edit'],
                           'portal_type': itemTypeName})

        # now do the query
        # this adapter is used by the "searchalladviseditemswithdelay"
        collection = self.meetingConfig.searches.searches_items.searchalladviseditemswithdelay
        # by default, no advised item...
        self.changeUser('pmAdviser1')
        self.failIf(collection.getQuery())
        # an advice can be given when an item is 'proposed'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
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
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # non delay-aware advices are not found
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
        self.meetingConfig.setCustomAdvisers([originalCustomAdvisers, ])
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
        self.failUnless(len(collection.getQuery()) == 1)
        self.changeUser('pmCreator1')
        self.failIf(collection.getQuery())

    def test_pm_SearchItemsInCopy(self):
        '''Test the 'search-items-in-copy' adapter.  This should return a list of items
           a user is in copy of.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))

        itemTypeName = self.meetingConfig.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='items-in-copy')
        # admin is just member of 'AuthenticatedUsers'
        self.assertEquals(adapter.query,
                          {'getCopyGroups': ['AuthenticatedUsers'],
                           'portal_type': itemTypeName})
        # as creator, query is correct
        self.changeUser('pmCreator1')
        self.assertEquals(adapter.query,
                          {'getCopyGroups': ['AuthenticatedUsers', 'developers_creators'],
                           'portal_type': itemTypeName})

        # now do the query
        # this adapter is used by the "searchallitemsincopy"
        collection = self.meetingConfig.searches.searches_items.searchallitemsincopy
        # create an item and set another proposing group in copy of
        item = self.create('MeetingItem')
        # give a view access to members of vendors, like pmReviewer2
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        self.failIf(collection.getQuery())
        # connect as a member of 'developers_reviewers'
        self.changeUser('pmReviewer2')
        # the item is not proposed so not listed
        self.failIf(collection.getQuery())
        # propose the item, it will be listed
        self.proposeItem(item)
        self.failUnless(collection.getQuery())

    def test_pm_SearchMyItemsTakenOver(self):
        '''Test the 'search-my-items-taken-over' method.  This should return
           a list of items a user has taken over.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))

        itemTypeName = self.meetingConfig.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='my-items-taken-over')
        # query is correct
        self.changeUser('pmManager')
        self.assertEquals(adapter.query,
                          {'portal_type': itemTypeName,
                           'getTakenOverBy': 'pmManager'})

        # now do the query
        # this adapter is used by the "searchmyitemstakenover"
        collection = self.meetingConfig.searches.searches_items.searchmyitemstakenover
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
        itemTypeName = self.meetingConfig.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-highest-hierarchic-level')
        # if user si not a reviewer, we want the search to return
        # nothing so the query uses an unknown review_state
        self.assertEquals(adapter.query,
                          {'review_state': ['unknown_review_state']})
        # for a reviewer, query is correct
        self.changeUser('pmManager')
        self.assertEquals(adapter.query,
                          {'getProposingGroup': ['developers'],
                           'portal_type': itemTypeName,
                           'review_state': self.WF_STATE_NAME_MAPPINGS['proposed']})

        # activate 'prevalidation' if necessary
        if 'prereviewers' in MEETINGREVIEWERS:
            self.meetingConfig.setWorkflowAdaptations('pre_validation')
            logger = logging.getLogger('PloneMeeting: testing')
            performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        # now do the query
        # this adapter is used by the "searchitemstovalidate"
        collection = self.meetingConfig.searches.searches_items.searchitemstovalidate
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # jump to first level of validation
        self.do(item, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.failIf(collection.getQuery())
        self.changeUser('pmReviewerLevel1')
        self.failUnless(collection.getQuery())
        # now as 'pmReviewerLevel2', the item should not be returned
        # as he only see items of his highest hierarchic level
        self.changeUser('pmReviewerLevel2')
        self.failIf(collection.getQuery())
        # pass the item to second last level of hierarchy, where 'pmReviewerLevel2' is reviewer for
        self.changeUser('pmReviewerLevel1')
        # jump to last level of validation
        self.proposeItem(item)
        self.failIf(collection.getQuery())
        self.changeUser('pmReviewerLevel2')
        self.failUnless(collection.getQuery())

        # now give a view on the item by 'pmReviewer2' and check if, as a reviewer,
        # the search does returns him the item, it should not as he is just a reviewer
        # but not able to really validate the new item
        self.meetingConfig.setUseCopies(True)
        review_states = MEETINGREVIEWERS[MEETINGREVIEWERS.keys()[0]]
        if 'prereviewers' in MEETINGREVIEWERS:
            review_states = ('prevalidated',)
        self.meetingConfig.setItemCopyGroupsStates(review_states)
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        self.changeUser('pmReviewer2')
        # the user can see the item
        self.failUnless(self.hasPermission('View', item))
        # but the search will not return it
        self.failIf(collection.getQuery())
        # if the item is validated, it will not appear for pmReviewer1 anymore
        self.changeUser('pmReviewer1')
        self.failUnless(collection.getQuery())
        self.validateItem(item)
        self.failIf(collection.getQuery())

    def test_pm_SearchItemsToValidateOfMyReviewerGroups(self):
        '''Test the 'items-to-validate-of-my-reviewer-groups' adapter.
           This should return a list of items a user could validate at any level,
           so not only his highest hierarchic level.  This will return finally every items
           corresponding to Plone reviewer groups the user is in.'''
        self.changeUser('admin')
        logger = logging.getLogger('PloneMeeting: testing')
        # activate the 'pre_validation' wfAdaptation if it exists in current profile...
        # if not, then MEETINGREVIEWERS must be at least 2 elements long
        if not len(MEETINGREVIEWERS) > 1:
            logger.info("Could not launch test 'test_pm_SearchItemsToValidateOfMyReviewerGroups' because "
                        "we need at least 2 levels of item validation.")
        if 'pre_validation' in self.meetingConfig.listWorkflowAdaptations():
            self.meetingConfig.setWorkflowAdaptations('pre_validation')
            logger = logging.getLogger('PloneMeeting: testing')
            performWorkflowAdaptations(self.portal, self.meetingConfig, logger)

        itemTypeName = self.meetingConfig.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-my-reviewer-groups')
        # if user si not a reviewer, we want the search to return
        # nothing so the query uses an unknown review_state
        self.assertEquals(adapter.query,
                          {'review_state': ['unknown_review_state']})
        # for a reviewer, query is correct
        self.changeUser('pmManager')
        self.assertEquals(adapter.query,
                          {'portal_type': itemTypeName,
                           'reviewProcessInfo': ['developers__reviewprocess__prevalidated']})

        # now do the query
        # this adapter is not used by default, but is intended to be used with
        # the "searchitemstovalidate" collection so use it with it
        collection = self.meetingConfig.searches.searches_items.searchitemstovalidate
        patchedQuery = list(collection.query)
        patchedQuery[0]['v'] = 'items-to-validate-of-my-reviewer-groups'
        collection.query = patchedQuery

        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.failIf(collection.getQuery())
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        self.failUnless(len(collection.getQuery()) == 2)
        # as second level user, he will not see items of first level also
        self.changeUser('pmReviewerLevel2')
        self.failIf(collection.getQuery())

        # define 'pmReviewerLevel2' as a prereviewer (first validation level reviewer)
        self._turnUserIntoPrereviewer(self.member)
        # change again to 'pmReviewerLevel2' so changes in his groups are taken into account
        self.changeUser('pmReviewerLevel2')
        # he can access first validation level items
        self.failUnless(len(collection.getQuery()) == 2)
        # move item1 to last validation level
        self.proposeItem(item1)
        # both items still returned by the search for 'pmReviewerLevel2'
        self.failUnless(len(collection.getQuery()) == 2)
        # but now, the search only returns item2 to 'pmReviewerLevel1'
        self.changeUser('pmReviewerLevel1')
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
        logger = logging.getLogger('PloneMeeting: testing')
        # by default we use the 'pre_validation_keep_reviewer_permissions' to check
        # this, but if a subplugin has the right workflow behaviour, this can works also
        # so if we have 'pre_validation_keep_reviewer_permissions' apply it, either,
        # check if self.runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest() is True
        if not 'pre_validation_keep_reviewer_permissions' and not \
           self.runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest():
            logger.info("Could not launch test 'test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels'"
                        "because we need a correctly configured workflow.")
        if 'pre_validation_keep_reviewer_permissions' in self.meetingConfig.listWorkflowAdaptations():
            self.meetingConfig.setWorkflowAdaptations(('pre_validation_keep_reviewer_permissions', ))
            logger = logging.getLogger('PloneMeeting: testing')
            performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        itemTypeName = self.meetingConfig.getItemTypeName()
        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        adapter = getAdapter(self.meetingConfig,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-every-reviewer-levels-and-lower-levels')
        self.assertEquals(adapter.query,
                          {'review_state': ['unknown_review_state']})
        # now do the query
        # this adapter is not used by default, but is intended to be used with
        # the "searchitemstovalidate" collection so use it with it
        collection = self.meetingConfig.searches.searches_items.searchitemstovalidate
        patchedQuery = list(collection.query)
        patchedQuery[0]['v'] = 'items-to-validate-of-every-reviewer-levels-and-lower-levels'
        collection.query = patchedQuery
        self.failIf(collection.getQuery())
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        self.assertEquals(adapter.query,
                          {'portal_type': itemTypeName,
                           'reviewProcessInfo': ['developers__reviewprocess__proposed']})

        self.failUnless(len(collection.getQuery()) == 2)
        # as second level user, he will also see items because items are from lower reviewer levels
        self.changeUser('pmReviewerLevel2')
        self.failUnless(len(collection.getQuery()) == 2)

        # now propose item1, both items are still viewable to 'pmReviewerLevel2', but 'pmReviewerLevel1'
        # will only see item of 'his' highest hierarchic level
        self.proposeItem(item1)
        self.failUnless(len(collection.getQuery()) == 2)
        self.changeUser('pmReviewerLevel1')
        self.failUnless(len(collection.getQuery()) == 1)
        self.failUnless(collection.getQuery()[0].UID == item2.UID())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSearches, prefix='test_pm_'))
    return suite
