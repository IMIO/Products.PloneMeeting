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

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.config import TOPIC_SEARCH_FILTERS


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
        self.assertEquals(self.meetingConfig.getItemAdviceStates(), ('proposed', 'validated'))
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
        item.editAdvice(group=self.portal.portal_plonemeeting.developers, adviceType='positive', comment='My comment')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))

    def test_pm_searchAdvisedItems(self):
        '''Test the searchAdvisedItems method.  This should return a list of items
           a user has already give an advice for.'''
        self.setMeetingConfig(self.meetingConfig2.getId())
        # by default, no advices item...
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # an advice can be given when an item is 'proposed' or 'validated'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(), ('proposed', 'validated'))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers',))
        self.proposeItem(item1)
        item1.reindexObject()
        # give an advice
        self.changeUser('pmAdviser1')
        item1.editAdvice(group=self.portal.portal_plonemeeting.developers, adviceType='positive', comment='My comment')
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
        item2.editAdvice(group=self.portal.portal_plonemeeting.vendors, adviceType='positive', comment='My comment')
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
        self.meetingConfig.setItemCopyGroupsStates(('proposed', 'validated', ))
        # create an item and set another service in copy of
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups(('developers_reviewers',))
        self.failIf(self.meetingConfig.searchItemsInCopy('', '', '', ''))
        # connect as a member of 'developers_reviewers'
        self.changeUser('pmReviewer1')
        # the item is not proposed so not listed
        self.failIf(self.meetingConfig.searchItemsInCopy('', '', '', ''))
        # propose the item, it will be listed
        self.proposeItem(item)
        item.reindexObject()
        self.failUnless(self.meetingConfig.searchItemsInCopy('', '', '', ''))

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
        filters = {'query': {'review_state': ('proposed', 'validated', ),
                             'getProposingGroup': ('vendors', 'developers'), },
                   'filters': ({'getProposingGroup': ('vendors', ), 'review_state': ('proposed', )},
                               {'getProposingGroup': ('developers', ), 'review_state': ('validated', )},),
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
