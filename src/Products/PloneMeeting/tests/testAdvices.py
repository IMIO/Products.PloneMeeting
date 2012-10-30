# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# Copyright (c) 2012 by CommunesPlone.org
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

from DateTime import DateTime
from AccessControl import Unauthorized

from plone.app.testing import login

from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testAdvices(PloneMeetingTestCase):
    '''Tests various aspects of advices management.
       Advices are enabled for PloneGov Assembly, not for PloneMeeting Assembly.'''

    def testViewItemToAdvice(self):
        '''Test when an adviser can see the item his advice is asked on.
           The item can still be viewable no matter the advice has been given or not,
           is addable/editable/deletable...
           Create an item for group 'developers' and ask the 'vendors' advice.
           'pmReviewer2' is adviser for 'vendors'.
           In the configuration, an item an advice is asked on is viewable
           in state 'proposed' and 'validated'.'''
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.assertEquals(self.meetingConfig.getItemAdviceStates(), \
                         ('proposed', 'validated',))
        self.assertEquals(self.meetingConfig.getItemAdviceEditStates(), \
                         ('proposed',))
        self.assertEquals(self.meetingConfig.getItemAdviceViewStates(), \
                         ('presented',))
        # creator for group 'developers'
        login(self.portal, 'pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance'
        }
        item1 = self.create('MeetingItem', **data)
        item1.setOptionalAdvisers(('vendors',))
        item2 = self.create('MeetingItem', **data)
        item2.setOptionalAdvisers(('developers',))
        item3 = self.create('MeetingItem', **data)
        # at this state, the item is not viewable by the advisers
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', (item1, item2, item3)))
        # propose the items
        login(self.portal, 'pmCreator1')
        for item in (item1, item2, item3):
            self.do(item, 'propose')
        # now the item (item1) to advice is viewable because 'pmReviewer2' has an advice to add
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', (item2, item3)))
        login(self.portal, 'pmReviewer1')
        # validate the items
        for item in (item1, item2, item3):
            self.do(item, 'validate')
        # item1 still viewable because 'pmReviewer2' can still edit advice
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', (item2, item3)))
        # present the items
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        self.create('Meeting', date=meetingDate)
        for item in (item1, item2, item3):
            self.do(item, 'present')
        # item1 still viewable because the item an advice is asked for is still viewable in the 'presented' state...
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', (item2, item3)))

    def testAddEditDeleteAdvices(self):
        '''This test the MeetingItem.getAdvicesToGive method.
           MeetingItem.getAdvicesToGive returns 2 lists : first with addable advices and
           the second with editable/deletable advices.'''
        self.setMeetingConfig(self.meetingConfig2.getId())
        # creator for group 'developers'
        login(self.portal, 'pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance'
        }
        item1 = self.create('MeetingItem', **data)
        self.assertEquals(item1.needsAdvices(), False)
        item1.setOptionalAdvisers(('vendors',))
        item1.at_post_edit_script()
        self.assertEquals(item1.needsAdvices(), True)
        # 'pmCreator1' has no addable nor editable advice to give
        self.assertEquals(item1.getAdvicesToGive(), (None, None))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', item1))
        login(self.portal, 'pmCreator1')
        self.do(item1, 'propose')
        # a user able to View the item can not add an advice, even if he tries...
        self.assertRaises(Unauthorized, item1.editAdvice, group=self.portal.portal_plonemeeting.developers, adviceType='positive', comment='My comment')
        self.assertEquals(item1.getAdvicesToGive(), (None, None))
        login(self.portal, 'pmReviewer2')
        # the given 'adviceType' must exists (selected in the MeetingConfig.usedAdviceTypes)
        self.assertRaises(KeyError, item1.editAdvice, group=self.portal.portal_plonemeeting.vendors, adviceType='wrong_advice_type', comment='My comment')
        # even if the user can give an advice, he can not for another group
        self.assertRaises(Unauthorized, item1.editAdvice, group=self.portal.portal_plonemeeting.developers, adviceType='positive', comment='My comment')
        # 'pmReviewer2' has one advice to give for 'vendors' and no advice to edit
        self.assertEquals(item1.getAdvicesToGive(), ([('vendors', u'Vendors')], []))
        self.assertEquals(item1.hasAdvices(), False)
        #give the advice
        item1.editAdvice(group=self.portal.portal_plonemeeting.vendors, adviceType='positive', comment='My comment')
        self.assertEquals(item1.hasAdvices(), True)
        # 'pmReviewer2' has no more addable advice (as already given) but it is now an editable advice
        self.assertEquals(item1.getAdvicesToGive(), ([], ['vendors']))
        # given advice is correctly stored
        self.assertEquals(item1.advices['vendors']['type'], 'positive')
        self.assertEquals(item1.advices['vendors']['comment'], 'My comment')
        login(self.portal, 'pmReviewer1')
        self.do(item1, 'validate')
        # now 'pmReviewer2' can't add (already given) or edit an advice
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.assertEquals(item1.getAdvicesToGive(), ([], []))
        # if a user that can not remove the advice tries (here the item is validated), he gets Unauthorized
        self.assertRaises(Unauthorized, item1.deleteAdvice, 'vendors')
        # put the item back in a state where 'pmReviewer2' can remove the advice
        login(self.portal, 'pmManager')
        self.do(item1, 'backToProposed')
        login(self.portal, 'pmReviewer2')
        # remove the advice
        item1.deleteAdvice('vendors')
        self.assertEquals(item1.getAdvicesToGive(), ([('vendors', u'Vendors')], []))
        # remove the fact that we asked the advice
        login(self.portal, 'pmManager')
        item1.setOptionalAdvisers([])
        item1.at_post_edit_script()
        login(self.portal, 'pmReviewer2')
        self.assertEquals(item1.getAdvicesToGive(), ([], []))

    def testGiveAdviceOnCreatedItem(self):
        '''This test the MeetingItem.getAdvicesToGive method.
           MeetingItem.getAdvicesToGive returns 2 lists : first with addable advices and
           the second with editable/deletable advices.'''
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.meetingConfig.setItemAdviceStates(('itemcreated', 'proposed', 'validated',))
        self.meetingConfig.setItemAdviceEditStates(('itemcreated', 'proposed', 'validated',))
        self.meetingConfig.setItemAdviceViewStates(('itemcreated', 'proposed', 'validated',))
        login(self.portal, 'pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors',)
        }
        item1 = self.create('MeetingItem', **data)
        self.assertEquals(item1.needsAdvices(), True)
        # check than the adviser can see the item
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.assertEquals(item1.getAdvicesToGive(), ([('vendors', u'Vendors')], []))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAdvices))
    return suite
