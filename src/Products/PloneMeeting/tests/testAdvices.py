# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# Copyright (c) 2013 by Imio.be
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

    def setUp(self):
        """
        """
        super(testAdvices, self).setUp()
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.meetingConfig.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], 'validated', ))
        self.meetingConfig.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.meetingConfig.setItemAdviceViewStates(('presented', ))

    def test_pm_ViewItemToAdvice(self):
        '''Test when an adviser can see the item his advice is asked on.
           The item can still be viewable no matter the advice has been given or not,
           is addable/editable/deletable...
           Create an item for group 'developers' and ask the 'vendors' advice.
           'pmReviewer2' is adviser for 'vendors'.
           In the configuration, an item an advice is asked on is viewable
           in state 'proposed' and 'validated'.'''
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
        self.failIf(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', item2))
        self.failIf(self.hasPermission('View', item3))
        # propose the items
        login(self.portal, 'pmCreator1')
        for item in (item1, item2, item3):
            self.proposeItem(item)
        # now the item (item1) to advice is viewable because 'pmReviewer2' has an advice to add
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', (item2, item3)))
        login(self.portal, 'pmReviewer1')
        # validate the items
        for item in (item1, item2, item3):
            self.validateItem(item)
        # item1 still viewable because 'pmReviewer2' can still edit advice
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', (item2, item3)))
        # present the items
        login(self.portal, 'pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        self.create('Meeting', date=meetingDate)
        for item in (item1, item2, item3):
            self.presentItem(item)
        # item1 still viewable because the item an advice is asked for is still viewable in the 'presented' state...
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.failIf(self.hasPermission('View', (item2, item3)))

    def test_pm_AddEditDeleteAdvices(self):
        '''This test the MeetingItem.getAdvicesToGive method.
           MeetingItem.getAdvicesToGive returns 2 lists : first with addable advices and
           the second with editable/deletable advices.'''
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
        self.proposeItem(item1)
        # a user able to View the item can not add an advice, even if he tries...
        self.assertRaises(Unauthorized,
                          item1.editAdvice,
                          group=self.portal.portal_plonemeeting.developers,
                          adviceType='positive',
                          comment='My comment')
        self.assertEquals(item1.getAdvicesToGive(), (None, None))
        login(self.portal, 'pmReviewer2')
        # the given 'adviceType' must exists (selected in the MeetingConfig.usedAdviceTypes)
        self.assertRaises(KeyError,
                          item1.editAdvice,
                          group=self.portal.portal_plonemeeting.vendors,
                          adviceType='wrong_advice_type',
                          comment='My comment')
        # even if the user can give an advice, he can not for another group
        self.assertRaises(Unauthorized,
                          item1.editAdvice,
                          group=self.portal.portal_plonemeeting.developers,
                          adviceType='positive',
                          comment='My comment')
        # 'pmReviewer2' has one advice to give for 'vendors' and no advice to edit
        self.assertEquals(item1.getAdvicesToGive(), ([('vendors', u'Vendors')], []))
        self.assertEquals(item1.hasAdvices(), False)
        #give the advice
        item1.editAdvice(group=self.portal.portal_plonemeeting.vendors,
                         adviceType='positive',
                         comment='My comment')
        self.assertEquals(item1.hasAdvices(), True)
        # 'pmReviewer2' has no more addable advice (as already given) but it is now an editable advice
        self.assertEquals(item1.getAdvicesToGive(), ([], ['vendors']))
        # given advice is correctly stored
        self.assertEquals(item1.advices['vendors']['type'], 'positive')
        self.assertEquals(item1.advices['vendors']['comment'], 'My comment')
        login(self.portal, 'pmReviewer1')
        self.validateItem(item1)
        # now 'pmReviewer2' can't add (already given) or edit an advice
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.assertEquals(item1.getAdvicesToGive(), ([], []))
        # if a user that can not remove the advice tries (here the item is validated), he gets Unauthorized
        self.assertRaises(Unauthorized, item1.deleteAdvice, 'vendors')
        # put the item back in a state where 'pmReviewer2' can remove the advice
        login(self.portal, 'pmManager')
        self.backToState(item1, 'proposed')
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

    def test_pm_CanNotGiveAdviceIfNotAsked(self):
        '''
          Test that an adviser that can access an item can not give his advice
          if it was not asked.
        '''
        # create an item and ask advice of 'vendors'
        login(self.portal, 'pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('vendors',))
        item1.at_post_edit_script()
        self.proposeItem(item1)
        # if a user tries to give an advice for the 'developers' group,
        # it will raise an Unauthorized
        self.changeUser('pmAdviser1')
        self.assertRaises(Unauthorized,
                          item1.editAdvice,
                          group=self.portal.portal_plonemeeting.developers,
                          adviceType='positive',
                          comment='My comment')

    def test_pm_GiveAdviceOnCreatedItem(self,
                                        itemAdviceStates=('itemcreated', 'proposed', 'validated',),
                                        itemAdviceEditStates=('itemcreated', 'proposed', 'validated',),
                                        itemAdviceViewStates=('itemcreated', 'proposed', 'validated',)):
        '''This test the MeetingItem.getAdvicesToGive method.
           MeetingItem.getAdvicesToGive returns 2 lists : first with addable advices and
           the second with editable/deletable advices.'''
        self.meetingConfig.setItemAdviceStates(itemAdviceStates)
        self.meetingConfig.setItemAdviceEditStates(itemAdviceEditStates)
        self.meetingConfig.setItemAdviceViewStates(itemAdviceViewStates)
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

    def test_pm_AdvicesInvalidation(self):
        '''Test the advice invalidation process.'''
        # advisers can give an advice when item is 'proposed' or 'validated'
        # activate advice invalidation in state 'validated'
        self.meetingConfig.setEnableAdviceInvalidation(True)
        self.meetingConfig.setItemAdviceInvalidateStates(('validated',))
        login(self.portal, 'pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors',)
        }
        item1 = self.create('MeetingItem', **data)
        self.assertEquals(item1.needsAdvices(), True)
        self.failIf(item1.willInvalidateAdvices())
        self.proposeItem(item1)
        # login as adviser and add an advice
        self.changeUser('pmReviewer2')
        self.assertEquals(item1.getAdvicesToGive(), ([('vendors', u'Vendors')], []))
        # give an advice
        item1.editAdvice(group=self.portal.portal_plonemeeting.vendors, adviceType='positive', comment='My comment')
        # login as a user that can actually edit the item
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission('Modify portal content', item1))
        # modifying the item will not invalidate the advices
        self.failIf(item1.willInvalidateAdvices())
        item1.setDecision(item1.getDecision() + '<p>New line</p>')
        item1.at_post_edit_script()
        # check that advices are still there
        self.failUnless(item1.hasAdvices())
        # adding an annex or editing a field thru ajax does not invalidate the item
        annex1 = self.addAnnex(item1, annexType=self.annexFileType)
        self.failUnless(item1.hasAdvices())
        item1.setFieldFromAjax('decision', item1.getDecision() + '<p>Another new line</p>')
        # validate the item
        self.validateItem(item1)
        # login as a user that can edit the item when it is 'validated'
        self.changeUser('pmManager')
        # now that the item is validated, editing it will invalidate advices
        self.failUnless(item1.willInvalidateAdvices())
        # removing an annex will invalidate the advices
        item1.restrictedTraverse('@@delete_givenuid')(annex1.UID())
        self.failIf(item1.hasAdvices())
        # put advices back so we can check other case where advices are invalidated
        item1.advices['vendors']['type'] = 'positive'
        item1.updateAdvices()
        self.failUnless(item1.hasAdvices())
        # adding an annex will invalidate advices
        self.failUnless(item1.willInvalidateAdvices())
        annex1 = self.addAnnex(item1, annexType=self.annexFileType)
        self.failIf(item1.hasAdvices())
        # retrieve removed advices
        item1.advices['vendors']['type'] = 'positive'
        item1.updateAdvices()
        self.failUnless(item1.hasAdvices())
        # editing the item will invalidate advices
        self.failUnless(item1.willInvalidateAdvices())
        item1.setDecision(item1.getDecision() + '<p>Still another new line</p>')
        item1.at_post_edit_script()
        self.failIf(item1.hasAdvices())
        # retrieve removed advices
        item1.advices['vendors']['type'] = 'positive'
        item1.updateAdvices()
        self.failUnless(item1.hasAdvices())
        # changing a field value thru ajax will invalidate advices
        self.failUnless(item1.willInvalidateAdvices())
        item1.setFieldFromAjax('description', '<p>My new description</p>')
        self.failIf(item1.hasAdvices())
        self.failIf(item1.willInvalidateAdvices())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAdvices, prefix='test_pm_'))
    return suite
