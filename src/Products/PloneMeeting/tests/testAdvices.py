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

from datetime import datetime
from DateTime import DateTime
from AccessControl import Unauthorized
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import RequiredMissing

from plone.app.testing import login
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from Products.CMFCore.permissions import ModifyPortalContent
from Products.PloneMeeting.config import AddAdvice
from Products.PloneMeeting.indexes import indexAdvisers
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testAdvices(PloneMeetingTestCase):
    '''Tests various aspects of advices management.
       Advices are enabled for PloneGov Assembly, not for PloneMeeting Assembly.'''

    def setUp(self):
        """
        """
        super(testAdvices, self).setUp()
        self.setMeetingConfig(self.meetingConfig2.getId())

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
        # now put the item back to itemcreated so it is no more viewable
        # by 'pmReviewer2' as 'itemcreated' is not in self.meetingConfig.itemAdviceViewStates
        self.changeUser('pmManager')
        self.backToState(item1, 'itemcreated')
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission('View', (item1, item2, item3)))

    def test_pm_AddEditDeleteAdvices(self):
        '''This test the MeetingItem.getAdvicesGroupsInfosForUser method.
           MeetingItem.getAdvicesGroupsInfosForUser returns 2 lists : first with addable advices and
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
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), (None, None))
        login(self.portal, 'pmReviewer2')
        self.failIf(self.hasPermission('View', item1))
        login(self.portal, 'pmCreator1')
        self.proposeItem(item1)
        # a user able to View the item can not add an advice, even if he tries...
        self.assertRaises(Unauthorized,
                          createContentInContainer,
                          item1,
                          'meetingadvice')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), (None, None))
        login(self.portal, 'pmReviewer2')
        # 'pmReviewer2' has one advice to give for 'vendors' and no advice to edit
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        self.assertEquals(item1.hasAdvices(), False)
        # fields 'advice_type' and 'advice_group' are mandatory
        form = item1.restrictedTraverse('++add++meetingadvice').form_instance
        form.update()
        errors = form.extractData()[1]
        self.assertEquals(errors[0].error, RequiredMissing('advice_group'))
        self.assertEquals(errors[1].error, RequiredMissing('advice_type'))
        # value used for 'advice_type' and 'advice_group' must be correct
        form.request.set('form.widgets.advice_type', u'wrong_value')
        errors = form.extractData()[1]
        self.assertEquals(errors[1].error, RequiredMissing('advice_type'))
        # but if the value is correct, the field renders correctly
        form.request.set('form.widgets.advice_type', u'positive')
        data = form.extractData()[0]
        self.assertEquals(data['advice_type'], u'positive')
        # regarding 'advice_group' value, only correct are the ones in the vocabulary
        # so using another will fail, for example, can not give an advice for another group
        form.request.set('form.widgets.advice_group', self.portal.portal_plonemeeting.developers.getId())
        data = form.extractData()[0]
        self.assertFalse('advice_group' in data)
        # we can use the values from the vocabulary
        vocab = form.widgets.get('advice_group').terms.terms
        self.failUnless('vendors' in vocab)
        self.failUnless(len(vocab) == 1)
        # give the advice, select a valid 'advice_group' and save
        form.request.set('form.widgets.advice_group', u'vendors')
        # the 3 fields 'advice_group', 'advice_type' and 'advice_comment' are handled correctly
        data = form.extractData()[0]
        self.assertTrue('advice_group' in data and
                        'advice_type' in data and
                        'advice_comment' in data and
                        'advice_row_id' in data)
        self.assertTrue(len(data) == 4)
        form.request.form['advice_group'] = u'vendors'
        form.request.form['advice_type'] = u'positive'
        form.request.form['advice_comment'] = RichTextValue(u'My comment')
        form.createAndAdd(form.request.form)
        self.assertEquals(item1.hasAdvices(), True)
        # 'pmReviewer2' has no more addable advice (as already given) but has now an editable advice
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], ['vendors']))
        # given advice is correctly stored
        self.assertEquals(item1.adviceIndex['vendors']['type'], 'positive')
        self.assertEquals(item1.adviceIndex['vendors']['comment'], u'My comment')
        login(self.portal, 'pmReviewer1')
        self.validateItem(item1)
        # now 'pmReviewer2' can't add (already given) an advice
        # but he can still edit the advice he just gave
        login(self.portal, 'pmReviewer2')
        self.failUnless(self.hasPermission('View', item1))
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], ['vendors', ]))
        given_advice = getattr(item1, item1.adviceIndex['vendors']['advice_id'])
        self.failUnless(self.hasPermission('Modify portal content', given_advice))
        # another member of the same _advisers group may also edit the given advice
        self.changeUser('pmManager')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], ['vendors', ]))
        self.failUnless(self.hasPermission('Modify portal content', given_advice))
        # if a user that can not remove the advice tries he gets Unauthorized
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, item1.restrictedTraverse('@@delete_givenuid'), item1.meetingadvice.UID())
        # put the item back in a state where 'pmReviewer2' can remove the advice
        login(self.portal, 'pmManager')
        self.backToState(item1, self.WF_STATE_NAME_MAPPINGS['proposed'])
        login(self.portal, 'pmReviewer2')
        # remove the advice
        item1.restrictedTraverse('@@delete_givenuid')(item1.meetingadvice.UID())
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        # remove the fact that we asked the advice
        login(self.portal, 'pmManager')
        item1.setOptionalAdvisers([])
        item1.at_post_edit_script()
        login(self.portal, 'pmReviewer2')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], []))

    def test_pm_CanNotEditAnotherGroupAdvice(self):
        '''
          Test that when the advice of group1 and group2 is asked, group1 can not
          do anything else but see advice given by group2 even when 'advices' are addable/editable.
        '''
        # create an item and ask advice of 'vendors'
        login(self.portal, 'pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', 'developers', ))
        item.at_post_edit_script()
        # an advice can be given when an item is 'proposed'
        self.proposeItem(item)
        # add advice for 'vednors'
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(item,
                                                     'meetingadvice',
                                                     **{'advice_group': 'developers',
                                                     'advice_type': u'positive',
                                                     'advice_comment': RichTextValue(u'My comment')})
        # can view/edit/delete is own advice
        self.assertTrue(self.hasPermission('View', developers_advice))
        self.assertTrue(self.hasPermission('Modify portal content', developers_advice))
        self.assertTrue(self.hasPermission('Delete objects', developers_advice))
        self.changeUser('pmReviewer2')
        # can view
        self.assertTrue(self.hasPermission('View', developers_advice))
        # can not edit/delete
        self.assertFalse(self.hasPermission('Modify portal content', developers_advice))
        self.assertFalse(self.hasPermission('Delete objects', developers_advice))
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': 'vendors',
                                                  'advice_type': u'positive',
                                                  'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmAdviser1')
        # can view
        self.assertTrue(self.hasPermission('View', vendors_advice))
        # can not edit/delete
        self.assertFalse(self.hasPermission('Modify portal content', vendors_advice))
        self.assertFalse(self.hasPermission('Delete objects', vendors_advice))

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
                          createContentInContainer,
                          item1,
                          'meetingadvice')

    def test_pm_GiveAdviceOnCreatedItem(self,
                                        itemAdviceStates=('itemcreated', 'proposed', 'validated',),
                                        itemAdviceEditStates=('itemcreated', 'proposed', 'validated',),
                                        itemAdviceViewStates=('itemcreated', 'proposed', 'validated',)):
        '''This test the MeetingItem.getAdvicesGroupsInfosForUser method.
           MeetingItem.getAdvicesGroupsInfosForUser returns 2 lists : first with addable advices and
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
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        self.failUnless(self.hasPermission(AddAdvice, item1))

    def test_pm_AdvicesInvalidation(self):
        '''Test the advice invalidation process.'''
        # advisers can give an advice when item is 'proposed' or 'validated'
        # activate advice invalidation in state 'validated'
        self.meetingConfig.setEnableAdviceInvalidation(True)
        self.meetingConfig.setItemAdviceInvalidateStates((self.WF_STATE_NAME_MAPPINGS['validated'],))
        login(self.portal, 'pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors',)
        }
        item = self.create('MeetingItem', **data)
        self.assertEquals(item.needsAdvices(), True)
        self.failIf(item.willInvalidateAdvices())
        self.proposeItem(item)
        # login as adviser and add an advice
        self.changeUser('pmReviewer2')
        self.assertEquals(item.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        # give an advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # login as an user that can actually edit the item
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission('Modify portal content', item))
        # modifying the item will not invalidate the advices
        self.failIf(item.willInvalidateAdvices())
        item.setDecision(item.getDecision() + '<p>New line</p>')
        item.at_post_edit_script()
        # check that advices are still there
        self.failUnless(item.hasAdvices())
        # adding an annex or editing a field thru ajax does not invalidate the item
        annex1 = self.addAnnex(item, annexType=self.annexFileType)
        self.failUnless(item.hasAdvices())
        item.setFieldFromAjax('decision', item.getDecision() + '<p>Another new line</p>')
        # validate the item
        self.validateItem(item)
        # login as a user that can edit the item when it is 'validated'
        self.changeUser('pmManager')
        # now that the item is validated, editing it will invalidate advices
        self.failUnless(item.willInvalidateAdvices())
        # removing an annex will invalidate the advices
        item.restrictedTraverse('@@delete_givenuid')(annex1.UID())
        self.failIf(item.hasAdvices())
        self.failIf(item.getGivenAdvices())
        # given the advice again so we can check other case where advices are invalidated
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmManager')
        self.validateItem(item)
        self.failUnless(item.hasAdvices())
        self.failUnless(item.getGivenAdvices())
        # adding an annex will invalidate advices
        self.failUnless(item.willInvalidateAdvices())
        annex1 = self.addAnnex(item, annexType=self.annexFileType)
        self.failIf(item.hasAdvices())
        self.failIf(item.getGivenAdvices())
        # given the advice again so we can check other case where advices are invalidated
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmManager')
        self.validateItem(item)
        self.failUnless(item.hasAdvices())
        self.failUnless(item.getGivenAdvices())
        # editing the item will invalidate advices
        self.failUnless(item.willInvalidateAdvices())
        item.setDecision(item.getDecision() + '<p>Still another new line</p>')
        item.at_post_edit_script()
        self.failIf(item.hasAdvices())
        self.failIf(item.getGivenAdvices())
        # given the advice again so we can check other case where advices are invalidated
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmManager')
        self.validateItem(item)
        self.failUnless(item.hasAdvices())
        self.failUnless(item.getGivenAdvices())
        # changing a field value thru ajax will invalidate advices
        self.failUnless(item.willInvalidateAdvices())
        item.setFieldFromAjax('description', '<p>My new description</p>')
        self.failIf(item.hasAdvices())
        self.failIf(item.getGivenAdvices())
        self.failIf(item.willInvalidateAdvices())

    def test_pm_IndexAdvisers(self):
        '''Test the indexAdvisers index and check that it is always consistent.
           Ask a delay and a non delay-aware advice.'''
        # advices are activated for meetingConfig2
        self.setMeetingConfig(self.meetingConfig2.getId())
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'delay': '5', }, ])
        # an advice can be given when an item is 'proposed' or 'validated'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(), (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', 'vendors__rowid__unique_id_123', ))
        self.proposeItem(item)
        item.reindexObject()
        # no advice to give as item is 'itemcreated'
        self.changeUser('pmAdviser1')
        self.assertEquals(set(indexAdvisers.callable(item)), set(['developers0', 'delay__vendors0', ]))
        itemUID = item.UID()
        brains = self.portal.portal_catalog(indexAdvisers='developers0')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        brains = self.portal.portal_catalog(indexAdvisers='delay__vendors0')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'developers',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # now that an advice has been given for the developers group, the indexAdvisers has been updated
        self.assertEquals(set(indexAdvisers.callable(item)), set(['developers1', 'delay__vendors0', ]))
        brains = self.portal.portal_catalog(indexAdvisers='developers1')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # now change the value of the created meetingadvice.advice_group
        item.meetingadvice.advice_group = self.portal.portal_plonemeeting.vendors.getId()
        # notify modified
        notify(ObjectModifiedEvent(item.meetingadvice))
        self.assertEquals(set(indexAdvisers.callable(item)), set(['developers0', 'delay__vendors1', ]))
        # the index in the portal_catalog is updated too
        brains = self.portal.portal_catalog(indexAdvisers='delay__vendors1')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # delete the advice
        item.restrictedTraverse('@@delete_givenuid')(item.meetingadvice.UID())
        self.assertEquals(set(indexAdvisers.callable(item)), set(['developers0', 'delay__vendors0', ]))
        # the index in the portal_catalog is updated too
        brains = self.portal.portal_catalog(indexAdvisers='delay__vendors0')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        brains = self.portal.portal_catalog(indexAdvisers='developers0')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # if a delay-aware advice delay is exceeded, it is indexed with an ending '2'
        item.adviceIndex['vendors']['delay_started_on'] = datetime(2012, 01, 01)
        self.assertEquals(set(indexAdvisers.callable(item)), set(['developers0', 'delay__vendors2', ]))

    def test_pm_AutomaticAdvices(self):
        '''Test the automatic advices mechanism, some advices can be
           automatically asked under specific conditions.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', ))
        item.at_post_edit_script()
        self.assertTrue('developers' in item.adviceIndex)
        self.assertFalse('vendors' in item.adviceIndex)
        # now make 'vendors' advice automatically asked
        # it will be asked if item.budgetRelated is True
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01', }, ])
        # if the item is not budgetRelated, nothing happens
        item.at_post_edit_script()
        self.assertFalse('vendors' in item.adviceIndex)
        # but if the condition is True, then the advice is automatically asked
        item.setBudgetRelated(True)
        item.at_post_edit_script()
        self.assertTrue('vendors' in item.adviceIndex)
        # moreover, this automatic advice is not considered as optional
        self.assertFalse(item.adviceIndex['vendors']['optional'])
        # the advice asked using optionalAdvisers is marked as optional
        self.assertTrue(item.adviceIndex['developers']['optional'])
        # if an automatic advice is asked and it was also asked as optional
        # the advice is only asked once and considered as automatic, aka not optional
        # but before, 'developers' advice is still considered as optional
        self.assertTrue('developers' in item.getOptionalAdvisers())
        self.meetingConfig.setCustomAdvisers([{'row_id': 'unique_id_123',
                                               'group': 'vendors',
                                               'gives_auto_advice_on': 'item/getBudgetRelated',
                                               'for_item_created_from': '2012/01/01', },
                                              {'row_id': 'unique_id_456',
                                               'group': 'developers',
                                               'gives_auto_advice_on': 'item/getBudgetRelated',
                                               'for_item_created_from': '2012/01/01', }, ])
        item.at_post_edit_script()
        self.assertFalse(item.adviceIndex['vendors']['optional'])
        # 'developers' asked advice is no more considered as optional even if in optionalAdvisers
        self.assertFalse(item.adviceIndex['developers']['optional'])
        # 'developers' asked advice is still in item.optionalAdvisers
        self.assertTrue('developers' in item.getOptionalAdvisers())

    def test_pm_getAutomaticAdvisers(self):
        '''Test the getAutomaticAdvisers method that compute automatic advices to ask.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.meetingConfig.setCustomAdvisers([])
        # if nothing defined, getAutomaticAdvisers returns nothing...
        self.failIf(item.getAutomaticAdvisers())
        # define some customAdvisers
        self.meetingConfig.setCustomAdvisers([])
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': 'item/wrongMethod',
              'for_item_created_from': '2012/01/01',
              'delay': '',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'group': 'developers',
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'delay': '',
              'delay_label': ''}, ])
        # one wrong condition (raising an error when evaluated) and one returning False
        self.failIf(item.getAutomaticAdvisers())
        # now make the second row expression return True, set item.budgetRelated
        item.setBudgetRelated(True)
        self.assertEquals(item.getAutomaticAdvisers(),
                          [{'gives_auto_advice_on_help_message': '',
                            'meetingGroupId': 'developers',
                            'meetingGroupName': 'Developers',
                            'row_id': 'unique_id_456',
                            'delay': '',
                            'delay_left_alert': '',
                            'delay_label': ''}])
        # define one condition for wich the date is > than current item CreationDate
        futureDate = DateTime() + 1
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': futureDate.strftime('%Y/%m/%d'),
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        # nothing should be returned as defined date is bigger than current item's date
        self.assertTrue(futureDate > item.created())
        self.failIf(item.getAutomaticAdvisers())
        # define an old 'for_item_created_from' and a 'for_item_created_until' in the future
        # the advice should be considered as automatic advice to ask
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': futureDate.strftime('%Y/%m/%d'),
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        self.assertEquals(item.getAutomaticAdvisers(),
                          [{'gives_auto_advice_on_help_message': '',
                            'meetingGroupId': 'developers',
                            'meetingGroupName': 'Developers',
                            'row_id': 'unique_id_123',
                            'delay': '',
                            'delay_left_alert': '',
                            'delay_label': ''}])
        # now define a 'for_item_created_until' that is in the past
        # relative to the item created date
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '2013/01/01',
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        self.failIf(item.getAutomaticAdvisers())

    def test_pm_RowIdSetOnAdvices(self):
        '''Test that if we are adding an automatic and/or delay-aware advice,
           the 'advice_row_id' field is correctly initialized on the meetingadvice object.'''
        # for now, make sure no custom adviser is defined
        cfg = self.meetingConfig
        cfg.setCustomAdvisers([])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', ))
        item.at_post_edit_script()

        # add the optional advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'developers',
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEquals(advice.advice_row_id, '')
        self.assertEquals(item.adviceIndex[advice.advice_group]['row_id'], '')

        # now remove it and make it a 'delay-aware' advice
        item.restrictedTraverse('@@delete_givenuid')(advice.UID())
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'delay': '10'}, ])
        item.setOptionalAdvisers(('developers__rowid__unique_id_123', ))
        item.at_post_edit_script()
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'developers',
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEquals(advice.advice_row_id, 'unique_id_123')
        self.assertEquals(item.adviceIndex[advice.advice_group]['row_id'], 'unique_id_123')

        # same behaviour for an automatic advice
        cfg.setCustomAdvisers(
            list(cfg.getCustomAdvisers()) +
            [{'row_id': 'unique_id_456',
              'group': 'vendors',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'delay': ''}, ])
        item.at_post_edit_script()
        # the automatic advice was asked, now add it
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'negative',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEquals(item.adviceIndex['vendors']['row_id'], 'unique_id_456')
        automatic_advice_obj = getattr(item, item.adviceIndex['vendors']['advice_id'])
        self.assertEquals(automatic_advice_obj.advice_row_id, 'unique_id_456')

    def test_pm_delayStartedStoppedOn(self):
        '''Test the 'advice_started_on' and 'advice_stopped_on' date initialization.
           The 'advice_started_on' is set when advice are turning to 'giveable', aka when
           they turn from not being in itemAdviceStates to being in it.
           The 'advice_stopped_on' date is initialized when the advice is no more giveable,
           so when the item state is no more in itemAdviceStates.
           The 2 dates are only reinitialized to None if the user
           triggers the MeetingConfig.transitionReinitializingDelays.
        '''
        self.changeUser('pmManager')
        # configure one automatic adviser with delay
        # and ask one non-delay-aware optional adviser
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''}, ])
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # advice are correctly asked
        self.assertEquals(item.adviceIndex.keys(), ['vendors', 'developers'])
        # for now, dates are not defined
        self.assertEquals([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        self.assertEquals([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        # now do delays start
        # delay will start when the item advices will be giveable
        # advices are giveable when item is proposed, so propose the item
        # this will initialize the 'delay_started_on' date
        self.proposeItem(item)
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['proposed'])
        # we have datetime now in 'delay_started_on' and still nothing in 'delay_stopped_on'
        self.assertTrue(isinstance(item.adviceIndex['developers']['delay_started_on'], datetime))
        self.assertTrue(item.adviceIndex['developers']['delay_stopped_on'] is None)
        # vendors optional advice is not delay-aware
        self.assertTrue(item.adviceIndex['vendors']['delay_started_on'] is None)
        self.assertTrue(item.adviceIndex['vendors']['delay_stopped_on'] is None)
        # if we go on, the 'delay_started_on' date does not change anymore, even in a state where
        # advice are not giveable anymore, but at this point, the 'delay_stopped_date' will be set.
        # We set the item in 'validated'
        saved_developers_start_date = item.adviceIndex['developers']['delay_started_on']
        saved_vendors_start_date = item.adviceIndex['vendors']['delay_started_on']
        self.validateItem(item)
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['validated'])
        self.assertEquals(item.adviceIndex['developers']['delay_started_on'], saved_developers_start_date)
        self.assertEquals(item.adviceIndex['vendors']['delay_started_on'], saved_vendors_start_date)
        # the 'delay_stopped_on' is now set on the delay-aware advice
        self.assertTrue(isinstance(item.adviceIndex['developers']['delay_stopped_on'], datetime))
        self.assertTrue(item.adviceIndex['vendors']['delay_stopped_on'] is None)
        # if we excute the transition that will reinitialize dates, it is 'backToItemCreated'
        self.assertEquals(self.meetingConfig.getTransitionReinitializingDelays(),
                          self.WF_TRANSITION_NAME_MAPPINGS['backToItemCreated'])
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        # the delays have been reinitialized to None
        self.assertEquals([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        self.assertEquals([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                          [None, None])

    def test_pm_mayNotAddAdviceEditIfDelayExceeded(self):
        '''Test that if the delay to give an advice is exceeded, the advice is no more giveable.'''
        # configure one delay-aware optional adviser
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item.at_post_edit_script()
        self.changeUser('pmReviewer2')
        # the advice is asked but not giveable
        self.assertTrue('vendors' in item.adviceIndex)
        # check 'PloneMeeting: add advice' permission
        self.assertTrue(not self.hasPermission(AddAdvice, item))
        # put the item in a state where we can add an advice
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        # now we can add the item and the delay is not exceeded
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] > 0)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # now make the delay exceeded and check again
        item.adviceIndex['vendors']['delay_started_on'] = datetime(2012, 1, 1)
        item.updateAdvices()
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] < 0)
        self.assertTrue(not self.hasPermission(AddAdvice, item))
        # recover delay, add the advice and check the 'edit' behaviour
        item.adviceIndex['vendors']['delay_started_on'] = datetime.now()
        item.updateAdvices()
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] > 0)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # add the advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'negative',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEquals(item.adviceIndex['vendors']['row_id'], 'unique_id_123')
        # advice is editable as delay is not exceeded
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] > 0)
        self.assertTrue(self.hasPermission(ModifyPortalContent, advice))
        # now make sure the advice is no more editable when delay is exceeded
        item.adviceIndex['vendors']['delay_started_on'] = datetime(2012, 1, 1)
        item.updateAdvices()
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] < 0)
        self.assertTrue(not self.hasPermission(ModifyPortalContent, advice))

    def test_pm_UpdateDelayAwareAdvicesView(self):
        '''Test the maintenance task view that will update delay-aware advisers at midnight (0:00)
           at the end of a clear day to keep everything consistent.'''
        # configure one delay-aware optional adviser
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item.at_post_edit_script()
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        # by default, advice is giveable as delay is not exceeded
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] > 0)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # so make delay exceeded, until advices are not updated
        # the state is still somewhat inconsistent as the user as still the AddAdvice permission
        item.adviceIndex['vendors']['delay_started_on'] = datetime(2012, 1, 1)
        # the state is not consistent as advices have not been updated
        # delay is exceeded...
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] < 0)
        # ... but user has still the permission to add it?! ;-)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # make things consistent by calling the @@update-delay-aware-advices view
        # this view is automatically called by cron4plone every days at 0:00
        # the view is only accessible to Managers
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, '@@update-delay-aware-advices')
        self.changeUser('admin')
        # call the view as admin
        self.portal.restrictedTraverse('@@update-delay-aware-advices')()
        # now that advices have been updated, the state is coherent
        self.changeUser('pmReviewer2')
        # delay is still exceeded...
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] < 0)
        # ... but now the user does not have the permission to add the advice anymore
        self.assertTrue(not self.hasPermission(AddAdvice, item))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAdvices, prefix='test_pm_'))
    return suite
