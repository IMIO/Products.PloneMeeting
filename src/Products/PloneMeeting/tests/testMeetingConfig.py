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

from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone import PloneMessageFactory

from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.config import TOPIC_SEARCH_FILTERS
from Products.PloneMeeting.config import WriteHarmlessConfig
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
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # now propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        # only advisers can give an advice, so a creator for example will not see it
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 0)
        # now test as advisers
        self.changeUser('pmAdviser1')
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 1)
        self.assertEquals(self.meetingConfig.searchItemsToAdvice('', '', '', '')[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmAdviser1 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.failIf(self.meetingConfig.searchItemsToAdvice('', '', '', ''))
        # pmReviewer2 is adviser for 'vendors', delay-aware advices are also returned
        self.changeUser('pmReviewer2')
        self.failUnless(len(self.meetingConfig.searchItemsToAdvice('', '', '', '')) == 1)
        self.assertEquals(self.meetingConfig.searchItemsToAdvice('', '', '', '')[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmReviewer2 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                                    'advice_type': u'negative',
                                    'advice_comment': RichTextValue(u'My comment')})
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
        self.changeUser('pmManager')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.vendors.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 2)
        self.changeUser('pmAdviser1')
        self.failUnless(len(self.meetingConfig.searchAdvisedItems('', '', '', '')) == 1)
        self.changeUser('pmCreator1')
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
        self.changeUser('pmAdviser1')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.portal.portal_plonemeeting.developers.getId(),
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        self.failUnless(len(self.meetingConfig.searchAdvisedItemsWithDelay('', '', '', '')) == 1)
        self.changeUser('pmCreator1')
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
        self.failUnless(self.meetingConfig.searchItemsInCopy('', '', '', ''))

    def test_pm_SearchMyItemsTakenOver(self):
        '''Test the searchMyItemsTakenOver method.  This should return
           a list of items a user has taken over.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # by default nothing is returned
        self.failIf(self.meetingConfig.searchMyItemsTakenOver('', '', '', ''))
        # now take item over
        item.setTakenOverBy(self.member.getId())
        item.reindexObject(idxs=['getTakenOverBy', ])
        # now it is returned
        self.failUnless(self.meetingConfig.searchMyItemsTakenOver('', '', '', ''))
        # takenOverBy is set back to '' on each transition
        self.proposeItem(item)
        self.assertTrue(not item.getTakenOverBy())
        self.failIf(self.meetingConfig.searchMyItemsTakenOver('', '', '', ''))

    def test_pm_SearchItemsToValidateOfHighestHierarchicLevel(self):
        '''Test the searchItemsToValidateOfHighestHierarchicLevel method.
           This should return a list of items a user ***really*** has to validate.
           Items to validate are items for which user is a reviewer and only regarding
           his higher hierarchic level.
           So a reviewer level 1 and level 2 will only see items in level 2, a reviewer in level
           1 (only) will only see items in level 1.'''
        # activate 'prevalidation' if necessary
        if 'prereviewers' in MEETINGREVIEWERS:
            self.meetingConfig.setWorkflowAdaptations('pre_validation')
            logger = logging.getLogger('PloneMeeting: testing')
            performWorkflowAdaptations(self.portal, self.meetingConfig, logger)
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # jump to first level of validation
        self.do(item, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.failIf(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))
        self.changeUser('pmReviewerLevel1')
        self.failUnless(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))
        # now as 'pmReviewerLevel2', the item should not be returned
        # as he only see items of his highest hierarchic level
        self.changeUser('pmReviewerLevel2')
        self.failIf(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))
        # pass the item to second last level of hierarchy, where 'pmReviewerLevel2' is reviewer for
        self.changeUser('pmReviewerLevel1')
        # jump to last level of validation
        self.proposeItem(item)
        self.failIf(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))
        self.changeUser('pmReviewerLevel2')
        self.failUnless(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))

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
        self.failIf(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))
        # if the item is validated, it will not appear for pmReviewer1 anymore
        self.changeUser('pmReviewer1')
        self.failUnless(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))
        self.validateItem(item)
        self.failIf(self.meetingConfig.searchItemsToValidateOfHighestHierarchicLevel('', '', '', ''))

    def test_pm_SearchItemsToValidateOfMyReviewerGroups(self):
        '''Test the searchItemsToValidateOfMyReviewerGroups method.
           This should return a list of items a user could validate at any level,
           so not only his highest hierarchic level.  This will return finally every items
           corresponding to Plone reviewer groups the user is in.'''
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
        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.failIf(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', ''))
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', '')) == 2)
        # as second level user, he will not see items of first level also
        self.changeUser('pmReviewerLevel2')
        self.failIf(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', ''))

        # define 'pmReviewerLevel2' as a prereviewer (first validation level reviewer)
        self._turnUserIntoPrereviewer(self.member)
        # change again to 'pmReviewerLevel2' so changes in his groups are taken into account
        self.changeUser('pmReviewerLevel2')
        # he can access first validation level items
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', '')) == 2)
        # move item1 to last validation level
        self.proposeItem(item1)
        # both items still returned by the search for 'pmReviewerLevel2'
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', '')) == 2)
        # but now, the search only returns item2 to 'pmReviewerLevel1'
        self.changeUser('pmReviewerLevel1')
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', '')) == 1)
        self.failUnless(self.meetingConfig.searchItemsToValidateOfMyReviewerGroups('', '', '', '')[0].UID == item2.UID())

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
        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.failIf(self.meetingConfig.searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels('', '', '', ''))
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels('', '', '', '')) == 2)
        # as second level user, he will also see items because items are from lower reviewer levels
        self.changeUser('pmReviewerLevel2')
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels('', '', '', '')) == 2)

        # now propose item1, both items are still viewable to 'pmReviewerLevel2', but 'pmReviewerLevel1'
        # will only see item of 'his' highest hierarchic level
        self.proposeItem(item1)
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels('', '', '', '')) == 2)
        self.changeUser('pmReviewerLevel1')
        self.failUnless(len(self.meetingConfig.searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels('', '', '', '')) == 1)
        self.failUnless(self.meetingConfig.searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels('', '', '', '')[0].UID == item2.UID())

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
        self.failUnless(len(self.meetingConfig.searchItemsWithFilters('', '', '', '', **kwargs)) == 1)
        # set developers_item to proposed, not listed...
        self.proposeItem(developers_item)
        self.failUnless(len(self.meetingConfig.searchItemsWithFilters('', '', '', '', **kwargs)) == 1)
        # now set developers_item to validated, it will be listed
        self.validateItem(developers_item)
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
        empty_columns_msg = translate('custom_adviser_not_enough_columns_filled',
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
        # if both columns are filled, it validated too obviously
        customAdvisers[0]['delay'] = '10'
        self.failIf(cfg.validate_customAdvisers(customAdvisers))
        # if a 'orderindex_' key with value 'template_row_marker' is found
        # it validates the row, it is the case when using the UI to manage the
        # DataGridField, this row is not saved
        # append something that should not validate
        customAdvisers.append({'row_id': '',
                               'group': 'vendors',
                               # empty
                               'gives_auto_advice_on': '',
                               'for_item_created_from': '',
                               'for_item_created_until': '',
                               'gives_auto_advice_on_help_message': '',
                               # empty
                               'delay': '',
                               'delay_left_alert': '',
                               'delay_label': '',
                               'available_on': '',
                               'is_linked_to_previous_row': '0', },)
        # test that like that it does not validate
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == empty_columns_msg)
        # but when a 'orderindex_' key with value 'template_row_marker' found, it validates
        customAdvisers[1]['orderindex_'] = 'template_row_marker'
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
        right_date = '2013/12/31'
        # if wrong syntax, it fails
        for wrong_date in wrong_dates:
            customAdvisers[0]['for_item_created_from'] = wrong_date
            self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_date_msg)
            # set a right date for 'for_item_created_from' so we are sure that
            # validation fails because of 'for_item_created_until'
            customAdvisers[0]['for_item_created_from'] = right_date
            customAdvisers[0]['for_item_created_until'] = wrong_date
            self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == wrong_date_msg)
        # with a valid date, then it works, set back 'for_item_created_until' to ''
        # his special behaviour will be tested later in this test
        customAdvisers[0]['for_item_created_until'] = ''
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
           - can not be set if linked row is for another group;
           - can be changed if row is not in use.'''
        cfg = self.meetingConfig
        # the validate method returns a translated message if the validation failed
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

        # check that 'is_linked_to_previous_row'
        # can not be set on the first row
        first_row_msg = translate('custom_adviser_first_row_can_not_be_linked_to_previous',
                                  domain='PloneMeeting',
                                  mapping={'groupName': groupName},
                                  context=self.portal.REQUEST)
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

        # check that 'is_linked_to_previous_row'
        # can only be set on a row that is actually a delay-aware row
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

        # check that if previous row use another group, it does not validate
        # make first row a delay-aware advice, then change group
        customAdvisers[0]['delay'] = '10'
        customAdvisers[0]['group'] = 'developers'
        self.assertTrue(not customAdvisers[0]['group'] == customAdvisers[1]['group'])
        previous_row_not_same_group_msg = translate('custom_adviser_can_not_is_linked_to_previous_row_with_other_group',
                                                    domain='PloneMeeting',
                                                    mapping={'groupName': groupName},
                                                    context=self.portal.REQUEST)
        self.assertEquals(cfg.validate_customAdvisers(customAdvisers),
                          previous_row_not_same_group_msg)

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
           - if categories are not used, we can not select the 'on_categories' method;
           - fi the 'toDiscuss' field is not used, we can not select the 'on_to_discuss' method.'''
        cfg = self.meetingConfig
        # first test when using 'at_the_end' and something else
        at_the_end_error_msg = translate('inserting_methods_at_the_end_not_alone_error',
                                         domain='PloneMeeting',
                                         context=self.request)
        values = ({'insertingMethod': 'at_the_end',
                   'reverse': '0'},
                  {'insertingMethod': 'on_proposing_groups',
                   'reverse': '0'}, )
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == at_the_end_error_msg)

        # test when using several times same inserting method
        several_times_error_msg = translate('inserting_methods_can_not_select_several_times_same_method_error',
                                            domain='PloneMeeting',
                                            context=self.request)
        values = ({'insertingMethod': 'on_proposing_groups',
                   'reverse': '0'},
                  {'insertingMethod': 'on_proposing_groups',
                   'reverse': '0'}, )
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == several_times_error_msg)

        # test when selecting 'on_categories' without using categories
        not_using_categories_error_msg = translate('inserting_methods_not_using_categories_error',
                                                   domain='PloneMeeting',
                                                   context=self.request)
        values = ({'insertingMethod': 'on_categories',
                   'reverse': '0'}, )
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

        # test when selecting 'on_to_discuss' without using the 'toDiscuss' field
        not_using_categories_error_msg = translate('inserting_methods_not_using_to_discuss_error',
                                                   domain='PloneMeeting',
                                                   context=self.request)
        values = ({'insertingMethod': 'on_to_discuss',
                   'reverse': '0'}, )
        self.assertTrue('toDiscuss' in cfg.getUsedItemAttributes())
        # it valdiates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # check on using 'toDiscuss' is made on presence of 'toDiscuss' in 'usedItemAttributes' in the
        # REQUEST, or if not found, on the value defined on the MeetingConfig object
        # unselect 'toDiscuss', validation fails
        usedItemAttrs = list(cfg.getUsedItemAttributes())
        usedItemAttrsWithoutToDiscuss = usedItemAttrs
        usedItemAttrsWithoutToDiscuss.remove('toDiscuss')
        cfg.setUsedItemAttributes(usedItemAttrsWithoutToDiscuss)
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == not_using_categories_error_msg)
        # it validates if 'usedItemAttributes' found in the REQUEST
        # and 'toDiscuss' in the 'usedItemAttributes', if not it fails...
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutToDiscuss)
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == not_using_categories_error_msg)
        # but validates if 'toDiscuss' in 'usedItemAttributes' found in the REQUEST
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutToDiscuss + ['toDiscuss', ])
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # if we have a 'orderindex_' key with value 'template_row_marker'
        # it validates, it is the case when using DataGridField in the UI
        # here it works even if 'at_the_end' is used together with 'on_to_discuss'
        # as the 'at_the_end' value has the 'orderindex_' key
        values = ({'insertingMethod': 'on_to_discuss',
                   'reverse': '0'},
                  {'insertingMethod': 'at_the_end',
                   'orderindex_': 'template_row_marker',
                   'reverse': '0'})
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))

    def test_pm_Validate_meetingConfigsToCloneTo(self):
        '''Test the MeetingConfig.meetingConfigsToCloneTo validation.
           We will test that :
           - same config to clone to is not selected several times;
           - the same inserting method is not selected twice;
           - if transition selected does not correspond to the WF used by the meeting config to clone to;
           - an icon is mandatory when cloning to another config, if the icon is not found, it will not validate.'''
        cfg = self.meetingConfig
        cfg2Id = self.meetingConfig2.getId()
        # define nothing, it validates
        self.failIf(cfg.validate_meetingConfigsToCloneTo([]))

        # check that we can not select several times same meeting config to clone to
        values = ({'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': '__nothing__'},
                  {'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': '__nothing__'})
        two_rows_error_msg = _('can_not_define_two_rows_for_same_meeting_config')
        self.assertTrue(cfg.validate_meetingConfigsToCloneTo(values) == two_rows_error_msg)

        # check that value selected in 'trigger_workflow_transitions_until' correspond
        # to a value of the wf used for the corresponding selected 'meeting_config'
        values = ({'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': 'wrong-config-id.a_wf_transition'},)
        wrong_wf_transition_error_msg = _('transition_not_from_selected_meeting_config')
        self.assertTrue(cfg.validate_meetingConfigsToCloneTo(values) == wrong_wf_transition_error_msg)

        # if a key 'orderindex_' with value 'template_row_marker' is found, the row is ignored
        values = ({'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': 'wrong-config-id.a_wf_transition',
                   'orderindex_': 'template_row_marker'},)
        self.failIf(cfg.validate_meetingConfigsToCloneTo(values))

        # with a right configuration, it can fails if a corresponding icon is not found
        # indeed, an icon has to exist to manage the action in the UI
        values = ({'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': '%s.present' % cfg2Id},)
        self.failIf(cfg.validate_meetingConfigsToCloneTo(values))

    def test_pm_GetAvailablePodTemplates(self):
        '''We can define a condition and a permission on a PodTemplate
           influencing if it will be returned by MeetingConfig.getAvailablePodTemplates.'''
        cfg = self.meetingConfig
        # Create an item as creator
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        podTemplates = cfg.getAvailablePodTemplates(item)
        self.assertEquals(len(podTemplates), 1)
        self.assertEquals(podTemplates[0].Title(), 'Meeting item')
        self.validateItem(item)
        meeting = self.create('Meeting', date='2008/06/23 15:39:00')
        podTemplates = cfg.getAvailablePodTemplates(meeting)
        self.assertEquals(len(podTemplates), 1)
        self.assertEquals(podTemplates[0].Title(), 'Meeting agenda')
        self.presentItem(item)
        item.setDecision('Decision')
        self.decideMeeting(meeting)
        podTemplates = cfg.getAvailablePodTemplates(meeting)
        self.assertEquals(len(podTemplates), 2)
        self.assertEquals(podTemplates[1].Title(), 'Meeting decisions')
        # now set a permission 'pmManager' does not have
        # for second pod template available for meeting
        podTemplate = podTemplates[0]
        podTemplate.setPodPermission('Manage portal')
        self.assertTrue(len(cfg.getAvailablePodTemplates(meeting)) == 1)

    def test_pm_AddingExistingTopicDoesNotBreak(self):
        '''
          Check that we can call MeetingConfig.createTopics and that if
          a topic already exist, it does not break.
        '''
        # try to add a topic name 'searchmyitems' that already exist...
        self.assertTrue(hasattr(self.meetingConfig.topics, 'searchmyitems'))
        topicInfo = self.meetingConfig.topicsInfo[0]
        self.assertTrue(topicInfo[0] == 'searchmyitems')
        self.meetingConfig.createTopics((topicInfo, ))

    def test_pm_GetTopics(self):
        '''Test the MeetingConfig.getTopics method.  This returns topics depending on :
           - topicType parameter (Meeting or MeetingItem);
           - the evaluation of the TAL expression defined on the topic.
        '''
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        numberOfItemRelatedTopics = len(cfg.getTopics('MeetingItem'))
        # we have item related topics
        self.assertTrue(numberOfItemRelatedTopics > 1)
        # 2 topics related to meetings
        self.assertTrue(len(cfg.getTopics('Meeting')) == 2)
        # now deactivate one MeetingItem related topic and check that it is no more returned
        topic = cfg.getTopics('MeetingItem')[0]
        self.changeUser('admin')
        self.do(topic, 'deactivate')
        self.changeUser('pmManager')
        self.cleanMemoize()
        self.assertTrue(len(cfg.getTopics('MeetingItem')) == numberOfItemRelatedTopics - 1)
        # if we define a wrong TAL expression on a topic, it is no more taken into account
        topic = cfg.getTopics('MeetingItem')[0]
        topic.manage_changeProperties(topic_tal_expression='context/wrong_expression_method')
        self.cleanMemoize()
        self.assertTrue(len(cfg.getTopics('MeetingItem')) == numberOfItemRelatedTopics - 2)
        # test the fromPortletTodo parameter so we can have it in the TAL expression and take it into account
        # define a TAL expression on a topic using the 'fromPortletTodo'
        topic = cfg.getTopics('MeetingItem')[0]
        # make it only be displayed in portlet_todo
        topic.manage_changeProperties(topic_tal_expression='python: fromPortletTodo')
        # if called from portlet_todo, it is taken into account
        self.cleanMemoize()
        self.assertTrue(len(cfg.getTopics('MeetingItem', fromPortletTodo=True)) == numberOfItemRelatedTopics - 2)
        # else it is not...
        self.cleanMemoize()
        self.assertTrue(len(cfg.getTopics('MeetingItem', fromPortletTodo=False)) == numberOfItemRelatedTopics - 3)

    def test_pm_MeetingManagersMayEditHarmlessConfigFields(self):
        '''A MeetingManager may edit some harmless fields on the MeetingConfig,
           make sure we specify the write_permission 'PloneMeeting: Write harmless config'
           on fields MeetingManagers may edit...'''
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        # a MeetingManager is able to edit a MeetingConfig
        self.assertTrue(self.hasPermission(ModifyPortalContent, cfg))
        # every editable fields are protected by the 'PloneMeeting: Write harmless config' permission
        for field in cfg.Schema().editableFields(cfg):
            self.assertTrue(field.write_permission == WriteHarmlessConfig)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingConfig, prefix='test_pm_'))
    return suite
