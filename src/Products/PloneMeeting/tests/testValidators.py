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

from zope.i18n import translate
from Products.validation import validation

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testValidators(PloneMeetingTestCase):
    '''Tests the validators.'''

    def test_pm_IsValidCertifiedSignaturesValidator(self):
        '''Test the 'isCertifiedSignaturesValidator' validator.
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

        # if we want to use date, we have to provide both from and to
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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testValidators, prefix='test_pm_'))
    return suite
