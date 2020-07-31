# -*- coding: utf-8 -*-

from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.utils import get_plone_group
from copy import deepcopy
from plone import api
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.validators import PloneGroupSettingsValidator
from Products.validation import validation
from zope.i18n import translate
from zope.interface import Invalid


class testValidators(PloneMeetingTestCase):
    '''Tests the validators.'''

    def test_pm_IsValidCertifiedSignaturesValidatorWorking(self):
        '''Test the 'isCertifiedSignaturesValidator' validator.
           Here we are testing that working cases are actually working..."""
           It fails if :
           - signatures are not ordered by signature number;
           - both date_from/date_to are not provided together (if provided);
           - date format is wrong (respect YYYY/DD/MM, valid DateTime, date_from <= date_to).'''
        v = validation.validatorFor('isValidCertifiedSignatures')
        # if nothing is defined, validation is successful
        self.failIf(v([]))
        # nothing is required, except signatureNumber
        # here is a working sample
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1a',
             'function': 'Function1a',
             'date_from': '2015/01/01',
             'date_to': '2015/02/02',
             },
            {'signatureNumber': '1',
             'name': 'Name1b',
             'function': 'Function1b',
             'date_from': '2015/02/15',
             'date_to': '2015/02/15',
             },
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2a',
             'function': 'Function2a',
             'date_from': '2015/01/01',
             'date_to': '2015/01/15',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             },
        ]
        self.failIf(v(certified))

        # every signatures are not mandatorily redefined
        # this is the case especially while overriding for example signature 2
        # on a MeetingGroup and keep signature 1 from the MeetingConfig
        # fails if signatureNumber are not ordered
        certified = [
            {'signatureNumber': '2',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
        ]
        self.failIf(v(certified))

    def test_pm_IsValidCertifiedSignaturesValidatorFailsIfNotOrdered(self):
        '''Test the 'isCertifiedSignaturesValidator' validator.
           It fails if signatures are not ordered by signature number.'''
        v = validation.validatorFor('isValidCertifiedSignatures')
        # fails if signatureNumber are not ordered
        certified = [
            {'signatureNumber': '2',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
        ]
        order_error_msg = translate('error_certified_signatures_order',
                                    domain='PloneMeeting',
                                    context=self.portal.REQUEST)
        self.assertEquals(v(certified),
                          order_error_msg)

    def test_pm_IsValidCertifiedSignaturesValidatorFailsIfBothDatesNotProvided(self):
        '''Test the 'isCertifiedSignaturesValidator' validator.
           It fails if signatures both dates are not provided.'''
        v = validation.validatorFor('isValidCertifiedSignatures')
        # if we want to use date, we have to provide both date_from and date_to
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '2015/01/01',
             'date_to': '',
             },
        ]
        both_error_msg = translate('error_certified_signatures_both_dates_required',
                                   mapping={'row_number': 1},
                                   domain='PloneMeeting',
                                   context=self.portal.REQUEST)
        self.assertEquals(v(certified),
                          both_error_msg)
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '2015/01/01',
             },
        ]
        self.assertEquals(v(certified),
                          both_error_msg)

    def test_pm_IsValidCertifiedSignaturesValidatorFailsIfWrongDateFormat(self):
        '''Test the 'isCertifiedSignaturesValidator' validator.
           It fails if signatures use wrong format for dates.'''
        v = validation.validatorFor('isValidCertifiedSignatures')
        # check date format
        # wrong date
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '2015/02/00',
             'date_to': '2015/02/15',
             },
        ]
        invalid_dates_error_msg = translate('error_certified_signatures_invalid_dates',
                                            mapping={'row_number': 1},
                                            domain='PloneMeeting',
                                            context=self.portal.REQUEST)
        self.assertEquals(v(certified),
                          invalid_dates_error_msg)
        # wrong date format, not respecting YYYY/MM/DD
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '2015/15/01',
             'date_to': '2015/20/01',
             },
        ]
        self.assertEquals(v(certified),
                          invalid_dates_error_msg)
        # date_from must be <= date_to
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '2015/01/15',
             'date_to': '2015/01/10',
             },
        ]
        self.assertEquals(v(certified),
                          invalid_dates_error_msg)

        # row number is displayed in the error message, check that it works
        # here, row 2 is wrong
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': 'wrong_date',
             'date_to': '2015/01/01',
             },
            {'signatureNumber': '2',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
        ]
        invalid_dates_error_msg2 = translate('error_certified_signatures_invalid_dates',
                                             mapping={'row_number': 2},
                                             domain='PloneMeeting',
                                             context=self.portal.REQUEST)
        self.assertEquals(v(certified),
                          invalid_dates_error_msg2)

    def test_pm_IsValidCertifiedSignaturesValidatorFailIfUsingDuplicatedEntries(self):
        '''Test the 'isCertifiedSignaturesValidator' validator.
           It fails if 2 entries use exactly same signatureNumber/date_from/date_to.'''
        v = validation.validatorFor('isValidCertifiedSignatures')
        # test first without dates, row 3 is wrong
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
        ]
        duplicated_entries_error_msg = translate('error_certified_signatures_duplicated_entries',
                                                 mapping={'row_number': 3},
                                                 domain='PloneMeeting',
                                                 context=self.portal.REQUEST)
        self.assertEquals(v(certified),
                          duplicated_entries_error_msg)
        # test with dates, row 2 is wrong
        certified = [
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '2015/01/01',
             'date_to': '2015/02/02',
             },
            {'signatureNumber': '1',
             'name': '',
             'function': '',
             'date_from': '2015/01/01',
             'date_to': '2015/02/02',
             },
            {'signatureNumber': '2',
             'name': '',
             'function': '',
             'date_from': '',
             'date_to': '',
             },
        ]
        duplicated_entries_error_msg2 = translate('error_certified_signatures_duplicated_entries',
                                                  mapping={'row_number': 2},
                                                  domain='PloneMeeting',
                                                  context=self.portal.REQUEST)
        self.assertEquals(v(certified),
                          duplicated_entries_error_msg2)

    def test_pm_PloneGroupSettingsValidator(self):
        """Completed plonegroup settings validation with our use cases :
           - can not remove a suffix if used in MeetingConfig.selectableCopyGroups;
           - can not remove a suffix if used in MeetingItem.copyGroups."""
        self.changeUser('siteadmin')
        # add a new suffix and play with it
        cfg = self.meetingConfig
        functions = get_registry_functions()
        functions_without_samplers = deepcopy(functions)
        functions.append({'enabled': True,
                          'fct_id': u'samplers',
                          'fct_orgs': [],
                          'fct_title': u'Samplers'})
        validator = PloneGroupSettingsValidator(self.portal,
                                                self.request,
                                                None,
                                                IContactPlonegroupConfig['functions'],
                                                None)
        self.assertIsNone(validator.validate(functions))
        set_registry_functions(functions)
        # developers_samplers was created
        dev_samplers = get_plone_group(self.developers_uid, 'samplers')
        dev_samplers_id = dev_samplers.getId()
        self.assertTrue(dev_samplers in api.group.get_groups())
        # use samplers in MeetingConfig
        cfg.setSelectableCopyGroups(cfg.getSelectableCopyGroups() + (dev_samplers_id, ))
        validation_error_msg = _('can_not_delete_plone_group_meetingconfig',
                                 mapping={'cfg_url': cfg.absolute_url()})
        with self.assertRaises(Invalid) as cm:
            validator.validate(functions_without_samplers)
        self.assertEqual(cm.exception.message, validation_error_msg)
        # use samplers on item, remove it from MeetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups((dev_samplers_id, ))
        item.reindexObject()
        cfg.setSelectableCopyGroups(())
        validation_error_msg = _('can_not_delete_plone_group_meetingitem',
                                 mapping={'item_url': item.absolute_url()})
        with self.assertRaises(Invalid) as cm:
            validator.validate(functions_without_samplers)
        self.assertEqual(cm.exception.message, validation_error_msg)
        # remove it on item, then everything is correct
        item.setCopyGroups(())
        item.reindexObject()
        self.assertIsNone(validator.validate(functions))
        set_registry_functions(functions_without_samplers)
        self.assertFalse(dev_samplers in api.group.get_groups())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testValidators, prefix='test_pm_'))
    return suite
