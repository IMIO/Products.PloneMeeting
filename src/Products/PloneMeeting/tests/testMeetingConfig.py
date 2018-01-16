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

from collections import OrderedDict
from DateTime import DateTime

from AccessControl import Unauthorized
from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate

from collective.iconifiedcategory.utils import get_category_object

from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone import PloneMessageFactory
from Products.CMFPlone.CatalogTool import getIcon
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget
from imio.dashboard.utils import _get_criterion

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import DEFAULT_ITEM_COLUMNS
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES
from Products.PloneMeeting.config import DEFAULT_MEETING_COLUMNS
from Products.PloneMeeting.config import ITEM_ICON_COLORS
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.config import WriteHarmlessConfig
from Products.PloneMeeting.MeetingConfig import DUPLICATE_SHORT_NAME


class testMeetingConfig(PloneMeetingTestCase):
    '''Tests the MeetingConfig class methods.'''

    def test_pm_Validate_shortName(self):
        '''Test the MeetingConfig.shortName validate method.
           This validates that the shortName is unique across every MeetingConfigs.'''
        cfg = self.meetingConfig
        cfg2Name = self.meetingConfig2.getShortName()
        # can validate it's own shortName
        self.assertFalse(cfg.validate_shortName(cfg.getShortName()))
        # can validate an unknown shortName
        self.assertFalse(cfg.validate_shortName('other-short-name'))
        self.assertTrue(cfg.validate_shortName(cfg2Name) == DUPLICATE_SHORT_NAME % cfg2Name)

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
        item._update_after_edit()
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

        # 'available_on' may be changed even if advice is in use
        cfg.setCustomAdvisers(customAdvisers)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item._update_after_edit()
        customAdvisers[0]['available_on'] = ''
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
        first_row_msg = translate(
            'custom_adviser_first_row_can_not_be_linked_to_previous',
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
        row_not_delay_aware_msg = translate(
            'custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser',
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
        previous_row_not_delay_aware_msg = translate(
            'custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser_previous_row',
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
        previous_row_not_same_group_msg = translate(
            'custom_adviser_can_not_is_linked_to_previous_row_with_other_group',
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
        item._update_after_edit()
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
        cfg.setUsedItemAttributes(('pollType', 'toDiscuss', 'privacy'))
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

        # test when selecting 'on_poll_type' without using the 'pollType' field
        inserting_methods_not_using_poll_type_error_msg = \
            translate('inserting_methods_not_using_poll_type_error',
                      domain='PloneMeeting',
                      context=self.request)
        values = ({'insertingMethod': 'on_poll_type',
                   'reverse': '0'}, )
        if 'pollType' not in cfg.getUsedItemAttributes():
            cfg.setUsedItemAttributes(cfg.getUsedItemAttributes() + ('pollType', ))
        self.assertTrue('pollType' in cfg.getUsedItemAttributes())
        # it validates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # check on using 'pollType' is made on presence of 'pollType' in 'usedItemAttributes' in the
        # REQUEST, or if not found, on the value defined on the MeetingConfig object
        # unselect 'pollType', validation fails
        usedItemAttrs = list(cfg.getUsedItemAttributes())
        usedItemAttrsWithoutPollType = usedItemAttrs
        usedItemAttrsWithoutPollType.remove('pollType')
        cfg.setUsedItemAttributes(usedItemAttrsWithoutPollType)
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_not_using_poll_type_error_msg)
        # it validates if 'usedItemAttributes' found in the REQUEST
        # and 'pollType' in the 'usedItemAttributes', if not it fails...
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutPollType)
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_not_using_poll_type_error_msg)
        # but validates if 'pollType' in 'usedItemAttributes' found in the REQUEST
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutPollType + ['pollType', ])
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))

        # test when selecting 'on_to_discuss' without using the 'toDiscuss' field
        inserting_methods_not_using_to_discuss_error_msg = \
            translate('inserting_methods_not_using_to_discuss_error',
                      domain='PloneMeeting',
                      context=self.request)
        values = ({'insertingMethod': 'on_to_discuss',
                   'reverse': '0'}, )
        self.assertTrue('toDiscuss' in cfg.getUsedItemAttributes())
        # it validates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # check on using 'toDiscuss' is made on presence of 'toDiscuss' in 'usedItemAttributes' in the
        # REQUEST, or if not found, on the value defined on the MeetingConfig object
        # unselect 'toDiscuss', validation fails
        usedItemAttrs = list(cfg.getUsedItemAttributes())
        usedItemAttrsWithoutToDiscuss = usedItemAttrs
        usedItemAttrsWithoutToDiscuss.remove('toDiscuss')
        cfg.setUsedItemAttributes(usedItemAttrsWithoutToDiscuss)
        self.portal.REQUEST.set('usedItemAttributes', ())
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_not_using_to_discuss_error_msg)
        # it validates if 'usedItemAttributes' found in the REQUEST
        # and 'toDiscuss' in the 'usedItemAttributes', if not it fails...
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutToDiscuss)
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_not_using_to_discuss_error_msg)
        # but validates if 'toDiscuss' in 'usedItemAttributes' found in the REQUEST
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutToDiscuss + ['toDiscuss', ])
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))

        # test when selecting 'on_privacy' without using the 'privacy' field
        inserting_methods_not_using_privacy_error_msg = \
            translate('inserting_methods_not_using_privacy_error',
                      domain='PloneMeeting',
                      context=self.request)
        values = ({'insertingMethod': 'on_privacy',
                   'reverse': '0'}, )
        self.assertTrue('privacy' in cfg.getUsedItemAttributes())
        # it validates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # check on using 'privacy' is made on presence of 'privacy' in 'usedItemAttributes' in the
        # REQUEST, or if not found, on the value defined on the MeetingConfig object
        # unselect 'privacy', validation fails
        usedItemAttrs = list(cfg.getUsedItemAttributes())
        usedItemAttrsWithoutPrivacy = usedItemAttrs
        usedItemAttrsWithoutPrivacy.remove('privacy')
        cfg.setUsedItemAttributes(usedItemAttrsWithoutPrivacy)
        self.portal.REQUEST.set('usedItemAttributes', ())
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_not_using_privacy_error_msg)
        # it validates if 'usedItemAttributes' found in the REQUEST
        # and 'privacy' in the 'usedItemAttributes', if not it fails...
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutPrivacy)
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_not_using_privacy_error_msg)
        # but validates if 'privacy' in 'usedItemAttributes' found in the REQUEST
        self.portal.REQUEST.set('usedItemAttributes', usedItemAttrsWithoutToDiscuss + ['privacy', ])
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))

        # 'on_privacy' may not be used with 'reverse'
        values = ({'insertingMethod': 'on_privacy',
                   'reverse': '1'}, )
        inserting_methods_on_privacy_reverse_error_msg = \
            translate('inserting_methods_on_privacy_reverse_error',
                      domain='PloneMeeting',
                      context=self.request)
        self.assertEqual(cfg.validate_insertingMethodsOnAddItem(values),
                         inserting_methods_on_privacy_reverse_error_msg)

        # if we have a 'orderindex_' key with value 'template_row_marker'
        # it validates, it is the case when using DataGridField in the UI
        # here it works even if 'at_the_end' is used together with 'on_to_discuss'
        # as the 'at_the_end' value has the 'orderindex_' key
        values = ({'insertingMethod': 'on_privacy',
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
                   'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},
                  {'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL})
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

        # with a right configuration, it works
        values = ({'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': '%s.present' % cfg2Id},)
        self.failIf(cfg.validate_meetingConfigsToCloneTo(values))

    def test_pm_Validate_listTypes(self):
        '''Test the MeetingConfig.listTypes validation.'''
        cfg = self.meetingConfig

        # default listTypes must be present
        values = list(DEFAULT_LIST_TYPES)
        # validates
        self.failIf(cfg.validate_listTypes(values))
        values.remove(DEFAULT_LIST_TYPES[0])
        missing_default_msg = _('error_list_types_missing_default')
        self.assertEquals(cfg.validate_listTypes(values), missing_default_msg)

        # used one may not be removed
        values = list(DEFAULT_LIST_TYPES)
        valuesWithExtra = list(values)
        valuesWithExtra.append({'identifier': 'extra',
                                'label': 'Extra'})
        self.failIf(cfg.validate_listTypes(valuesWithExtra))
        cfg.setListTypes(valuesWithExtra)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setListType('extra')
        item.reindexObject()
        already_used_msg = _('error_list_types_identifier_removed_already_used',
                             mapping={'url': item.absolute_url()})
        self.assertEquals(cfg.validate_listTypes(values), already_used_msg)
        self.failIf(cfg.validate_listTypes(valuesWithExtra))
        # if no more used, removeable
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        self.changeUser('siteadmin')
        self.failIf(cfg.validate_listTypes(values))
        self.failIf(cfg.validate_listTypes(valuesWithExtra))

        # wrong format for identifier
        valuesWithWrongFormat = list(values)
        valuesWithWrongFormat.append({'identifier': 'extra wrong',
                                      'label': 'Extra wrong'})
        wrong_format_msg = _('error_list_types_wrong_identifier_format')
        self.assertEquals(cfg.validate_listTypes(valuesWithWrongFormat), wrong_format_msg)

        # already used identifier
        valuesWithDouble = list(values)
        valuesWithDouble.append(values[0])
        double_msg = _('error_list_types_same_identifier')
        self.assertEquals(cfg.validate_listTypes(valuesWithDouble), double_msg)
        self.failIf(cfg.validate_listTypes(values))

    def test_pm_AddingExistingSearchDoesNotBreak(self):
        '''
          Check that we can call MeetingConfig.createSearches and that if
          a search already exist, it does not break.
        '''
        cfg = self.meetingConfig
        # try to add a topic name 'searchmyitems' that already exist...
        self.assertTrue(hasattr(cfg.searches.searches_items, 'searchmyitems'))
        searchInfo = cfg._searchesInfo().items()[0]
        self.assertEquals(searchInfo[0], 'searchmyitems')
        self.meetingConfig.createSearches(OrderedDict((searchInfo, )))
        # we can evrn call it again with full searchesInfo
        cfg.createSearches(cfg._searchesInfo())

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

    def test_pm_MeetingConfigGroupsCreatedCorrectly(self):
        '''When a meetingConfig is created, some groups are created and configured,
           make sure it is done correctly...'''
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        existingGroupIds = self.portal.portal_groups.getGroupIds()
        # create mymeetings/cfgId folder for 'pmManager'
        self.changeUser('pmManager')
        self.tool.getPloneMeetingFolder(cfgId)
        pmManagerConfigFolder = getattr(self.portal.Members.pmManager.mymeetings, cfgId)
        # different groups are created for each MeetingConfig :
        # powerobservers
        # restrictedpowerobservers
        # budgetimpacteditors
        # meetingmanagers
        # itemtemplatesmanagers
        for suffix in (BUDGETIMPACTEDITORS_GROUP_SUFFIX,
                       POWEROBSERVERS_GROUP_SUFFIX,
                       RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX,
                       MEETINGMANAGERS_GROUP_SUFFIX,
                       ITEMTEMPLATESMANAGERS_GROUP_SUFFIX):
            groupId = '{0}_{1}'.format(cfgId, suffix)
            self.assertTrue(groupId in existingGroupIds)
            # for (restricted)powerobservers, it gets a Reader localrole on tool and MeetingConfig
            if suffix in (POWEROBSERVERS_GROUP_SUFFIX,
                          RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX,
                          ITEMTEMPLATESMANAGERS_GROUP_SUFFIX):
                self.assertTrue(self.tool.__ac_local_roles__[groupId] == [READER_USECASES[suffix], ])
                self.assertTrue(cfg.__ac_local_roles__[groupId] == [READER_USECASES[suffix], ])
            # for meetingmanagers, it gets MeetingManager localrole on MeetingConfig
            # and every users meetingConfig folder
            if suffix == MEETINGMANAGERS_GROUP_SUFFIX:
                self.assertTrue(self.tool.__ac_local_roles__[groupId] == ['MeetingManager', ])
                self.assertTrue(cfg.__ac_local_roles__[groupId] == ['MeetingManager', ])
                # the _meetingmanagers group gets also MeetingManager localrole on every user meetingConfig folder
                self.assertTrue(pmManagerConfigFolder.__ac_local_roles__[groupId] == ['MeetingManager', ])
                # 'pmManager' is in each _meetingmanagers group
                self.assertTrue(groupId in self.member.getGroups())
            # for itemtemplatesmanagers, it gets a Manager localrole on itemtemplates MC subfolder
            if suffix == ITEMTEMPLATESMANAGERS_GROUP_SUFFIX:
                self.assertTrue(cfg.itemtemplates.__ac_local_roles__[groupId] == ['Manager'])

    def test_pm_ItemIconColor(self):
        '''When changing itemIconColor on the MeetingConfig, make sure the linked
           portal_type is also updated and the 'getIcon' metadata is updated as well.'''
        # create an item, it is using default itemIconColor, then change and check
        self.changeUser('pmCreator1')
        cfg = self.meetingConfig
        self.assertTrue(cfg.getItemIconColor() == "default")
        itemType = self.portal.portal_types[cfg.getItemTypeName()]
        self.assertTrue(itemType.icon_expr.endswith('MeetingItem.png'))
        # get one item of the config to check that these items are updated too
        itemInConfig = cfg.getRecurringItems()[0]
        item = self.create('MeetingItem')
        # the item's getIcon metadata is correct
        itemBrain = self.portal.portal_catalog(UID=item.UID())[0]
        itemInConfigBrain = self.portal.portal_catalog(UID=itemInConfig.UID(),
                                                       isDefinedInTool=True)[0]
        self.assertTrue(itemBrain.getIcon == getIcon(item)())
        self.assertTrue(itemInConfigBrain.getIcon == getIcon(itemInConfig)())
        otherColor = ITEM_ICON_COLORS[0]
        otherColorIconName = "MeetingItem{0}.png".format(ITEM_ICON_COLORS[0].capitalize())
        cfg.setItemIconColor(otherColor)
        cfg.at_post_edit_script()
        # portal_type was updated
        self.assertTrue(itemType.icon_expr.endswith(otherColorIconName))
        self.assertTrue(itemType.icon_expr_object)
        self.assertTrue(itemType.icon_expr.endswith(otherColorIconName))
        # 'getIcon' metadata was updated
        itemBrain = self.portal.portal_catalog(UID=item.UID())[0]
        itemInConfigBrain = self.portal.portal_catalog(UID=itemInConfig.UID(),
                                                       isDefinedInTool=True)[0]
        self.assertTrue(itemBrain.getIcon == getIcon(item)())
        self.assertTrue(itemInConfigBrain.getIcon == getIcon(itemInConfig)())

    def test_pm_CanNotRemoveUsedMeetingConfig(self):
        '''While removing a MeetingConfig, it should raise if it is used somewhere...'''
        cfg = self.meetingConfig
        cfgId = cfg.getId()

        # a user can not delete the MeetingConfig
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, self.tool.manage_delObjects, [cfgId, ])

        # fails if items left in the meetingConfig
        # we have recurring items
        self.changeUser('admin')
        self.assertTrue(cfg.getRecurringItems())
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingitem_container = \
            translate('can_not_delete_meetingitem_container',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_meetingitem_container)
        self._removeConfigObjectsFor(cfg)

        # fails if a meeting exists
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date='2008/06/23 15:39:00')
        self.changeUser('admin')
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meeting = \
            translate('can_not_delete_meetingconfig_meeting',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_meetingconfig_meeting)
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())

        # fails if an item exists
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.changeUser('admin')
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meetingitem = \
            translate('can_not_delete_meetingconfig_meetingitem',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_meetingconfig_meetingitem)
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())

        # fails if another element then searches_xxx folder exists in the pmFolders
        self.changeUser('pmManager')
        pmFolder = self.tool.getPloneMeetingFolder(cfgId)
        afileId = pmFolder.invokeFactory('File', id='afile')
        afile = getattr(pmFolder, afileId)
        self.changeUser('admin')
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meetingfolder = \
            translate('can_not_delete_meetingconfig_meetingfolder',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_meetingconfig_meetingfolder)
        self.portal.restrictedTraverse('@@delete_givenuid')(afile.UID())

        self.assertTrue(cfgId in self.tool.objectIds())
        self.tool.manage_delObjects([cfgId, ])
        self.assertFalse(cfgId in self.tool.objectIds())

    def test_pm_ConfigLinkedGroupsRemovedWhenConfigDeleted(self, ):
        """When the MeetingConfig is deleted, created groups are removed too :
           - meetingmanagers group;
           - powerobservers groups;
           - budgetimpacteditors group;
           - itemtemplatesmanagers group.
           """
        self.changeUser('siteadmin')
        newCfg = self.create('MeetingConfig')
        newCfgId = newCfg.getId()
        # this created 5 groups
        created_groups = [groupId for groupId in self.portal.portal_groups.listGroupIds()
                          if groupId.startswith(newCfgId)]
        self.assertEquals(len(created_groups), 5)
        # remove the MeetingConfig, groups are removed as well
        self.tool.restrictedTraverse('@@delete_givenuid')(newCfg.UID())
        self.assertFalse(newCfgId in self.tool.objectIds())
        created_groups = [groupId for groupId in self.portal.portal_groups.listGroupIds()
                          if groupId.startswith(newCfgId)]
        self.assertFalse(created_groups)

    def test_pm_SynchSearches(self):
        '''Test the synchSearches functionnality.'''
        cfg = self.meetingConfig
        # correctly synchronized when a new pmFolder is created
        createdFolders = [info[0] for info in cfg.subFoldersInfo[TOOL_FOLDER_SEARCHES][2]]
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        for createdFolder in createdFolders:
            self.assertTrue(createdFolder in pmFolder.objectIds('ATFolder'))

    def test_pm_GetRecurringItems(self):
        """Test the MeetingConfig.getRecurringItems method."""
        self.changeUser('admin')
        cfg = self.meetingConfig
        # by default, returns active recurring items
        self.assertTrue([item.getId() for item in cfg.getRecurringItems()] ==
                        cfg.recurringitems.objectIds('MeetingItem'))
        # disbable first recurring item
        recItem1 = cfg.getRecurringItems()[0]
        self.do(recItem1, 'deactivate')
        self.assertTrue(recItem1.queryState() == 'inactive')
        activeRecItems = cfg.recurringitems.objectIds('MeetingItem')
        activeRecItems.remove(recItem1.getId())
        self.assertTrue([item.getId() for item in cfg.getRecurringItems()] == activeRecItems)
        # but we may nevertheless get also inactive items
        self.assertTrue([item.getId() for item in cfg.getRecurringItems(onlyActive=False)] ==
                        cfg.recurringitems.objectIds('MeetingItem'))

    def test_pm_NewDashboardCollectionColumns(self):
        """When a new collection is added, on save the right columns are selected
           from what is defined in the MeetingConfig.itemColumns or MeetingConfig.meetingColumns."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        searches = cfg.searches
        # item related collection
        newItemColId = searches.searches_items.invokeFactory('DashboardCollection', id='newItemCol')
        newItemCol = getattr(searches.searches_items, newItemColId)
        newItemCol.processForm(values={'dummy': None})
        itemColumns = list(cfg.getItemColumns())
        for column in DEFAULT_ITEM_COLUMNS:
            itemColumns.insert(column['position'], column['name'])
        self.assertEquals(newItemCol.getCustomViewFields(), tuple(itemColumns))
        # meeting related collection
        newMeetingColId = searches.searches_meetings.invokeFactory('DashboardCollection', id='newMeetingCol')
        newMeetingCol = getattr(searches.searches_meetings, newMeetingColId)
        newMeetingCol.processForm(values={'dummy': None})
        meetingColumns = list(cfg.getMeetingColumns())
        for column in DEFAULT_MEETING_COLUMNS:
            meetingColumns.insert(column['position'], column['name'])
        self.assertEquals(newMeetingCol.getCustomViewFields(), tuple(meetingColumns))
        # decision related collection
        newDecisionColId = searches.searches_decisions.invokeFactory('DashboardCollection', id='newDecisionCol')
        newDecisionCol = getattr(searches.searches_decisions, newDecisionColId)
        newDecisionCol.processForm(values={'dummy': None})
        self.assertEquals(newDecisionCol.getCustomViewFields(), tuple(meetingColumns))

    def test_pm_WorkflowsForGeneratedTypes(self):
        """Workflows used for the generated Meeting and MeetigItem portal_types
           are duplicated versions of what is selected in the MeetingConfig so it
           is possible to use the same workflow for several MeetingConfigs."""
        # Meeting and MeetingItem type is using a generated workflow
        cfg = self.meetingConfig
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        meetingWF = self.wfTool.getWorkflowsFor(cfg.getMeetingTypeName())[0]
        self.assertEquals(itemWF.id, '{0}__{1}'.format(cfg.getId(), cfg.getItemWorkflow()))
        self.assertEquals(itemWF.title, '{0}__{1}'.format(cfg.getId(), cfg.getItemWorkflow()))
        self.assertEquals(meetingWF.id, '{0}__{1}'.format(cfg.getId(), cfg.getMeetingWorkflow()))
        self.assertEquals(meetingWF.title, '{0}__{1}'.format(cfg.getId(), cfg.getMeetingWorkflow()))
        # MeetingItemTemplate and MeetingItemRecurring continue to use the activation_workflow
        itemRecurringWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName('MeetingItemRecurring'))[0]
        itemTemplateWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName('MeetingItemTemplate'))[0]
        self.assertEquals(itemRecurringWF.id, 'plonemeeting_activity_managers_workflow')
        self.assertEquals(itemTemplateWF.id, 'plonemeeting_activity_managers_workflow')

    def test_pm_UpdateAnnexConfidentiality(self):
        """Test the 'updateAnnexConfidentiality' method that will initialize every existing
           annexes to the default confidentiality defined on the annex type.  This is used
           when enabling confidentialty on an existing application."""
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # default value is used
        category = get_category_object(annex, annex.content_category)
        self.assertFalse(category.confidential)
        self.assertFalse(annex.confidential)

        # change default then update existing annexes
        category.confidential = True
        # raise Unauthorized if not Manager
        self.assertRaises(Unauthorized, self.meetingConfig.updateAnnexConfidentiality)
        self.changeUser('admin')
        self.meetingConfig.updateAnnexConfidentiality()
        # as the confidentiality was not enabled, nothing changed
        category_group = category.get_category_group()
        self.assertFalse(category_group.confidentiality_activated)
        self.assertFalse(annex.confidential)
        # now with confidentiality activated, default is set to True
        category_group.confidentiality_activated = True
        self.meetingConfig.updateAnnexConfidentiality()
        self.assertTrue(annex.confidential)

    def test_pm_ItemInConfigIsNotPastableToAnotherMC(self):
        """ """
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2

        # item template
        item_template = cfg.itemtemplates.objectValues()[0]
        copied_data = cfg.itemtemplates.manage_copyObjects(ids=[item_template.getId()])
        # pastable locally
        self.assertEqual(len(cfg.itemtemplates.objectIds()), 2)
        cfg.itemtemplates.manage_pasteObjects(copied_data)
        self.assertEqual(len(cfg.itemtemplates.objectIds()), 3)
        # but not to another MC
        self.assertRaises(Unauthorized,
                          cfg2.itemtemplates.manage_pasteObjects, copied_data)

        # recurring item
        rec_item = cfg.recurringitems.objectValues()[0]
        copied_data = cfg.recurringitems.manage_copyObjects(ids=[rec_item.getId()])
        # pastable locally
        self.assertEqual(len(cfg.recurringitems.objectIds()), 2)
        cfg.recurringitems.manage_pasteObjects(copied_data)
        self.assertEqual(len(cfg.recurringitems.objectIds()), 3)
        # but not to another MC
        self.assertRaises(Unauthorized,
                          cfg2.recurringitems.manage_pasteObjects, copied_data)

    def test_pm_MaxShownListings(self):
        """Field MeetingConfig.maxShownListings is synchronized with faceted filter 'resultsperpage'."""
        # default value works while used in import_data, default is '100' here
        cfg = self.meetingConfig
        self.assertEqual(cfg.getMaxShownListings(), u'100')
        # no resultsperpage widget on 'cfg.searches'
        self.assertIsNone(
            _get_criterion(
                cfg.searches,
                ResultsPerPageWidget.widget_type)
            )
        # filter on searches_items is synchronized
        criterion = _get_criterion(cfg.searches.searches_items, ResultsPerPageWidget.widget_type)
        # sync from cfg to faceted widget
        self.assertEqual(criterion.default, u'100')
        cfg.setMaxShownListings('80')
        self.assertEqual(criterion.default, u'80')
        self.assertEqual(cfg.getMaxShownListings(), u'80')
        # sync from faceted widget to cfg
        criterion.default = u'60'
        self.assertEqual(criterion.default, u'60')
        self.assertEqual(cfg.getMaxShownListings(), u'60')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingConfig, prefix='test_pm_'))
    return suite
