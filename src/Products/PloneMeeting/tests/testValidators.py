# -*- coding: utf-8 -*-

from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group
from copy import deepcopy
from plone import api
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.validators import PloneGroupSettingsFunctionsValidator
from Products.PloneMeeting.validators import PloneGroupSettingsOrganizationsValidator
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

    def test_pm_PloneGroupSettingsFunctionsValidator(self):
        """Completed plonegroup settings validation with our use cases :
           - can not remove a suffix if used in MeetingConfig.selectableCopyGroups;
           - can not remove a suffix if used in MeetingItem.copyGroups;
           - can not remove a suffix if used as composed value, so like
             'suffix_proposing_group_level1reviewers',
             in MeetingConfig.itemAnnexConfidentialVisibleFor for example;
           - can not remove a suffix used by MeetingConfig.itemWFValidationLevels."""
        # make sure we use default itemWFValidationLevels,
        # useful when test executed with custom profile
        cfg = self.meetingConfig
        self._setUpDefaultItemWFValidationLevels(cfg)

        def _check(validation_error_msg, checks=['without', 'disabled', 'fct_orgs']):
            """ """
            values = []
            if 'without' in checks:
                values.append(functions_without_samplers)
            if 'disabled' in checks:
                values.append(functions_with_disabled_samplers)
            if 'fct_orgs' in checks:
                values.append(functions_with_fct_orgs_samplers)
            for value in values:
                with self.assertRaises(Invalid) as cm:
                    validator.validate(value)
                self.assertEqual(cm.exception.message, validation_error_msg)

        self.changeUser('siteadmin')
        # add a new suffix and play with it
        functions = get_registry_functions()
        functions_without_samplers = deepcopy(functions)
        functions.append({'enabled': True,
                          'fct_management': False,
                          'fct_id': u'samplers',
                          'fct_orgs': [],
                          'fct_title': u'Samplers'})
        functions_with_disabled_samplers = deepcopy(functions)
        functions_with_disabled_samplers[-1]['enabled'] = False
        functions_with_fct_orgs_samplers = deepcopy(functions)
        functions_with_fct_orgs_samplers[-1]['fct_orgs'] = [self.vendors_uid]

        validator = PloneGroupSettingsFunctionsValidator(
            self.portal, self.request, None, IContactPlonegroupConfig['functions'], None)
        self.assertIsNone(validator.validate(functions))
        set_registry_functions(functions)
        # use samplers suffix
        self._enableItemValidationLevel(cfg, level='prevalidated', suffix='samplers')

        # developers_samplers was created
        dev_samplers = get_plone_group(self.developers_uid, 'samplers')
        dev_samplers_id = dev_samplers.getId()
        self.assertTrue(dev_samplers in api.group.get_groups())
        # use samplers in MeetingConfig
        cfg.setSelectableCopyGroups(cfg.getSelectableCopyGroups() + (dev_samplers_id, ))
        validation_error_msg = _('can_not_delete_plone_group_meetingconfig',
                                 mapping={'cfg_url': cfg.absolute_url()})
        _check(validation_error_msg)
        # also check composed values like 'suffix_proposing_group_level1reviewers'
        cfg.setSelectableCopyGroups(())
        cfg.setItemAnnexConfidentialVisibleFor(('suffix_proposing_group_samplers', ))
        _check(validation_error_msg, checks=['without', 'disabled'])
        cfg.setItemAnnexConfidentialVisibleFor(())
        # use samplers on item, remove it from MeetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setCopyGroups((dev_samplers_id, ))
        item.reindexObject()
        # still complaining about config because used in itemWFValidationLevels
        _check(validation_error_msg, checks=['without', 'disabled'])
        self._disableItemValidationLevel(cfg, level='prevalidated', suffix='prereviewers')
        validation_error_msg = _('can_not_delete_plone_group_meetingitem',
                                 mapping={'item_url': item.absolute_url()})
        _check(validation_error_msg)
        # remove it on item, then everything is correct
        item.setCopyGroups(())
        item.reindexObject()
        self.assertIsNone(validator.validate(functions))
        set_registry_functions(functions_without_samplers)
        self.assertFalse(dev_samplers in api.group.get_groups())

        # an _advisers may not be disabled if used
        item.setOptionalAdvisers((self.developers_uid, ))
        item._update_after_edit(idxs=['indexAdvisers'])
        functions_with_fct_orgs_advisers = deepcopy(functions)
        self.assertEqual(functions_with_fct_orgs_advisers[0]['fct_id'], u'advisers')
        functions_with_fct_orgs_advisers[0]['fct_orgs'] = [self.vendors_uid]
        with self.assertRaises(Invalid) as cm:
            validator.validate(functions_with_fct_orgs_advisers)
        self.assertEqual(cm.exception.message, validation_error_msg)
        # but if disabling another level it is correct
        # disable level prereviewers for vendors
        functions_with_fct_orgs_prereviewers = deepcopy(functions)
        self.assertEqual(functions_with_fct_orgs_advisers[3]['fct_id'], u'prereviewers')
        functions_with_fct_orgs_prereviewers[3]['fct_orgs'] = [self.vendors_uid]
        self.assertIsNone(validator.validate(functions_with_fct_orgs_prereviewers))
        # remove adviser so it validates
        item.setOptionalAdvisers(())
        item._update_after_edit(idxs=['indexAdvisers'])
        self.assertIsNone(validator.validate(functions_with_fct_orgs_advisers))
        set_registry_functions(functions_with_fct_orgs_advisers)
        self.assertFalse(self.developers_advisers in api.group.get_groups())

    def test_pm_PloneGroupSettingsOrganizationsValidator(self):
        """Can not unselected an organization if used as groups_in_charge
           of another organziations or in MeetingConfig.usingGroups."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        validator = PloneGroupSettingsOrganizationsValidator(
            self.portal, self.request, None, IContactPlonegroupConfig['organizations'], None)
        organizations = get_registry_organizations()
        self.assertIsNone(validator.validate(organizations))

        # org can not be unselected if used in another org.groups_in_charge
        orgs = get_organizations()
        orgs[0].groups_in_charge = [orgs[1].UID()]
        with self.assertRaises(Invalid) as cm:
            validator.validate([organizations[0]])
        validation_error_msg = _('can_not_unselect_plone_group_org',
                                 mapping={'item_url': orgs[0].absolute_url()})
        self.assertEqual(cm.exception.message, validation_error_msg)
        # but other could be unselected
        self.assertIsNone(validator.validate([organizations[1]]))
        # remove groups_in_charge so org may be unselected
        orgs[0].groups_in_charge = []

        # MeetingConfg.usingGroups
        cfg.setUsingGroups([orgs[1].UID()])
        with self.assertRaises(Invalid) as cm:
            validator.validate([organizations[0]])
        validation_error_msg = _('can_not_unselect_plone_group_meetingconfig',
                                 mapping={'cfg_title': cfg.Title()})
        self.assertEqual(cm.exception.message, validation_error_msg)
        # remove usingGroups so org may be unselected
        cfg.setUsingGroups([])

        # now org may be unselected
        self.assertIsNone(validator.validate([organizations[0]]))


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testValidators, prefix='test_pm_'))
    return suite
