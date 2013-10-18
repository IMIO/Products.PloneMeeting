# -*- coding: utf-8 -*-
#
# File: testMeetingConfig.py
#
# Copyright (c) 2007-2013 by Imio.be
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
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.config import TOPIC_SEARCH_FILTERS
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations


class testMeetingConfig(PloneMeetingTestCase):
    '''Tests the MeetingConfig class methods.'''

    def test_pm_searchItemsToAdvice(self):
        '''Test the searchItemsToAdvice method.  This should return a list of items
           a user has to give an advice for.'''
        self.setMeetingConfig(self.meetingConfig2.getId())
        # by default, no item to advice...
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # an advice can be given when an item is 'proposed' or 'validated'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated'))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers',))
        # as the item is "itemcreated", advices are not givable
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # now propose the item
        self.proposeItem(item)
        item.reindexObject()
        # only advisers can give an advice, so a creator for example will not see it
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 1)
        self.assertEquals(self.meetingConfig.searchItemsToAdvice('', '', '', '')[0].UID, item.UID())
        # when an advice on an item is given, the item is noe more returned by searchItemsToAdvice
        # so pmAdviser1 gives his advice
        item.editAdvice(group=self.portal.portal_plonemeeting.developers,
                        adviceType='positive',
                        comment='My comment')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))

    def test_pm_searchAdvisedItems(self):
        '''Test the searchAdvisedItems method.  This should return a list of items
           a user has already give an advice for.'''
        self.setMeetingConfig(self.meetingConfig2.getId())
        # by default, no advices item...
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # an advice can be given when an item is 'proposed' or 'validated'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated'))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers',))
        self.proposeItem(item1)
        item1.reindexObject()
        # give an advice
        self.changeUser('pmAdviser1')
        item1.editAdvice(group=self.portal.portal_plonemeeting.developers,
                         adviceType='positive',
                         comment='My comment')
        self.failUnless(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # another user will not see given advices
        self.changeUser('pmCreator1')
        self.failIf(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # other advisers of the same group will also see advised items
        self.changeUser('pmManager')
        self.failUnless(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # now create a second item and ask advice to the vendors (pmManager)
        # it will be returned for pmManager but not for pmAdviser1
        self.changeUser('pmCreator1')
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('vendors',))
        self.proposeItem(item2)
        item2.reindexObject()
        self.changeUser('pmManager')
        item2.editAdvice(group=self.portal.portal_plonemeeting.vendors,
                         adviceType='positive',
                         comment='My comment')
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 2)
        self.changeUser('pmAdviser1')
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 1)
        self.changeUser('pmCreator1')
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 0)

    def test_pm_searchItemsInCopy(self):
        '''Test the searchItemsInCopy method.  This should return a list of items
           a user is in copy of.'''
        # specify that copyGroups can see the item when it is proposed
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))
        # create an item and set another proposing group in copy of
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # give a view access to members of vendors, like pmReviewer2
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        self.failIf(self.meetingConfig.searchItemsInCopy('', '', '', ''))
        # connect as a member of 'developers_reviewers'
        self.changeUser('pmReviewer2')
        # the item is not proposed so not listed
        self.failIf(self.meetingConfig.searchItemsInCopy('', '', '', ''))
        # propose the item, it will be listed
        self.proposeItem(item)
        item.reindexObject()
        self.failUnless(self.meetingConfig.searchItemsInCopy('', '', '', ''))

    def test_pm_searchItemsToValidate(self):
        '''Test the searchItemsToValidate method.  This should return a list of items
           a user ***really*** has to validate.
           Items to validate are items in state 'proposed' or 'prevalidated' if wfAdaptation
           'pre_validation' is used, and for wich current user is really reviewer.'''
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.failIf(self.meetingConfig.searchItemsToValidate('', '', '', ''))
        self.changeUser('pmReviewer1')
        self.failUnless(self.meetingConfig.searchItemsToValidate('', '', '', ''))
        # now give a view on the item by 'pmReviewer2' and check if, as a reviewer,
        # the search does returns him the item, it should not as he is just a reviewer
        # but not able to really validate the new item
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('proposed', ))
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        self.changeUser('pmReviewer2')
        # the user can see the item
        self.failUnless(self.hasPermission('View', item))
        # but the search will not return it
        self.failIf(self.meetingConfig.searchItemsToValidate('', '', '', ''))
        # if the item is validated, it will not appear for pmReviewer1 anymore
        self.changeUser('pmReviewer1')
        self.failUnless(self.meetingConfig.searchItemsToValidate('', '', '', ''))
        self.validateItem(item)
        self.failIf(self.meetingConfig.searchItemsToValidate('', '', '', ''))

    def test_pm_searchItemsToPrevalidate(self):
        '''Test the searchItemsToPrevalidate method.  This should return a list of items
           a user ***really*** has to prevalidate.
           Items to prevalidate are items in state 'proposed' when wfAdaptation
           'pre_validation' is active, and for wich current user is really reviewer.'''
        # activate the 'pre_validation' wfAdaptation
        self.meetingConfig.setWorkflowAdaptations('pre_validation')
        logger = logging.getLogger('PloneMeeting: testing')
        performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.failIf(self.meetingConfig.searchItemsToPrevalidate('', '', '', ''))
        self.changeUser('pmReviewer1')
        # define pmReviewer1 as a prereviewer
        self._turnUserIntoPrereviewer(self.portal.portal_membership.getAuthenticatedMember())
        # change again to 'pmReviewer1' so changes in his groups are taken into account
        self.changeUser('pmReviewer1')
        # the next available transition is 'prevalidate'
        self.failUnless('prevalidate' in self.transitions(item))
        self.failUnless(self.meetingConfig.searchItemsToPrevalidate('', '', '', ''))
        # now give a view on the item by 'pmReviewer2' and check if, as a reviewer,
        # the search does returns him the item, it should not as he is just a reviewer
        # but not able to really validate the new item
        self.meetingConfig.setUseCopies(True)
        self.meetingConfig.setItemCopyGroupsStates(('proposed', ))
        item.setCopyGroups(('vendors_reviewers',))
        item.at_post_edit_script()
        self.changeUser('pmReviewer2')
        # the user can see the item
        self.failUnless(self.hasPermission('View', item))
        # but the search will not return it
        self.failIf(self.meetingConfig.searchItemsToPrevalidate('', '', '', ''))
        # if the item is prevalidated, it will not appear for pmReviewer1 anymore
        self.changeUser('pmReviewer1')
        self.failUnless(self.meetingConfig.searchItemsToPrevalidate('', '', '', ''))
        self.prevalidateItem(item)
        self.failIf(self.meetingConfig.searchItemsToPrevalidate('', '', '', ''))

    def test_pm_searchItemsWithFilters(self):
        '''Test the searchItemsWithFilters method.  This should return a list of items
           depending on the 'topic_search_script' property defined values.'''
        # while a 'topic_search_filters' if defined on the relevant topic, it is passed
        # as kwargs to searchItemsWithFilters, so do the same here
        # the 'query' will restrict list of brains to be treated
        # by filters defined in 'filters'.  The filters are applied with a 'OR', so, if one of
        # the filters is correct, the brain is kept
        kwargs = {}
        # we want items of 'vendors' that are 'proposed' and items of 'developers' that are 'validated'
        filters = {'query': {'review_state': (self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ),
                             'getProposingGroup': ('vendors', 'developers'), },
                   'filters': ({'getProposingGroup': ('vendors', ),
                                'review_state': (self.WF_STATE_NAME_MAPPINGS['proposed'], )},
                               {'getProposingGroup': ('developers', ),
                                'review_state': ('validated', )},),
        }
        kwargs[TOPIC_SEARCH_FILTERS] = filters
        self.changeUser('pmManager')
        vendors_item = self.create('MeetingItem')
        vendors_item.setProposingGroup('vendors')
        developers_item = self.create('MeetingItem')
        developers_item.setProposingGroup('developers')
        # as items are not in the correct state, nothing is returned for now
        self.failIf(self.meetingConfig.searchItemsWithFilters('', '', '', '', **kwargs))
        # set vendors_item in right state
        self.proposeItem(vendors_item)
        vendors_item.reindexObject()
        self.failUnless(len(self.meetingConfig.searchItemsWithFilters('', '', '', '', **kwargs)) == 1)
        # set developers_item to proposed, not listed...
        self.proposeItem(developers_item)
        developers_item.reindexObject()
        self.failUnless(len(self.meetingConfig.searchItemsWithFilters('', '', '', '', **kwargs)) == 1)
        # now set developers_item to validated, it will be listed
        self.validateItem(developers_item)
        developers_item.reindexObject()
        self.failUnless(len(self.meetingConfig.searchItemsWithFilters('', '', '', '', **kwargs)) == 2)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingConfig, prefix='test_pm_'))
    return suite
