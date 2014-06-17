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
from DateTime import DateTime

from zope.i18n import translate

from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from Products.CMFPlone import PloneMessageFactory

from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.config import TOPIC_SEARCH_FILTERS
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations


class testMeetingConfig(PloneMeetingTestCase):
    '''Tests the MeetingConfig class methods.'''

    def test_pm_SearchItemsToAdvice(self):
        '''Test the searchItemsToAdvice method.  This should return a list of items
           a user has to give an advice for.'''
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'delay': '5', }, ])
        # by default, no item to advice...
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # an advice can be given when an item is 'proposed'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', 'vendors__rowid__unique_id_123'))
        # as the item is "itemcreated", advices are not givable
        self.changeUser('pmAdviser1')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # now propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        item.reindexObject()
        # only advisers can give an advice, so a creator for example will not see it
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 0)
        # now test as advisers
        self.changeUser('pmAdviser1')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 1)
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.assertEquals(self.meetingConfig.searchItemsToAdvice('', '', '', '')[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmAdviser1 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # pmReviewer2 is adviser for 'vendors', delay-aware advices are also returned
        self.changeUser('pmReviewer2')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 1)
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.assertEquals(self.meetingConfig.searchItemsToAdvice('', '', '', '')[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmReviewer2 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                                    'advice_type': u'negative',
                                    'advice_comment': RichTextValue(u'My comment')})
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))

    def test_pm_SearchAdvisedItems(self):
        '''Test the searchAdvisedItems method.  This should return a list of items
           a user has already give an advice for.'''
        # by default, no advices item...
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # an advice can be given when an item is 'proposed'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers',))
        self.proposeItem(item1)
        item1.reindexObject()
        # give an advice
        self.changeUser('pmAdviser1')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.failUnless(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # another user will not see given advices
        self.changeUser('pmCreator1')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failIf(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # other advisers of the same group will also see advised items
        self.changeUser('pmManager')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(self.meetingConfig.searchAdvisedItems('', '', '', ''))
        # now create a second item and ask advice to the vendors (pmManager)
        # it will be returned for pmManager but not for pmAdviser1
        self.changeUser('pmCreator1')
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('vendors',))
        self.proposeItem(item2)
        item2.reindexObject()
        self.changeUser('pmManager')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 2)
        self.changeUser('pmAdviser1')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 1)
        self.changeUser('pmCreator1')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 0)

    def test_pm_SearchAdvisedItemsWithDelay(self):
        '''Test the searchAdvisedItemsWithDelay method.  This should return a list
           of items a user has already give a delay-aware advice for.'''
        # by default, no advices item...
        self.changeUser('pmAdviser1')
        self.failIf(self.meetingConfig.searchAdvisedItemsWithDelay('', '', '', ''))
        # an advice can be given when an item is 'proposed'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers',))
        self.proposeItem(item1)
        item1.reindexObject()
        # give a non delay-aware advice
        self.changeUser('pmAdviser1')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # non delay-aware advices are not found
        self.failIf(self.meetingConfig.searchAdvisedItemsWithDelay('', '', '', ''))
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
        item2.reindexObject()
        self.changeUser('pmAdviser1')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        self.failUnless(len(self.meetingConfig.searchAdvisedItemsWithDelay('', '', '', '')) == 1)
        self.changeUser('pmCreator1')
        self._cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.failUnless(len(self.meetingConfig.searchAdvisedItemsWithDelay('', '', '', '')) == 0)

    def test_pm_SearchItemsInCopy(self):
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

    def test_pm_SearchItemsToValidate(self):
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

    def test_pm_SearchItemsToPrevalidate(self):
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

    def test_pm_SearchItemsWithFilters(self):
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

    def test_pm_Validate_customAdvisersEnoughData(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates that enough columns are filled, either the 'delay' or the
           'gives_auto_advice_on' column must be filled.'''
        cfg = self.meetingConfig
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           # empty
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           # empty
                           'delay': '',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', }, ]
        groupName = getattr(self.tool, customAdvisers[0]['group']).Title()
        empty_columns_msg = translate('custom_adviser_not_enough_colmuns_filled',
                                      domain='PloneMeeting',
                                      mapping={'groupName': groupName},
                                      context=self.portal.REQUEST)
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == empty_columns_msg)
        # if the 'delay' column is filled, it validates
        customAdvisers[0]['delay'] = '10'
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # if the 'gives_auto_advice_on' column is filled, it validates
        customAdvisers[0]['gives_auto_advice_on'] = 'python:True'
        customAdvisers[0]['delay'] = ''
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # if both colmuns are filled, it validated too obviously
        customAdvisers[0]['delay'] = '10'
        self.failIf(cfg.validate_customAdvisers(customAdvisers))

    def test_pm_Validate_customAdvisersDateColumns(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates dates of the 'for_item_created_from' and ''for_item_created_until' columns :
           dates are strings that need to respect following format 'YYYY/MM/DD'.'''
        cfg = self.meetingConfig
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           # wrong date format, should have been '2012/12/31'
                           'for_item_created_from': '2012/31/12',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', }, ]
        groupName = getattr(self.tool, customAdvisers[0]['group']).Title()
        wrong_date_msg = translate('custom_adviser_wrong_date_format',
                                   domain='PloneMeeting',
                                   mapping={'groupName': groupName},
                                   context=self.portal.REQUEST)
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_date_msg)
        # not a date, wrong format (YYYY/MM/DD) or extra blank are not valid dates
        wrong_dates = ['wrong', '2013/20/05', '2013/02/05 ', ]
        # if wrong syntax, it fails
        for wrong_date in wrong_dates:
            customAdvisers[0]['for_item_created_from'] = wrong_date
            self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_date_msg)
            customAdvisers[0]['for_item_created_until'] = wrong_date
            self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_date_msg)
        # with a valid date, then it works, set back 'for_item_created_until' to ''
        # his special behaviour will be tested later in this test
        customAdvisers[0]['for_item_created_until'] = ''
        customAdvisers[0]['for_item_created_from'] = '2013/12/31'
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # 'for_item_create_until' date must be in the future
        customAdvisers[0]['for_item_created_until'] = '2010/12/31'
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_date_msg)
        # with a future date, it validates ONLY if it is the first time the date
        # is defined, aka we can not change an already encoded 'for_item_created_until' date
        future_date = (DateTime() + 1).strftime('%Y/%m/%d')
        customAdvisers[0]['for_item_created_until'] = future_date
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # as long as the rule is not used, we can still change it...
        # like another date in the past or back to ''
        self.meetingConfig.setCustomAdvisers(customAdvisers)
        other_future_date = (DateTime() + 2).strftime('%Y/%m/%d')
        customAdvisers[0]['for_item_created_until'] = other_future_date
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        self.meetingConfig.setCustomAdvisers(customAdvisers)
        customAdvisers[0]['for_item_created_until'] = ''
        self.failIf(cfg.validate_customAdvisers(customAdvisers))

    def test_pm_Validate_customAdvisersDelayColumn(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates delays of the 'delay' column : either field is empty or
           a delay is defined as a single digit value.
           If both 'delay' and 'delay_left_alert' are defined, make sure the value in 'delay'
           is higher or equals the value in 'delay_left_alert' and if a value is defined in 'delay_left_alert',
           then a value in the 'delay' column is required.'''
        cfg = self.meetingConfig
        # the validate method returns a translated message if the validation failed
        # wrong format, should be empty or a digit
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': 'python:True',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           # wrong value
                           'delay': 'a',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', }, ]
        groupName = getattr(self.tool, customAdvisers[0]['group']).getName()
        wrong_delay_msg = translate('custom_adviser_wrong_delay_format',
                                    domain='PloneMeeting',
                                    mapping={'groupName': groupName},
                                    context=self.portal.REQUEST)
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_delay_msg)
        # if wrong syntax, it fails
        customAdvisers[0]['delay'] = '10,5'
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_delay_msg)
        # if extra blank, it fails
        customAdvisers[0]['delay'] = '10 '
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_delay_msg)
        # if not integer, it fails
        customAdvisers[0]['delay'] = '10.5'
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_delay_msg)
        # with a valid date, then it works
        # with a single delay value
        customAdvisers[0]['delay'] = '10'
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # 'delay' must be higher or equals 'delay_left_alert'
        delay_higher_msg = translate('custom_adviser_delay_left_must_be_inferior_to_delay',
                                     domain='PloneMeeting',
                                     mapping={'groupName': groupName},
                                     context=self.portal.REQUEST)
        customAdvisers[0]['delay_left_alert'] = '12'
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == delay_higher_msg)
        # equals or higher is ok
        customAdvisers[0]['delay'] = '12'
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        customAdvisers[0]['delay'] = '15'
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # if 'delay_alert_left' is defined, 'delay' must be as well
        delay_required_msg = translate('custom_adviser_no_delay_left_if_no_delay',
                                       domain='PloneMeeting',
                                       mapping={'groupName': groupName},
                                       context=self.portal.REQUEST)
        customAdvisers[0]['delay'] = ''
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == delay_required_msg)

    def test_pm_Validate_customAdvisersCanNotChangeUsedConfig(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates that if a configuration is already in use, logical data can
           not be changed anymore, only basic data can be changed (.'''
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # first check that we can edit an unused configuration
        self.changeUser('admin')
        cfg = self.meetingConfig
        originalCustomAdvisers = {'row_id': 'unique_id_123',
                                  'group': 'developers',
                                  'gives_auto_advice_on': 'item/getBudgetRelated',
                                  'for_item_created_from': '2012/01/01',
                                  'for_item_created_until': '',
                                  'gives_auto_advice_on_help_message': 'Auto help message',
                                  'delay': '10',
                                  'delay_left_alert': '',
                                  'delay_label': 'Delay label',
                                  'available_on': '',
                                  'is_linked_to_previous_row': '0', }
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
        # change everything including logical data
        changedCustomAdvisers = {'row_id': 'unique_id_123',
                                 'group': 'vendors',
                                 'gives_auto_advice_on': 'not:item/getBudgetRelated',
                                 'for_item_created_from': '2013/01/01',
                                 'for_item_created_until': '2025/01/01',
                                 'gives_auto_advice_on_help_message': 'Auto help message changed',
                                 'delay': '20',
                                 'delay_left_alert': '',
                                 'delay_label': 'Delay label changed',
                                 'available_on': '',
                                 'is_linked_to_previous_row': '0', }
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers([changedCustomAdvisers, ]))
        # now use the config
        # make advice givable when item is 'itemcreated'
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setCustomAdvisers([originalCustomAdvisers, ])
        item.setBudgetRelated(True)
        item.at_post_edit_script()
        # the automatic advice has been asked
        self.assertEquals(item.adviceIndex['developers']['row_id'], 'unique_id_123')
        # current config is still valid
        self.failIf(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
        # now we can not change a logical field, aka
        # 'group', 'gives_auto_advice_on', 'for_item_created_from' and 'delay'
        logical_fields_wrong_values_mapping = {
            'group': 'vendors',
            'gives_auto_advice_on': 'not:item/getBudgetRelated',
            'for_item_created_from': '2000/01/01',
            'delay': '55', }
        savedOriginalCustomAdvisers = dict(originalCustomAdvisers)
        for field in logical_fields_wrong_values_mapping:
            originalCustomAdvisers[field] = logical_fields_wrong_values_mapping[field]
            # it does not validate, aka the validate method returns something
            self.failUnless(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
            originalCustomAdvisers = dict(savedOriginalCustomAdvisers)
        # now change a non logical field, then it still validates
        non_logical_fields_wrong_values_mapping = {
            'gives_auto_advice_on_help_message': 'New help message gives auto',
            'delay_left_alert': '5',
            'delay_label': 'New delay label', }
        savedOriginalCustomAdvisers = dict(originalCustomAdvisers)
        for field in non_logical_fields_wrong_values_mapping:
            originalCustomAdvisers[field] = non_logical_fields_wrong_values_mapping[field]
            # it does validate
            self.failIf(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
            originalCustomAdvisers = dict(savedOriginalCustomAdvisers)

        # special behaviour for field 'for_item_created_until' that can be set once
        # if it was empty, if a date was encoded and the rule is used, it can not be changed anymore
        # set a future date and try to change it
        future_date = (DateTime() + 1).strftime('%Y/%m/%d')
        originalCustomAdvisers['for_item_created_until'] = future_date
        self.failIf(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
        cfg.setCustomAdvisers([originalCustomAdvisers, ])
        # now changing the encoded date would fail
        other_future_date = (DateTime() + 2).strftime('%Y/%m/%d')
        originalCustomAdvisers['for_item_created_until'] = other_future_date
        self.failUnless(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
        # it can not neither be set back to ''
        originalCustomAdvisers['for_item_created_until'] = ''
        self.failUnless(cfg.validate_customAdvisers([originalCustomAdvisers, ]))

        # we can not remove a used row
        can_not_remove_msg = translate('custom_adviser_can_not_remove_used_row',
                                       domain='PloneMeeting',
                                       mapping={'item_url': item.absolute_url(),
                                                'adviser_group': 'Developers', },
                                       context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers([]), can_not_remove_msg)

        # if the 'for_item_created_until' date was set, it validates if not changed
        # even if the 'for_item_created_until' is now past
        customAdvisersCreatedUntilSetAndPast = \
            {'row_id': 'unique_id_123',
             'group': 'vendors',
             'gives_auto_advice_on': 'not:item/getBudgetRelated',
             'for_item_created_from': '2013/01/01',
             'for_item_created_until': '2013/01/15',
             'gives_auto_advice_on_help_message': 'Auto help message changed',
             'delay': '20',
             'delay_left_alert': '',
             'delay_label': 'Delay label changed',
             'available_on': '',
             'is_linked_to_previous_row': '0', }
        cfg.setCustomAdvisers([customAdvisersCreatedUntilSetAndPast, ])
        self.failIf(cfg.validate_customAdvisers([customAdvisersCreatedUntilSetAndPast, ]))

    def test_pm_Validate_customAdvisersAvailableOn(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates that available_on can only be used if nothing is defined
           in the 'gives_auto_advice_on' column.'''
        cfg = self.meetingConfig
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           # empty
                           'gives_auto_advice_on': 'python: item.getBudgetRelated()',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'available_on': 'python: item.getItemIsSigned()',
                           'is_linked_to_previous_row': '0', }, ]
        groupName = getattr(self.tool, customAdvisers[0]['group']).Title()
        available_on_msg = translate('custom_adviser_can_not_available_on_and_gives_auto_advice_on',
                                     domain='PloneMeeting',
                                     mapping={'groupName': groupName},
                                     context=self.portal.REQUEST)
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == available_on_msg)
        # available_on can be filled if nothing is defined in the 'gives_auto_advice_on'
        customAdvisers[0]['gives_auto_advice_on'] = ''
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers(customAdvisers))

    def test_pm_Validate_customAdvisersIsLinkedToPreviousRowDelayAware(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates the 'is_linked_to_previous_row' row regarding :
           - first row can not be linked to previous row...;
           - can not be set on a row that is not delay-aware;
           - can not be set if linked row is not delay-aware;
           - can be changed if row is not in use.'''
        cfg = self.meetingConfig
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': 'python:True',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', }, ]
        groupName = getattr(self.tool, customAdvisers[0]['group']).Title()
        first_row_msg = translate('custom_adviser_first_row_can_not_be_linked_to_previous',
                                  domain='PloneMeeting',
                                  mapping={'groupName': groupName},
                                  context=self.portal.REQUEST)
        # check that 'is_linked_to_previous_row'
        # can not be set on the first row
        customAdvisers[0]['is_linked_to_previous_row'] = '1'
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          first_row_msg)
        customAdvisers[0]['is_linked_to_previous_row'] = '0'

        # check that 'is_linked_to_previous_row'
        # can only be set on a delay-aware row
        customAdvisers.append({'row_id': 'unique_id_456',
                               'group': 'vendors',
                               'gives_auto_advice_on': 'python:True',
                               'for_item_created_from': '2012/12/31',
                               'for_item_created_until': '',
                               'gives_auto_advice_on_help_message': '',
                               'delay': '',
                               'delay_left_alert': '',
                               'delay_label': '',
                               'available_on': '',
                               'is_linked_to_previous_row': '1'})
        row_not_delay_aware_msg = translate('custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser',
                                            domain='PloneMeeting',
                                            mapping={'groupName': groupName},
                                            context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          row_not_delay_aware_msg)

        # check that 'is_linked_to_previous_row'
        # can only be set if previous row is also a delay-aware row
        # make second row a delay aware row, first row is not delay aware
        customAdvisers[1]['delay'] = '5'
        self.assertTrue(customAdvisers[0]['delay'] == '')
        previous_row_not_delay_aware_msg = translate('custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser_previous_row',
                                                     domain='PloneMeeting',
                                                     mapping={'groupName': groupName},
                                                     context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          previous_row_not_delay_aware_msg)
        # check that 'is_linked_to_previous_row' value can be changed
        # while NOT already in use by created items
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '5',
                           'delay_left_alert': '2',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', },
                          {'row_id': 'unique_id_456',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '20',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'}]
        cfg.setCustomAdvisers(customAdvisers)
        # change 'is_linked_to_previous_row' of second row to ''
        customAdvisers[1]['is_linked_to_previous_row'] = '0'
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        customAdvisers[2]['is_linked_to_previous_row'] = '1'
        customAdvisers[1]['is_linked_to_previous_row'] = '0'
        self.failIf(cfg.validate_customAdvisers(customAdvisers))

        # we can change row positions, no problem
        customAdvisers[1], customAdvisers[2] = customAdvisers[2], customAdvisers[1]
        self.assertTrue(customAdvisers[1]['row_id'] == 'unique_id_789')
        self.assertTrue(customAdvisers[2]['row_id'] == 'unique_id_456')
        self.failIf(cfg.validate_customAdvisers(customAdvisers))

    def test_pm_Validate_customAdvisersIsLinkedToPreviousRowIsUsed(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates the 'is_linked_to_previous_row' row when it is in use.'''
        cfg = self.meetingConfig
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '5',
                           'delay_left_alert': '2',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', },
                          {'row_id': 'unique_id_456',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '20',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_1011',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '30',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'}]
        cfg.setCustomAdvisers(customAdvisers)
        # for now stored data are ok
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))
        # create an item and ask advice relative to second row, row_id 'unique_id_456'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors__rowid__unique_id_456', ))
        # 'is_linked_to_previous_row' can be changed if the row is used as optional adviser
        customAdvisers[1]['is_linked_to_previous_row'] = '0'
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))
        customAdvisers[1]['is_linked_to_previous_row'] = '1'
        # an element of the chain of rows linked together can be changed
        # as the advice is used as optional advice
        customAdvisers[2]['is_linked_to_previous_row'] = '0'
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))
        customAdvisers[2]['is_linked_to_previous_row'] = '1'

        # 'is_linked_to_previous_row' can not be changed
        # when used as an automatic adviser because this is the only link
        # when updating advices
        item.setOptionalAdvisers(())
        customAdvisers[2]['gives_auto_advice_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        item.at_post_edit_script()
        # advice linked to second row is asked
        self.assertTrue(item.adviceIndex['vendors']['row_id'] == customAdvisers[2]['row_id'])
        # current config still does validate correctly
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))

        # disable the second row 'is_linked_to_previous_row' will
        # "break" the chain of linked elements, it is not permitted if
        # one of the element of the chain is in use
        customAdvisers[1]['is_linked_to_previous_row'] = '0'
        isolated_row_msg = translate('custom_adviser_can_not_change_is_linked_to_previous_row_isolating_used_rows',
                                     domain='PloneMeeting',
                                     mapping={'item_url': item.absolute_url(),
                                              'adviser_group': 'Vendors'},
                                     context=self.portal.REQUEST)
        # we need to invalidate ram.cache of _findLinkedRowsFor
        cfg.setModificationDate(DateTime())
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          isolated_row_msg)
        customAdvisers[1]['is_linked_to_previous_row'] = '1'

        # now it will not be possible anymore to change value, position of any element
        # of the chain of linked rows thru 'is_linked_to_previous_row'
        customAdvisers[2]['is_linked_to_previous_row'] = '0'
        changed_used_row_msg = translate('custom_adviser_can_not_edit_used_row',
                                         domain='PloneMeeting',
                                         mapping={'item_url': item.absolute_url(),
                                                  'adviser_group': 'Vendors',
                                                  'column_old_data': '1',
                                                  'column_name': 'Is linked to previous row?'},
                                         context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          changed_used_row_msg)
        customAdvisers[2]['is_linked_to_previous_row'] = '1'
        # change position of second and third rows
        customAdvisers[1], customAdvisers[2] = customAdvisers[2], customAdvisers[1]
        self.assertTrue(customAdvisers[1]['row_id'] == 'unique_id_789')
        self.assertTrue(customAdvisers[2]['row_id'] == 'unique_id_456')
        changed_row_pos_msg = translate('custom_adviser_can_not_change_row_order_of_used_row_linked_to_previous',
                                        domain='PloneMeeting',
                                        mapping={'item_url': item.absolute_url(),
                                                 'adviser_group': 'Vendors'},
                                        context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          changed_row_pos_msg)
        # recover right order
        customAdvisers[1], customAdvisers[2] = customAdvisers[2], customAdvisers[1]

        # can not delete used or chained row
        # delete second row (unused but in the chain)
        secondRow = customAdvisers.pop(1)
        # while removing a row in a chain, it consider first that the chain was changed
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          changed_row_pos_msg)
        customAdvisers.insert(1, secondRow)
        # delete third row (used)
        thirdRow = customAdvisers.pop(2)
        can_not_remove_msg = translate('custom_adviser_can_not_remove_used_row',
                                       domain='PloneMeeting',
                                       mapping={'item_url': item.absolute_url(),
                                                'adviser_group': 'Vendors', },
                                       context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          can_not_remove_msg)
        customAdvisers.insert(2, thirdRow)
        # we can remove the last row, chained but unused
        customAdvisers.pop(3)
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))

    def test_pm_Validate_transitionsForPresentingAnItem(self):
        '''Test the MeetingConfig.transitionsForPresentingAnItem validation.
           It fails if :
           - empty, as it is required;
           - first given transition is not correct;
           - given sequence is wrong;
           - last given transition does not result in the 'presented' state.'''
        cfg = self.meetingConfig
        # the right sequence is the one defined on self.meetingConfig
        self.failIf(cfg.validate_transitionsForPresentingAnItem(cfg.getTransitionsForPresentingAnItem()))
        # if not sequence provided, it fails
        label = cfg.Schema()['transitionsForPresentingAnItem'].widget.Label(cfg)
        required_error_msg = PloneMessageFactory(u'error_required',
                                                 default=u'${name} is required, please correct.',
                                                 mapping={'name': label})
        self.assertEquals(cfg.validate_transitionsForPresentingAnItem([]), required_error_msg)
        # if first provided transition is wrong, it fails with a specific message
        first_transition_error_msg = _('first_transition_must_leave_wf_initial_state')
        self.assertEquals(cfg.validate_transitionsForPresentingAnItem(['not_a_transition_leaving_initial_state']),
                          first_transition_error_msg)
        # if the given sequence is not right, it fails
        wrong_sequence_error_msg = _('given_wf_path_does_not_lead_to_present')
        sequence = list(cfg.getTransitionsForPresentingAnItem())
        sequence.insert(1, 'wrong_transition')
        self.assertEquals(cfg.validate_transitionsForPresentingAnItem(sequence),
                          wrong_sequence_error_msg)
        # XXX for this test, we need at least 2 transitions in the sequence
        # as we will remove last transition from the sequence and if we only have
        # one transition, it leads to the required_error message instead
        if not len(cfg.getTransitionsForPresentingAnItem()) > 1:
            pm_logger.info('Could not make every checks in test_pm_validateTransitionsForPresentingAnItem '
                           'because only one TransitionsForPresentingAnItem')
            return
        last_transition_error_msg = _('last_transition_must_result_in_presented_state')
        sequence_with_last_removed = list(cfg.getTransitionsForPresentingAnItem())[:-1]
        self.assertEquals(cfg.validate_transitionsForPresentingAnItem(sequence_with_last_removed),
                          last_transition_error_msg)

    def test_pm_Validate_insertingMethodsOnAddItem(self):
        '''Test the MeetingConfig.insertingMethodsOnAddItem validation.
           We will test that :
           - if 'at_the_end' is selected, no other is selected;
           - the same inserting method is not selected twice;
           - if categories are not used, we can not select the 'on_categories' method.'''
        cfg = self.meetingConfig
        # first test when using 'at_the_end' and something else
        at_the_end_error_msg = _('inserting_methods_at_the_end_not_alone_error')
        values = ({'insertingMethod': 'at_the_end'},
                  {'insertingMethod': 'on_proposing_groups'}, )
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == at_the_end_error_msg)
        # test when using several times same inserting method
        several_times_error_msg = _('inserting_methods_can_not_select_several_times_same_method_error')
        values = ({'insertingMethod': 'on_proposing_groups'},
                  {'insertingMethod': 'on_proposing_groups'}, )
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == several_times_error_msg)
        # test when selecting 'on_categories' without using categories
        not_using_categories_error_msg = _('inserting_methods_not_using_categories_error')
        values = ({'insertingMethod': 'on_categories'}, )
        self.assertTrue(cfg.getUseGroupsAsCategories() is True)
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == not_using_categories_error_msg)
        # check on using categories is made on presence of 'useGroupsAsCategories' in the
        # REQUEST, or if not found, on the value defined on the MeetingConfig object
        cfg.setUseGroupsAsCategories(False)
        # this time it validates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # except if we just redefined it, aka 'useGroupsAsCategories' to True in the REQUEST
        self.portal.REQUEST.set('useGroupsAsCategories', True)
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == not_using_categories_error_msg)
        self.portal.REQUEST.set('useGroupsAsCategories', False)
        # this time it validates as redefining it to using categories
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingConfig, prefix='test_pm_'))
    return suite
