# -*- coding: utf-8 -*-
#
# File: testAdvices.py
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

from os import path

from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from AccessControl import Unauthorized
from zope.component import queryUtility
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import RequiredMissing
from zope.schema.interfaces import IVocabularyFactory

from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from collective.iconifiedcategory.utils import get_categorized_elements
from imio.helpers.cache import cleanRamCacheFor

from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from plone import api
from Products.PloneMeeting.config import AddAdvice
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import ADVICE_STATES_ENDED
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import POWEROBSERVERS_GROUP_SUFFIX
from Products.PloneMeeting.indexes import indexAdvisers
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testAdvices(PloneMeetingTestCase):
    '''Tests various aspects of advices management.
       Advices are enabled for PloneGov Assembly, not for PloneMeeting Assembly.'''

    def test_pm_ViewItemToAdvice(self):
        '''Test when an adviser can see the item his advice is asked on.
           The item can still be viewable no matter the advice has been given or not,
           is addable/editable/deletable...
           Create an item for group 'developers' and ask the 'vendors' advice.
           'pmReviewer2' is adviser for 'vendors'.
           In the configuration, an item an advice is asked on is viewable
           in state 'proposed' and 'validated'.'''
        # creator for group 'developers'
        self.changeUser('pmCreator1')
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
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, item1))
        self.failIf(self.hasPermission(View, item2))
        self.failIf(self.hasPermission(View, item3))
        # propose the items
        self.changeUser('pmCreator1')
        for item in (item1, item2, item3):
            self.proposeItem(item)
        # now the item (item1) to advice is viewable because 'pmReviewer2' has an advice to add
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.failIf(self.hasPermission(View, (item2, item3)))
        self.changeUser('pmReviewer1')
        # validate the items
        for item in (item1, item2, item3):
            self.validateItem(item)
        # item1 still viewable because 'pmReviewer2' can still edit advice
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.failIf(self.hasPermission(View, (item2, item3)))
        # present the items
        self.changeUser('pmManager')
        meetingDate = DateTime('2008/06/12 08:00:00')
        self.create('Meeting', date=meetingDate)
        for item in (item1, item2, item3):
            self.presentItem(item)
        self.assertEquals(item1.queryState(), self.WF_STATE_NAME_MAPPINGS['presented'])
        self.assertEquals(item2.queryState(), self.WF_STATE_NAME_MAPPINGS['presented'])
        self.assertEquals(item3.queryState(), self.WF_STATE_NAME_MAPPINGS['presented'])
        # item1 still viewable because the item an advice is asked for is still viewable in the 'presented' state...
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.failIf(self.hasPermission(View, (item2, item3)))
        # now put the item back to itemcreated so it is no more viewable
        # by 'pmReviewer2' as 'itemcreated' is not in self.meetingConfig.itemAdviceViewStates
        self.changeUser('pmManager')
        self.backToState(item1, 'itemcreated')
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, (item1, item2, item3)))

    def test_pm_AddEditDeleteAdvices(self):
        '''This test the MeetingItem.getAdvicesGroupsInfosForUser method.
           MeetingItem.getAdvicesGroupsInfosForUser returns 2 lists : first with addable advices and
           the second with editable/deletable advices.'''
        # creator for group 'developers'
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance'
        }
        item1 = self.create('MeetingItem', **data)
        self.assertEquals(item1.adapted().showAdvices(), False)
        item1.setOptionalAdvisers(('vendors',))
        item1.at_post_edit_script()
        self.assertEquals(item1.adapted().showAdvices(), True)
        # 'pmCreator1' has no addable nor editable advice to give
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, item1))
        self.changeUser('pmCreator1')
        self.proposeItem(item1)
        # a user able to View the item can not add an advice, even if he tries...
        self.assertRaises(Unauthorized,
                          createContentInContainer,
                          item1,
                          'meetingadvice')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('pmReviewer2')
        # 'pmReviewer2' has one advice to give for 'vendors' and no advice to edit
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        self.assertEquals(item1.hasAdvices(), False)
        # fields 'advice_type' and 'advice_group' are mandatory
        form = item1.restrictedTraverse('++add++meetingadvice').form_instance
        self.request['PUBLISHED'] = form
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
        form.request.set('form.widgets.advice_group', self.tool.developers.getId())
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
                        'advice_row_id' in data and
                        'advice_observations' in data and
                        'advice_hide_during_redaction' in data)
        # we receive the 6 fields
        self.assertTrue(len(data) == len(form.fields))
        form.request.form['advice_group'] = u'vendors'
        form.request.form['advice_type'] = u'positive'
        form.request.form['advice_comment'] = RichTextValue(u'My comment')
        form.createAndAdd(form.request.form)
        self.assertEquals(item1.hasAdvices(), True)
        # 'pmReviewer2' has no more addable advice (as already given) but has now an editable advice
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], [('vendors', 'Vendors')]))
        # given advice is correctly stored
        self.assertEquals(item1.adviceIndex['vendors']['type'], 'positive')
        self.assertEquals(item1.adviceIndex['vendors']['comment'], u'My comment')
        self.changeUser('pmReviewer1')
        self.validateItem(item1)
        # now 'pmReviewer2' can't add (already given) an advice
        # but he can still edit the advice he just gave
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], [('vendors', 'Vendors')]))
        given_advice = getattr(item1, item1.adviceIndex['vendors']['advice_id'])
        self.failUnless(self.hasPermission('Modify portal content', given_advice))
        # another member of the same _advisers group may also edit the given advice
        self.changeUser('pmManager')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], [('vendors', 'Vendors')]))
        self.failUnless(self.hasPermission('Modify portal content', given_advice))
        # if a user that can not remove the advice tries he gets Unauthorized
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, item1.restrictedTraverse('@@delete_givenuid'), item1.meetingadvice.UID())
        # put the item back in a state where 'pmReviewer2' can remove the advice
        self.changeUser('pmManager')
        self.backToState(item1, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer2')
        # remove the advice
        item1.restrictedTraverse('@@delete_givenuid')(item1.meetingadvice.UID())
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))

        # if advices are disabled in the meetingConfig, getAdvicesGroupsInfosForUser is emtpy
        self.changeUser('admin')
        self.meetingConfig.setUseAdvices(False)
        self.changeUser('pmReviewer2')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('admin')
        self.meetingConfig.setUseAdvices(True)

        # activate advices again and this time remove the fact that we asked the advice
        self.changeUser('pmReviewer2')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        self.changeUser('pmManager')
        item1.setOptionalAdvisers([])
        item1.at_post_edit_script()
        self.changeUser('pmReviewer2')
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([], []))

    def test_pm_AddAnnexToAdvice(self):
        '''
          Test that we can add annexes to an advice.
        '''
        # advice are addable/editable when item is 'proposed'
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['proposed'],
                                     self.WF_STATE_NAME_MAPPINGS['validated'], ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # an advice can be given when an item is 'proposed'
        self.proposeItem(item)
        # add advice for 'vendors'
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        # annexes are addable if advice is editable
        self.assertTrue(self.hasPermission(ModifyPortalContent, advice))
        self.assertTrue(self.hasPermission(DeleteObjects, advice))
        annex = self.addAnnex(advice)
        self.assertEqual(len(get_categorized_elements(advice)), 1)
        self.assertEqual(get_categorized_elements(advice)[0]['id'], annex.getId())
        # annex is removable
        self.assertTrue(self.hasPermission(DeleteObjects, annex))
        # if we validate the item, the advice is no more editable
        # and annexes are no more addable/removable
        self.changeUser('pmManager')
        self.validateItem(item)
        self.changeUser('pmReviewer2')
        self.assertTrue(not self.hasPermission(ModifyPortalContent, advice))
        self.assertTrue(not self.hasPermission(DeleteObjects, advice))
        self.assertTrue(not self.hasPermission(DeleteObjects, annex))

    def test_pm_CanNotEditAnotherGroupAdvice(self):
        '''
          Test that when the advice of group1 and group2 is asked, group1 can not
          do anything else but see advice given by group2 even when 'advices' are addable/editable.
        '''
        # create an item and ask advice of 'vendors'
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', 'developers', ))
        item.at_post_edit_script()
        # an advice can be given when an item is 'proposed'
        self.proposeItem(item)
        # add advice for 'developers'
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(item,
                                                     'meetingadvice',
                                                     **{'advice_group': 'developers',
                                                        'advice_type': u'positive',
                                                        'advice_comment': RichTextValue(u'My comment')})
        # can view/edit/delete is own advice
        self.assertTrue(self.hasPermission(View, developers_advice))
        self.assertTrue(self.hasPermission('Modify portal content', developers_advice))
        self.assertTrue(self.hasPermission('Delete objects', developers_advice))
        self.changeUser('pmReviewer2')
        # can view
        self.assertTrue(self.hasPermission(View, developers_advice))
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
        self.assertTrue(self.hasPermission(View, vendors_advice))
        # can not edit/delete
        self.assertFalse(self.hasPermission('Modify portal content', vendors_advice))
        self.assertFalse(self.hasPermission('Delete objects', vendors_advice))

    def test_pm_CanNotGiveAdviceIfNotAsked(self):
        '''
          Test that an adviser that can access an item can not give his advice
          if it was not asked.
        '''
        # create an item and ask advice of 'vendors'
        self.changeUser('pmCreator1')
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
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(itemAdviceStates)
        cfg.setItemAdviceEditStates(itemAdviceEditStates)
        cfg.setItemAdviceViewStates(itemAdviceViewStates)
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors',)
        }
        item1 = self.create('MeetingItem', **data)
        self.assertEquals(item1.adapted().showAdvices(), True)
        # check than the adviser can see the item
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.assertEquals(item1.getAdvicesGroupsInfosForUser(), ([('vendors', u'Vendors')], []))
        self.failUnless(self.hasPermission(AddAdvice, item1))

    def test_pm_AdvicesInvalidation(self):
        '''Test the advice invalidation process.'''
        # advisers can give an advice when item is 'proposed' or 'validated'
        # activate advice invalidation in state 'validated'
        cfg = self.meetingConfig
        cfg.setEnableAdviceInvalidation(True)
        cfg.setItemAdviceInvalidateStates((self.WF_STATE_NAME_MAPPINGS['validated'],))
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors',)
        }
        item = self.create('MeetingItem', **data)
        self.assertEquals(item.adapted().showAdvices(), True)
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
        # login as an user that can actually edit the item because not 'validated'
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission('Modify portal content', item))
        # modifying the item will not invalidate the advices because not 'validated'
        self.failIf(item.willInvalidateAdvices())
        item.setDecision(item.getDecision() + '<p>New line</p>')
        item.at_post_edit_script()
        # check that advices are still there
        self.failUnless(item.hasAdvices())
        # adding an annex or editing a field thru ajax does not invalidate the item because not 'validated'
        annex1 = self.addAnnex(item)
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
        annex1 = self.addAnnex(item)
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
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        # an advice can be given or edited when an item is 'proposed'
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', 'vendors__rowid__unique_id_123', ))
        item.updateLocalRoles()
        # no advice to give as item is 'itemcreated'
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__not_given',
                                                                  'delay__vendors_advice_not_giveable',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__not_given',
                                                                  'developers_advice_not_giveable',
                                                                  'not_given']))
        self.proposeItem(item)
        item.reindexObject()
        self.changeUser('pmAdviser1')
        # now advice are giveable but not given
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__not_given',
                                                                  'delay__vendors_advice_not_given',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__not_given',
                                                                  'developers_advice_not_given',
                                                                  'not_given']))
        itemUID = item.UID()
        brains = self.portal.portal_catalog(indexAdvisers='developers_advice_not_given')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        brains = self.portal.portal_catalog(indexAdvisers='delay_real_group_id__unique_id_123')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # create the advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'developers',
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        # now that an advice has been given for the developers group, the indexAdvisers has been updated
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__not_given',
                                                                  'delay__vendors_advice_not_given',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__positive',
                                                                  'developers_advice_under_edit',
                                                                  'not_given', 'positive']))
        brains = self.portal.portal_catalog(indexAdvisers='developers_advice_under_edit')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)

        # turn advice to hidden during redaction
        changeHiddenDuringRedactionView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeHiddenDuringRedactionView()
        self.assertTrue(advice.advice_hide_during_redaction)
        self.assertEquals(set(indexAdvisers.callable(item)),
                          set(['delay_real_group_id__unique_id_123',
                               'delay_real_group_id__unique_id_123__not_given',
                               'delay__vendors_advice_not_given',
                               'real_group_id__developers',
                               'real_group_id__developers__hidden_during_redaction',
                               'developers_advice_under_edit',
                               'not_given', HIDDEN_DURING_REDACTION_ADVICE_VALUE]))
        brains = self.portal.portal_catalog(indexAdvisers='real_group_id__developers__hidden_during_redaction')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # makes this advice 'considered_not_given_hidden_during_redaction'
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        self.assertEquals(set(indexAdvisers.callable(item)),
                          set(['delay_real_group_id__unique_id_123',
                               'delay_real_group_id__unique_id_123__not_given',
                               'delay__vendors_advice_not_giveable',
                               'real_group_id__developers',
                               'real_group_id__developers__considered_not_given_hidden_during_redaction',
                               'developers_advice_given',
                               'not_given', CONSIDERED_NOT_GIVEN_ADVICE_VALUE]))
        brains = self.portal.portal_catalog(
            indexAdvisers='real_group_id__developers__considered_not_given_hidden_during_redaction')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # back to 'proposed' and not more hidden_during_redaction
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmAdviser1')
        changeHiddenDuringRedactionView()

        # now change the value of the created meetingadvice.advice_group
        advice.advice_group = self.tool.vendors.getId()
        # notify modified
        notify(ObjectModifiedEvent(advice))
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__positive',
                                                                  'delay__vendors_advice_under_edit',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__not_given',
                                                                  'developers_advice_not_given',
                                                                  'not_given', 'positive']))
        # the index in the portal_catalog is updated too
        brains = self.portal.portal_catalog(indexAdvisers='delay__vendors_advice_under_edit')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)

        # put the item in a state where given advices are not editable anymore
        self.changeUser('pmReviewer1')
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__positive',
                                                                  'delay__vendors_advice_given',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__not_given',
                                                                  'developers_advice_not_giveable',
                                                                  'not_given', 'positive']))
        # ask a given advice again
        self.changeUser('pmCreator1')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.assertEquals(sorted(indexAdvisers.callable(item)),
                          ['asked_again',
                           'delay__vendors_advice_given',
                           'delay__vendors_advice_not_giveable',
                           'delay_real_group_id__unique_id_123',
                           'delay_real_group_id__unique_id_123__asked_again',
                           'developers_advice_not_giveable',
                           'not_given',
                           'real_group_id__developers',
                           'real_group_id__developers__not_given'])

        # put it back to a state where it is editable
        self.proposeItem(item)
        self.assertEquals(sorted(indexAdvisers.callable(item)),
                          ['asked_again',
                           'delay__vendors_advice_asked_again',
                           'delay__vendors_advice_under_edit',
                           'delay_real_group_id__unique_id_123',
                           'delay_real_group_id__unique_id_123__asked_again',
                           'developers_advice_not_given',
                           'not_given',
                           'real_group_id__developers',
                           'real_group_id__developers__not_given'])

        # delete the advice
        self.changeUser('pmAdviser1')
        item.restrictedTraverse('@@delete_givenuid')(advice.UID())
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__not_given',
                                                                  'delay__vendors_advice_not_given',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__not_given',
                                                                  'developers_advice_not_given',
                                                                  'not_given']))
        # the index in the portal_catalog is updated too
        brains = self.portal.portal_catalog(indexAdvisers='delay__vendors_advice_not_given')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        brains = self.portal.portal_catalog(indexAdvisers='developers_advice_not_given')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # if a delay-aware advice delay is exceeded, it is indexed with an ending '2'
        item.adviceIndex['vendors']['delay_started_on'] = datetime(2012, 01, 01)
        item.updateLocalRoles()
        self.assertEquals(set(indexAdvisers.callable(item)), set(['delay_real_group_id__unique_id_123',
                                                                  'delay_real_group_id__unique_id_123__not_given',
                                                                  'delay__vendors_advice_delay_exceeded',
                                                                  'real_group_id__developers',
                                                                  'real_group_id__developers__not_given',
                                                                  'developers_advice_not_given',
                                                                  'not_given']))

    def test_pm_IndexAdvisersCombinedIndex(self):
        '''Test the indexAdvisers 'combined idnex' functionnality that makes it possible
           to query items having advice of a given group using a given advice_type.'''
        # an advice can be given when an item is 'proposed' or 'validated'
        self.assertEquals(self.meetingConfig.getItemAdviceStates(),
                          (self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # create 3 items with various advices
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers', 'vendors', ))
        item1.updateLocalRoles()
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('developers'))
        item2.updateLocalRoles()
        item3 = self.create('MeetingItem')
        item3.setOptionalAdvisers(())
        item3.updateLocalRoles()

        # query not_given advices
        catalog = self.portal.portal_catalog
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='not_given')]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers')]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers__not_given')]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__vendors__not_given')]),
                          set([item1.UID()]))

        # give positive developers advice on item1
        self.proposeItem(item1)
        item1.reindexObject()
        self.changeUser('pmAdviser1')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': 'developers',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # query not given and positive advices
        self.changeUser('pmCreator1')
        # item1 still have vendors advice not given
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='not_given')]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers=['not_given', 'positive'])]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers')]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers__not_given')]),
                          set([item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers__positive')]),
                          set([item1.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__vendors__not_given')]),
                          set([item1.UID()]))

        # give negative developers advice on item2
        self.changeUser('pmCreator1')
        self.proposeItem(item2)
        item2.reindexObject()
        self.changeUser('pmAdviser1')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': 'developers',
                                    'advice_type': u'negative',
                                    'advice_comment': RichTextValue(u'My comment')})
        # query not given and positive advices
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers=['not_given'])]),
                          set([item1.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers=['positive'])]),
                          set([item1.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers=['negative'])]),
                          set([item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers')]),
                          set([item1.UID(), item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers__negative')]),
                          set([item2.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__developers__positive')]),
                          set([item1.UID()]))
        self.assertEquals(set([brain.UID for brain in catalog(indexAdvisers='real_group_id__vendors__not_given')]),
                          set([item1.UID()]))

    def test_pm_AutomaticAdvices(self):
        '''Test the automatic advices mechanism, some advices can be
           automatically asked under specific conditions.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', ))
        item.at_post_edit_script()
        self.assertTrue('developers' in item.adviceIndex)
        self.assertFalse('vendors' in item.adviceIndex)
        # now make 'vendors' advice automatically asked
        # it will be asked if item.budgetRelated is True
        cfg.setCustomAdvisers(
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
        cfg.setCustomAdvisers([{'row_id': 'unique_id_123',
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

        # now make sure an adviser of 'vendors' may add his advice and updateLocalRoles
        # in MeetingItem._updateAdvices, this is why we call getAutomaticAdvisersData
        # with api.env.adopt_roles(['Reader', ])
        self.proposeItem(item)
        item.updateLocalRoles()
        self.assertTrue('vendors' in item.adviceIndex)
        self.changeUser('pmReviewer2')
        item.updateLocalRoles()
        # 'vendors' is still in adviceIndex, the TAL expr could be evaluated correctly
        self.assertTrue('vendors' in item.adviceIndex)
        self.assertEquals(item.getAdvicesGroupsInfosForUser(),
                          ([('vendors', 'Vendors')], []))
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})

    def test_pm_GivenDelayAwareAutomaticAdviceLeftEvenIfItemConditionChanged(self):
        '''This test that if an automatic advice is asked because a condition
           on the item is True, the automatic advice is given then the condition
           on the item changes, the advice is kept.'''
        self.meetingConfig.setCustomAdvisers([{'row_id': 'unique_id_123',
                                               'group': 'vendors',
                                               'gives_auto_advice_on': 'item/getBudgetRelated',
                                               'for_item_created_from': '2012/01/01',
                                               'delay': '10'}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setBudgetRelated(True)
        item.at_post_edit_script()
        # the automatic advice is asked
        self.assertTrue('vendors' in item.adviceIndex)
        self.assertTrue(not item.adviceIndex['vendors']['optional'])
        self.assertTrue(item.getAutomaticAdvisersData()[0]['meetingGroupId'] == 'vendors')
        # now give the advice
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        item.setBudgetRelated(False)
        item.at_post_edit_script()
        # the automatic advice is still there even if no more returned by getAutomaticAdvisersData
        self.assertTrue('vendors' in item.adviceIndex)
        self.assertTrue(not item.adviceIndex['vendors']['optional'])
        self.assertTrue(not item.getAutomaticAdvisersData())

    def test_pm_GetAutomaticAdvisers(self):
        '''Test the getAutomaticAdvisersData method that compute automatic advices to ask.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        cfg.setCustomAdvisers([])
        # if nothing defined, getAutomaticAdvisersData returns nothing...
        self.failIf(item.getAutomaticAdvisersData())
        # define some customAdvisers
        cfg.setCustomAdvisers([])
        cfg.setCustomAdvisers(
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
              'delay_label': ''},
             # an non automatic advice configuration
             {'row_id': 'unique_id_789',
              'group': 'developers',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'delay': '10',
              'delay_label': ''}])
        # one wrong condition (raising an error when evaluated) and one returning False
        self.failIf(item.getAutomaticAdvisersData())
        # now make the second row expression return True, set item.budgetRelated
        item.setBudgetRelated(True)
        self.assertEquals(item.getAutomaticAdvisersData(),
                          [{'gives_auto_advice_on_help_message': '',
                            'meetingGroupId': 'developers',
                            'meetingGroupName': 'Developers',
                            'row_id': 'unique_id_456',
                            'delay': '',
                            'delay_left_alert': '',
                            'delay_label': ''}])
        # define one condition for wich the date is > than current item CreationDate
        futureDate = DateTime() + 1
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': futureDate.strftime('%Y/%m/%d'),
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        # nothing should be returned as defined date is bigger than current item's date
        self.assertTrue(futureDate > item.created())
        self.failIf(item.getAutomaticAdvisersData())
        # define an old 'for_item_created_from' and a 'for_item_created_until' in the future
        # the advice should be considered as automatic advice to ask
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': futureDate.strftime('%Y/%m/%d'),
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        self.assertEquals(item.getAutomaticAdvisersData(),
                          [{'gives_auto_advice_on_help_message': '',
                            'meetingGroupId': 'developers',
                            'meetingGroupName': 'Developers',
                            'row_id': 'unique_id_123',
                            'delay': '',
                            'delay_left_alert': '',
                            'delay_label': ''}])
        # now define a 'for_item_created_until' that is in the past
        # relative to the item created date
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '2013/01/01',
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        self.failIf(item.getAutomaticAdvisersData())

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

    def test_pm_DelayStartedStoppedOn(self):
        '''Test the 'advice_started_on' and 'advice_stopped_on' date initialization.
           The 'advice_started_on' is set when advice are turning to 'giveable', aka when
           they turn from not being in itemAdviceStates to being in it.
           The 'advice_stopped_on' date is initialized when the advice is no more giveable,
           so when the item state is no more in itemAdviceStates.
           The 2 dates are only reinitialized to None if the user
           triggers the MeetingConfig.transitionsReinitializingDelays.
        '''
        self.meetingConfig.setKeepAccessToItemWhenAdviceIsGiven(False)
        self._checkDelayStartedStoppedOn()

    def test_pm_DelayStartedStoppedOnWithKeepAccessToItemWhenAdviceIsGiven(self):
        '''Same has 'test_pm_DelayStartedStoppedOn' but when
           MeetingConfig.keepAccessToItemWhenAdviceIsGiven is True.
        '''
        self.meetingConfig.setKeepAccessToItemWhenAdviceIsGiven(True)
        self._checkDelayStartedStoppedOn()

    def _checkDelayStartedStoppedOn(self):
        # make advice giveable when item is 'validated'
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(('validated', ))
        cfg.setItemAdviceEditStates(('validated', ))
        self.changeUser('pmManager')
        # configure one automatic adviser with delay
        # and ask one non-delay-aware optional adviser
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''}, ])
        data = {
            'title': 'Item to advice',
            'category': 'maintenance'
        }
        item = self.create('MeetingItem', **data)
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # advice are correctly asked
        self.assertEquals(item.adviceIndex.keys(), ['vendors', 'developers'])
        # for now, dates are not defined
        self.assertEquals([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        self.assertEquals([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        # propose the item, nothing should have changed
        self.proposeItem(item)
        self.assertEquals(item.adviceIndex.keys(), ['vendors', 'developers'])
        self.assertEquals([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        self.assertEquals([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        # now do delays start
        # delay will start when the item advices will be giveable
        # advices are giveable when item is validated, so validate the item
        # this will initialize the 'delay_started_on' date
        self.validateItem(item)
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['validated'])
        # we have datetime now in 'delay_started_on' and still nothing in 'delay_stopped_on'
        self.assertTrue(isinstance(item.adviceIndex['developers']['delay_started_on'], datetime))
        self.assertTrue(item.adviceIndex['developers']['delay_stopped_on'] is None)
        # vendors optional advice is not delay-aware
        self.assertTrue(item.adviceIndex['vendors']['delay_started_on'] is None)
        self.assertTrue(item.adviceIndex['vendors']['delay_stopped_on'] is None)

        # set item back to proposed, 'delay_stopped_on' should be set
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertTrue(isinstance(item.adviceIndex['developers']['delay_started_on'], datetime))
        self.assertTrue(isinstance(item.adviceIndex['developers']['delay_stopped_on'], datetime))
        # vendors optional advice is not delay-aware
        self.assertTrue(item.adviceIndex['vendors']['delay_started_on'] is None)
        self.assertTrue(item.adviceIndex['vendors']['delay_stopped_on'] is None)

        # if we go on, the 'delay_started_on' date does not change anymore, even in a state where
        # advice are not giveable anymore, but at this point, the 'delay_stopped_date' will be set.
        # We present the item
        self.create('Meeting', date=DateTime('2012/01/01'))
        saved_developers_start_date = item.adviceIndex['developers']['delay_started_on']
        saved_vendors_start_date = item.adviceIndex['vendors']['delay_started_on']
        self.presentItem(item)
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['presented'])
        self.assertEquals(item.adviceIndex['developers']['delay_started_on'], saved_developers_start_date)
        self.assertEquals(item.adviceIndex['vendors']['delay_started_on'], saved_vendors_start_date)
        # the 'delay_stopped_on' is now set on the delay-aware advice
        self.assertTrue(isinstance(item.adviceIndex['developers']['delay_stopped_on'], datetime))
        self.assertTrue(item.adviceIndex['vendors']['delay_stopped_on'] is None)
        # if we excute the transition that will reinitialize dates, it is 'backToItemCreated'
        self.assertEquals(cfg.getTransitionsReinitializingDelays(),
                          (self.WF_TRANSITION_NAME_MAPPINGS['backToItemCreated'], ))
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        # the delays have been reinitialized to None
        self.assertEquals([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                          [None, None])
        self.assertEquals([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                          [None, None])

    def test_pm_MayNotAddAdviceEditIfDelayExceeded(self):
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
        item.updateLocalRoles()
        # if delay is negative, we show complete delay
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] == 5)
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['delay_status'] == 'timed_out')
        self.assertTrue(not self.hasPermission(AddAdvice, item))
        # recover delay, add the advice and check the 'edit' behaviour
        item.adviceIndex['vendors']['delay_started_on'] = datetime.now()
        item.updateLocalRoles()
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
        item.updateLocalRoles()
        # when delay is exceeded, left_delay is complete delay so we show it in red
        # we do not show the exceeded delay because it could be very large (-654?)
        # and represent nothing...
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['left_delay'] == 5)
        # 'delay_status' is 'timed_out'
        self.assertTrue(item.getDelayInfosForAdvice('vendors')['delay_status'] == 'timed_out')
        self.assertTrue(not self.hasPermission(ModifyPortalContent, advice))

    def test_pm_MeetingGroupDefinedItemAdviceStatesValuesOverridesMeetingConfigValues(self):
        '''Advices are giveable/editable/viewable depending on defined item states on the MeetingConfig,
           these states can be overrided locally for a particular MeetingGroup so this particluar MeetingGroup
           will be able to add an advice in different states than one defined globally on the MeetingConfig.'''
        # by default, nothing defined on the MeetingGroup, the MeetingConfig states are used
        vendors = self.tool.vendors
        # getItemAdviceStates on a MeetingGroup returns values of the meetingConfig
        # if nothing is defined on the meetingGroup
        self.assertTrue(not vendors.getItemAdviceStates())
        # make advice giveable when item is proposed
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.assertTrue(vendors.getItemAdviceStates(cfg) == cfg.getItemAdviceStates())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # ask 'vendors' advice
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_create_script()
        self.proposeItem(item)
        self.assertTrue(item.queryState() == self.WF_STATE_NAME_MAPPINGS['proposed'])
        # the advice is giveable by the vendors
        self.changeUser('pmReviewer2')
        self.assertTrue('vendors' in [key for key, value in item.getAdvicesGroupsInfosForUser()[0]])
        # now if we define on the 'vendors' MeetingGroup.itemAdviceStates
        # that advice is giveable when item is 'validated', it will not be anymore
        # in 'proposed' state, but well in 'validated' state
        self.changeUser('admin')
        vendors.setItemAdviceStates(("%s__state__%s" % (cfg.getId(),
                                                        self.WF_STATE_NAME_MAPPINGS['validated'])))
        # no more using values defined on the meetingConfig
        self.assertTrue(not vendors.getItemAdviceStates(cfg) == cfg.getItemAdviceStates())
        self.assertTrue(vendors.getItemAdviceStates(cfg) == (self.WF_STATE_NAME_MAPPINGS['validated'], ))
        item.at_post_create_script()
        self.changeUser('pmReviewer2')
        self.assertTrue(not 'vendors' in [key for key, value in item.getAdvicesGroupsInfosForUser()[0]])
        # now validate the item and the advice is giveable
        self.changeUser('pmManager')
        self.validateItem(item)
        self.changeUser('pmReviewer2')
        self.assertTrue(item.queryState() == self.WF_STATE_NAME_MAPPINGS['validated'])
        self.assertTrue('vendors' in [key for key, value in item.getAdvicesGroupsInfosForUser()[0]])

        # it is the same for itemAdviceEditStates and itemAdviceViewStates
        self.assertTrue(vendors.getItemAdviceEditStates(cfg) == cfg.getItemAdviceEditStates())
        self.assertTrue(vendors.getItemAdviceViewStates(cfg) == cfg.getItemAdviceViewStates())
        vendors.setItemAdviceEditStates(("%s__state__%s" % (cfg.getId(),
                                                            self.WF_STATE_NAME_MAPPINGS['validated'])))
        vendors.setItemAdviceViewStates(("%s__state__%s" % (cfg.getId(),
                                                            self.WF_STATE_NAME_MAPPINGS['validated'])))
        self.assertTrue(not vendors.getItemAdviceEditStates(cfg) == cfg.getItemAdviceEditStates())
        self.assertTrue(vendors.getItemAdviceEditStates(cfg) == (self.WF_STATE_NAME_MAPPINGS['validated'], ))
        self.assertTrue(not vendors.getItemAdviceViewStates(cfg) == cfg.getItemAdviceViewStates())
        self.assertTrue(vendors.getItemAdviceViewStates(cfg) == (self.WF_STATE_NAME_MAPPINGS['validated'], ))

    def test_pm_MeetingGroupDefinedItemAdviceStatesWorksTogetherWithMeetingConfigValues(self):
        '''Advices giveable/editable/viewable states defined for a MeetingConfig on a MeetingGroup will
           not interact other MeetingConfig for which nothing is defined on this MeetingGroup...'''
        # make advices giveable for vendors for cfg1 in state 'proposed' and define nothing regarding
        # cfg2, values defined on the cfg2 will be used
        cfg = self.meetingConfig
        vendors = self.tool.vendors
        vendors.setItemAdviceStates(("%s__state__%s" % (cfg.getId(),
                                                        self.WF_STATE_NAME_MAPPINGS['proposed'])))
        vendors.setItemAdviceEditStates(("%s__state__%s" % (cfg.getId(),
                                                            self.WF_STATE_NAME_MAPPINGS['proposed'])))
        vendors.setItemAdviceViewStates(("%s__state__%s" % (cfg.getId(),
                                                            self.WF_STATE_NAME_MAPPINGS['proposed'])))
        cfg2 = self.meetingConfig2
        cfg2.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['itemcreated'], ))
        cfg2.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['itemcreated'], ))
        cfg2.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['itemcreated'], ))

        # getting states for cfg2 will get states on the cfg2
        self.assertTrue(vendors.getItemAdviceStates(cfg2) == cfg2.getItemAdviceStates())
        self.assertTrue(vendors.getItemAdviceEditStates(cfg2) == cfg2.getItemAdviceEditStates())
        self.assertTrue(vendors.getItemAdviceViewStates(cfg2) == cfg2.getItemAdviceViewStates())

    def test_pm_PowerAdvisers(self):
        '''Power advisers are users that can give an advice even when not asked...
           This will give these users opportunity to add the advice but 'View' access to the relevant
           item is given by another functionnality (MeetingManager, power observer, ...).'''
        # set developers as power advisers
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setPowerAdvisersGroups(('developers', ))
        cfg.setItemPowerObserversStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        item.at_post_edit_script()
        # pmAdviser1 must have 'View' on the item to be able to give advice
        # for now, it is not the case, the 'View' is not given automatically to power advisers
        self.changeUser('pmAdviser1')
        # pmAdviser1 is not power adviser
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, isRestricted=False))
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, isRestricted=True))
        self.assertTrue(not 'developers' in item.adviceIndex)
        # he may not see item
        self.failIf(self.hasPermission(View, item))
        # but he is able to add the advice
        self.failUnless(self.hasPermission(AddPortalContent, item))
        self.failUnless(self.hasPermission(AddAdvice, item))
        # right, give 'View' access, now pmAdviser1 will be able to see the item
        # add pmAdviser1 to power observers
        self.changeUser('siteadmin')
        self.portal.portal_groups.addPrincipalToGroup('pmAdviser1', '%s_%s' %
                                                      (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX))
        item.updateLocalRoles()
        self.changeUser('pmAdviser1')
        # pmAdviser1 can give advice for developers even if
        # not asked, aka not in item.adviceIndex
        self.assertTrue(not 'developers' in item.adviceIndex)
        self.failUnless(self.hasPermission(AddPortalContent, item))
        self.failUnless(self.hasPermission(AddAdvice, item))
        self.failUnless(self.hasPermission(View, item))
        # he can actually give it
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'developers',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})

        # he can give advice for every groups he is adviser for
        # here as only adviser for 'developers', he can not give an advice anymore
        # after having given the advice for 'developers'
        self.failIf(self.hasPermission(AddAdvice, item))
        # but he can still see the item obviously
        self.failUnless(self.hasPermission(View, item))
        # but if he is also adviser for 'vendors', he can give it also
        self.changeUser('admin')
        self.portal.portal_groups.addPrincipalToGroup('pmAdviser1', 'vendors_advisers')
        cfg.setPowerAdvisersGroups(('developers', 'vendors', ))
        item.updateLocalRoles()
        # now as pmAdviser1 is adviser for vendors and vendors is a PowerAdviser,
        # he can add an advice for vendors
        self.changeUser('pmAdviser1')
        self.assertTrue(not 'vendors' in item.adviceIndex)
        self.failUnless(self.hasPermission(AddAdvice, item))
        self.failUnless(self.hasPermission(View, item))
        # make sure he can not add an advice for an other group he is adviser for
        # but he already gave the advice for.  So check that 'developers' is not in the
        # meetingadvice.advice_group vocabulary
        factory = queryUtility(IVocabularyFactory, u'Products.PloneMeeting.content.advice.advice_group_vocabulary')
        vocab = factory(item)
        self.assertTrue(len(vocab) == 1)
        self.assertTrue('vendors' in vocab)
        self.assertTrue(not 'developers' in vocab)

    def test_pm_ComputeDelaysWorkingDaysAndHolidaysAndUnavailableEndDays(self):
        '''Test that computing of delays relying on workingDays, holidays
           and unavailable ending days is correct.'''
        # configure one delay-aware optional adviser
        # we use 7 days of delay so we are sure that we when setting
        # manually 'delay_started_on' to last monday, delay is still ok
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '7',
              'delay_label': ''}, ])
        # no holidays for now...
        self.tool.setHolidays([])
        # no unavailable ending days for now...
        self.tool.setDelayUnavailableEndDays([])
        # make advice giveable when item is proposed
        self.meetingConfig.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.meetingConfig.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.meetingConfig.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item.at_post_edit_script()
        self.proposeItem(item)
        # advice should be giveable during 7 working days, we set manually 'delay_started_on'
        # to last monday (or today if we are monday) so we are sure about delay and limit_date and so on...
        delay_started_on = item.adviceIndex['vendors']['delay_started_on']
        while not delay_started_on.weekday() == 0:
            delay_started_on = delay_started_on - timedelta(1)
        item.adviceIndex['vendors']['delay_started_on'] = delay_started_on
        item.updateLocalRoles()
        self.assertTrue(item.adviceIndex['vendors']['delay_started_on'].weekday() == 0)
        # for now, weekends are days 5 and 6, so saturday and sunday
        self.assertTrue(self.tool.getNonWorkingDayNumbers() == [5, 6])
        # limit_date should be in 9 days, 7 days of delay + 2 days of weekends
        limit_date_9_days = item._doClearDayFrom(item.adviceIndex['vendors']['delay_started_on'] + timedelta(9))
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['limit_date'] == limit_date_9_days)
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['delay_status'] == 'still_time')
        # now set weekends to only 'sunday'
        self.tool.setWorkingDays(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', ))
        # the method is ram.cached, check that it is correct when changed
        self.tool.setModificationDate(DateTime())
        self.assertTrue(self.tool.getNonWorkingDayNumbers() == [6, ])
        item.updateLocalRoles()
        # this will decrease delay of one day
        self.assertTrue(limit_date_9_days - timedelta(1) ==
                        item.adviceIndex['vendors']['delay_infos']['limit_date'])
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['delay_status'] == 'still_time')

        # now add 2 holidays, one passed date and one date that will change delay
        # a date next day after the 'delay_started_on'
        delay_started_on = item.adviceIndex['vendors']['delay_started_on']
        holiday_changing_delay = '%s' % (delay_started_on + timedelta(1)).strftime('%Y/%m/%d')
        self.tool.setHolidays(({'date': '2012/05/06'},
                               {'date': holiday_changing_delay}, ))
        # the method getHolidaysAs_datetime is ram.cached, check that it is correct when changed
        self.tool.setModificationDate(DateTime())
        year, month, day = holiday_changing_delay.split('/')
        self.assertTrue(self.tool.getHolidaysAs_datetime() == [datetime(2012, 5, 6),
                                                               datetime(int(year), int(month), int(day)), ])
        # this should increase delay of one day, so as original limit_date_9_days
        item.updateLocalRoles()
        self.assertTrue(limit_date_9_days == item.adviceIndex['vendors']['delay_infos']['limit_date'])
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['delay_status'] == 'still_time')

        # now add one unavailable day for end of delay
        # for now, limit_date ends day number 2, so wednesday
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['limit_date'].weekday() == 2)
        self.tool.setDelayUnavailableEndDays(('wed', ))
        # the method getUnavailableWeekDaysNumbers is ram.cached, check that it is correct when changed
        self.tool.setModificationDate(DateTime())
        self.assertTrue(self.tool.getUnavailableWeekDaysNumbers() == [2, ])
        item.updateLocalRoles()
        # this increase limit_date of one day, aka next available day
        self.assertTrue(limit_date_9_days + timedelta(1) == item.adviceIndex['vendors']['delay_infos']['limit_date'])
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['delay_status'] == 'still_time')
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['limit_date'].weekday() == 3)

        # test that the advice may still be added the last day
        # to avoid that current day (aka last day) is a weekend or holiday or unavailable day
        # or so, we just remove everything that increase/decrease delay
        self.tool.setDelayUnavailableEndDays([])
        self.tool.setHolidays([])
        self.tool.setWorkingDays(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', ))
        self.tool.setModificationDate(DateTime())
        # change 'delay_started_on' manually and check that last day, the advice is 'still_giveable'
        item.adviceIndex['vendors']['delay_started_on'] = datetime.now() - timedelta(7)
        item.updateLocalRoles()
        # we are the last day
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['limit_date'].day == datetime.now().day)
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['delay_status'] == 'still_time')
        # one day more and it is not giveable anymore...
        item.adviceIndex['vendors']['delay_started_on'] = datetime.now() - timedelta(8)
        item.updateLocalRoles()
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['limit_date'] < datetime.now())
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['delay_status'] == 'timed_out')

    def test_pm_ComputeDelaysAsCalendarDays(self):
        '''
          Test that computing of delays works also as 'calendar days'.
          To do this, we simply define 7 days of the week as working days and no holidays.
        '''
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': ''}, ])
        # no holidays...
        self.tool.setHolidays([])
        # every days are working days
        self.tool.setWorkingDays(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', ))
        self.assertTrue(self.tool.getNonWorkingDayNumbers() == [])
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item.at_post_edit_script()
        self.proposeItem(item)
        # now test that limit_date is just now + delay of 10 days
        self.assertTrue(item.adviceIndex['vendors']['delay_infos']['limit_date'] ==
                        item._doClearDayFrom(item.adviceIndex['vendors']['delay_started_on'] + timedelta(10)))

    def test_pm_AvailableDelaysView(self):
        '''Test the view '@@advice-available-delays' that shows
           available delays for a selected delay-aware advice.'''
        cfg = self.meetingConfig
        # make advice addable and editable when item is 'proposed'
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['proposed'],
                                     self.WF_STATE_NAME_MAPPINGS['validated']))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # no other linked delay
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '5',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # select delay of 5 days
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item.at_post_edit_script()
        availableDelaysView = item.restrictedTraverse('@@advice-available-delays')
        # some values are defined in the __init__ of the view
        availableDelaysView.advice = item.adviceIndex['vendors']
        availableDelaysView.cfg = cfg
        self.assertFalse(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']))
        # now add delays to change to
        customAdvisers += [{'row_id': 'unique_id_456',
                            'group': 'vendors',
                            'gives_auto_advice_on': '',
                            'for_item_created_from': '2012/01/01',
                            'for_item_created_until': '',
                            'delay': '10',
                            'delay_label': '',
                            'available_on': '',
                            'is_linked_to_previous_row': '1'},
                           {'row_id': 'unique_id_789',
                            'group': 'vendors',
                            'gives_auto_advice_on': '',
                            'for_item_created_from': '2012/01/01',
                            'for_item_created_until': '',
                            'delay': '20',
                            'delay_label': '',
                            'available_on': '',
                            'is_linked_to_previous_row': '1'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # we need to cleanRamCacheFor _findLinkedRowsFor used by listSelectableDelays
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        # the delay may still be edited when the user can edit the item
        # except if it is an automatic advice for wich only MeetingManagers may change delay
        self.assertEquals(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                          [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # the creator may only edit the delays if it has the 'PloneMeeting: Write optional advisers' permission
        # if pmCreator1 propose the item, it can no more edit it so it can not change delays
        # now propose the item, selectable delays should be empty
        self.proposeItem(item)
        self.assertFalse(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']))
        # the pmReviewer1 can change delay as he can write optional advisers
        self.changeUser('pmReviewer1')
        self.assertEquals(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                          [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])

        # makes it an automatic advice
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.changeUser('pmCreator1')
        item.at_post_edit_script()
        customAdvisers[0]['gives_auto_advice_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        # MeetingConfig._findLinkedRowsFor is ram cached
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        item.setOptionalAdvisers(())
        item.at_post_edit_script()
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [])
        self.proposeItem(item)
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [])
        # the pmReviewer1 can not change an automatic advice delay
        self.changeUser('pmReviewer1')
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [])
        # a MeetingManager may edit an automatic advice delay
        self.changeUser('pmManager')
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # test the 'available_on' behaviour
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertTrue(item.adviceIndex['vendors']['delay_stopped_on'] is None)
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # now define a 'available_on' for third row
        # first step, something that is False
        customAdvisers[2]['available_on'] = 'python:False'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ])
        # a wrong TAL expression for 'available_on' does not break anything
        customAdvisers[2]['available_on'] = 'python:here.someUnexistingMethod()'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ])
        # second step, something that is True
        customAdvisers[2]['available_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # now test the particular expression that makes a custom adviser
        # useable when changing delays but not in other cases
        customAdvisers[2]['available_on'] = "python:item.REQUEST.get('managing_available_delays', False)"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])

        # the mayEdit variable is available in the expression, it is True if current
        # user may edit item, False otherwise
        customAdvisers[2]['available_on'] = "mayEdit"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        customAdvisers[2]['available_on'] = "not:mayEdit"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(item.adviceIndex['vendors']['row_id']),
                         [('unique_id_456', '10', u''), ])

    def test_pm_ChangeDelayView(self):
        '''Test the view '@@change-advice-delay' that apply the change delay action.'''
        cfg = self.meetingConfig
        # make advice addable and editable when item is 'proposed'
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['proposed'],
                                     self.WF_STATE_NAME_MAPPINGS['validated']))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '5',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0'},
                          {'row_id': 'unique_id_456',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '10',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '20',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # select delay of 5 days
        item.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        item.at_post_edit_script()
        # for now, delay is 5 days and 'row_id' is unique_id_123
        self.assertTrue(item.adviceIndex['vendors']['row_id'] == 'unique_id_123')
        self.assertTrue(item.adviceIndex['vendors']['delay'] == '5')
        self.assertTrue(item.adviceIndex['vendors']['optional'] is True)
        changeDelayForm = item.restrictedTraverse('@@advice_delay_change_form').form_instance
        self.request['form.widgets.current_delay_row_id'] = u'unique_id_123'

        # first check that if we try to play the fennec, it raises Unauthorized
        self.request['form.widgets.new_delay_row_id'] = u'some_dummy_value'
        self.assertRaises(Unauthorized, changeDelayForm)
        # now change the delay, really
        self.request['form.widgets.new_delay_row_id'] = u'unique_id_789'
        # delay is changed to third custom adviser, aka 20 days
        changeDelayForm()
        changeDelayForm.handleSaveAdviceDelay(changeDelayForm, '')
        # not changed as comment is required
        self.assertEqual(item.adviceIndex['vendors']['row_id'], 'unique_id_123')
        self.assertEqual(item.adviceIndex['vendors']['delay'], '5')
        # now apply with comment
        self.request['form.widgets.comment'] = u'My comment'
        changeDelayForm.handleSaveAdviceDelay(changeDelayForm, '')
        self.assertTrue(item.adviceIndex['vendors']['row_id'] == 'unique_id_789')
        self.assertTrue(item.adviceIndex['vendors']['delay'] == '20')
        # a special key save the fact that we saved delay of an automatic adviser
        # this should be 'False' for now as we changed an optional adviser delay
        self.assertTrue(item.adviceIndex['vendors']['delay_for_automatic_adviser_changed_manually'] is False)

        # it works also for automatic advices but only MeetingManagers may change it
        # makes it an automatic advice
        customAdvisers[0]['gives_auto_advice_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        # MeetingConfig._findLinkedRowsFor is ram cached, based on MC modified
        cfg.processForm({'dummy': ''})
        item.setOptionalAdvisers(())
        item.at_post_edit_script()
        self.assertTrue(item.adviceIndex['vendors']['row_id'] == 'unique_id_123')
        self.assertTrue(item.adviceIndex['vendors']['delay'] == '5')
        self.assertTrue(item.adviceIndex['vendors']['optional'] is False)
        # if a normal user tries to change an automatic advice delay, it will raises Unauthorized
        self.assertRaises(Unauthorized, changeDelayForm.handleSaveAdviceDelay, changeDelayForm, '')
        # now as MeetingManager it works
        self.changeUser('pmManager')
        changeDelayForm.handleSaveAdviceDelay(changeDelayForm, '')
        self.assertTrue(item.adviceIndex['vendors']['row_id'] == 'unique_id_789')
        self.assertTrue(item.adviceIndex['vendors']['delay'] == '20')
        self.assertTrue(item.adviceIndex['vendors']['delay_for_automatic_adviser_changed_manually'] is True)

    def test_pm_ConfigAdviceStates(self):
        '''
          This test that states defined in config.py in two constants
          ADVICE_STATES_ALIVE and ADVICE_STATES_ENDED
          consider every states of the workflow used for content_type 'meetingadvice'.
        '''
        adviceWF = self.wfTool.getWorkflowsFor('meetingadvice')
        # we have only one workflow for 'meetingadvice'
        self.assertTrue(len(adviceWF) == 1)
        adviceWF = adviceWF[0]
        everyStates = adviceWF.states.keys()
        statesOfConfig = ADVICE_STATES_ALIVE + ADVICE_STATES_ENDED
        # statesOfConfig are all in everyStates
        self.assertFalse(set(everyStates).difference(set(statesOfConfig)))

    def test_pm_AdvicesConfidentiality(self):
        '''Test the getAdvicesByType method when advice confidentiality is enabled.
           A confidential advice is not visible by power observers or restricted power observers.'''
        cfg = self.meetingConfig
        # hide confidential advices to power observers
        cfg.setEnableAdviceConfidentiality(True)
        cfg.setAdviceConfidentialityDefault(True)
        cfg.setAdviceConfidentialFor(('power_observers', ))
        # make power observers able to see proposed items
        cfg.setItemPowerObserversStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        # first check default confidentiality value
        # create an item and ask advice of 'developers'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('developers', ))
        item.at_post_edit_script()
        # must be MeetingManager to be able to change advice confidentiality
        self.assertFalse(item.adapted().mayEditAdviceConfidentiality('developers'))
        # if creator tries to change advice confidentiality, he gets Unauthorized
        toggleView = item.restrictedTraverse('@@toggle_advice_is_confidential')
        self.assertRaises(Unauthorized, toggleView.toggle, UID='%s__%s' % (item.UID(), 'developers'))
        self.assertTrue(item.adviceIndex['developers']['isConfidential'])
        cfg.setAdviceConfidentialityDefault(False)
        # ask 'vendors' advice
        item.setOptionalAdvisers(('developers', 'vendors', ))
        item.at_post_edit_script()
        # still confidential for 'developers'
        self.assertTrue(item.adviceIndex['developers']['isConfidential'])
        # but not by default for 'vendors'
        self.assertFalse(item.adviceIndex['vendors']['isConfidential'])
        # so we have one confidential advice and one that is not confidential
        # but MeetingManagers may see both
        self.assertTrue(len(item.getAdvicesByType()[NOT_GIVEN_ADVICE_VALUE]) == 2)
        # propose the item so power observers can see it
        self.proposeItem(item)

        # log as power observer and check what he may access
        self.changeUser('powerobserver1')
        # only the not confidential advice is visible
        advicesByType = item.getAdvicesByType()
        self.assertTrue(len(advicesByType[NOT_GIVEN_ADVICE_VALUE]) == 1)
        self.assertTrue(advicesByType[NOT_GIVEN_ADVICE_VALUE][0]['id'] == 'vendors')

        # now give the advice so we check that trying to access a confidential
        # advice will raise Unauthorized
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(item,
                                                     'meetingadvice',
                                                     **{'advice_group': 'developers',
                                                        'advice_type': u'positive',
                                                        'advice_comment': RichTextValue(u'My comment')})
        # if powerobserver tries to access the Title of the confidential advice
        # displayed in particular on the advice view, it raises Unauthorized
        self.changeUser('powerobserver1')
        self.assertRaises(Unauthorized, developers_advice.Title)
        advice_view = developers_advice.restrictedTraverse('@@view')
        self.assertRaises(Unauthorized, advice_view)

        # a MeetingManager may toggle advice confidentiality
        # a MeetingManager would be able to change advice confidentiality
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().mayEditAdviceConfidentiality('developers'))
        self.assertTrue(item.adviceIndex['developers']['isConfidential'])
        toggleView.toggle(UID='%s__%s' % (item.UID(), 'developers'))
        self.assertFalse(item.adviceIndex['developers']['isConfidential'])

    def test_pm_MayTriggerGiveAdviceWhenItemIsBackToANotViewableState(self, ):
        '''Test that if an item is set back to a state the user that set it back can
           not view anymore, and that the advice turn from giveable to not giveable anymore,
           transitions triggered on advice that will 'giveAdvice'.'''
        cfg = self.meetingConfig
        # advice can be given when item is validated
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['validated'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['validated'], ))
        cfg.setItemAdviceViewStates((self.WF_STATE_NAME_MAPPINGS['validated'], ))
        # create an item as vendors and give an advice as vendors on it
        # it is viewable by MeetingManager when validated
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        # validate the item and advice it
        self.validateItem(item)
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # make sure if a MeetingManager send the item back to 'proposed' it works...
        self.changeUser('pmManager')
        # do the back transition that send the item back to 'proposed'
        itemWF = self.wfTool.getWorkflowsFor(item)[0]
        backToProposedTr = None
        for tr in self.transitions(item):
            # get the transition that ends to 'proposed'
            transition = itemWF.transitions[tr]
            if transition.new_state_id == self.WF_STATE_NAME_MAPPINGS['proposed']:
                backToProposedTr = tr
                break
        # this will work...
        self.do(item, backToProposedTr)

    def test_pm_ChangeAdviceHiddenDuringRedactionView(self):
        """Test the view that will toggle the advice_hide_during_redaction attribute on an item."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(['itemcreated', ])
        cfg.setItemAdviceEditStates(['itemcreated', ])
        cfg.setItemAdviceViewStates(['itemcreated', ])
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors',)
        }
        item = self.create('MeetingItem', **data)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'positive',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})
        # 'pmReviewer2', as adviser, is able to toggle advice_hide_during_redaction
        self.assertTrue(advice.advice_hide_during_redaction is False)
        self.assertTrue(item.adviceIndex['vendors']['hidden_during_redaction'] is False)
        changeView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeView()
        self.assertTrue(advice.advice_hide_during_redaction is True)
        self.assertTrue(item.adviceIndex['vendors']['hidden_during_redaction'] is True)
        changeView()
        self.assertTrue(advice.advice_hide_during_redaction is False)
        self.assertTrue(item.adviceIndex['vendors']['hidden_during_redaction'] is False)
        # user must be able to edit the advice, here, it is not the case for 'pmCreator1'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, changeView)
        self.assertTrue(advice.advice_hide_during_redaction is False)
        self.assertTrue(item.adviceIndex['vendors']['hidden_during_redaction'] is False)

    def test_pm_ChangeAdviceAskedAgainView(self):
        """Test the view that will change from advice asked_again/back to previous advice."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceEditStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceViewStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        # set that default value of field 'advice_hide_during_redaction' will be True
        cfg.setDefaultAdviceHiddenDuringRedaction(True)
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors', 'developers', )
        }
        item = self.create('MeetingItem', **data)
        self.proposeItem(item)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'negative',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})
        changeView = advice.restrictedTraverse('@@change-advice-asked-again')
        # 'asked_again' must be in usedAdviceTypes so the functionnality is activated
        self.assertTrue(not 'asked_again' in cfg.getUsedAdviceTypes())
        self.changeUser('pmManager')
        self.assertFalse(item.adapted().mayAskAdviceAgain(advice))
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        self.assertTrue(item.adapted().mayAskAdviceAgain(advice))

        # advice can not be asked_again if current user may not edit the item
        self.changeUser('pmCreator1')
        self.assertFalse(item.adapted().mayAskAdviceAgain(advice))
        self.assertFalse(item.adapted().mayBackToPreviousAdvice(advice))
        self.assertRaises(Unauthorized, changeView)

        # send advice back to creator so advice may be asked_again
        self.changeUser('pmCreator1')
        # never historized
        pr = api.portal.get_tool('portal_repository')
        self.assertFalse(pr.getHistoryMetadata(advice))
        self.backToState(item, 'itemcreated')
        # advice was historized
        self.assertEquals(pr.getHistoryMetadata(advice)._available, [0])
        self.assertTrue(item.adapted().mayAskAdviceAgain(advice))
        self.assertFalse(item.adapted().mayBackToPreviousAdvice(advice))
        # for now 'advice_hide_during_redaction' is False
        self.assertFalse(advice.advice_hide_during_redaction)
        # 'asked_again' term is not in advice_type_vocabulary as it is not selectable manually
        factory = queryUtility(IVocabularyFactory, u'Products.PloneMeeting.content.advice.advice_type_vocabulary')
        vocab = factory(advice)
        self.assertFalse('asked_again' in vocab)
        # right, ask advice again
        changeView()
        # advice was not historized again because it was not modified
        self.assertEquals(pr.getHistoryMetadata(advice)._available, [0])
        self.assertTrue(advice.advice_type == 'asked_again')
        # now it is available in vocabulary
        vocab = factory(advice)
        self.assertTrue('asked_again' in vocab)
        pr = self.portal.portal_repository
        # version 0 was saved
        self.assertTrue(pr.getHistoryMetadata(advice)._available == [0])
        # we may also revert to previous version
        self.assertFalse(item.adapted().mayAskAdviceAgain(advice))
        self.assertTrue(item.adapted().mayBackToPreviousAdvice(advice))
        # when an advice is 'asked_again', the field hidden_during_redaction
        # is set to the default defined in the MeetingConfig
        self.assertTrue(cfg.getDefaultAdviceHiddenDuringRedaction())
        self.assertTrue(advice.advice_hide_during_redaction)
        changeView()
        # when going back to previous version, a new version is done
        self.assertEquals(pr.getHistoryMetadata(advice)._available, [0, 1])
        self.assertTrue(advice.advice_type == 'negative')
        # advice was automatically shown
        self.assertFalse(advice.advice_hide_during_redaction)
        # ok, ask_again and send it again to 'pmReviewer2', he will be able to edit it
        # but before, edit the advice so it is historized again
        notify(ObjectModifiedEvent(advice))
        changeView()
        # this time a new version has been saved
        self.assertEquals(pr.getHistoryMetadata(advice)._available, [0, 1, 2])
        self.assertTrue(advice.advice_type == 'asked_again')
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, advice))

        # when an advice is 'asked_again', it is not versioned twice even
        # if advice was edited in between, an advice 'asked_again' is like 'never given'
        # this will avoid that previous advice of an advice 'asked_again' is also
        # an advice 'asked_again'...
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.backToState(item, 'itemcreated')
        self.assertEquals(pr.getHistoryMetadata(advice)._available, [0, 1, 2])
        # but works after when advice is no more 'asked_again'
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        advice.advice_type = 'positive'
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.backToState(item, 'itemcreated')
        self.assertEquals(pr.getHistoryMetadata(advice)._available, [0, 1, 2, 3])

    def test_pm_AdviceHistorizedWithItemDataWhenAdviceGiven(self):
        """When an advice is given, it is versioned and relevant item infos are saved.
           Moreover, advice is only versioned if it was modified."""
        cfg = self.meetingConfig
        # item data are saved if cfg.historizeItemDataWhenAdviceIsGiven
        self.assertTrue(cfg.getHistorizeItemDataWhenAdviceIsGiven())
        # make sure we know what item rich text fields are enabled
        cfg.setUsedItemAttributes(('detailedDescription', 'motivation', ))
        cfg.setItemAdviceStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceEditStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceViewStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        # set that default value of field 'advice_hide_during_redaction' will be True
        cfg.setDefaultAdviceHiddenDuringRedaction(True)
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors', 'developers', ),
            'description': '<p>Item description</p>',
        }
        item = self.create('MeetingItem', **data)
        item.setDetailedDescription('<p>Item detailed description</p>')
        item.setMotivation('<p>Item motivation</p>')
        item.setDecision('<p>Item decision</p>')
        self.proposeItem(item)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'negative',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})
        # advice is versioned when it is given, aka transition giveAdvice has been triggered
        pr = api.portal.get_tool('portal_repository')
        self.assertFalse(pr.getHistoryMetadata(advice))
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertTrue(h_metadata)
        # first version, item data was historized on it
        self.assertEquals(h_metadata._available, [0])
        previous = pr.retrieve(advice, 0).object
        self.assertEquals(previous.historized_item_data,
                          [{'field_name': 'title', 'field_content': 'Item to advice'},
                           {'field_name': 'description', 'field_content': '<p>Item description</p>'},
                           {'field_name': 'detailedDescription', 'field_content': '<p>Item detailed description</p>'},
                           {'field_name': 'motivation', 'field_content': '<p>Item motivation</p>'},
                           {'field_name': 'decision', 'field_content': '<p>Item decision</p>'}])
        # when giving advice for a second time, if advice is not edited, it is not versioned uselessly
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertEquals(advice.queryState(), 'advice_under_edit')
        self.validateItem(item)
        self.assertEquals(advice.queryState(), 'advice_given')
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0])

        # come back to 'proposed' and edit advice
        item.setDecision('<p>Another decision</p>')
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        notify(ObjectModifiedEvent(advice))
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1])
        previous = pr.retrieve(advice, 1).object
        self.assertEquals(previous.historized_item_data,
                          [{'field_name': 'title', 'field_content': 'Item to advice'},
                           {'field_name': 'description', 'field_content': '<p>Item description</p>'},
                           {'field_name': 'detailedDescription', 'field_content': '<p>Item detailed description</p>'},
                           {'field_name': 'motivation', 'field_content': '<p>Item motivation</p>'},
                           {'field_name': 'decision', 'field_content': '<p>Another decision</p>'}])

    def test_pm_AdviceHistorizedIfGivenAndItemChanged(self):
        """When an advice is given, if it was not historized and an item richText field
           is changed, it is versioned and relevant item infos are saved.  This way we are sure that
           historized infos about item are the one when the advice was given.
           Moreover, advice is only versioned if it was modified since last version."""
        cfg = self.meetingConfig
        # item data are saved if cfg.historizeItemDataWhenAdviceIsGiven
        self.assertTrue(cfg.getHistorizeItemDataWhenAdviceIsGiven())
        # make sure we know what item rich text fields are enabled
        cfg.setUsedItemAttributes(('detailedDescription', 'motivation', ))
        cfg.setItemAdviceStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceEditStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceViewStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        # default value of field 'advice_hide_during_redaction' is False
        self.assertFalse(cfg.getDefaultAdviceHiddenDuringRedaction())

        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': ('vendors', 'developers', ),
            'description': '<p>Item description</p>',
        }
        item = self.create('MeetingItem', **data)
        item.setDetailedDescription('<p>Item detailed description</p>')
        item.setMotivation('<p>Item motivation</p>')
        item.setDecision('<p>Item decision</p>')
        self.proposeItem(item)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'negative',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})
        # advice will be versioned if the item is edited
        # this is only the case if cfg.versionateAdviceIfGivenAndItemModified is True
        self.changeUser('siteadmin')
        cfg.setVersionateAdviceIfGivenAndItemModified(False)
        self.changeUser('pmReviewer1')
        pr = api.portal.get_tool('portal_repository')
        self.assertFalse(pr.getHistoryMetadata(advice))
        self.request.form['detailedDescription'] = '<p>Item detailed description not active</p>'
        item.processForm()
        self.assertEquals(item.getDetailedDescription(),
                          '<p>Item detailed description not active</p>')
        # it was not versioned because versionateAdviceIfGivenAndItemModified is False
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata, [])
        # activate and try again
        self.changeUser('siteadmin')
        cfg.setVersionateAdviceIfGivenAndItemModified(True)
        self.changeUser('pmReviewer1')
        item.processForm()
        # first version, item data was historized on it
        previous = pr.retrieve(advice, 0).object
        # we have item data before it was modified
        self.assertEquals(previous.historized_item_data,
                          [{'field_name': 'title',
                            'field_content': 'Item to advice'},
                           {'field_name': 'description',
                            'field_content': '<p>Item description</p>'},
                           {'field_name': 'detailedDescription',
                            'field_content': '<p>Item detailed description not active</p>'},
                           {'field_name': 'motivation',
                            'field_content': '<p>Item motivation</p>'},
                           {'field_name': 'decision',
                            'field_content': '<p>Item decision</p>'}])

        # when editing item a second time, if advice is not edited, it is not versioned uselessly
        self.request.form['detailedDescription'] = '<p>Item detailed description edited 2</p>'
        item.processForm({'detailedDescription': '<p>Item detailed description edited 2</p>'})
        self.assertEquals(item.getDetailedDescription(), '<p>Item detailed description edited 2</p>')
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0])

        # when moving to 'validated', advice is 'adviceGiven', but not versioned again
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0])

        # but it is again if advice is edited
        self.changeUser('pmManager')
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        # validate item, this time advice is versioned again
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1])

        # and once again back to proposed and edit item
        # not versioned because advice was not edited
        self.changeUser('pmManager')
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer1')
        self.request.form['detailedDescription'] = '<p>Item detailed description edited 3</p>'
        item.processForm({'detailedDescription': '<p>Item detailed description edited 3</p>'})
        self.assertEquals(item.getDetailedDescription(), '<p>Item detailed description edited 3</p>')
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1])

        # right, back to proposed and use ajax edit
        self.changeUser('pmManager')
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        item.setFieldFromAjax('detailedDescription', '<p>Item detailed description edited 4</p>')
        self.assertEquals(item.getDetailedDescription(), '<p>Item detailed description edited 4</p>')
        # advice was versioned again
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1, 2])
        # we have item data before it was modified
        previous = pr.retrieve(advice, 2).object
        self.assertEquals(previous.historized_item_data,
                          [{'field_name': 'title',
                            'field_content': 'Item to advice'},
                           {'field_name': 'description',
                            'field_content': '<p>Item description</p>'},
                           {'field_name': 'detailedDescription',
                            'field_content': '<p>Item detailed description edited 3</p>'},
                           {'field_name': 'motivation',
                            'field_content': '<p>Item motivation</p>'},
                           {'field_name': 'decision',
                            'field_content': '<p>Item decision</p>'}])

        # advice is also versionated if some annex are added/removed
        annex = self.addAnnex(item)
        # was already versionated so no more
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1, 2])
        # right edit the advice and remove the annex
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        item.restrictedTraverse('@@delete_givenuid')(annex.UID())
        # advice was versioned again
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1, 2, 3])
        # edit advice and add a new annex, advice will be versionated
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        annex = self.addAnnex(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1, 2, 3, 4])

    def _setupKeepAccessToItemWhenAdviceIsGiven(self):
        """Setup for testing aroung 'keepAccessToItemWhenAdviceIsGiven'."""
        # classic scenario is an item visible by advisers when it is 'proposed'
        # and no more when it goes back to 'itemcreated'
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceEditStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setItemAdviceViewStates([self.WF_STATE_NAME_MAPPINGS['proposed'], ])
        cfg.setKeepAccessToItemWhenAdviceIsGiven(False)

        # create an item, set it to 'proposed', give advice and set it back to 'itemcreated'
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to advice',
            'optionalAdvisers': ('vendors', 'developers'),
            'description': '<p>Item description</p>',
        }
        item = self.create('MeetingItem', **data)
        self.proposeItem(item)
        # give advice
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': 'vendors',
                                                     'advice_type': u'positive',
                                                     'advice_hide_during_redaction': False,
                                                     'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(item,
                                                     'meetingadvice',
                                                     **{'advice_group': 'developers',
                                                        'advice_type': u'positive',
                                                        'advice_hide_during_redaction': False,
                                                        'advice_comment': RichTextValue(u'My comment')})
        return item, vendors_advice, developers_advice

    def test_pm_KeepAccessToItemWhenAdviceIsGiven(self):
        """Test when MeetingConfig.keepAccessToItemWhenAdviceIsGiven is True,
           access to the item is kept if advice was given no matter the item is
           in a state where it should not be anymore."""

        cfg = self.meetingConfig
        item, vendors_advice, developers_advice = self._setupKeepAccessToItemWhenAdviceIsGiven()

        # set item back to 'itemcreated', it will not be visible anymore by advisers
        self.changeUser('pmReviewer2')
        self.assertFalse(cfg.getKeepAccessToItemWhenAdviceIsGiven())
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertFalse(self.hasPermission(View, item))

        # activate keepAccessToItemWhenAdviceIsGiven, then item is visible again
        cfg.setKeepAccessToItemWhenAdviceIsGiven(True)
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # access is only kept if advice was given
        self.deleteAsManager(vendors_advice.UID())
        self.assertFalse(self.hasPermission(View, item))

    def test_pm_MeetingGroupDefinedKeepAccessToItemWhenAdviceIsGivenOverridesMeetingConfigValues(self):
        '''MeetingGroup.keepAccessToItemWhenAdviceIsGiven will use or override the MeetingConfig value.'''
        cfg = self.meetingConfig
        item, vendors_advice, developers_advice = self._setupKeepAccessToItemWhenAdviceIsGiven()
        vendors = self.tool.vendors
        developers = self.tool.developers

        # by default, the MeetingConfig value is used
        self.changeUser('pmReviewer2')
        self.assertEquals(vendors.getKeepAccessToItemWhenAdviceIsGiven(), '')
        self.assertFalse(cfg.getKeepAccessToItemWhenAdviceIsGiven())
        self.backToState(item, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertFalse(self.hasPermission(View, item))

        # override MeetingConfig value
        vendors.setKeepAccessToItemWhenAdviceIsGiven('1')
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # this does not interact with other given advices
        self.changeUser('pmAdviser1')
        self.assertEquals(developers.getKeepAccessToItemWhenAdviceIsGiven(), '')
        self.assertFalse(self.hasPermission(View, item))

        # override the other way round
        self.changeUser('pmReviewer2')
        vendors.setKeepAccessToItemWhenAdviceIsGiven('')
        cfg.setKeepAccessToItemWhenAdviceIsGiven(True)
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # use MeetingConfig value that is True
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))

        # force disable keep access
        self.changeUser('pmReviewer2')
        vendors.setKeepAccessToItemWhenAdviceIsGiven('0')
        item.updateLocalRoles()
        self.assertFalse(self.hasPermission(View, item))

        # this does not interact with other given advices, still using MeetingConfig value
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))

    def test_pm_AdviceAddImagePermission(self):
        """A user able to edit the advice is able to add images."""
        cfg = self.meetingConfig
        cfg.setCustomAdvisers([])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')

        # just check that an adviser may add images to an editable advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()

        # give advice
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': 'vendors',
                                                     'advice_type': u'positive',
                                                     'advice_hide_during_redaction': False,
                                                     'advice_comment': RichTextValue(u'My comment')})
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', vendors_advice))
        self.assertTrue(self.hasPermission(AddPortalContent, vendors_advice))
        vendors_advice.invokeFactory('Image', id='img1', title='Image1', file=data.read())

        # make advice no more editable and test image addition
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        # pmReviewer2 still have AddPortalContent because he is Owner but he may not add anything
        self.assertTrue(self.hasPermission(AddPortalContent, vendors_advice))
        self.assertFalse(self.hasPermission('ATContentTypes: Add Image', vendors_advice))
        self.assertRaises(Unauthorized, item.invokeFactory, 'Image', id='img', title='Image1', file=data.read())
        # back to 'itemcreated', add image permission is set back correctly
        self.changeUser('pmCreator1')
        self.backToState(item, 'itemcreated')
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(AddPortalContent, vendors_advice))
        self.assertTrue(self.hasPermission('ATContentTypes: Add Image', vendors_advice))

    def test_pm_AdviceExternalImagesStoredLocally(self):
        """External images are stored locally."""
        cfg = self.meetingConfig
        cfg.setCustomAdvisers([])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()

        # give advice
        self.changeUser('pmReviewer2')
        # creation time
        text = u'<p>Working external image <img src="http://www.imio.be/contact.png"/>.</p>'
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'vendors',
                                             'advice_type': u'positive',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(text)})
        self.assertTrue('contact.png' in advice.objectIds())

        # test using IObjectModifiedEvent event, aka using edit form
        text = '<p>Working external image <img src="http://www.imio.be/spw.png"/>.</p>'
        advice.advice_comment = RichTextValue(text)
        # notify modified
        notify(ObjectModifiedEvent(advice))
        self.assertTrue('spw.png' in advice.objectIds())

    def test_pm_ManualVersioningEnabledForMeetingAdvicePortalTypes(self):
        """ """
        portal_types = self.portal.portal_types
        portal_repository = self.portal.portal_repository
        for portal_type_id in portal_types:
            if portal_type_id.startswith('meetingadvice'):
                self.assertEquals(portal_repository._version_policy_mapping[portal_type_id],
                                  [u'version_on_revert'])

    def test_pm_GetAdviceObj(self):
        """Test the MeetingItem.getAdviceObj that return the real advice
           object if available, otherwise it returns None."""
        cfg = self.meetingConfig
        cfg.setCustomAdvisers([])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', 'developers', ))
        item.at_post_edit_script()

        # give 'vendors' advice and test
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': 'vendors',
                                                     'advice_type': u'positive',
                                                     'advice_hide_during_redaction': False,
                                                     'advice_comment': RichTextValue(u'My comment')})
        self.assertEqual(item.getAdviceObj('vendors'), vendors_advice)
        self.assertIsNone(item.getAdviceObj('developers'))

    def _setupInheritedAdvice(self):
        """ """
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))

        # create 2 items and inheritate from an advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('vendors', 'developers__rowid__unique_id_123'))
        item1.updateLocalRoles()
        self.changeUser('pmAdviser1')
        vendors_advice = createContentInContainer(item1,
                                                  'meetingadvice',
                                                  **{'advice_group': 'developers',
                                                     'advice_type': u'positive',
                                                     'advice_hide_during_redaction': False,
                                                     'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmReviewer2')
        developers_advices = createContentInContainer(item1,
                                                      'meetingadvice',
                                                      **{'advice_group': 'vendors',
                                                         'advice_type': u'positive',
                                                         'advice_hide_during_redaction': False,
                                                         'advice_comment': RichTextValue(u'My comment')})
        # link items and inherit
        self.changeUser('pmCreator1')
        item2 = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        return item1, item2, vendors_advice, developers_advices

    def test_pm_InheritedAdviceAccesses(self):
        """While an advice is marked as 'inherited', it will show another advice
           coming from another item, in this case, read access to current item are same as
           usual but advisers of the inherited advice will never be able to add/edit it."""
        item1, item2, vendors_advices, developers_advice = self._setupInheritedAdvice()
        self.assertTrue(item2.adviceIndex['vendors']['inherited'])
        self.assertTrue(item2.adviceIndex['developers']['inherited'])
        # advisers of vendors are able to see item2 but not able to add advice
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))

        # not addable
        self.assertFalse(item2.adviceIndex['vendors']['advice_addable'])
        self.assertFalse(item2.adviceIndex['developers']['advice_addable'])

        # delay for delay aware advices are not started
        # delay aware
        self.assertTrue(item2.adviceIndex['developers']['delay'])
        # not started
        self.assertIsNone(item2.adviceIndex['developers']['delay_started_on'])

    def test_pm_GetAdviceDataFor(self):
        '''Test the getAdviceDataFor method, essentially the fact that it needs the item
           we are calling the method on as first parameter, this will avoid this method
           being callable TTW.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        # raises Unauthorized if item is not passed as first parameter
        self.assertRaises(Unauthorized, item.getAdviceDataFor, '')
        self.assertRaises(Unauthorized, item.getAdviceDataFor, item2)
        # but works if right parameters are passed
        self.assertTrue(item.getAdviceDataFor(item) == {})

    def test_pm_GetAdviceDataForInheritedAdvice(self):
        '''Test the getAdviceDataFor method when the advice is inherited.'''
        item1, item2, vendors_advices, developers_advice = self._setupInheritedAdvice()
        # item1 and item2 have same values except that inherited advice have a 'adviceHolder'
        item1VendorsData = item1.getAdviceDataFor(item1, 'vendors').copy()
        item1VendorsData['adviceHolder'] = item1
        item1DevData = item1.getAdviceDataFor(item1, 'developers').copy()
        item1DevData['adviceHolder'] = item1
        item2VendorsData = item2.getAdviceDataFor(item2, 'vendors').copy()
        item2DevData = item2.getAdviceDataFor(item2, 'developers').copy()
        self.assertEqual(item1VendorsData, item2VendorsData)
        self.assertEqual(item1DevData, item2DevData)
        # adviceIndex is not impacted
        self.assertFalse('adviceHolder' in item1.adviceIndex)
        self.assertFalse('adviceHolder' in item2.adviceIndex)

    def test_pm_GetInheritedAdviceInfo(self):
        '''MeetingItem.getInheritedAdviceInfo will return advice info of original
           advice when inherit from.  Advice inheritance may be multiple as long as
           original advice exist, so we may have several chained predecessors.'''
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/10',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))

        self.changeUser('pmCreator1')
        # item without predecessor
        item1WithoutAdvice = self.create('MeetingItem')
        item1WithoutAdvice.setOptionalAdvisers(('vendors', 'developers__rowid__unique_id_123'))
        item1WithoutAdvice.at_post_edit_script()
        self.assertIsNone(item1WithoutAdvice.getInheritedAdviceInfo('vendors'))
        self.assertIsNone(item1WithoutAdvice.getInheritedAdviceInfo('developers'))

        # predecessor does not have given advices
        item2WithAdvices = item1WithoutAdvice.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.changeUser('pmReviewer2')
        createContentInContainer(item2WithAdvices,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.assertIsNone(item2WithAdvices.getInheritedAdviceInfo('vendors'))
        self.assertIsNone(item2WithAdvices.getInheritedAdviceInfo('developers'))

        # direct predecessor holds advices
        self.changeUser('pmCreator1')
        item3DirectPredecessor = item2WithAdvices.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        # we get adviceInfos + 'adviceHolder'
        inheritedItem3AdviceInfos = item3DirectPredecessor.getInheritedAdviceInfo('vendors')
        self.assertEqual(inheritedItem3AdviceInfos['adviceHolder'], item2WithAdvices)
        inheritedItem3AdviceInfos.pop('adviceHolder')
        self.assertEqual(inheritedItem3AdviceInfos, item2WithAdvices.adviceIndex['vendors'])
        # nothing for 'developers'
        self.assertIsNone(item3DirectPredecessor.getInheritedAdviceInfo('developers'))

        # now tries with a chain of predecessors, new item predecessor holding advice
        # is not the direct predecessor, we have one item in between
        item4ChainedPredecessor = item3DirectPredecessor.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        inheritedItem4AdviceInfos = item4ChainedPredecessor.getInheritedAdviceInfo('vendors')
        self.assertEqual(inheritedItem4AdviceInfos['adviceHolder'], item2WithAdvices)
        inheritedItem4AdviceInfos.pop('adviceHolder')
        self.assertEqual(inheritedItem4AdviceInfos, item2WithAdvices.adviceIndex['vendors'])
        # nothing for 'developers'
        self.assertIsNone(item4ChainedPredecessor.getInheritedAdviceInfo('developers'))

    def test_pm_InheritedAdviceStoppedWhenInheritedAdviceRemoved(self):
        '''When advices are inherited, it is only valid as long as the original
           advice is still given, if removed, every inherited advice of the chain
           of predecessors are automatically set back to not inherited.'''
        item1, item2, vendors_advices, developers_advice = self._setupInheritedAdvice()
        # add more items so we use multiple chains where predecessors may go
        # into varipus ways, for now we have :
        # item1 --- item1b --- item1b2
        #     --- item1c
        #     --- item2 --- item3
        # item1b, item1c and item2 have item1 as predecessor
        item1b = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item1b2 = item1b.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item1c = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item1b.getPredecessor(), item1)
        self.assertEqual(item1b.getInheritedAdviceInfo('vendors')['adviceHolder'], item1)
        item3 = item2.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item3.getInheritedAdviceInfo('vendors')['adviceHolder'], item1)

        # remove item2, chain of predecessors is broken to item3,
        # it will not inherit of advice anymore
        self.portal.restrictedTraverse('@@delete_givenuid')(item2.UID())
        self.assertFalse(item3.adviceIndex['vendors']['inherited'])
        self.assertFalse(item3.adviceIndex['developers']['inherited'])
        # recomputed, advice is addable, ...
        self.assertTrue(item3.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(item3.adviceIndex['developers']['advice_addable'])
        # but still ok for item1b, item1b2 and item1c
        self.assertTrue(item1b.adviceIndex['vendors']['inherited'])
        self.assertTrue(item1b.adviceIndex['developers']['inherited'])
        self.assertTrue(item1b2.adviceIndex['vendors']['inherited'])
        self.assertTrue(item1b2.adviceIndex['developers']['inherited'])
        self.assertTrue(item1c.adviceIndex['vendors']['inherited'])
        self.assertTrue(item1c.adviceIndex['developers']['inherited'])

        # remove 'vendors' advice of item1, this time item1b, item1b2 and item1c are updated
        # it will no longer inherits from item1
        self.changeUser('pmReviewer2')
        self.portal.restrictedTraverse('@@delete_givenuid')(item1.getAdviceObj('vendors').UID())
        self.assertFalse(item1b.adviceIndex['vendors']['inherited'])
        self.assertFalse(item1b2.adviceIndex['vendors']['inherited'])
        self.assertFalse(item1c.adviceIndex['vendors']['inherited'])
        # still ok for 'developers' advice
        self.assertTrue(item1b.adviceIndex['developers']['inherited'])
        self.assertTrue(item1b2.adviceIndex['developers']['inherited'])
        self.assertTrue(item1c.adviceIndex['developers']['inherited'])
        # recomputed, advice is addable, ...
        self.assertTrue(item1b.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(item1b2.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(item1c.adviceIndex['vendors']['advice_addable'])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAdvices, prefix='test_pm_'))
    return suite
