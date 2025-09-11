# -*- coding: utf-8 -*-
#
# File: testMeetingConfig.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collections import OrderedDict
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.contact.plonegroup.utils import select_org_for_function
from collective.eeafaceted.collectionwidget.utils import _get_criterion
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.collectionwidget.utils import getCollectionLinkCriterion
from collective.iconifiedcategory.utils import _categorized_elements
from collective.iconifiedcategory.utils import get_category_object
from copy import deepcopy
from DateTime import DateTime
from datetime import datetime
from datetime import timedelta
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget
from ftw.labels.interfaces import ILabeling
from ftw.labels.interfaces import ILabelJar
from imio.helpers.content import get_vocab
from imio.helpers.content import get_vocab_values
from imio.helpers.workflow import get_leading_transitions
from OFS.ObjectManager import BeforeDeleteException
from plone import api
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.CatalogTool import getIcon
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import DEFAULT_ITEM_COLUMNS
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES
from Products.PloneMeeting.config import DEFAULT_MEETING_COLUMNS
from Products.PloneMeeting.config import EXECUTE_EXPR_VALUE
from Products.PloneMeeting.config import ITEM_ICON_COLORS
from Products.PloneMeeting.config import ITEMTEMPLATESMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETING_REMOVE_MOG_WFA
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import TOOL_FOLDER_SEARCHES
from Products.PloneMeeting.config import WriteHarmlessConfig
from Products.PloneMeeting.content.meeting import default_committees
from Products.PloneMeeting.events import _itemAnnexTypes
from Products.PloneMeeting.interfaces import IConfigElement
from Products.PloneMeeting.MeetingConfig import DUPLICATE_SHORT_NAME
from Products.PloneMeeting.tests.PloneMeetingTestCase import DefaultData
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import createOrUpdatePloneGroup
from Products.PloneMeeting.utils import sendMailIfRelevant
from zope.event import notify
from zope.i18n import translate
from zope.lifecycleevent import ObjectModifiedEvent


MC_GROUP_SUFFIXES = (
    BUDGETIMPACTEDITORS_GROUP_SUFFIX,
    'powerobservers',
    'restrictedpowerobservers',
    MEETINGMANAGERS_GROUP_SUFFIX,
    ITEMTEMPLATESMANAGERS_GROUP_SUFFIX)


class testMeetingConfig(PloneMeetingTestCase):
    '''Tests the MeetingConfig class methods.'''

    def test_pm_Validate_shortName(self):
        '''Test the MeetingConfig.shortName validate method.
           This validates that the shortName is unique across every MeetingConfigs.'''
        self.changeUser("siteadmin")
        cfg = self.meetingConfig
        cfg2Name = self.meetingConfig2.getShortName()
        # can validate it's own shortName
        self.assertFalse(cfg.validate_shortName(cfg.getShortName()))
        # can validate an unknown shortName
        self.assertFalse(cfg.validate_shortName('other-short-name'))
        self.assertEqual(cfg.validate_shortName(cfg2Name),
                         DUPLICATE_SHORT_NAME % cfg2Name)
        # test the validate method as it is monkeypatched
        self.request.form["shortName"] = cfg2Name
        self.assertEqual(cfg.validate(REQUEST=self.request, data=self.request.form),
                         {"shortName": DUPLICATE_SHORT_NAME % cfg2Name})

    def test_pm_Validate_customAdvisersSameRowIdForDifferentRows(self):
        '''This validates that there can not be several rows having same 'row_id'.
           This could happen when creating MeetingConfig from an import_data.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [
            {'row_id': 'unique_id_001',
             'org': self.vendors_uid,
             'gives_auto_advice_on': 'python:True',
             'for_item_created_from': '2012/01/01',
             'for_item_created_until': '',
             'gives_auto_advice_on_help_message': '',
             'delay': '',
             'delay_left_alert': '',
             'delay_label': '',
             'available_on': '',
             'is_linked_to_previous_row': '0', },
            {'row_id': 'unique_id_001',
             'org': self.vendors_uid,
             'gives_auto_advice_on': 'python:True',
             'for_item_created_from': '2012/01/01',
             'for_item_created_until': '',
             'gives_auto_advice_on_help_message': '',
             'delay': '',
             'delay_left_alert': '',
             'delay_label': '',
             'available_on': '',
             'is_linked_to_previous_row': '0', },
        ]
        same_row_ids_msg = translate('custom_adviser_can_not_use_same_row_id_for_different_rows',
                                     domain='PloneMeeting',
                                     context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), same_row_ids_msg)
        # same if we have 3 times the same roid
        customAdvisers = [
            {'row_id': 'unique_id_001',
             'org': self.vendors_uid,
             'gives_auto_advice_on': 'python:True',
             'for_item_created_from': '2012/01/01',
             'for_item_created_until': '',
             'gives_auto_advice_on_help_message': '',
             'delay': '',
             'delay_left_alert': '',
             'delay_label': '',
             'available_on': '',
             'is_linked_to_previous_row': '0', },
            {'row_id': 'unique_id_001',
             'org': self.vendors_uid,
             'gives_auto_advice_on': 'python:True',
             'for_item_created_from': '2012/01/01',
             'for_item_created_until': '',
             'gives_auto_advice_on_help_message': '',
             'delay': '',
             'delay_left_alert': '',
             'delay_label': '',
             'available_on': '',
             'is_linked_to_previous_row': '0', },
            {'row_id': 'unique_id_001',
             'org': self.vendors_uid,
             'gives_auto_advice_on': 'python:True',
             'for_item_created_from': '2012/01/01',
             'for_item_created_until': '',
             'gives_auto_advice_on_help_message': '',
             'delay': '',
             'delay_left_alert': '',
             'delay_label': '',
             'available_on': '',
             'is_linked_to_previous_row': '0', }
        ]
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), same_row_ids_msg)

    def test_pm_Validate_customAdvisersEnoughData(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates that enough columns are filled, either the 'delay' or the
           'gives_auto_advice_on' column must be filled.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
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
        org = get_organization(customAdvisers[0]['org'])
        empty_columns_msg = translate('custom_adviser_not_enough_columns_filled',
                                      domain='PloneMeeting',
                                      mapping={'groupName': org.get_full_title()},
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
                               'org': self.vendors_uid,
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
        self.changeUser('siteadmin')
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           # wrong date format, should have been '2012/12/31'
                           'for_item_created_from': '2012/31/12',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', }, ]
        org = get_organization(customAdvisers[0]['org'])
        wrong_date_msg = translate('custom_adviser_wrong_date_format',
                                   domain='PloneMeeting',
                                   mapping={'groupName': org.get_full_title()},
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
        self.changeUser('siteadmin')
        # the validate method returns a translated message if the validation failed
        # wrong format, should be empty or a digit
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
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
        org = get_organization(customAdvisers[0]['org'])
        wrong_delay_msg = translate('custom_adviser_wrong_delay_format',
                                    domain='PloneMeeting',
                                    mapping={'groupName': org.get_full_title()},
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
                                     mapping={'groupName': org.get_full_title()},
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
                                       mapping={'groupName': org.get_full_title()},
                                       context=self.portal.REQUEST)
        customAdvisers[0]['delay'] = ''
        self.assertTrue(cfg.validate_customAdvisers(customAdvisers) == delay_required_msg)

    def test_pm_Validate_customAdvisersCanNotChangeUsedConfig(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates that if a configuration is already in use, logical data can
           not be changed anymore, only basic data can be changed.'''
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # first check that we can edit an unused configuration
        self.changeUser('admin')
        cfg = self.meetingConfig
        originalCustomAdvisers = {'row_id': 'unique_id_123',
                                  'org': self.developers_uid,
                                  'gives_auto_advice_on': 'item/getBudgetRelated',
                                  'for_item_created_from': '2012/01/01',
                                  'for_item_created_until': '',
                                  'gives_auto_advice_on_help_message': 'Auto help message',
                                  'delay': '10',
                                  'delay_left_alert': '',
                                  'delay_label': 'Delay label',
                                  'is_delay_calendar_days': '0',
                                  'available_on': '',
                                  'is_linked_to_previous_row': '0', }
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
        # change everything including logical data
        now = datetime.now()
        changedCustomAdvisers = {'row_id': 'unique_id_123',
                                 'org': self.vendors_uid,
                                 'gives_auto_advice_on': 'not:item/getBudgetRelated',
                                 'for_item_created_from': '2013/01/01',
                                 'for_item_created_until': (now + timedelta(days=10)).strftime('%Y/%m/%d'),
                                 'gives_auto_advice_on_help_message': 'Auto help message changed',
                                 'delay': '20',
                                 'delay_left_alert': '',
                                 'delay_label': 'Delay label changed',
                                 'is_delay_calendar_days': '1',
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
        self.assertEqual(item.adviceIndex[self.developers_uid]['row_id'], 'unique_id_123')
        # current config is still valid
        self.failIf(cfg.validate_customAdvisers([originalCustomAdvisers, ]))
        # now we can not change a logical field, aka
        # 'group', 'gives_auto_advice_on', 'for_item_created_from' and 'delay'
        logical_fields_wrong_values_mapping = {
            'org': self.vendors_uid,
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
            'is_delay_calendar_days': '1',
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

        # we can not remove an used row
        can_not_remove_msg = translate('custom_adviser_can_not_remove_used_row',
                                       domain='PloneMeeting',
                                       mapping={'item_url': item.absolute_url(),
                                                'adviser_group': 'Developers', },
                                       context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers([]), can_not_remove_msg)

        # if the 'for_item_created_until' date was set, it validates if not changed
        # even if the 'for_item_created_until' is now past
        customAdvisersCreatedUntilSetAndPast = \
            {'row_id': 'unique_id_123',
             'org': self.vendors_uid,
             'gives_auto_advice_on': 'not:item/getBudgetRelated',
             'for_item_created_from': '2013/01/01',
             'for_item_created_until': '2013/01/15',
             'gives_auto_advice_on_help_message': 'Auto help message changed',
             'delay': '20',
             'delay_left_alert': '',
             'delay_label': 'Delay label changed',
             'is_delay_calendar_days': '0',
             'available_on': '',
             'is_linked_to_previous_row': '0', }
        cfg.setCustomAdvisers([customAdvisersCreatedUntilSetAndPast, ])
        self.failIf(cfg.validate_customAdvisers([customAdvisersCreatedUntilSetAndPast, ]))

        # the 'for_item_created_from' may be changed if it is not an 'auto' advice
        customAdvisersNotAutoChangedCreatedFrom = \
            {'row_id': 'unique_id_123',
             'org': self.vendors_uid,
             'gives_auto_advice_on': '',
             'for_item_created_from': '2013/01/01',
             'for_item_created_until': '2013/01/15',
             'gives_auto_advice_on_help_message': 'Auto help message changed',
             'delay': '20',
             'delay_left_alert': '',
             'delay_label': 'Delay label changed',
             'is_delay_calendar_days': '0',
             'available_on': '',
             'is_linked_to_previous_row': '0', }
        cfg.setCustomAdvisers([customAdvisersNotAutoChangedCreatedFrom, ])
        customAdvisersNotAutoChangedCreatedFrom['for_item_created_from'] = '2010/01/01'
        self.failIf(cfg.validate_customAdvisers([customAdvisersNotAutoChangedCreatedFrom, ]))
        # but can not be changed for an "auto" adviser
        customAdvisersNotAutoChangedCreatedFrom['gives_auto_advice_on'] = 'python: True'
        cfg.setCustomAdvisers([customAdvisersNotAutoChangedCreatedFrom, ])
        customAdvisersNotAutoChangedCreatedFrom['for_item_created_from'] = '2009/01/01'
        # does not validate
        self.failUnless(cfg.validate_customAdvisers([customAdvisersNotAutoChangedCreatedFrom, ]))

    def test_pm_Validate_customAdvisersDelayAwareConfigRemovableIfNotUsed(self):
        '''Test the MeetingConfig.customAdvisers validate method.'''
        # first check that we can edit an unused configuration
        self.changeUser('admin')
        cfg = self.meetingConfig
        customAdvisers = {'row_id': 'unique_id_123',
                          'org': self.developers_uid,
                          'gives_auto_advice_on': '',
                          'for_item_created_from': '2012/01/01',
                          'for_item_created_until': '',
                          'gives_auto_advice_on_help_message': 'Help message',
                          'delay': '10',
                          'delay_left_alert': '',
                          'delay_label': 'Delay label',
                          'available_on': '',
                          'is_linked_to_previous_row': '0', }
        # validate returns nothing if validation was successful
        self.failIf(cfg.validate_customAdvisers([customAdvisers, ]))
        cfg.setCustomAdvisers([customAdvisers])

        # create an item
        self.changeUser('pmCreator1')
        item = self.create(
            'MeetingItem',
            optionalAdvisers=['{0}__rowid__unique_id_123'.format(self.developers_uid)])
        # can not remove configuration
        self.failUnless(cfg.validate_customAdvisers([]))
        item.setOptionalAdvisers([])
        item._update_after_edit()
        # now may be removed
        self.failIf(cfg.validate_customAdvisers([]))

    def test_pm_Validate_customAdvisersAvailableOn(self):
        '''Test the MeetingConfig.customAdvisers validate method.
           This validates that available_on can only be used if nothing is defined
           in the 'gives_auto_advice_on' column.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # the validate method returns a translated message if the validation failed
        # wrong date format, should be YYYY/MM/DD
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           # empty
                           'gives_auto_advice_on': 'python: item.getBudgetRelated()',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': 'python: item.getItemIsSigned()',
                           'is_linked_to_previous_row': '0', }, ]
        org = get_organization(customAdvisers[0]['org'])
        available_on_msg = translate('custom_adviser_can_not_available_on_and_gives_auto_advice_on',
                                     domain='PloneMeeting',
                                     mapping={'groupName': org.get_full_title()},
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
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
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
        self.changeUser('siteadmin')
        # the validate method returns a translated message if the validation failed
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': 'python:True',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', }, ]
        org = get_organization(customAdvisers[0]['org'])

        # check that 'is_linked_to_previous_row'
        # can not be set on the first row
        first_row_msg = translate(
            'custom_adviser_first_row_can_not_be_linked_to_previous',
            domain='PloneMeeting',
            mapping={'groupName': org.get_full_title()},
            context=self.portal.REQUEST)
        customAdvisers[0]['is_linked_to_previous_row'] = '1'
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), first_row_msg)
        customAdvisers[0]['is_linked_to_previous_row'] = '0'

        # check that 'is_linked_to_previous_row'
        # can only be set on a delay-aware row
        customAdvisers.append({'row_id': 'unique_id_456',
                               'org': self.vendors_uid,
                               'gives_auto_advice_on': 'python:True',
                               'for_item_created_from': '2012/12/31',
                               'for_item_created_until': '',
                               'gives_auto_advice_on_help_message': '',
                               'delay': '',
                               'delay_left_alert': '',
                               'delay_label': '',
                               'is_delay_calendar_days': '0',
                               'available_on': '',
                               'is_linked_to_previous_row': '1'})

        # check that 'is_linked_to_previous_row'
        # can only be set on a row that is actually a delay-aware row
        row_not_delay_aware_msg = translate(
            'custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser',
            domain='PloneMeeting',
            mapping={'groupName': org.get_full_title()},
            context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), row_not_delay_aware_msg)

        # check that 'is_linked_to_previous_row'
        # can only be set if previous row is also a delay-aware row
        # make second row a delay aware row, first row is not delay aware
        customAdvisers[1]['delay'] = '5'
        self.assertTrue(customAdvisers[0]['delay'] == '')
        previous_row_not_delay_aware_msg = translate(
            'custom_adviser_is_linked_to_previous_row_with_non_delay_aware_adviser_previous_row',
            domain='PloneMeeting',
            mapping={'groupName': org.get_full_title()},
            context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), previous_row_not_delay_aware_msg)

        # check that if previous row use another group, it does not validate
        # make first row a delay-aware advice, then change group
        customAdvisers[0]['delay'] = '10'
        customAdvisers[0]['org'] = self.developers_uid
        self.assertTrue(not customAdvisers[0]['org'] == customAdvisers[1]['org'])
        previous_row_not_same_group_msg = translate(
            'custom_adviser_can_not_is_linked_to_previous_row_with_other_group',
            domain='PloneMeeting',
            mapping={'groupName': org.get_full_title()},
            context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), previous_row_not_same_group_msg)

        # check that 'is_linked_to_previous_row' value can be changed
        # while NOT already in use by created items
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '5',
                           'delay_left_alert': '2',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', },
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '20',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
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
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '5',
                           'delay_left_alert': '2',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '0', },
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '10',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '20',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_1011',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/12/31',
                           'for_item_created_until': '',
                           'gives_auto_advice_on_help_message': '',
                           'delay': '30',
                           'delay_left_alert': '4',
                           'delay_label': '',
                           'is_delay_calendar_days': '0',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'}]
        cfg.setCustomAdvisers(customAdvisers)
        # for now stored data are ok
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))
        # create an item and ask advice relative to second row, row_id 'unique_id_456'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('{0}__rowid__unique_id_456'.format(self.vendors_uid), ))
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
        self.assertTrue(item.adviceIndex[self.vendors_uid]['row_id'] == customAdvisers[2]['row_id'])
        # current config still does validate correctly
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))

        # disable the second row 'is_linked_to_previous_row' will
        # "break" the chain of linked elements, it is not permitted if
        # one of the element of the chain is in use
        customAdvisers[1]['is_linked_to_previous_row'] = '0'
        isolated_row_msg = translate(
            'custom_adviser_can_not_change_is_linked_to_previous_row_isolating_used_rows',
            domain='PloneMeeting',
            mapping={'item_url': item.absolute_url(),
                     'adviser_group': 'Vendors'},
            context=self.portal.REQUEST)
        # we need to invalidate ram.cache of _findLinkedRowsFor
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), isolated_row_msg)
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
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), changed_used_row_msg)
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
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), changed_row_pos_msg)
        # recover right order
        customAdvisers[1], customAdvisers[2] = customAdvisers[2], customAdvisers[1]

        # can not delete used or chained row
        # delete second row (unused but in the chain)
        secondRow = customAdvisers.pop(1)
        # while removing a row in a chain, it consider first that the chain was changed
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), changed_row_pos_msg)
        customAdvisers.insert(1, secondRow)
        # delete third row (used)
        thirdRow = customAdvisers.pop(2)
        can_not_remove_msg = translate('custom_adviser_can_not_remove_used_row',
                                       domain='PloneMeeting',
                                       mapping={'item_url': item.absolute_url(),
                                                'adviser_group': 'Vendors', },
                                       context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), can_not_remove_msg)
        customAdvisers.insert(2, thirdRow)
        # we can remove the before last row, chained but unused
        customAdvisers.pop(3)
        cfg.setCustomAdvisers(customAdvisers)
        self.failIf(cfg.validate_customAdvisers(cfg.getCustomAdvisers()))

        # check that a non delay aware auto asked row may not be removed when used
        extra_row = {'row_id': 'unique_id_1213',
                     'org': self.developers_uid,
                     'gives_auto_advice_on': 'python: True',
                     'for_item_created_from': '2012/12/31',
                     'for_item_created_until': '',
                     'gives_auto_advice_on_help_message': '',
                     'delay': '',
                     'delay_left_alert': '',
                     'delay_label': '',
                     'is_delay_calendar_days': '0',
                     'available_on': '',
                     'is_linked_to_previous_row': '0'}
        customAdvisers.insert(99, extra_row)
        cfg.setCustomAdvisers(customAdvisers)
        item._update_after_edit()
        self.assertTrue(item.adviceIndex[self.developers_uid]['row_id'] == customAdvisers[-1]['row_id'])
        customAdvisers.pop(-1)
        can_not_remove_msg = translate('custom_adviser_can_not_remove_used_row',
                                       domain='PloneMeeting',
                                       mapping={'item_url': item.absolute_url(),
                                                'adviser_group': 'Developers', },
                                       context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_customAdvisers(customAdvisers), can_not_remove_msg)

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
        self.assertFalse('category' in cfg.getUsedItemAttributes())
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == not_using_categories_error_msg)
        # check on using categories is made on presence of 'category' in 'usedItemAttributes'
        # in the REQUEST, or if not found, on the value defined on the MeetingConfig object
        self._enableField('category')
        # this time it validates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # except if we just redefined it, aka 'category' not in 'usedItemAttributes' in the REQUEST
        used_item_attrs = list(cfg.getUsedItemAttributes())
        used_item_attrs.remove('category')
        self.portal.REQUEST.set('usedItemAttributes', used_item_attrs)
        self.assertTrue(cfg.validate_insertingMethodsOnAddItem(values) == not_using_categories_error_msg)
        self.portal.REQUEST.set('usedItemAttributes', cfg.getUsedItemAttributes())
        # this time it validates as redefining it to using category
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))

        # test when selecting 'on_poll_type' without using the 'pollType' field
        inserting_methods_not_using_poll_type_error_msg = \
            translate('inserting_methods_not_using_poll_type_error',
                      domain='PloneMeeting',
                      context=self.request)
        values = ({'insertingMethod': 'on_poll_type',
                   'reverse': '0'}, )
        self._enableField('pollType')
        del self.request.other['usedItemAttributes']
        # it validates
        self.failIf(cfg.validate_insertingMethodsOnAddItem(values))
        # check on using 'pollType' is made on presence of 'pollType' in 'usedItemAttributes' in the
        # REQUEST, or if not found, on the value defined on the MeetingConfig object
        # unselect 'pollType', validation fails
        usedItemAttrsWithoutPollType = list(cfg.getUsedItemAttributes())
        usedItemAttrsWithoutPollType.remove('pollType')
        self._enableField('pollType', enable=False)
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
        usedItemAttrsWithoutToDiscuss = list(cfg.getUsedItemAttributes())
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
        usedItemAttrsWithoutPrivacy = list(cfg.getUsedItemAttributes())
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
        two_rows_error_msg = translate(
            msgid='can_not_define_two_rows_for_same_meeting_config',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(cfg.validate_meetingConfigsToCloneTo(values),
                         two_rows_error_msg)

        # check that value selected in 'trigger_workflow_transitions_until' correspond
        # to a value of the wf used for the corresponding selected 'meeting_config'
        values = ({'meeting_config': '%s' % cfg2Id,
                   'trigger_workflow_transitions_until': 'wrong-config-id.a_wf_transition'},)
        wrong_wf_transition_error_msg = translate(
            msgid='transition_not_from_selected_meeting_config',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(cfg.validate_meetingConfigsToCloneTo(values),
                         wrong_wf_transition_error_msg)

        # unknown meetingConfig id, this is possible when creating MeetingConfig from a import_data
        values = ({'meeting_config': 'unknown',
                   'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},)
        unknown_error_msg = translate(
            msgid='unknown_meeting_config_id',
            mapping={'meeting_config_id': 'unknown'},
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(cfg.validate_meetingConfigsToCloneTo(values),
                         unknown_error_msg)

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
        self.assertEqual(cfg.validate_listTypes(values), missing_default_msg)

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
        self.assertEqual(cfg.validate_listTypes(values), already_used_msg)
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
        self.assertEqual(cfg.validate_listTypes(valuesWithWrongFormat), wrong_format_msg)

        # already used identifier
        valuesWithDouble = list(values)
        valuesWithDouble.append(values[0])
        double_msg = _('error_list_types_same_identifier')
        self.assertEqual(cfg.validate_listTypes(valuesWithDouble), double_msg)
        self.failIf(cfg.validate_listTypes(values))

    def test_pm_Validate_onMeetingTransitionItemActionToExecute(self):
        '''If a tal_expression is provided, item_action
           must be EXECUTE_EXPR_VALUE and the other way round.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        tal_expr_error_msg = _('on_meeting_transition_item_action_tal_expr_error')
        # missing tal_expression
        values = [{'meeting_transition': 'close',
                   'item_action': EXECUTE_EXPR_VALUE,
                   'tal_expression': ''}]
        self.assertEqual(cfg.validate_onMeetingTransitionItemActionToExecute(values),
                         tal_expr_error_msg)
        # tal_expression defined on a item_action WF transition
        values = [{'meeting_transition': 'close',
                   'item_action': 'accept',
                   'tal_expression': 'item/Title'}]
        self.assertEqual(cfg.validate_onMeetingTransitionItemActionToExecute(values),
                         tal_expr_error_msg)

        # valid
        values = [{'meeting_transition': 'close',
                   'item_action': EXECUTE_EXPR_VALUE,
                   'tal_expression': 'item/Title'},
                  {'meeting_transition': 'close',
                   'item_action': 'accept',
                   'tal_expression': ''}]
        self.failIf(cfg.validate_onMeetingTransitionItemActionToExecute(values))
        # bypass template_row_marker
        values.append({'meeting_transition': 'close',
                       'orderindex_': 'template_row_marker',
                       'item_action': EXECUTE_EXPR_VALUE,
                       'tal_expression': ''})
        self.failIf(cfg.validate_onMeetingTransitionItemActionToExecute(values))
        # 'template_row_marker' is ignored by datagridfield
        cfg.setOnMeetingTransitionItemActionToExecute(values)
        self.assertEqual(cfg.getOnMeetingTransitionItemActionToExecute(),
                         ({'item_action': EXECUTE_EXPR_VALUE,
                           'meeting_transition': 'close',
                           'tal_expression': 'item/Title'},
                          {'item_action': 'accept',
                           'meeting_transition': 'close',
                           'tal_expression': ''}))

    def test_pm_AddingExistingSearchDoesNotBreak(self):
        '''
          Check that we can call MeetingConfig.createSearches and that if
          a search already exist, it does not break.
        '''
        cfg = self.meetingConfig
        # try to add a topic name 'searchmyitems' that already exist...
        self.assertTrue(hasattr(cfg.searches.searches_items, 'searchmyitems'))
        searchInfo = cfg._searchesInfo().items()[0]
        self.assertEqual(searchInfo[0], 'searchmyitems')
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
            if field.getName() in ('showinsearch', 'searchwords'):
                continue
            self.assertTrue(field.write_permission == WriteHarmlessConfig)

    def test_pm_LinkedGroupsCreatedCorrectly(self):
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
        for suffix in MC_GROUP_SUFFIXES:
            groupId = '{0}_{1}'.format(cfgId, suffix)
            self.assertTrue(groupId in existingGroupIds)
            # for (restricted)powerobservers, it gets a Reader localrole on tool and MeetingConfig
            if suffix in ('powerobservers',
                          'restrictedpowerobservers',
                          ITEMTEMPLATESMANAGERS_GROUP_SUFFIX):
                # we have same reader usecase for every powerobservers
                if suffix == 'restrictedpowerobservers':
                    suffix = 'powerobservers'
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
        itemBrain = self.catalog(UID=item.UID())[0]
        itemInConfigBrain = self.catalog(UID=itemInConfig.UID(), isDefinedInTool=True)[0]
        self.assertTrue(itemBrain.getIcon == getIcon(item)())
        self.assertTrue(itemInConfigBrain.getIcon == getIcon(itemInConfig)())
        otherColor = ITEM_ICON_COLORS[0]
        otherColorIconName = "MeetingItem{0}.png".format(ITEM_ICON_COLORS[0].capitalize())
        cfg.setItemIconColor(otherColor)
        notify(ObjectEditedEvent(cfg))
        # portal_type was updated
        self.assertTrue(itemType.icon_expr.endswith(otherColorIconName))
        self.assertTrue(itemType.icon_expr_object)
        self.assertTrue(itemType.icon_expr.endswith(otherColorIconName))
        # 'getIcon' metadata was updated
        itemBrain = self.catalog(UID=item.UID())[0]
        itemInConfigBrain = self.catalog(UID=itemInConfig.UID(), isDefinedInTool=True)[0]
        self.assertTrue(itemBrain.getIcon == getIcon(item)())
        self.assertTrue(itemInConfigBrain.getIcon == getIcon(itemInConfig)())

    def test_pm_CanNotRemoveUsedMeetingConfig(self):
        '''While removing a MeetingConfig, it should raise if it is used somewhere...'''
        # work with cfg2 where meetingConfigsToCloneTo and other_mc_correspondences are defined
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2.setMeetingConfigsToCloneTo(
            ({'meeting_config': cfgId,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},)
        )

        # a user can not delete the MeetingConfig
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, self.tool.manage_delObjects, [cfgId])

        # fails if a meeting exists
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.changeUser('siteadmin')
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meeting = \
            translate('can_not_delete_meetingconfig_meeting',
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_meetingconfig_meeting)
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())

        # fails if an item exists
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.changeUser('siteadmin')
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meetingitem = \
            translate('can_not_delete_meetingconfig_meetingitem',
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_meetingconfig_meetingitem)
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())

        # fails if another element than searches_xxx folder exists in the pmFolders
        self.changeUser('pmManager')
        pmFolder = self.tool.getPloneMeetingFolder(cfgId)
        afileId = pmFolder.invokeFactory('File', id='afile')
        afile = getattr(pmFolder, afileId)
        self.changeUser('siteadmin')
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meetingfolder = \
            translate('can_not_delete_meetingconfig_meetingfolder',
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_meetingconfig_meetingfolder)
        self.portal.restrictedTraverse('@@delete_givenuid')(afile.UID())

        # fails if used in another MeetingConfig (meetingConfigsToCloneTo)
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfgId, ])
        can_not_delete_meetingconfig_meetingconfig = \
            translate('can_not_delete_meetingconfig_meetingconfig',
                      mapping={'other_config_title': cfg2.Title()},
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_meetingconfig_meetingconfig)
        cfg2.setMeetingConfigsToCloneTo(())

        # fails if an annex_type is used by another MeetingConfig annex_type in other_mc_correspondences
        # here we use cfg2 where correspondences are defined
        self._removeConfigObjectsFor(cfg2)
        cfg.setMeetingConfigsToCloneTo(())
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([cfg2Id, ])
        can_not_delete_meetingconfig_annex_types = \
            translate('can_not_delete_meetingconfig_annex_types',
                      mapping={'other_config_title': safe_unicode(cfg.Title())},
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_meetingconfig_annex_types)
        annex_types = _itemAnnexTypes(cfg)
        for annex_type in annex_types:
            annex_type.other_mc_correspondences = set()

        # items stored in MeetingConfig (recurring, itemtemplates) do not avoid removal
        self.assertTrue(cfg.recurringitems.objectIds())
        self.assertTrue(cfg.itemtemplates.objectIds())
        # everything ok, MeetingConfig may be deleted
        self.assertTrue(cfgId in self.tool.objectIds() and cfg2Id in self.tool.objectIds())
        self.tool.manage_delObjects([cfgId, cfg2Id])
        self.assertFalse(cfgId in self.tool.objectIds() or cfg2Id in self.tool.objectIds())
        # elements created by MeetingConfig were deleted (portal_types, groups, metingFolders)
        # portal_types
        all_portal_type_ids = self.portal.portal_types.listContentTypes()
        self.assertEqual([pt for pt in all_portal_type_ids if pt.endswith(cfg.getShortName())], [])
        self.assertEqual([pt for pt in all_portal_type_ids if pt.endswith(cfg2.getShortName())], [])
        # groups, cfg id is suffixed with different values
        all_group_ids = self.portal.portal_groups.listGroupIds()
        self.assertEqual([gr for gr in all_group_ids if gr.startswith('{0}_'.format(cfgId))], [])
        self.assertEqual([gr for gr in all_group_ids if gr.startswith('{0}_'.format(cfg2Id))], [])
        # meetingFolders
        for member_folder in self.portal.Members.objectValues():
            mymeetings = member_folder.get('mymeetings', None)
            if mymeetings:
                self.assertEqual(mymeetings.objectIds(), [])
            else:
                pm_logger.info(
                    "{0}: no 'mymeetings' folder for user '{1}'".format(
                        self._testMethodName, member_folder.id))

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
        self.assertEqual(len(created_groups), 5)
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
        self.assertTrue(recItem1.query_state() == 'inactive')
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
        self.assertEqual(newItemCol.customViewFields, tuple(itemColumns))
        # meeting related collection
        newMeetingColId = searches.searches_meetings.invokeFactory('DashboardCollection', id='newMeetingCol')
        newMeetingCol = getattr(searches.searches_meetings, newMeetingColId)
        newMeetingCol.processForm(values={'dummy': None})
        meetingColumns = list(cfg.getMeetingColumns())
        for column in DEFAULT_MEETING_COLUMNS:
            meetingColumns.insert(column['position'], column['name'])
        self.assertEqual(newMeetingCol.customViewFields, tuple(meetingColumns))
        # decision related collection
        newDecisionColId = searches.searches_decisions.invokeFactory('DashboardCollection', id='newDecisionCol')
        newDecisionCol = getattr(searches.searches_decisions, newDecisionColId)
        newDecisionCol.processForm(values={'dummy': None})
        self.assertEqual(newDecisionCol.customViewFields, tuple(meetingColumns))

    def test_pm_WorkflowsForGeneratedTypes(self):
        """Workflows used for the generated Meeting and MeetigItem portal_types
           are duplicated versions of what is selected in the MeetingConfig so it
           is possible to use the same workflow for several MeetingConfigs."""
        # Meeting and MeetingItem type is using a generated workflow
        cfg = self.meetingConfig
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        meetingWF = self.wfTool.getWorkflowsFor(cfg.getMeetingTypeName())[0]
        self.assertEqual(itemWF.id, '{0}__{1}'.format(cfg.getId(), cfg.getItemWorkflow()))
        self.assertEqual(itemWF.title, '{0}__{1}'.format(cfg.getId(), cfg.getItemWorkflow()))
        self.assertEqual(meetingWF.id, '{0}__{1}'.format(cfg.getId(), cfg.getMeetingWorkflow()))
        self.assertEqual(meetingWF.title, '{0}__{1}'.format(cfg.getId(), cfg.getMeetingWorkflow()))
        # MeetingItemTemplate and MeetingItemRecurring continue to use the activation_workflow
        itemRecurringWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName('MeetingItemRecurring'))[0]
        itemTemplateWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName('MeetingItemTemplate'))[0]
        self.assertEqual(itemRecurringWF.id, 'plonemeeting_activity_managers_workflow')
        self.assertEqual(itemTemplateWF.id, 'plonemeeting_activity_managers_workflow')

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

    def _usersToRemoveFromGroupsForUpdatePersonalLabels(self):
        """ """
        return []

    def test_pm_UpdatePersonalLabels(self):
        """Test the 'updatePersonalLabels' method that will activate a personal label
           on every existing items that were not modified for a given number of days."""
        cfg = self.meetingConfig
        # custom cleanup for profiles having extra roles
        self._removeUsersFromEveryGroups(self._usersToRemoveFromGroupsForUpdatePersonalLabels())
        # do not consider observers group as it changes too often from one WF to another...
        self._removePrincipalFromGroups('pmReviewer1', [self.developers_observers])
        self._removePrincipalFromGroups('pmObserver1', [self.developers_observers])
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        # only for Managers
        self.assertRaises(Unauthorized, cfg.updatePersonalLabels)
        self.changeUser('siteadmin')
        # by default, it only updates items not modified for 30 days
        # so calling it will change nothing
        cfg.updatePersonalLabels(personal_labels=['personal-label'])
        item1_labeling = ILabeling(item1)
        item2_labeling = ILabeling(item2)
        self.assertEqual(item1_labeling.storage, {})
        self.assertEqual(item2_labeling.storage, {})
        cfg.updatePersonalLabels(personal_labels=['personal-label'], modified_since_days=0)
        self.assertEqual(
            sorted(item1_labeling.storage['personal-label']),
            ['budgetimpacteditor', 'pmCreator1', 'pmCreator1b', 'pmManager', 'powerobserver1'])
        self.assertEqual(
            sorted(item2_labeling.storage['personal-label']),
            ['budgetimpacteditor', 'pmCreator1', 'pmCreator1b', 'pmManager', 'powerobserver1'])
        # method takes into account users able to see the items
        # when item is proposed, powerobserver1 may not see it...
        self.proposeItem(item1)
        cfg.updatePersonalLabels(personal_labels=['personal-label'], modified_since_days=0)
        self.assertEqual(
            sorted(item1_labeling.storage['personal-label']),
            ['pmCreator1', 'pmCreator1b', 'pmManager', 'pmReviewer1', 'pmReviewerLevel2'])
        self.assertEqual(
            sorted(item2_labeling.storage['personal-label']),
            ['budgetimpacteditor', 'pmCreator1', 'pmCreator1b', 'pmManager', 'powerobserver1'])

        # test that only items older than given days are updated
        self.proposeItem(item2)
        item2.setModificationDate(DateTime() - 50)
        item2.reindexObject()
        cfg.updatePersonalLabels(personal_labels=['personal-label'], modified_since_days=30)
        # still olf value for item2
        self.assertEqual(
            sorted(item2_labeling.storage['personal-label']),
            ['budgetimpacteditor', 'pmCreator1', 'pmCreator1b', 'pmManager', 'powerobserver1'])

    def test_pm_ItemInConfigIsNotPastableToAnotherMC(self):
        """ """
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2

        # item template
        item_template = cfg.itemtemplates.objectValues()[0]
        copied_data = cfg.itemtemplates.manage_copyObjects(ids=[item_template.getId()])
        # pastable locally
        self.assertEqual(len(cfg.itemtemplates.objectIds()), 3)
        cfg.itemtemplates.manage_pasteObjects(copied_data)
        self.assertEqual(len(cfg.itemtemplates.objectIds()), 4)
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
        # default value works while used in import_data, default is 100 here
        cfg = self.meetingConfig
        self.assertEqual(cfg.getMaxShownListings(), 100)
        # no resultsperpage widget on 'cfg.searches'
        self.assertIsNone(
            _get_criterion(
                cfg.searches,
                ResultsPerPageWidget.widget_type)
        )
        # filter on searches_items is synchronized
        criterion = _get_criterion(cfg.searches.searches_items, ResultsPerPageWidget.widget_type)
        # sync from cfg to faceted widget
        self.assertEqual(criterion.default, 100)
        cfg.setMaxShownListings(80)
        self.assertEqual(criterion.default, 80)
        self.assertEqual(cfg.getMaxShownListings(), 80)
        # sync from faceted widget to cfg
        criterion.default = 60
        self.assertEqual(criterion.default, 60)
        self.assertEqual(cfg.getMaxShownListings(), 60)

    def test_pm_UpdateLinkedPloneGroupsTitle(self):
        '''When the title of a MeetingConfig changed, the title of linked Plone groups is changed accordingly.'''
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfgTitle = cfg.Title()
        for suffix in MC_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(cfgId, suffix))
            self.assertTrue(cfgTitle in ploneGroup.getProperty('title'))

        # update MeetingConfig title and check again
        cfgTitle = 'New cfg title'
        cfg.setTitle(cfgTitle)
        notify(ObjectEditedEvent(cfg))
        # Plone groups title have been updated
        for suffix in MC_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(cfgId, suffix))
            self.assertTrue(cfgTitle in ploneGroup.getProperty('title'))

    def test_pm_LinkedPloneGroupsTitleWhenUsingConfigGroups(self):
        '''When cfg is in a configGroup, the title of created Plone groups is prepended with configGroup title.'''
        self.tool.setConfigGroups(
            (
                {'label': 'ConfigGroup1', 'row_id': 'unique_id_1', 'full_label': 'Config Group 1'},
                {'label': 'ConfigGroup2', 'row_id': 'unique_id_2', 'full_label': 'Config Group 2'},
                {'label': 'ConfigGroup3', 'row_id': 'unique_id_3', 'full_label': 'Config Group 3'},
            )
        )
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        self.assertEqual(cfg.getConfigGroup(), '')
        self.assertEqual(cfg.getConfigGroup(full=True), {})
        for suffix in MC_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(cfgId, suffix))
            self.assertFalse(ploneGroup.getProperty('title').startswith('ConfigGroup1'))

        # use a configGroup and check
        cfg.setConfigGroup('unique_id_1')
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(cfg.getConfigGroup(full=True),
                         {'label': 'ConfigGroup1', 'row_id': 'unique_id_1', 'full_label': 'Config Group 1'})
        # now linked Plone groups contain the configGroup title
        for suffix in MC_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(cfgId, suffix))
            self.assertTrue(ploneGroup.getProperty('title').startswith('ConfigGroup1'))

        # remove configGroup, and check
        cfg.setConfigGroup('')
        notify(ObjectEditedEvent(cfg))
        for suffix in MC_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(cfgId, suffix))
            self.assertFalse(ploneGroup.getProperty('title').startswith('ConfigGroup1'))

    def test_pm_ConfigFolderModifiedOnConfigFolderReorder(self):
        """When a subfolder of the MeetingConfig is reordered,
           the folder modification date is updated."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        categories_modified = cfg.categories.modified()
        cfg.categories.folder_position(position='up', id='development')
        self.assertNotEqual(categories_modified, cfg.categories.modified())

    def test_pm_Update_cfgs(self):
        """ """
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setWorkflowAdaptations(())
        notify(ObjectEditedEvent(cfg))
        cfg2 = self.meetingConfig2
        cfg2.setWorkflowAdaptations(())
        notify(ObjectEditedEvent(cfg2))
        cfg3 = self.create('MeetingConfig', workflowAdaptations=[])

        # test with normal value
        self.assertEqual(cfg2.getPlaces(), '')
        self.assertEqual(cfg3.getPlaces(), '')
        places = 'Place1\r\nPlace2\r\nPlace3\r\n'
        cfg.setPlaces(places)
        cfg.update_cfgs(field_name='places')
        self.assertEqual(cfg2.getPlaces(), places)
        self.assertEqual(cfg3.getPlaces(), places)

        # test with dict and cfg_ids parameter
        cfg_value = ({'meeting_config': cfg2.getId(),
                      'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},)
        self.assertEqual(cfg.meetingConfigsToCloneTo, cfg_value)
        self.assertEqual(cfg2.meetingConfigsToCloneTo, ())
        self.assertEqual(cfg3.meetingConfigsToCloneTo, ())
        cfg.update_cfgs(field_name='meetingConfigsToCloneTo', cfg_ids=[cfg3.getId()])
        self.assertEqual(cfg.meetingConfigsToCloneTo, cfg_value)
        self.assertEqual(cfg2.meetingConfigsToCloneTo, ())
        self.assertEqual(cfg.meetingConfigsToCloneTo, cfg_value)
        # dict are copy
        cfg.meetingConfigsToCloneTo[0]['meeting_config'] = 'dummy'
        self.assertEqual(cfg.meetingConfigsToCloneTo[0]['meeting_config'], 'dummy')
        self.assertEqual(cfg3.meetingConfigsToCloneTo[0]['meeting_config'], cfg2.getId())
        cfg.meetingConfigsToCloneTo[0]['meeting_config'] = cfg2.getId()

        # if reload=True, at_post_edit_script is called
        # useful to reapply WFAdaptations for example
        # enable 'mark_not_applicable' WFAdaptation that adds the
        # 'marked_not_applicable' state to the item WF
        self.assertEqual(cfg.getWorkflowAdaptations(), ())
        self.assertEqual(cfg2.getWorkflowAdaptations(), ())
        self.assertEqual(cfg3.getWorkflowAdaptations(), ())
        cfg_item_type_name = cfg.getItemTypeName()
        cfg2_item_type_name = cfg2.getItemTypeName()
        cfg3_item_type_name = cfg3.getItemTypeName()
        if 'return_to_proposing_group' in get_vocab_values(cfg, 'WorkflowAdaptations') and \
           'return_to_proposing_group' in get_vocab_values(cfg2, 'WorkflowAdaptations') and \
           'return_to_proposing_group' in get_vocab_values(cfg3, 'WorkflowAdaptations'):
            wfFor = self.wfTool.getWorkflowsFor
            self.assertFalse('returned_to_proposing_group' in wfFor(cfg_item_type_name)[0].states)
            self.assertFalse('returned_to_proposing_group' in wfFor(cfg2_item_type_name)[0].states)
            self.assertFalse('returned_to_proposing_group' in wfFor(cfg3_item_type_name)[0].states)
            cfg3.setWorkflowAdaptations(('return_to_proposing_group', ))
            notify(ObjectEditedEvent(cfg3))
            cfg3.update_cfgs(field_name='workflowAdaptations', reload=False)
            self.assertFalse('returned_to_proposing_group' in wfFor(cfg_item_type_name)[0].states)
            self.assertFalse('returned_to_proposing_group' in wfFor(cfg2_item_type_name)[0].states)
            self.assertTrue('returned_to_proposing_group' in wfFor(cfg3_item_type_name)[0].states)
            cfg3.update_cfgs(field_name='workflowAdaptations', reload=True)
            self.assertTrue('returned_to_proposing_group' in wfFor(cfg_item_type_name)[0].states)
            self.assertTrue('returned_to_proposing_group' in wfFor(cfg2_item_type_name)[0].states)
            self.assertTrue('returned_to_proposing_group' in wfFor(cfg3_item_type_name)[0].states)
        else:
            pm_logger.info("Could not test reload in test_pm_update_cfgs because wfAdaptation "
                           "'return_to_proposing_group' is not available")

    def test_pm_ConfigModifiedWhenFacetedChanged(self):
        """When faceted settings are changed (changed default collection in collectionwidget),
           MeetingConfig is modified (so cache is invalidated)."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # change default collection, change from searchallitems to searchmyitems
        searches_items = cfg.searches.searches_items
        self.assertEqual(getCollectionLinkCriterion(searches_items).default, searches_items.searchallitems.UID())
        # _updateDefaultCollectionFor will trigger the event
        original_cfg_modified = cfg.modified()
        _updateDefaultCollectionFor(searches_items, searches_items.searchmyitems.UID())
        self.assertNotEqual(original_cfg_modified, cfg.modified())

    def test_pm_ItemInConfigProvidesIConfigElementNotOtherItems(self):
        """Item created in MeetingConfig (recurring, itemtemplate) will provide IConfigElement,
           but not items created in the application."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # recurring item
        recurring_item = cfg.recurringitems.objectValues()[0]
        self.assertTrue(IConfigElement.providedBy(recurring_item))
        # item template
        item_template = cfg.itemtemplates.objectValues()[0]
        self.assertTrue(IConfigElement.providedBy(item_template))

        # fresh item
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.assertFalse(IConfigElement.providedBy(item))
        # item from item template
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemFromTemplate = view.createItemFromTemplate(item_template.UID())
        self.assertFalse(IConfigElement.providedBy(itemFromTemplate))
        # recurring item
        meeting = self.create('Meeting')
        recurring_item = meeting.get_items()[0]
        self.assertFalse(IConfigElement.providedBy(recurring_item))

    def test_pm_ConfigModifiedWhenConfigElementAddedModifiedRemoved(self):
        """When any element contained in a MeetingConfig is added/modified/removed,
           MeetingConfig.modified is updated so caching is invalidated."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        original_cfg_modified = cfg.modified()

        # edit a POD template
        pod_template = [pod_template for pod_template in cfg.podtemplates.objectValues()
                        if pod_template.portal_type == 'ConfigurablePODTemplate'][0]
        notify(ObjectModifiedEvent(pod_template))
        pod_template_cfg_modified = cfg.modified()
        self.assertNotEqual(original_cfg_modified, pod_template_cfg_modified)

        # edit a POD style template
        style_template = [style_template for style_template in cfg.podtemplates.objectValues()
                          if style_template.portal_type == 'StyleTemplate'][0]
        notify(ObjectModifiedEvent(style_template))
        style_template_cfg_modified = cfg.modified()
        self.assertNotEqual(pod_template_cfg_modified, style_template_cfg_modified)

        # edit a ContentCategory
        content_category = cfg.annexes_types.item_annexes.objectValues()[0]
        notify(ObjectModifiedEvent(content_category))
        content_category_cfg_modified = cfg.modified()
        self.assertNotEqual(style_template_cfg_modified, content_category_cfg_modified)

        # edit a meetingcategory
        category = cfg.categories.objectValues()[0]
        notify(ObjectModifiedEvent(category))
        category_cfg_modified = cfg.modified()
        self.assertNotEqual(content_category_cfg_modified, category_cfg_modified)

        # edit a Collection
        collection = cfg.searches.searches_items.objectValues()[0]
        notify(ObjectModifiedEvent(collection))
        collection_cfg_modified = cfg.modified()
        self.assertNotEqual(category_cfg_modified, collection_cfg_modified)

        # recurring item
        recurring_item = cfg.recurringitems.objectValues()[0]
        notify(ObjectModifiedEvent(recurring_item))
        recurring_item_cfg_modified = cfg.modified()
        self.assertNotEqual(collection_cfg_modified, recurring_item_cfg_modified)

        # item template
        item_template = cfg.itemtemplates.objectValues()[0]
        notify(ObjectModifiedEvent(item_template))
        item_template_cfg_modified = cfg.modified()
        self.assertNotEqual(recurring_item_cfg_modified, item_template_cfg_modified)

        # test add and remove a POD template using pod_template_to_use
        # add
        new_pod_template = self.create(
            'ConfigurablePODTemplate',
            pod_template_to_use=cfg.podtemplates.itemTemplate.UID())
        new_pod_template_cfg_modified = cfg.modified()
        self.assertNotEqual(item_template_cfg_modified, new_pod_template_cfg_modified)
        # remove
        self.deleteAsManager(new_pod_template.UID())
        new_pod_template_removed_cfg_modified = cfg.modified()
        self.assertNotEqual(new_pod_template_cfg_modified, new_pod_template_removed_cfg_modified)

    def test_pm_UsedLabelCanNotBeRemoved(self):
        """A ftw.labels label that is used on an item can not be removed."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # add a label
        labelingview = item.restrictedTraverse('@@labeling')
        self.request.form['activate_labels'] = ['label']
        labelingview.update()
        item_labeling = ILabeling(item)
        self.assertEqual(item_labeling.storage, {'label': []})
        jar = ILabelJar(cfg)
        self.assertTrue('label' in jar.storage)
        # trying to remove a used label will redirect and show a message
        # but the label is not removed
        jar.remove(label_id='label')
        self.assertTrue('label' in jar.storage)
        self.request.form['activate_labels'] = []
        labelingview.update()
        self.assertEqual(item_labeling.storage, {})
        self.assertTrue(jar.remove(label_id='label'))
        self.assertFalse('label' in jar.storage)

    def test_pm_ConfigModifiedWhenFTWLabelManaged(self):
        """MeetingConfig is modified when a label is added/updated/removed.
           As the 'Products.PloneMeeting.vocabularies.ftwlabelsforfacetedfiltervocabulary'
           relies on MeetingConfig modified, it's cache is invalidated as well."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        jar = ILabelJar(cfg)
        # vocabulary
        pmFolder = self.getMeetingFolder()
        vocab_factory = get_vocab(
            pmFolder,
            'Products.PloneMeeting.vocabularies.ftwlabelsforfacetedfiltervocabulary',
            only_factory=True)
        # add a label
        label_id = 'new-added-label'
        self.assertFalse(label_id in vocab_factory(pmFolder))
        config_modified_before_add = cfg.modified()
        jar.add(title='New added label', color='red', by_user=False)
        self.assertTrue(cfg.modified() > config_modified_before_add)
        self.assertTrue(label_id in vocab_factory(pmFolder))
        self.assertEqual(vocab_factory(pmFolder).getTerm(label_id).title, 'New added label')

        # update a label
        config_modified_before_update = cfg.modified()
        jar.update(label_id='new-added-label',
                   title='New added label2',
                   color='red',
                   by_user=False)
        self.assertTrue(cfg.modified() > config_modified_before_update)
        self.assertEqual(vocab_factory(pmFolder).getTerm(label_id).title, 'New added label2')

        # remove a label
        config_modified_before_remove = cfg.modified()
        jar.remove('new-added-label')
        self.assertTrue(cfg.modified() > config_modified_before_remove)
        self.assertFalse(label_id in vocab_factory(pmFolder))

    def test_pm_Validate_powerObservers(self):
        '''Test the MeetingConfig.powerObservers validation.
           We check that :
           - we do not have same value for 'label';
           - if we remove a line :
             - the power observer is not used in any other MeetingConfig fields;
             - not used in a 'hide_decisions_when_under_writing'__po__' wfa;
             - the linked Plone groups is empty.'''
        cfg = self.meetingConfig
        values = [
            {'item_access_on': '',
             'item_states': ['accepted'],
             'label': 'Power observers \xc3\xa9',
             'meeting_access_on': '',
             'meeting_states': ['closed'],
             'orderindex_': '1',
             'row_id': 'powerobservers'},
            {'item_access_on': '',
             'item_states': ['accepted'],
             'label': 'Restricted power observers \xc3\xa9',
             'meeting_access_on': '',
             'meeting_states': ['closed'],
             'orderindex_': '2',
             'row_id': 'restrictedpowerobservers'},
            {'item_access_on': '',
             'item_states': [],
             'label': '',
             'meeting_access_on': '',
             'meeting_states': [],
             'orderindex_': 'template_row_marker',
             'row_id': ''}]

        self.assertFalse(cfg.validate_powerObservers(values))

        # twice same label
        values = [
            {'item_access_on': '',
             'item_states': ['accepted'],
             'label': 'Label',
             'meeting_access_on': '',
             'meeting_states': ['closed'],
             'orderindex_': '1',
             'row_id': 'powerobservers'},
            {'item_access_on': '',
             'item_states': ['accepted'],
             'label': 'Label',
             'meeting_access_on': '',
             'meeting_states': ['closed'],
             'orderindex_': '2',
             'row_id': 'restrictedpowerobservers'}]

        same_label_error_msg = translate(
            'power_observer_same_label_error',
            domain='PloneMeeting',
            context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_powerObservers(values), same_label_error_msg)

        # remove a used powerObserver (restrictedpowerobservers)
        # used in MeetingConfig fields
        self.assertTrue('restrictedpowerobservers' in cfg.getRestrictAccessToSecretItemsTo())
        values = [
            {'item_access_on': '',
             'item_states': ['accepted'],
             'label': 'Power observers \xc3\xa9',
             'meeting_access_on': '',
             'meeting_states': ['closed'],
             'row_id': 'powerobservers'}]
        used_in_fields_error_msg = translate(
            'power_observer_removed_used_in_fields',
            domain='PloneMeeting',
            context=self.portal.REQUEST)
        plone_group_not_empty_error_msg = translate(
            'power_observer_removed_plone_group_not_empty',
            domain='PloneMeeting',
            context=self.portal.REQUEST)
        self.assertEqual(cfg.validate_powerObservers(values), used_in_fields_error_msg)
        cfg.setRestrictAccessToSecretItemsTo(())
        # also check configgroup_ prefixed fields
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        self.assertEqual(cfg.validate_powerObservers(values), used_in_fields_error_msg)
        cfg.setItemAnnexConfidentialVisibleFor(())
        self.assertEqual(cfg.validate_powerObservers(values), plone_group_not_empty_error_msg)

        # used as WFA
        if self._check_wfa_available(['hide_decisions_when_under_writing__po__restrictedpowerobservers']):
            self._activate_wfas(('hide_decisions_when_under_writing__po__restrictedpowerobservers', ))
            self.assertEqual(cfg.validate_powerObservers(values), used_in_fields_error_msg)
            self._activate_wfas(())
            self.assertEqual(cfg.validate_powerObservers(values), plone_group_not_empty_error_msg)

        # linked Plone group is not empty
        plone_group_id = '{0}_{1}'.format(cfg.getId(), 'restrictedpowerobservers')
        plone_group = api.group.get(plone_group_id)
        self.assertEqual(plone_group.getMemberIds(), ['restrictedpowerobserver1'])
        self.assertEqual(cfg.validate_powerObservers(values), plone_group_not_empty_error_msg)
        self._removePrincipalFromGroups('restrictedpowerobserver1', [plone_group_id])
        # validates with removed power observer
        self.assertFalse(cfg.validate_powerObservers(values))
        cfg.setPowerObservers(values)
        # the linked Plone group was removed
        self.assertFalse(api.group.get(plone_group_id))

    def test_pm_Validate_itemWFValidationLevels_removed_used_state_item(self):
        """Test MeetingConfig.validate_itemWFValidationLevels, if we remove a validation
           level state that is used by an item."""
        cfg = self.meetingConfig
        # make sure we use default itemWFValidationLevels,
        # useful when test executed with custom profile
        self._setUpDefaultItemWFValidationLevels(cfg)
        # make sure not used in config
        cfg.setItemAdviceStates(())
        cfg.setItemAdviceEditStates(())

        # itemcreated level is mandatory
        level_itemcreated_error = \
            translate('item_wf_val_states_itemcreated_mandatory',
                      domain='PloneMeeting',
                      context=self.request)
        # values_disabled_itemcreated
        self._disableItemValidationLevel(cfg, level='itemcreated')
        values_disabled_itemcreated = deepcopy(cfg.getItemWFValidationLevels())
        self._enableItemValidationLevel(cfg, level='itemcreated')
        self.assertEqual(cfg.validate_itemWFValidationLevels(values_disabled_itemcreated),
                         level_itemcreated_error)

        # remove a state that is not in use
        self.assertEqual(cfg.getItemWFValidationLevels(data='state', only_enabled=True),
                         ['itemcreated', 'proposed'])
        # values_disabled_proposed
        self._disableItemValidationLevel(cfg, level='proposed')
        values_disabled_proposed = deepcopy(cfg.getItemWFValidationLevels())
        self._enableItemValidationLevel(cfg, level='proposed')
        self.failIf(cfg.validate_itemWFValidationLevels(values_disabled_proposed))

        # create an item that will be itemcreated
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.assertEqual(item.query_state(), 'itemcreated')
        self.do(item, 'propose')
        self.assertEqual(item.query_state(), 'proposed')
        level_removed_error = \
            translate('item_wf_val_states_can_not_be_removed_in_use',
                      domain='PloneMeeting',
                      mapping={'item_state': "Proposed",
                               'item_url': item.absolute_url()},
                      context=self.request)
        self.assertEqual(cfg.validate_itemWFValidationLevels(values_disabled_proposed),
                         level_removed_error)

        # delete item then validation is correct
        self.deleteAsManager(item.UID())
        self.failIf(cfg.validate_itemWFValidationLevels(values_disabled_proposed))

    def test_pm_Validate_itemWFValidationLevels_removed_depending_used_state_item(self):
        """Test MeetingConfig.validate_itemWFValidationLevels, if we remove a validation
           level state that is used by an item, not directly but by a workflowAdaptation
           that is using it, like for example the "prevalidated_waiting_advices" states."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['waiting_advices']):
            return

        proposed_state = self._stateMappingFor('proposed')
        # config, fix original_WAITING_ADVICES_FROM_STATES when called from subplugin
        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = deepcopy(adaptations.WAITING_ADVICES_FROM_STATES)
        adaptations.WAITING_ADVICES_FROM_STATES = {'*': (
            {'from_states': (proposed_state, ),
             'back_states': (proposed_state, ),
             'perm_cloned_states': (proposed_state, ),
             'remove_modify_access': True,
             'use_custom_icon': False,
             'use_custom_back_transition_title_for': (),
             'use_custom_state_title': True, },), }

        waiting_advices_proposed_state = '{0}_waiting_advices'.format(
            proposed_state)
        cfg.setItemAdviceStates((waiting_advices_proposed_state, ))
        cfg.setItemAdviceEditStates((waiting_advices_proposed_state, ))
        cfg.setItemAdviceViewStates((waiting_advices_proposed_state, ))

        # add item and set it in waiting_advices_proposed_state
        self.changeUser('pmManager')
        self._activate_wfas(('waiting_advices', ))
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        self.proposeItem(item)
        self._setItemToWaitingAdvices(item, 'wait_advices_from_{}'.format(proposed_state))
        # values_disabled_proposed
        self._disableItemValidationLevel(cfg, level=proposed_state)
        values_disabled_proposed = deepcopy(cfg.getItemWFValidationLevels())
        self._enableItemValidationLevel(cfg, level=proposed_state)
        proposed_state = cfg.getItemWorkflow(True).states['%s_waiting_advices' % proposed_state]
        translated_proposed_state = translate(
            safe_unicode(proposed_state.title), domain="plone", context=self.request)
        level_removed_error = \
            translate(
                'item_wf_val_states_can_not_be_removed_in_use',
                domain='PloneMeeting',
                mapping={'item_state': translated_proposed_state,
                         'item_url': item.absolute_url()},
                context=self.request)
        self.assertEqual(cfg.validate_itemWFValidationLevels(values_disabled_proposed),
                         level_removed_error)
        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def test_pm_Validate_itemWFValidationLevels_removed_used_state_in_config(self):
        """Test MeetingConfig.validate_itemWFValidationLevels, if we remove a validation
           level state that is used by the MeetingConfig."""
        cfg = self.meetingConfig
        cfg.setItemAdviceEditStates(())
        # itemcreated level is mandatory
        proposed_state = cfg.getItemWorkflow(True).states[self._stateMappingFor('proposed')]
        proposed_state_id = proposed_state.getId()
        translated_proposed_state = translate(safe_unicode(proposed_state.title), domain="plone")
        level_removed_config_error = \
            translate('state_or_transition_can_not_be_removed_in_use_config',
                      mapping={'state_or_transition': translated_proposed_state,
                               'cfg_field_name': 'Item states allowing to define advices', },
                      domain='PloneMeeting',
                      context=self.request)
        # values_disabled_proposed
        self._disableItemValidationLevel(cfg, level=proposed_state_id)
        values_disabled_proposed = deepcopy(cfg.getItemWFValidationLevels())
        self._enableItemValidationLevel(cfg, level=proposed_state_id)
        # used in itemAdviceStates, as state
        self.assertEqual(cfg.validate_itemWFValidationLevels(values_disabled_proposed),
                         level_removed_config_error)
        cfg.setItemAdviceStates(())
        # also for field itemObserversStates
        level_removed_config_error = \
            translate(
                'state_or_transition_can_not_be_removed_in_use_config',
                mapping={'state_or_transition': translated_proposed_state,
                         'cfg_field_name':
                         'Restrict observers access to item to following states', },
                domain='PloneMeeting',
                context=self.request)
        cfg.setItemObserversStates((self._stateMappingFor('proposed'), ))
        self.assertEqual(cfg.validate_itemWFValidationLevels(values_disabled_proposed),
                         level_removed_config_error)
        cfg.setItemObserversStates(())
        # used in transitionsToConfirm, as transition
        cfg.setTransitionsToConfirm(('MeetingItem.%s' % proposed_state_id, 'MeetingItem.validate'))
        level_removed_config_error = \
            translate('state_or_transition_can_not_be_removed_in_use_config',
                      mapping={'state_or_transition': translated_proposed_state,
                               'cfg_field_name': 'Transitions to confirm', },
                      domain='PloneMeeting',
                      context=self.request)
        self.assertEqual(cfg.validate_itemWFValidationLevels(values_disabled_proposed),
                         level_removed_config_error)
        # make no more used
        cfg.setItemAdviceEditStates(())
        cfg.setTransitionsToConfirm(())
        self.failIf(cfg.validate_itemWFValidationLevels(values_disabled_proposed))
        # could be used in another cfg field meetingConfigsToCloneTo.trigger_workflow_transitions_until
        cfg2 = self.meetingConfig2
        cfg_id = cfg.getId()
        tr = get_leading_transitions(
            cfg.getItemWorkflow(True), self._stateMappingFor('proposed'),
            not_starting_with="back")[0]
        error_msg = translate(
            'state_or_transition_can_not_be_removed_in_use_other_config',
            domain='PloneMeeting',
            mapping={
                'transition': translate(
                    tr.title,
                    domain="plone",
                    context=self.request),
                'parameter_label': translate(
                    "PloneMeeting_label_meetingConfigsToCloneTo",
                    domain="PloneMeeting",
                    context=self.request),
                'other_cfg_title': safe_unicode(cfg2.Title()), },
            context=self.request)
        cfg2.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg_id,
              'trigger_workflow_transitions_until': '%s.%s' % (cfg_id, tr.id)},))
        self.assertEqual(
            cfg.validate_itemWFValidationLevels(values_disabled_proposed), error_msg)
        # ok if transition not used
        cfg2.setMeetingConfigsToCloneTo(
            ({'meeting_config': '%s' % cfg_id,
              'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL},))
        self.failIf(cfg.validate_itemWFValidationLevels(values_disabled_proposed))

    def test_pm_Validate_itemWFValidationLevels_data_format(self):
        """Test MeetingConfig.validate_itemWFValidationLevels data format:
           - the "itemcreated" line must always be the first line,
             can not be removed, may only be disabled;
           - identifier columns (state, leading_transition, back_transition)
             must respect alpha format (letters without accent/blank/number);
           - the values in the "back_transition" column must always start with "back".
        """
        cfg = self.meetingConfig
        # make sure not used in config
        cfg.setItemAdviceStates(())
        cfg.setItemAdviceEditStates(())

        # the "itemcreated" row must exist as first row
        # itemcreated level is mandatory
        level_itemcreated_error = \
            translate('item_wf_val_states_itemcreated_must_exist',
                      domain='PloneMeeting',
                      context=self.request)
        self.assertEqual(cfg.validate_itemWFValidationLevels([]),
                         level_itemcreated_error)

        # every values in the "back_transition" column must start with "back"
        back_transition_error = \
            translate('item_wf_val_states_back_transition_must_start_with_back',
                      domain='PloneMeeting',
                      context=self.request)
        orig_item_wf_val_levels = cfg.getItemWFValidationLevels()
        back_tr_item_wf_val_levels = deepcopy(orig_item_wf_val_levels)
        back_tr_item_wf_val_levels[1]['back_transition'] = "dummyTransitionId"
        self.assertEqual(cfg.validate_itemWFValidationLevels(back_tr_item_wf_val_levels),
                         back_transition_error)

        # every identifier columns must respect alpha/num format
        wrong_format_error = \
            translate('item_wf_val_states_wrong_identifier_format',
                      domain='PloneMeeting',
                      context=self.request)
        format_item_wf_val_levels = deepcopy(orig_item_wf_val_levels)
        # state
        format_item_wf_val_levels[1]['state'] = "prop osed"
        self.assertEqual(cfg.validate_itemWFValidationLevels(format_item_wf_val_levels),
                         wrong_format_error)
        # leading_transition
        format_item_wf_val_levels[1]['state'] = "proposed"
        format_item_wf_val_levels[1]['leading_transition'] = "proposé"
        self.assertEqual(cfg.validate_itemWFValidationLevels(format_item_wf_val_levels),
                         wrong_format_error)
        # back_transition
        format_item_wf_val_levels[1]['leading_transition'] = "propose"
        format_item_wf_val_levels[1]['back_transition'] = "backToProposé"
        self.assertEqual(cfg.validate_itemWFValidationLevels(format_item_wf_val_levels),
                         wrong_format_error)
        format_item_wf_val_levels[1]['back_transition'] = "backToProposed"
        self.failIf(cfg.validate_itemWFValidationLevels(format_item_wf_val_levels))

    def test_pm_RemoveAnnexesPreviewsOnMeetingClosure(self):
        """When MeetingConfig.removeAnnexesPreviewsOnMeetingClosure is True,
           previews of annexes are deleted when the meeting is closed."""
        self._enableAutoConvert()
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_decision = self.addAnnex(item, relatedTo='item_decision')
        # preview for this will not be removed
        preview_annex = self.addAnnex(
            item, annexType='preview-annex', annexFile=self.annexFilePDF)
        infos = _categorized_elements(item)
        self.assertEqual(infos[annex.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[annex_decision.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[preview_annex.UID()]['preview_status'], 'converted')
        # removeAnnexesPreviewsOnMeetingClosure=False
        self.assertFalse(cfg.getRemoveAnnexesPreviewsOnMeetingClosure())
        self.presentItem(item)
        self.closeMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'closed')
        self.assertEqual(infos[annex.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[annex_decision.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[preview_annex.UID()]['preview_status'], 'converted')
        # removeAnnexesPreviewsOnMeetingClosure=True
        cfg.setRemoveAnnexesPreviewsOnMeetingClosure(True)
        self.backToState(meeting, 'created')
        self.closeMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'closed')
        infos = _categorized_elements(item)
        self.assertEqual(infos[annex.UID()]['preview_status'], 'not_converted')
        self.assertEqual(infos[annex_decision.UID()]['preview_status'], 'not_converted')
        self.assertEqual(infos[preview_annex.UID()]['preview_status'], 'converted')
        # close a Meeting without items, this was generating a bug
        self._removeConfigObjectsFor(cfg)
        meeting = self.create('Meeting', date=datetime(2020, 1, 15))
        self.closeMeeting(meeting)

    def test_pm_CanNotDeactivateConfigUsedInAnotherConfig(self):
        """A MeetingConfig will not be deactivated if used in another
           MeetingConfig.meetingConfigsToCloneTo."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('siteadmin')
        # add special characters into cfg/cfg2 titles
        cfg.setTitle(cfg.Title() + "hé")
        cfg2.setTitle(cfg.Title() + "hé")
        self.assertEqual(cfg.getMeetingConfigsToCloneTo()[0]['meeting_config'],
                         cfg2.getId())
        self.assertEqual(api.content.get_state(cfg2), 'active')
        # can not be deactivated
        with self.assertRaises(WorkflowException) as cm:
            self.do(cfg2, 'deactivate')
        self.assertEqual(
            translate(cm.exception.message),
            u'Can not disable a meeting configuration used in another, '
            'please check field "Meeting configs to clone items to" in meeting configuration "%s"!'
            % safe_unicode(cfg.Title()))
        # still 'active'
        self.assertEqual(api.content.get_state(cfg2), 'active')
        # make it deactivable
        cfg.setMeetingConfigsToCloneTo(())
        self.do(cfg2, 'deactivate')
        self.assertEqual(api.content.get_state(cfg2), 'inactive')

    def test_pm_Show_meeting_manager_reserved_field(self):
        """This condition is protecting some fields that should only be
           viewable by MeetingManagers."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # a reserved field is shown if used
        usedMeetingAttrs = cfg.getUsedMeetingAttributes()
        self.assertFalse('a_meeting_field' in usedMeetingAttrs)
        self.assertFalse(cfg.show_meeting_manager_reserved_field('a_meeting_field'))
        cfg.setUsedMeetingAttributes(usedMeetingAttrs + ('a_meeting_field', ))
        self.assertTrue(cfg.show_meeting_manager_reserved_field('a_meeting_field'))
        # not viewable by non MeetingManagers
        self.changeUser('pmCreator1')
        self.assertFalse(cfg.show_meeting_manager_reserved_field('a_meeting_field'))

    def test_pm_Validate_usedMeetingAttributes(self):
        """Check the MeetingConfig.usedMeetingAttributes validate method."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.failIf(cfg.validate_usedMeetingAttributes([]))
        incompatible_values = {"assembly": "attendees",
                               "signatures": "signatories",
                               "committees_assembly": "committees_attendees",
                               "committees_signatures": "committees_signatories"}
        for k, v in incompatible_values.items():
            self.failUnless(cfg.validate_usedMeetingAttributes([k, v]))
        required_values = {"assembly": ["assembly_excused", "assembly_absents"],
                           "attendees": ["excused", "absents"],
                           "committees": [v for v in cfg.Vocabulary('usedMeetingAttributes')[0]
                                          if v.startswith("committees_") and
                                          v not in ('committees_observations', )]}
        for k, values in required_values.items():
            for v in values:
                self.failUnless(cfg.validate_usedMeetingAttributes([v]))

    def test_pm_Validate_committees_not_removable_when_used(self):
        """Check that when used on a meeting or on an item, a committee may not
           be removed from the MeetingConfig.committees."""
        cfg = self.meetingConfig
        self._enableField("committees", related_to='Meeting')
        self.changeUser('pmManager')
        # Meeting
        meeting = self.create('Meeting', committees=default_committees(DefaultData(cfg)))
        cfg_committees = cfg.getCommittees()
        self.failIf(cfg.validate_committees(cfg_committees))
        self.failUnless(cfg.validate_committees([cfg_committees[1]]))
        self.deleteAsManager(meeting.UID())

        # MeetingItem
        item = self.create('MeetingItem', committees=[cfg_committees[0]['row_id']])
        self.failIf(cfg.validate_committees(cfg_committees))
        self.failUnless(cfg.validate_committees([cfg_committees[1]]))
        # supplement, second committee cfg has a supplement
        item.setCommittees(["{0}__suppl__1".format(cfg_committees[1]['row_id'])])
        item.reindexObject(idxs=["committees_index"])
        self.failIf(cfg.validate_committees(cfg_committees))
        self.failUnless(cfg.validate_committees([cfg_committees[0]]))

    def test_pm_Validate_committees_values(self):
        """Can not define values in column "auto_from" and in column "using_groups"."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # "using_groups" alone
        cfg_committees = cfg.getCommittees()
        cfg_committees[0]['using_groups'] = [self.vendors_uid]
        self.failIf(cfg.validate_committees([cfg_committees[0]]))
        # "auto_from" alone
        cfg_committees[1]['auto_from'] = ["proposing_group__" + self.vendors_uid]
        self.failIf(cfg.validate_committees([cfg_committees[1]]))
        # fails when used together
        self.failUnless(cfg_committees)
        # adding new values
        cfg.setCommittees([])
        cfg_committees[0]['row_id'] = ''
        cfg_committees[1]['row_id'] = ''
        cfg_committees[0]['using_groups'] = []
        cfg.validate_committees(cfg_committees)

    def test_pm_Validate_committees_orderedCommitteeContacts(self):
        """If a value in default_attendees/default_signatories is removed
           from orderedCommitteeContacts it must be unselected."""
        cfg = self.meetingConfig
        cfg.setOrderedCommitteeContacts((self.hp1_uid, self.hp2_uid))
        self.changeUser('pmManager')
        cfg_committees = cfg.getCommittees()
        cfg_committees[0]['default_attendees'] = [self.hp1_uid]
        cfg_committees[0]['default_signatories'] = [self.hp2_uid]
        self.failIf(cfg.validate_committees(cfg_committees))
        # removing a value used for default_attendees or default_signatories fails
        cfg.setOrderedCommitteeContacts((self.hp1_uid,))
        self.failUnless(cfg_committees)
        cfg.setOrderedCommitteeContacts((self.hp2_uid,))
        self.failUnless(cfg_committees)
        # except if no more used
        cfg_committees[0]['default_attendees'] = []
        self.failIf(cfg.validate_committees(cfg_committees))

    def test_pm_Validate_committees_enable_editors(self):
        """When enable_editors=="1" a Plone group is created and
           config will be removable/disablable if Plone group is empty."""
        cfg = self.meetingConfig
        self._enableField("committees", related_to='Meeting')
        self.changeUser('siteadmin')
        committees = cfg.getCommittees()
        # no Plone group for row 0
        plone_group_id = get_plone_group_id(cfg.getId(), committees[0]['row_id'])
        self.assertIsNone(api.group.get(plone_group_id))
        committees[0]['enable_editors'] = "1"
        cfg.setCommittees(committees)
        notify(ObjectEditedEvent(cfg))
        # a Plone group is created
        group = api.group.get(plone_group_id)
        self.assertTrue(group)
        # add a user to the group so config is not removable
        group.addMember('pmManager')
        # enable_editors can not be set to "0"
        committees[0]['enable_editors'] = "0"
        self.failUnless(cfg.validate_committees(committees))
        committees[0]['enable_editors'] = "1"
        self.failIf(cfg.validate_committees(committees))
        # row can not be removed
        self.failUnless(cfg.validate_committees([committees[1]]))
        # if group empty, then config me be disabled or line removed
        group.removeMember('pmManager')
        committees[0]['enable_editors'] = "0"
        self.failIf(cfg.validate_committees(committees))
        self.failIf(cfg.validate_committees([committees[1]]))

    def test_pm_Validate_defaultPollType(self):
        """Test the MeetingConfig.defaultPollType validator,
           selected defaultPollType must be among MeetingConfig.usedPollTypes."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        self.assertEqual(cfg.getUsedPollTypes(),
                         ('freehand', 'no_vote', 'secret', 'secret_separated'))
        self.failIf(cfg.validate_defaultPollType('secret_separated'))
        self.assertEqual(cfg.validate_defaultPollType('out_loud'),
                         u'error_default_poll_type_must_be_among_used_poll_types')
        # case we are removing 'secret_separated' when editing MeetingConfig
        self.request.set("usedPollTypes", ('freehand', 'no_vote', 'secret', ))
        self.failIf(cfg.validate_defaultPollType('freehand'))
        self.assertEqual(cfg.validate_defaultPollType('secret_separated'),
                         u'error_default_poll_type_must_be_among_used_poll_types')

    def test_pm_Validate_firstLinkedVoteUsedVoteValues(self):
        """Test the MeetingConfig.firstLinkedVoteUsedVoteValues validator,
           selected values must be among MeetingConfig.usedVoteValues."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        self.assertEqual(cfg.getUsedVoteValues(), ('yes', 'no', 'abstain'))
        self.failIf(cfg.validate_firstLinkedVoteUsedVoteValues(('no', 'abstain')))
        self.assertEqual(
            cfg.validate_firstLinkedVoteUsedVoteValues(('does_not_vote', )),
            u'error_first_linked_vote_used_vote_values_must_be_among_used_vote_values')
        # case we are removing 'abstain' when editing MeetingConfig
        self.request.set("usedVoteValues", ('yes', 'no'))
        self.failIf(cfg.validate_firstLinkedVoteUsedVoteValues(('no', )))
        self.assertEqual(
            cfg.validate_firstLinkedVoteUsedVoteValues(('no', 'abstain')),
            u'error_first_linked_vote_used_vote_values_must_be_among_used_vote_values')

    def test_pm_Validate_nextLinkedVotesUsedVoteValues(self):
        """Test the MeetingConfig.nexttLinkedVotesUsedVoteValues validator,
           selected values must be among MeetingConfig.usedVoteValues."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        self.assertEqual(cfg.getUsedVoteValues(), ('yes', 'no', 'abstain'))
        self.failIf(cfg.validate_nextLinkedVotesUsedVoteValues(('yes', )))
        self.assertEqual(
            cfg.validate_nextLinkedVotesUsedVoteValues(('does_not_vote', 'yes', )),
            u'error_next_linked_votes_used_vote_values_must_be_among_used_vote_values')
        # case we are removing 'abstain' when editing MeetingConfig
        self.request.set("usedVoteValues", ('yes', 'no'))
        self.failIf(cfg.validate_nextLinkedVotesUsedVoteValues(('yes', )))
        self.assertEqual(
            cfg.validate_nextLinkedVotesUsedVoteValues(('yes', 'abstain')),
            u'error_next_linked_votes_used_vote_values_must_be_among_used_vote_values')

    def test_pm_ConfigEditAndView(self):
        """Just call the edit and view to check it is displayed correctly."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        fieldsets = cfg.Schemata().keys()
        for fieldset in fieldsets:
            self.request.set('pageName', fieldset)
            self.assertTrue(cfg.restrictedTraverse('base_view')())
        for fieldset in fieldsets:
            self.request.set('fieldset', fieldset)
            self.assertTrue(cfg.restrictedTraverse('base_edit')())

    def test_pm_Validate_mailItemEvents(self):
        """Some notifications may not be selected together."""
        cfg = self.meetingConfig
        self.failIf(cfg.validate_mailItemEvents(''))
        self.failIf(cfg.validate_mailItemEvents(['']))
        self.failIf(cfg.validate_mailItemEvents(
            ["item_state_changed_validate", "itemPresentedOwner"]))
        # conflict between "adviceToGive" and "adviceToGiveByUser"
        self.assertEqual(cfg.validate_mailItemEvents(
            ["adviceToGive", "adviceToGiveByUser"]),
            u'Notifications "An advice needs to be given on an item '
            u'(notify users able to add advice), An advice needs to '
            u'be given on an item (notify users of advisers group '
            u'selected on item or the users able to add advice)" '
            u'may not be selected together.')

    def test_pm_ListSelectableAdvisers(self):
        """Vocabulary used for MeetingConfig.selectableAdvisers
           and Meetingconfig.selectableAdviserUsers fields."""
        cfg = self.meetingConfig
        self.changeUser("siteadmin")
        self._select_organization(self.endUsers_uid)
        self.assertListEqual(
            cfg.listSelectableAdvisers().keys(),
            [self.developers_uid, self.endUsers_uid, self.vendors_uid])
        # restrict _advisers to developers and vendors
        select_org_for_function(self.developers_uid, "advisers")
        select_org_for_function(self.vendors_uid, "advisers")
        # endUsers no more in selectable advisers
        self.assertListEqual(
            cfg.listSelectableAdvisers().keys(),
            [self.developers_uid, self.vendors_uid])

    def test_pm_GetCategories(self):
        """Test the MeetingConfig.getCategories method
           especially because it is ram.cached."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('pmManager')
        # onlySelectable=True by default
        cfg_cat_ids = [cat.getId() for cat in cfg.getCategories()]
        cfg2_cat_ids = [cat.getId() for cat in cfg2.getCategories()]
        # categories are not enabled in cfg
        self.assertFalse('category' in cfg.getUsedItemAttributes())
        self.assertFalse(cfg_cat_ids)
        self._enableField('category', reload=True)
        self.assertTrue('category' in cfg.getUsedItemAttributes())
        cfg_cat_ids = [cat.getId() for cat in cfg.getCategories()]
        self.assertEqual(cfg_cat_ids,
                         ['development', 'research', 'events'])
        self.assertEqual(cfg2_cat_ids,
                         ['deployment', 'maintenance', 'development',
                          'events', 'research', 'projects'])
        # onlySelectable=False, returned even if not enabled
        self._enableField('category', enable=False, reload=True)
        self.assertFalse('category' in cfg.getUsedItemAttributes())
        cfg_cat_ids = [cat.getId() for cat in cfg.getCategories(onlySelectable=False)]
        cfg2_cat_ids = [cat.getId() for cat in cfg2.getCategories(onlySelectable=False)]
        self.assertEqual(cfg_cat_ids,
                         ['development', 'research', 'events'])
        self.assertEqual(cfg2_cat_ids,
                         ['deployment', 'maintenance', 'development',
                          'events', 'research', 'projects', 'marketing', 'subproducts'])

    def test_pm_ConfigRelatedPloneGroupsLocalRoles(self):
        """Some local_roles are given to Plone groups related to the MeetingConfig
           (_meetingmanagers, _powerobservers, ...)."""
        self.changeUser('siteadmin')
        cfg_id = "newcfg1"
        # check also that if a Plone group already exists, it's local_roles are set
        plone_group_id = "{0}_{1}".format(cfg_id, MEETINGMANAGERS_GROUP_SUFFIX)
        was_created = createOrUpdatePloneGroup(
            groupId=plone_group_id,
            groupTitle="Cfg1 (Meeting managers)",
            groupSuffix=MEETINGMANAGERS_GROUP_SUFFIX)
        self.assertTrue(was_created)
        self.assertTrue(plone_group_id in self.portal.portal_groups.listGroupIds())
        new_cfg = self.create('MeetingConfig', id=cfg_id, shortName=cfg_id)
        new_cfg_id = new_cfg.getId()
        self.assertEqual(new_cfg_id, cfg_id)
        self.assertTrue(plone_group_id in self.portal.contacts.__ac_local_roles__)
        self.assertTrue(plone_group_id in self.tool.__ac_local_roles__)

    def test_pm_ItemTemplatesManagersMayEditMeetingManagersReservedFields(self):
        """Make sure itemtemplates managers may edit MeetingManagers reserved
           fields on the item, like for example the "checklist" field."""
        self._enableField('textCheckList', enable=False)
        self.changeUser('templatemanager1')
        template = self.meetingConfig.itemtemplates.template1
        self.assertFalse(template.attribute_is_used('textCheckList'))
        self.assertFalse(template.showMeetingManagerReservedField('textCheckList'))
        self._enableField('textCheckList')
        self.assertTrue(template.attribute_is_used('textCheckList'))
        self.assertTrue(template.showMeetingManagerReservedField('textCheckList'))
        # with a RichText field
        self._enableField('notes')
        self.assertTrue(template.attribute_is_used('notes'))
        self.assertTrue(template.showMeetingManagerReservedField('notes'))
        self.assertTrue(template.mayQuickEdit('notes'))
        # but it does not have access on a real item
        self._addPrincipalToGroup(
            self.member.id, get_plone_group_id(self.developers_uid, 'creators'))
        item = self.create('MeetingItem')
        self.assertTrue(item.attribute_is_used('textCheckList'))
        self.assertFalse(item.showMeetingManagerReservedField('textCheckList'))
        self.assertTrue(item.attribute_is_used('notes'))
        self.assertFalse(item.mayQuickEdit('notes'))

    def test_pm_UsingGroupsMeetingAccess(self):
        """Make sure when MeetingConfig.usingGroups is defined that user does not
           have access to the meetings as it will automatically use the
           MEETING_REMOVE_MOG_WFA WFA adaptation and update
           existing meetings created before defining the usingGroups."""
        cfg = self.meetingConfig
        # test without usingGroups then enable it
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(MEETING_REMOVE_MOG_WFA in cfg.getWorkflowAdaptations())
        # enable usingGroups
        # empty value '' is ignored
        self.changeUser('siteadmin')
        cfg.setUsingGroups([''])
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        # still no access as only '' was given
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(MEETING_REMOVE_MOG_WFA in cfg.getWorkflowAdaptations())
        # now with correct values
        self.changeUser('siteadmin')
        cfg.setUsingGroups((self.vendors_uid, ))
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        self.assertFalse(self.hasPermission(View, meeting))
        self.assertTrue(MEETING_REMOVE_MOG_WFA in cfg.getWorkflowAdaptations())
        # give access to developers
        self.changeUser('siteadmin')
        cfg.setUsingGroups((self.vendors_uid, self.developers_uid))
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertEqual(
            cfg.getWorkflowAdaptations().count(MEETING_REMOVE_MOG_WFA), 1)
        # disable usingGroups
        # empty value '' is ignored
        self.changeUser('siteadmin')
        cfg.setUsingGroups([''])
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(MEETING_REMOVE_MOG_WFA in cfg.getWorkflowAdaptations())

    def test_pm_UsingGroupsMailMeetingEvents(self):
        """When MeetingConfig.usingGroups is defined, mail notifications are not
           wrongly sent to wrong user."""
        cfg = self.meetingConfig
        cfg.setMailMeetingEvents(['meeting_state_changed_freeze'])
        # test without usingGroups then enable it
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.freezeMeeting(meeting)
        recipients, subject, body = sendMailIfRelevant(
            meeting,
            event='meeting_state_changed_freeze',
            value=View,
            isPermission=True,
            debug=True)
        dev_creator1_mail = u'M. PMCreator One <pmcreator1@plonemeeting.org>'
        dev_reviewer1_mail = u'M. PMReviewer One <pmreviewer1@plonemeeting.org>'
        ven_creator2_mail = u'M. PMCreator Two <pmcreator2@plonemeeting.org>'
        ven_reviewer2_mail = u'M. PMReviewer Two <pmreviewer2@plonemeeting.org>'
        # developers only access now
        self.assertTrue(dev_creator1_mail in recipients)
        self.assertTrue(dev_reviewer1_mail in recipients)
        # vendors, will have access after as well
        self.assertTrue(ven_creator2_mail in recipients)
        self.assertTrue(ven_reviewer2_mail in recipients)
        # enable usingGroups
        self.changeUser('siteadmin')
        cfg.setUsingGroups((self.vendors_uid, ))
        notify(ObjectEditedEvent(cfg))
        # developers did not receive the email
        recipients, subject, body = sendMailIfRelevant(
            meeting,
            event='meeting_state_changed_freeze',
            value=View,
            isPermission=True,
            debug=True)
        self.assertFalse(dev_creator1_mail in recipients)
        self.assertFalse(dev_reviewer1_mail in recipients)
        self.assertTrue(ven_creator2_mail in recipients)
        self.assertTrue(ven_reviewer2_mail in recipients)

    def test_pm_Get_transitions_to_close_a_meeting(self):
        """Suite of transitions to close a meeting."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # apply a default set of WFAs
        self._activate_wfas(['delayed'])
        self._activate_wfas(['delayed'], cfg=cfg2)
        self.assertEqual(cfg.get_transitions_to_close_a_meeting(),
                         ['freeze', 'publish', 'decide', 'close'])
        self.assertEqual(cfg2.get_transitions_to_close_a_meeting(),
                         ['freeze', 'publish', 'decide', 'close'])
        self._activate_wfas(['no_publication'])
        self.assertEqual(cfg.get_transitions_to_close_a_meeting(),
                         ['freeze', 'decide', 'close'])
        self._activate_wfas(['no_freeze'])
        self.assertEqual(cfg.get_transitions_to_close_a_meeting(),
                         ['publish', 'decide', 'close'])
        self._activate_wfas(['no_freeze', 'no_publication'])
        self.assertEqual(cfg.get_transitions_to_close_a_meeting(),
                         ['decide', 'close'])
        self._activate_wfas(['no_freeze', 'no_publication', 'no_decide'])
        self.assertEqual(cfg.get_transitions_to_close_a_meeting(), ['close'])


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingConfig, prefix='test_pm_'))
    return suite
