# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.iconifiedcategory.utils import get_categorized_elements
from DateTime import DateTime
from datetime import datetime
from datetime import timedelta
from imio.helpers.cache import cleanRamCacheFor
from imio.history.utils import getLastWFAction
from os import path
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.config import AddAdvice
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import ADVICE_STATES_ENDED
from Products.PloneMeeting.config import CONSIDERED_NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.indexes import indexAdvisers
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import isModifiedSinceLastVersion
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import queryUtility
from zope.event import notify
from zope.i18n import translate
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.interfaces import RequiredMissing


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
        item1.setOptionalAdvisers((self.vendors_uid, ))
        item2 = self.create('MeetingItem', **data)
        item2.setOptionalAdvisers((self.developers_uid, ))
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
        self.assertEqual(item1.queryState(), self._stateMappingFor('presented'))
        self.assertEqual(item2.queryState(), self._stateMappingFor('presented'))
        self.assertEqual(item3.queryState(), self._stateMappingFor('presented'))
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

    def test_pm_ShowAdvices(self):
        """Shown if MeetingConfig.useAdvices or MeetingItem.adviceIndex."""
        cfg = self.meetingConfig

        self.changeUser('pmCreator1')
        cfg.setUseAdvices(False)
        item = self.create('MeetingItem')
        self.assertFalse(item.adapted().showAdvices())
        # if an advice is asked, it will be shown
        item.setOptionalAdvisers((self.vendors_uid,))
        item._update_after_edit()
        self.assertTrue(item.adapted().showAdvices())
        # shown if cfg.useAdvices
        item.setOptionalAdvisers(())
        item._update_after_edit()
        self.assertFalse(item.adapted().showAdvices())
        cfg.setUseAdvices(True)
        self.assertTrue(item.adapted().showAdvices())

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
        item1.setOptionalAdvisers((self.vendors_uid, ))
        item1._update_after_edit()
        # 'pmCreator1' has no addable nor editable advice to give
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('pmReviewer2')
        self.failIf(self.hasPermission(View, item1))
        self.changeUser('pmCreator1')
        self.proposeItem(item1)
        # a user able to View the item can not add an advice, even if he tries...
        self.assertRaises(Unauthorized,
                          createContentInContainer,
                          item1,
                          'meetingadvice')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('pmReviewer2')
        # 'pmReviewer2' has one advice to give for 'vendors' and no advice to edit
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([(self.vendors_uid, u'Vendors')], []))
        self.assertEqual(item1.hasAdvices(), False)
        # fields 'advice_type' and 'advice_group' are mandatory
        form = item1.restrictedTraverse('++add++meetingadvice').form_instance
        form.ti = self.portal.portal_types['meetingadvice']
        self.request['PUBLISHED'] = form
        form.update()
        errors = form.extractData()[1]
        self.assertEqual(errors[0].error, RequiredMissing('advice_group'))
        self.assertEqual(errors[1].error, RequiredMissing('advice_type'))
        # value used for 'advice_type' and 'advice_group' must be correct
        form.request.set('form.widgets.advice_type', u'wrong_value')
        errors = form.extractData()[1]
        self.assertEqual(errors[1].error, RequiredMissing('advice_type'))
        # but if the value is correct, the field renders correctly
        form.request.set('form.widgets.advice_type', u'positive')
        data = form.extractData()[0]
        self.assertEqual(data['advice_type'], u'positive')
        # regarding 'advice_group' value, only correct are the ones in the vocabulary
        # so using another will fail, for example, can not give an advice for another group
        form.request.set('form.widgets.advice_group', self.developers_uid)
        data = form.extractData()[0]
        self.assertFalse('advice_group' in data)
        # we can use the values from the vocabulary
        vocab = form.widgets.get('advice_group').terms.terms
        self.failUnless(self.vendors_uid in vocab)
        self.assertEqual(len(vocab), 1)
        # give the advice, select a valid 'advice_group' and save
        form.request.set('form.widgets.advice_group', self.vendors_uid)
        # the 3 fields 'advice_group', 'advice_type' and 'advice_comment' are handled correctly
        data = form.extractData()[0]
        self.assertTrue('advice_group' in data and
                        'advice_type' in data and
                        'advice_comment' in data and
                        'advice_row_id' in data and
                        'advice_observations' in data and
                        'advice_hide_during_redaction' in data)
        # we receive the 6 fields
        self.assertEqual(len(data), len(form.fields))
        form.request.form['advice_group'] = self.vendors_uid
        form.request.form['advice_type'] = u'positive'
        form.request.form['advice_comment'] = RichTextValue(u'My comment')
        form.createAndAdd(form.request.form)
        self.assertEqual(item1.hasAdvices(), True)
        # 'pmReviewer2' has no more addable advice (as already given) but has now an editable advice
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], [(self.vendors_uid, 'Vendors')]))
        # given advice is correctly stored
        self.assertEqual(item1.adviceIndex[self.vendors_uid]['type'], 'positive')
        self.assertEqual(item1.adviceIndex[self.vendors_uid]['comment'], u'My comment')
        self.changeUser('pmReviewer1')
        # may edit the item but not the advice
        self.assertTrue(self.hasPermission(ModifyPortalContent, item1))
        self.assertTrue(self.hasPermission(View, item1))
        given_advice = getattr(item1, item1.adviceIndex[self.vendors_uid]['advice_id'])
        self.assertFalse(self.hasPermission(ModifyPortalContent, given_advice))
        self.assertTrue(self.hasPermission(View, given_advice))
        self.validateItem(item1)
        # now 'pmReviewer2' can't add (already given) an advice
        # but he can still edit the advice he just gave
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], [(self.vendors_uid, 'Vendors')]))
        self.failUnless(self.hasPermission(ModifyPortalContent, given_advice))
        # another member of the same _advisers group may also edit the given advice
        self.changeUser('pmManager')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], [(self.vendors_uid, 'Vendors')]))
        self.failUnless(self.hasPermission(ModifyPortalContent, given_advice))
        # if a user that can not remove the advice tries he gets Unauthorized
        self.changeUser('pmReviewer1')
        self.failIf(self.hasPermission(ModifyPortalContent, given_advice))
        self.assertRaises(Unauthorized, item1.restrictedTraverse('@@delete_givenuid'), item1.meetingadvice.UID())
        # put the item back in a state where 'pmReviewer2' can remove the advice
        self.changeUser('pmManager')
        self.backToState(item1, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        # remove the advice
        item1.restrictedTraverse('@@delete_givenuid')(item1.meetingadvice.UID())
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([(self.vendors_uid, u'Vendors')], []))

        # if advices are disabled in the meetingConfig, getAdvicesGroupsInfosForUser is emtpy
        self.changeUser('admin')
        self.meetingConfig.setUseAdvices(False)
        self.changeUser('pmReviewer2')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('admin')
        self.meetingConfig.setUseAdvices(True)

        # activate advices again and this time remove the fact that we asked the advice
        self.changeUser('pmReviewer2')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([(self.vendors_uid, u'Vendors')], []))
        self.changeUser('pmManager')
        item1.setOptionalAdvisers([])
        item1._update_after_edit()
        self.changeUser('pmReviewer2')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], []))

    def test_pm_AddAnnexToAdvice(self):
        '''
          Test that we can add annexes to an advice.
        '''
        # advice are addable/editable when item is 'proposed'
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('proposed'),
                                     self._stateMappingFor('validated'), ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        # an advice can be given when an item is 'proposed'
        self.proposeItem(item)
        # add advice for 'vendors'
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
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
        item.setOptionalAdvisers((self.developers_uid, self.vendors_uid, ))
        item._update_after_edit()
        # an advice can be given when an item is 'proposed'
        self.proposeItem(item)
        # add advice for 'developers'
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(item,
                                                     'meetingadvice',
                                                     **{'advice_group': self.developers_uid,
                                                        'advice_type': u'positive',
                                                        'advice_comment': RichTextValue(u'My comment')})
        # can view/edit/delete is own advice
        self.assertTrue(self.hasPermission(View, developers_advice))
        self.assertTrue(self.hasPermission(ModifyPortalContent, developers_advice))
        self.assertTrue(self.hasPermission(DeleteObjects, developers_advice))
        self.changeUser('pmReviewer2')
        # can view
        self.assertTrue(self.hasPermission(View, developers_advice))
        # can not edit/delete
        self.assertFalse(self.hasPermission(ModifyPortalContent, developers_advice))
        self.assertFalse(self.hasPermission(DeleteObjects, developers_advice))
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': self.vendors_uid,
                                                     'advice_type': u'positive',
                                                     'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmAdviser1')
        # can view
        self.assertTrue(self.hasPermission(View, vendors_advice))
        # can not edit/delete
        self.assertFalse(self.hasPermission(ModifyPortalContent, vendors_advice))
        self.assertFalse(self.hasPermission(DeleteObjects, vendors_advice))

    def test_pm_CanNotGiveAdviceIfNotAsked(self):
        '''
          Test that an adviser that can access an item can not give his advice
          if it was not asked.
        '''
        # create an item and ask advice of 'vendors'
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers((self.vendors_uid,))
        item1._update_after_edit()
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
            'optionalAdvisers': (self.vendors_uid,)
        }
        item1 = self.create('MeetingItem', **data)
        # check than the adviser can see the item
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([(self.vendors_uid, u'Vendors')], []))
        self.failUnless(self.hasPermission(AddAdvice, item1))

    def test_pm_AdvicesInvalidation(self):
        '''Test the advice invalidation process.'''
        # advisers can give an advice when item is 'proposed' or 'validated'
        # activate advice invalidation in state 'validated'
        cfg = self.meetingConfig
        cfg.setEnableAdviceInvalidation(True)
        cfg.setItemAdviceInvalidateStates((self._stateMappingFor('validated'),))
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.vendors_uid,)
        }
        item = self.create('MeetingItem', **data)
        self.failIf(item.willInvalidateAdvices())
        self.proposeItem(item)
        # login as adviser and add an advice
        self.changeUser('pmReviewer2')
        self.assertEqual(item.getAdvicesGroupsInfosForUser(), ([(self.vendors_uid, u'Vendors')], []))
        # give an advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # login as an user that can actually edit the item because not 'validated'
        self.changeUser('pmReviewer1')
        self.failUnless(self.hasPermission(ModifyPortalContent, item))
        # modifying the item will not invalidate the advices because not 'validated'
        self.failIf(item.willInvalidateAdvices())
        item.setDecision(item.getDecision() + '<p>New line</p>')
        item._update_after_edit()
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
        self.deleteAsManager(annex1.UID())
        self.failIf(item.hasAdvices())
        self.failIf(item.getGivenAdvices())
        # given the advice again so we can check other case where advices are invalidated
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
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
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmManager')
        self.validateItem(item)
        self.failUnless(item.hasAdvices())
        self.failUnless(item.getGivenAdvices())
        # editing the item will invalidate advices
        self.failUnless(item.willInvalidateAdvices())
        item.setDecision(item.getDecision() + '<p>Still another new line</p>')
        item._update_after_edit()
        self.failIf(item.hasAdvices())
        self.failIf(item.getGivenAdvices())
        # given the advice again so we can check other case where advices are invalidated
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
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
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        # an advice can be given or edited when an item is 'proposed'
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((
            self.developers_uid,
            '{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item.updateLocalRoles()
        # no advice to give as item is 'itemcreated'
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay__{0}_advice_not_giveable'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 '{0}_advice_not_giveable'.format(self.developers_uid),
                 'not_given'])
        )
        self.proposeItem(item)
        item.reindexObject()
        self.changeUser('pmAdviser1')
        # now advice are giveable but not given
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given'.format(self.developers_uid),
                 'not_given']))
        itemUID = item.UID()
        brains = self.catalog(
            indexAdvisers='{0}_advice_not_given'.format(self.developers_uid))
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        brains = self.catalog(indexAdvisers='delay_row_id__unique_id_123')
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        # create the advice
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_comment': RichTextValue(u'My comment')})
        # now that an advice has been given for the developers group, the indexAdvisers has been updated
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__positive'.format(self.developers_uid),
                 '{0}_advice_under_edit'.format(self.developers_uid),
                 'not_given',
                 'positive'])
        )
        brains = self.catalog(indexAdvisers='{0}_advice_under_edit'.format(self.developers_uid))
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)

        # turn advice to hidden during redaction
        changeHiddenDuringRedactionView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeHiddenDuringRedactionView()
        self.assertTrue(advice.advice_hide_during_redaction)
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 '{0}_advice_hidden_during_redaction'.format(self.developers_uid),
                 '{0}_advice_under_edit'.format(self.developers_uid),
                 HIDDEN_DURING_REDACTION_ADVICE_VALUE,
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__hidden_during_redaction'.format(self.developers_uid)])
        )
        brains = self.catalog(
            indexAdvisers='real_org_uid__{0}__hidden_during_redaction'.format(self.developers_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        # makes this advice 'considered_not_given_hidden_during_redaction'
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                [CONSIDERED_NOT_GIVEN_ADVICE_VALUE,
                 'delay__{0}_advice_not_giveable'.format(self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 '{0}_advice_given'.format(self.developers_uid),
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__considered_not_given_hidden_during_redaction'.format(self.developers_uid)])
        )
        brains = self.catalog(
            indexAdvisers='real_org_uid__{0}__considered_not_given_hidden_during_redaction'.format(
                self.developers_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        # back to 'proposed' and not more hidden_during_redaction
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmAdviser1')
        changeHiddenDuringRedactionView()

        # now change the value of the created meetingadvice.advice_group
        advice.advice_group = self.vendors_uid
        # notify modified
        notify(ObjectModifiedEvent(advice))
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__positive',
                 'delay__{0}_advice_under_edit'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given'.format(self.developers_uid),
                 'not_given',
                 'positive'])
        )
        # the index in the portal_catalog is updated too
        brains = self.catalog(
            indexAdvisers='delay__{0}_advice_under_edit'.format(self.vendors_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)

        # put the item in a state where given advices are not editable anymore
        self.changeUser('pmReviewer1')
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__positive',
                 'delay__{0}_advice_given'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 '{0}_advice_not_giveable'.format(self.developers_uid),
                 'not_given',
                 'positive']))
        # ask a given advice again
        self.changeUser('pmCreator1')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['asked_again',
                 'delay__{0}_advice_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_giveable'.format(self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__asked_again',
                 '{0}_advice_not_giveable'.format(self.developers_uid),
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid)])
        )
        # put it back to a state where it is editable
        self.proposeItem(item)
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['asked_again',
                 'delay__{0}_advice_asked_again'.format(self.vendors_uid),
                 'delay__{0}_advice_under_edit'.format(self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__asked_again',
                 '{0}_advice_not_given'.format(self.developers_uid),
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid)])
        )

        # delete the advice as Manager as it was historized
        self.changeUser('siteadmin')
        item.restrictedTraverse('@@delete_givenuid')(advice.UID())
        self.changeUser('pmAdviser1')
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given'.format(self.developers_uid),
                 'not_given'])
        )
        # the index in the portal_catalog is updated too
        brains = self.catalog(
            indexAdvisers='delay__{0}_advice_not_given'.format(self.vendors_uid))
        self.assertEquals(len(brains), 1)
        self.assertEquals(brains[0].UID, itemUID)
        brains = self.catalog(
            indexAdvisers='{0}_advice_not_given'.format(self.developers_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        # if a delay-aware advice delay is exceeded, it is indexed with an ending '2'
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2012, 01, 01)
        item.updateLocalRoles()
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay__{0}_advice_delay_exceeded'.format(self.vendors_uid),
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given'.format(self.developers_uid),
                 'not_given'])
        )

    def test_pm_IndexAdvisersCombinedIndex(self):
        '''Test the indexAdvisers 'combined idnex' functionnality that makes it possible
           to query items having advice of a given group using a given advice_type.'''
        # an advice can be given when an item is 'proposed' or 'validated'
        self.assertEqual(self.meetingConfig.getItemAdviceStates(),
                         (self._stateMappingFor('proposed'), ))
        # create 3 items with various advices
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers((self.developers_uid, self.vendors_uid, ))
        item1.updateLocalRoles()
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers((self.developers_uid, ))
        item2.updateLocalRoles()
        item3 = self.create('MeetingItem')
        item3.setOptionalAdvisers(())
        item3.updateLocalRoles()

        # query not_given advices
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='not_given')]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.vendors_uid))]),
            set([item1.UID()]))

        # give positive developers advice on item1
        self.proposeItem(item1)
        item1.reindexObject()
        self.changeUser('pmAdviser1')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # query not given and positive advices
        self.changeUser('pmCreator1')
        # item1 still have vendors advice not given
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='not_given')]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['not_given', 'positive'])]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.developers_uid))]),
            set([item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__positive'.format(self.developers_uid))]),
            set([item1.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.vendors_uid))]),
            set([item1.UID()]))

        # give negative developers advice on item2
        self.changeUser('pmCreator1')
        self.proposeItem(item2)
        item2.reindexObject()
        self.changeUser('pmAdviser1')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'negative',
                                    'advice_comment': RichTextValue(u'My comment')})
        # query not given and positive advices
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['not_given'])]),
            set([item1.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['positive'])]),
            set([item1.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['negative'])]),
            set([item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__negative'.format(self.developers_uid))]),
            set([item2.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__positive'.format(self.developers_uid))]),
            set([item1.UID()]))
        self.assertEquals(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.vendors_uid))]),
            set([item1.UID()]))

    def test_pm_AutomaticAdvices(self):
        '''Test the automatic advices mechanism, some advices can be
           automatically asked under specific conditions.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid, ))
        item._update_after_edit()
        self.assertTrue(self.developers_uid in item.adviceIndex)
        self.assertFalse(self.vendors_uid in item.adviceIndex)
        # now make 'vendors' advice automatically asked
        # it will be asked if item.budgetRelated is True
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01', }, ])
        # if the item is not budgetRelated, nothing happens
        item._update_after_edit()
        self.assertFalse(self.vendors_uid in item.adviceIndex)
        # but if the condition is True, then the advice is automatically asked
        item.setBudgetRelated(True)
        item._update_after_edit()
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        # moreover, this automatic advice is not considered as optional
        self.assertFalse(item.adviceIndex[self.vendors_uid]['optional'])
        # the advice asked using optionalAdvisers is marked as optional
        self.assertTrue(item.adviceIndex[self.developers_uid]['optional'])
        # if an automatic advice is asked and it was also asked as optional
        # the advice is only asked once and considered as automatic, aka not optional
        # but before, 'developers' advice is still considered as optional
        self.assertTrue(self.developers_uid in item.getOptionalAdvisers())
        cfg.setCustomAdvisers([{'row_id': 'unique_id_123',
                                'org': self.vendors_uid,
                                'gives_auto_advice_on': 'item/getBudgetRelated',
                                'for_item_created_from': '2012/01/01', },
                               {'row_id': 'unique_id_456',
                                'org': self.developers_uid,
                                'gives_auto_advice_on': 'item/getBudgetRelated',
                                'for_item_created_from': '2012/01/01', }, ])
        item._update_after_edit()
        self.assertFalse(item.adviceIndex[self.vendors_uid]['optional'])
        # 'developers' asked advice is no more considered as optional even if in optionalAdvisers
        self.assertFalse(item.adviceIndex[self.developers_uid]['optional'])
        # 'developers' asked advice is still in item.optionalAdvisers
        self.assertTrue(self.developers_uid in item.getOptionalAdvisers())

        # now make sure an adviser of 'vendors' may add his advice and updateLocalRoles
        # in MeetingItem._updateAdvices, this is why we call getAutomaticAdvisersData
        # with api.env.adopt_roles(['Reader', ])
        self.proposeItem(item)
        item.updateLocalRoles()
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.changeUser('pmReviewer2')
        item.updateLocalRoles()
        # 'vendors' is still in adviceIndex, the TAL expr could be evaluated correctly
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.assertEqual(item.getAdvicesGroupsInfosForUser(),
                         ([(self.vendors_uid, 'Vendors')], []))
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})

    def test_pm_AdviceAskedAutomaticallyWithGroupsInCharge(self):
        '''Advice asked when organization in charge of proposingGroup,
           this also test the org/org_uid variables available in the TAL expression.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        self.developers.groups_in_charge = [self.vendors_uid]
        # when using org_uid
        cfg.setCustomAdvisers([
            {'row_id': 'unique_id_123',
             'org': self.vendors_uid,
             'gives_auto_advice_on':
                'python: item.getGroupsInCharge(theObjects=False, fromOrgIfEmpty=True, first=True) == org_uid',
             'for_item_created_from': '2012/01/01',
             'delay': '10'}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # advice was asked
        self.assertTrue(self.vendors_uid in item.adviceIndex)

        # when using org
        cfg.setCustomAdvisers([
            {'row_id': 'unique_id_123',
             'org': self.vendors_uid,
             'gives_auto_advice_on':
                'python: item.getGroupsInCharge(theObjects=True, fromOrgIfEmpty=True, first=True) == org',
             'for_item_created_from': '2012/01/01',
             'delay': '10'}, ])
        item2 = self.create('MeetingItem')
        # advice was asked
        self.assertTrue(self.vendors_uid in item2.adviceIndex)

    def test_pm_GivenDelayAwareAutomaticAdviceLeftEvenIfItemConditionChanged(self):
        '''This test that if an automatic advice is asked because a condition
           on the item is True, the automatic advice is given then the condition
           on the item changes, the advice is kept.'''
        self.meetingConfig.setCustomAdvisers([{'row_id': 'unique_id_123',
                                               'org': self.vendors_uid,
                                               'gives_auto_advice_on': 'item/getBudgetRelated',
                                               'for_item_created_from': '2012/01/01',
                                               'delay': '10'}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setBudgetRelated(True)
        item._update_after_edit()
        # the automatic advice is asked
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.assertTrue(not item.adviceIndex[self.vendors_uid]['optional'])
        self.assertEqual(item.getAutomaticAdvisersData()[0]['org_uid'], self.vendors_uid)
        # now give the advice
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        item.setBudgetRelated(False)
        item._update_after_edit()
        # the automatic advice is still there even if no more returned by getAutomaticAdvisersData
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.assertTrue(not item.adviceIndex[self.vendors_uid]['optional'])
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
              'org': self.vendors_uid,
              'gives_auto_advice_on': 'item/wrongMethod',
              'for_item_created_from': '2012/01/01',
              'delay': '',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'delay': '',
              'delay_label': ''},
             # an non automatic advice configuration
             {'row_id': 'unique_id_789',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'delay': '10',
              'delay_label': ''}])
        # one wrong condition (raising an error when evaluated) and one returning False
        self.failIf(item.getAutomaticAdvisersData())
        # now make the second row expression return True, set item.budgetRelated
        item.setBudgetRelated(True)
        self.assertEqual(
            sorted(item.getAutomaticAdvisersData()),
            sorted(
                [{'gives_auto_advice_on_help_message': '',
                  'org_uid': self.developers_uid,
                  'org_title': 'Developers',
                  'row_id': 'unique_id_456',
                  'delay': '',
                  'delay_left_alert': '',
                  'delay_label': ''}])
        )
        # define one condition for wich the date is > than current item CreationDate
        futureDate = DateTime() + 1
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
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
              'org': self.developers_uid,
              'gives_auto_advice_on': 'item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': futureDate.strftime('%Y/%m/%d'),
              'delay': '',
              'delay_left_alert': '',
              'delay_label': ''}, ])
        self.assertEqual(item.getAutomaticAdvisersData(),
                         [{'gives_auto_advice_on_help_message': '',
                           'org_uid': self.developers_uid,
                           'org_title': 'Developers',
                           'row_id': 'unique_id_123',
                           'delay': '',
                           'delay_left_alert': '',
                           'delay_label': ''}])
        # now define a 'for_item_created_until' that is in the past
        # relative to the item created date
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
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
        item.setOptionalAdvisers((self.developers_uid, ))
        item._update_after_edit()

        # add the optional advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.developers_uid,
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEqual(advice.advice_row_id, '')
        self.assertEqual(item.adviceIndex[advice.advice_group]['row_id'], '')

        # now remove it and make it a 'delay-aware' advice
        item.restrictedTraverse('@@delete_givenuid')(advice.UID())
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'delay': '10'}, ])
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid), ))
        item._update_after_edit()
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.developers_uid,
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEqual(advice.advice_row_id, 'unique_id_123')
        self.assertEqual(item.adviceIndex[advice.advice_group]['row_id'], 'unique_id_123')

        # same behaviour for an automatic advice
        cfg.setCustomAdvisers(
            list(cfg.getCustomAdvisers()) +
            [{'row_id': 'unique_id_456',
              'org': self.vendors_uid,
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'delay': ''}, ])
        item._update_after_edit()
        # the automatic advice was asked, now add it
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_456')
        automatic_advice_obj = getattr(item, item.adviceIndex[self.vendors_uid]['advice_id'])
        self.assertEqual(automatic_advice_obj.advice_row_id, 'unique_id_456')

    def test_pm_DelayStartedStoppedOn(self):
        '''Test the 'advice_started_on' and 'advice_stopped_on' date initialization.
           The 'advice_started_on' is set when advice are turning to 'giveable', aka when
           they turn from not being in itemAdviceStates to being in it.
           The 'advice_stopped_on' date is initialized when the advice is no more giveable,
           so when the item state is no more in itemAdviceStates.
           The 2 dates are only reinitialized to None if the user
           triggers the MeetingConfig.transitionsReinitializingDelays.
        '''
        self.meetingConfig.setKeepAccessToItemWhenAdvice('default')
        self._checkDelayStartedStoppedOn()

    def test_pm_DelayStartedStoppedOnWithKeepAccessToItemWhenAdviceIsGiven(self):
        '''Same has 'test_pm_DelayStartedStoppedOn' but when
           MeetingConfig.keepAccessToItemWhenAdvice 'is_given'.
        '''
        self.meetingConfig.setKeepAccessToItemWhenAdvice('is_given')
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
              'org': self.developers_uid,
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
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        # advice are correctly asked
        self.assertEqual(
            sorted(item.adviceIndex.keys()),
            sorted([self.vendors_uid, self.developers_uid]))
        # for now, dates are not defined
        self.assertEqual([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                         [None, None])
        self.assertEqual([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                         [None, None])
        # propose the item, nothing should have changed
        self.proposeItem(item)
        self.assertEqual(
            sorted(item.adviceIndex.keys()),
            sorted([self.vendors_uid, self.developers_uid]))
        self.assertEqual(
            [advice['delay_started_on'] for advice in item.adviceIndex.values()],
            [None, None])
        self.assertEqual(
            [advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
            [None, None])
        # now do delays start
        # delay will start when the item advices will be giveable
        # advices are giveable when item is validated, so validate the item
        # this will initialize the 'delay_started_on' date
        self.validateItem(item)
        self.assertEqual(item.queryState(), self._stateMappingFor('validated'))
        # we have datetime now in 'delay_started_on' and still nothing in 'delay_stopped_on'
        self.assertTrue(isinstance(item.adviceIndex[self.developers_uid]['delay_started_on'], datetime))
        self.assertTrue(item.adviceIndex[self.developers_uid]['delay_stopped_on'] is None)
        # vendors optional advice is not delay-aware
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_started_on'] is None)
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_stopped_on'] is None)

        # set item back to proposed, 'delay_stopped_on' should be set
        self.backToState(item, self._stateMappingFor('proposed'))
        self.assertTrue(isinstance(item.adviceIndex[self.developers_uid]['delay_started_on'], datetime))
        self.assertTrue(isinstance(item.adviceIndex[self.developers_uid]['delay_stopped_on'], datetime))
        # vendors optional advice is not delay-aware
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_started_on'] is None)
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_stopped_on'] is None)

        # if we go on, the 'delay_started_on' date does not change anymore, even in a state where
        # advice are not giveable anymore, but at this point, the 'delay_stopped_date' will be set.
        # We present the item
        self.create('Meeting', date=DateTime('2012/01/01'))
        saved_developers_start_date = item.adviceIndex[self.developers_uid]['delay_started_on']
        saved_vendors_start_date = item.adviceIndex[self.vendors_uid]['delay_started_on']
        self.presentItem(item)
        self.assertEqual(item.queryState(), self._stateMappingFor('presented'))
        self.assertEqual(item.adviceIndex[self.developers_uid]['delay_started_on'], saved_developers_start_date)
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_started_on'], saved_vendors_start_date)
        # the 'delay_stopped_on' is now set on the delay-aware advice
        self.assertTrue(isinstance(item.adviceIndex[self.developers_uid]['delay_stopped_on'], datetime))
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_stopped_on'] is None)
        # if we excute the transition that will reinitialize dates, it is 'backToItemCreated'
        self.assertEqual(cfg.getTransitionsReinitializingDelays(),
                         (self._transitionMappingFor('backToItemCreated'), ))
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertEqual(item.queryState(), self._stateMappingFor('itemcreated'))
        # the delays have been reinitialized to None
        self.assertEqual([advice['delay_started_on'] for advice in item.adviceIndex.values()],
                         [None, None])
        self.assertEqual([advice['delay_stopped_on'] for advice in item.adviceIndex.values()],
                         [None, None])

    def test_pm_MayNotAddAdviceEditIfDelayExceeded(self):
        '''Test that if the delay to give an advice is exceeded, the advice is no more giveable.'''
        # configure one delay-aware optional adviser
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item._update_after_edit()
        self.changeUser('pmReviewer2')
        # the advice is asked but not giveable
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        # check 'PloneMeeting: add advice' permission
        self.assertFalse(self.hasPermission(AddAdvice, item))
        # put the item in a state where we can add an advice
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        # now we can add the item and the delay is not exceeded
        self.assertTrue(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] > 0)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # now make the delay exceeded and check again
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2012, 1, 1)
        item.updateLocalRoles()
        # if delay is negative, we show complete delay
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'], 5)
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['delay_status'], 'timed_out')
        self.assertFalse(self.hasPermission(AddAdvice, item))
        # recover delay, add the advice and check the 'edit' behaviour
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now()
        item.updateLocalRoles()
        self.assertTrue(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] > 0)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # add the advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_comment': RichTextValue(u'My comment')})
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_123')
        # advice is editable as delay is not exceeded
        self.assertTrue(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] > 0)
        self.assertTrue(self.hasPermission(ModifyPortalContent, advice))
        # now make sure the advice is no more editable when delay is exceeded
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2012, 1, 1)
        item.updateLocalRoles()
        # when delay is exceeded, left_delay is complete delay so we show it in red
        # we do not show the exceeded delay because it could be very large (-654?)
        # and represent nothing...
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'], 5)
        # 'delay_status' is 'timed_out'
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['delay_status'], 'timed_out')
        self.assertTrue(not self.hasPermission(ModifyPortalContent, advice))

    def test_pm_OrgDefinedItemAdviceStatesValuesOverridesMeetingConfigValues(self):
        '''Advices are giveable/editable/viewable depending on defined item states on the MeetingConfig,
           these states can be overrided locally for a particular organization so this particluar organization
           will be able to add an advice in different states than one defined globally on the MeetingConfig.'''
        # by default, nothing defined on the organization, the MeetingConfig states are used
        # getItemAdviceStates on a organziation returns values of the meetingConfig
        # if nothing is defined on the organziation
        self.assertTrue(not self.vendors.get_item_advice_states())
        # make advice giveable when item is proposed
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('proposed'), ))
        self.assertEqual(self.vendors.get_item_advice_states(cfg), cfg.getItemAdviceStates())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # ask 'vendors' advice
        item.setOptionalAdvisers((self.vendors_uid, ))
        item.at_post_create_script()
        self.proposeItem(item)
        self.assertEqual(item.queryState(), self._stateMappingFor('proposed'))
        # the advice is giveable by the vendors
        self.changeUser('pmReviewer2')
        self.assertTrue(self.vendors_uid in [key for key, value in item.getAdvicesGroupsInfosForUser()[0]])
        # now if we define on the 'vendors' item_advice_states
        # that advice is giveable when item is 'validated', it will not be anymore
        # in 'proposed' state, but well in 'validated' state
        self.changeUser('admin')
        self.vendors.item_advice_states = \
            ("%s__state__%s" % (cfg.getId(), self._stateMappingFor('validated')), )
        # no more using values defined on the meetingConfig
        self.assertNotEqual(self.vendors.get_item_advice_states(cfg), cfg.getItemAdviceStates())
        self.assertEqual(self.vendors.get_item_advice_states(cfg), [self._stateMappingFor('validated')])
        item.at_post_create_script()
        self.changeUser('pmReviewer2')
        self.assertTrue(self.vendors_uid not in [key for key, value in item.getAdvicesGroupsInfosForUser()[0]])
        # now validate the item and the advice is giveable
        self.changeUser('pmManager')
        self.validateItem(item)
        self.changeUser('pmReviewer2')
        self.assertEqual(item.queryState(), self._stateMappingFor('validated'))
        self.assertTrue(self.vendors_uid in [key for key, value in item.getAdvicesGroupsInfosForUser()[0]])

        # it is the same for itemAdviceEditStates and itemAdviceViewStates
        self.assertEqual(self.vendors.get_item_advice_edit_states(cfg), cfg.getItemAdviceEditStates())
        self.assertEqual(self.vendors.get_item_advice_view_states(cfg), cfg.getItemAdviceViewStates())
        self.vendors.item_advice_edit_states = \
            ("%s__state__%s" % (cfg.getId(), self._stateMappingFor('validated')), )
        self.vendors.item_advice_view_states = \
            ("%s__state__%s" % (cfg.getId(), self._stateMappingFor('validated')), )
        self.assertNotEqual(self.vendors.get_item_advice_edit_states(cfg), cfg.getItemAdviceEditStates())
        self.assertEqual(self.vendors.get_item_advice_edit_states(cfg), [self._stateMappingFor('validated')])
        self.assertNotEqual(self.vendors.get_item_advice_view_states(cfg), cfg.getItemAdviceViewStates())
        self.assertEqual(self.vendors.get_item_advice_view_states(cfg), [self._stateMappingFor('validated')])

    def test_pm_OrgDefinedItemAdviceStatesWorksTogetherWithMeetingConfigValues(self):
        '''Advices giveable/editable/viewable states defined for a MeetingConfig on an organization will
           not interact other MeetingConfig for which nothing is defined on this organization...'''
        # make advices giveable for vendors for cfg1 in state 'proposed' and define nothing regarding
        # cfg2, values defined on the cfg2 will be used
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        self.vendors.item_advice_states = \
            ("%s__state__%s" % (cfgId, self._stateMappingFor('proposed')), )
        self.vendors.item_advice_edit_states = \
            ("%s__state__%s" % (cfgId, self._stateMappingFor('proposed')), )
        self.vendors.item_advice_view_states = \
            ("%s__state__%s" % (cfgId, self._stateMappingFor('proposed')), )
        cfg2 = self.meetingConfig2
        cfg2.setItemAdviceStates((self._stateMappingFor('itemcreated'), ))
        cfg2.setItemAdviceEditStates((self._stateMappingFor('itemcreated'), ))
        cfg2.setItemAdviceViewStates((self._stateMappingFor('itemcreated'), ))

        # getting states for cfg2 will get states on the cfg2
        self.assertEqual(self.vendors.get_item_advice_states(cfg2), cfg2.getItemAdviceStates())
        self.assertEqual(self.vendors.get_item_advice_edit_states(cfg2), cfg2.getItemAdviceEditStates())
        self.assertEqual(self.vendors.get_item_advice_view_states(cfg2), cfg2.getItemAdviceViewStates())

    def test_pm_PowerAdvisers(self):
        '''Power advisers are users that can give an advice even when not asked...
           This will give these users opportunity to add the advice but 'View' access to the relevant
           item is given by another functionnality (MeetingManager, power observer, ...).'''
        # set developers as power advisers
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setPowerAdvisersGroups((self.developers_uid, ))
        self._setPowerObserverStates(states=(self._stateMappingFor('proposed'), ))

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        item._update_after_edit()
        # pmAdviser1 must have 'View' on the item to be able to give advice
        # for now, it is not the case, the 'View' is not given automatically to power advisers
        self.changeUser('pmAdviser1')
        # pmAdviser1 is not power adviser
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg))
        self.assertTrue(self.developers_uid not in item.adviceIndex)
        # he may not see item
        self.failIf(self.hasPermission(View, item))
        # but he is able to add the advice
        self.failUnless(self.hasPermission(AddPortalContent, item))
        self.failUnless(self.hasPermission(AddAdvice, item))
        # right, give 'View' access, now pmAdviser1 will be able to see the item
        # add pmAdviser1 to power observers
        self.changeUser('siteadmin')
        self._addPrincipalToGroup('pmAdviser1', '%s_powerobservers' % cfg.getId())
        item.updateLocalRoles()
        self.changeUser('pmAdviser1')
        # pmAdviser1 can give advice for developers even if
        # not asked, aka not in item.adviceIndex
        self.assertTrue(self.developers_uid not in item.adviceIndex)
        self.failUnless(self.hasPermission(AddPortalContent, item))
        self.failUnless(self.hasPermission(AddAdvice, item))
        self.failUnless(self.hasPermission(View, item))
        # he can actually give it
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
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
        self._addPrincipalToGroup('pmAdviser1', '{0}_advisers'.format(self.vendors_uid))
        cfg.setPowerAdvisersGroups((self.developers_uid, self.vendors_uid, ))
        item.updateLocalRoles()
        # now as pmAdviser1 is adviser for vendors and vendors is a PowerAdviser,
        # he can add an advice for vendors
        self.changeUser('pmAdviser1')
        self.assertTrue(self.vendors_uid not in item.adviceIndex)
        self.failUnless(self.hasPermission(AddAdvice, item))
        self.failUnless(self.hasPermission(View, item))
        # make sure he can not add an advice for an other group he is adviser for
        # but he already gave the advice for.  So check that 'developers' is not in the
        # meetingadvice.advice_group vocabulary
        factory = queryUtility(IVocabularyFactory, u'Products.PloneMeeting.content.advice.advice_group_vocabulary')
        vocab = factory(item)
        self.assertEqual(len(vocab), 1)
        self.assertTrue(self.vendors_uid in vocab)
        self.assertTrue(self.developers_uid not in vocab)

    def test_pm_ComputeDelaysWorkingDaysAndHolidaysAndUnavailableEndDays(self):
        '''Test that computing of delays relying on workingDays, holidays
           and unavailable ending days is correct.'''
        # configure one delay-aware optional adviser
        # we use 7 days of delay so we are sure that we when setting
        # manually 'delay_started_on' to last monday, delay is still ok
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
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
        self.meetingConfig.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        self.meetingConfig.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        self.meetingConfig.setItemAdviceViewStates((self._stateMappingFor('proposed'), ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item._update_after_edit()
        self.proposeItem(item)
        # advice should be giveable during 7 working days, we set manually 'delay_started_on'
        # to last monday (or today if we are monday) so we are sure about delay and limit_date and so on...
        delay_started_on = item.adviceIndex[self.vendors_uid]['delay_started_on']
        while not delay_started_on.weekday() == 0:
            delay_started_on = delay_started_on - timedelta(1)
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = delay_started_on
        item.updateLocalRoles()
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_started_on'].weekday(), 0)
        # for now, weekends are days 5 and 6, so saturday and sunday
        self.assertEqual(self.tool.getNonWorkingDayNumbers(), [5, 6])
        # limit_date should be in 9 days, 7 days of delay + 2 days of weekends
        limit_date_9_days = item._doClearDayFrom(item.adviceIndex[self.vendors_uid]['delay_started_on'] + timedelta(9))
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'], limit_date_9_days)
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'still_time')
        # now set weekends to only 'sunday'
        self.tool.setWorkingDays(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', ))
        # the method is ram.cached, check that it is correct when changed
        self.tool.setModificationDate(DateTime())
        self.assertEqual(self.tool.getNonWorkingDayNumbers(), [6, ])
        item.updateLocalRoles()
        # this will decrease delay of one day
        self.assertEqual(limit_date_9_days - timedelta(1),
                         item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'])
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'still_time')

        # now add 2 holidays, one passed date and one date that will change delay
        # a date next day after the 'delay_started_on'
        delay_started_on = item.adviceIndex[self.vendors_uid]['delay_started_on']
        holiday_changing_delay = '%s' % (delay_started_on + timedelta(1)).strftime('%Y/%m/%d')
        self.tool.setHolidays(({'date': '2012/05/06'},
                               {'date': holiday_changing_delay}, ))
        # the method getHolidaysAs_datetime is ram.cached, check that it is correct when changed
        self.tool.setModificationDate(DateTime())
        year, month, day = holiday_changing_delay.split('/')
        self.assertEqual(self.tool.getHolidaysAs_datetime(),
                         [datetime(2012, 5, 6), datetime(int(year), int(month), int(day)), ])
        # this should increase delay of one day, so as original limit_date_9_days
        item.updateLocalRoles()
        self.assertEqual(limit_date_9_days, item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'])
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'still_time')

        # now add one unavailable day for end of delay
        # for now, limit_date ends day number 2, so wednesday
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'].weekday(), 2)
        self.tool.setDelayUnavailableEndDays(('wed', ))
        # the method getUnavailableWeekDaysNumbers is ram.cached, check that it is correct when changed
        self.tool.setModificationDate(DateTime())
        self.assertEqual(self.tool.getUnavailableWeekDaysNumbers(), [2, ])
        item.updateLocalRoles()
        # this increase limit_date of one day, aka next available day
        self.assertEqual(limit_date_9_days + timedelta(1),
                         item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'])
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'],
                         'still_time')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'].weekday(),
                         3)

        # test that the advice may still be added the last day
        # to avoid that current day (aka last day) is a weekend or holiday or unavailable day
        # or so, we just remove everything that increase/decrease delay
        self.tool.setDelayUnavailableEndDays([])
        self.tool.setHolidays([])
        self.tool.setWorkingDays(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', ))
        self.tool.setModificationDate(DateTime())
        # change 'delay_started_on' manually and check that last day, the advice is 'still_giveable'
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now() - timedelta(7)
        item.updateLocalRoles()
        # we are the last day
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'].day, datetime.now().day)
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'still_time')
        # one day more and it is not giveable anymore...
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now() - timedelta(8)
        item.updateLocalRoles()
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'] < datetime.now())
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'timed_out')

    def test_pm_ComputeDelaysAsCalendarDays(self):
        '''
          Test that computing of delays works also as 'calendar days'.
          To do this, we simply define 7 days of the week as working days and no holidays.
        '''
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': ''}, ])
        # no holidays...
        self.tool.setHolidays([])
        # every days are working days
        self.tool.setWorkingDays(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', ))
        self.assertEqual(self.tool.getNonWorkingDayNumbers(), [])
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item._update_after_edit()
        self.proposeItem(item)
        # now test that limit_date is just now + delay of 10 days
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'],
                         item._doClearDayFrom(item.adviceIndex[self.vendors_uid]['delay_started_on'] + timedelta(10)))

    def test_pm_AvailableDelaysView(self):
        '''Test the view '@@advice-available-delays' that shows
           available delays for a selected delay-aware advice.'''
        cfg = self.meetingConfig
        # make advice addable and editable when item is 'proposed'
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('proposed'),
                                     self._stateMappingFor('validated')))
        self._setPowerObserverStates(states=(self._stateMappingFor('proposed'), ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # no other linked delay
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '5',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # select delay of 5 days
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item._update_after_edit()
        availableDelaysView = item.restrictedTraverse('@@advice-available-delays')
        availableDelaysView._initAttributes(self.vendors_uid)
        self.assertFalse(availableDelaysView.listSelectableDelays())
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # now add delays to change to
        customAdvisers += [{'row_id': 'unique_id_456',
                            'org': self.vendors_uid,
                            'gives_auto_advice_on': '',
                            'for_item_created_from': '2012/01/01',
                            'for_item_created_until': '',
                            'delay': '10',
                            'delay_label': '',
                            'available_on': '',
                            'is_linked_to_previous_row': '1'},
                           {'row_id': 'unique_id_789',
                            'org': self.vendors_uid,
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
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # the creator may only edit the delays if it may edit the item
        # if pmCreator1 propose the item, it can no more edit it so it can not change delays
        # now propose the item, selectable delays should be empty
        self.proposeItem(item)
        self.assertFalse(availableDelaysView.listSelectableDelays())
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # the pmReviewer1 can change delay as he may edit the item
        self.changeUser('pmReviewer1')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())

        # makes it an automatic advice
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.changeUser('pmCreator1')
        item._update_after_edit()
        customAdvisers[0]['gives_auto_advice_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        # MeetingConfig._findLinkedRowsFor is ram cached
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        item.setOptionalAdvisers(())
        item._update_after_edit()
        self.assertEqual(availableDelaysView.listSelectableDelays(), [])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        self.proposeItem(item)
        self.assertEqual(availableDelaysView.listSelectableDelays(), [])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # the pmReviewer1 can not change an automatic advice delay
        self.changeUser('pmReviewer1')
        self.assertEqual(availableDelaysView.listSelectableDelays(), [])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # a MeetingManager may edit an automatic advice delay
        self.changeUser('pmManager')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # test the 'available_on' behaviour
        self.backToState(item, self._stateMappingFor('proposed'))
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_stopped_on'] is None)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # now define a 'available_on' for third row
        # first step, something that is False
        customAdvisers[2]['available_on'] = 'python:False'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # a wrong TAL expression for 'available_on' does not break anything
        customAdvisers[2]['available_on'] = 'python:here.someUnexistingMethod()'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # second step, something that is True
        customAdvisers[2]['available_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # now test the particular expression that makes a custom adviser
        # useable when changing delays but not in other cases
        customAdvisers[2]['available_on'] = "python:item.REQUEST.get('managing_available_delays', False)"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())

        # the mayEdit variable is available in the expression, it is True if current
        # user may edit item, False otherwise
        customAdvisers[2]['available_on'] = "mayEdit"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ('unique_id_789', '20', u'')])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        customAdvisers[2]['available_on'] = "not:mayEdit"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u''), ])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())

        # access to delay changes history is only for adviser, proposingGroup and MeetingManagers
        # adviser
        self.changeUser('pmReviewer2')
        self.assertEqual(item.getAdvicesGroupsInfosForUser(),
                         ([(self.vendors_uid, 'Vendors')], []))
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # but not for powerobservers for example
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(availableDelaysView._mayAccessDelayChangesHistory())

    def test_pm_ChangeDelayView(self):
        '''Test the view '@@change-advice-delay' that apply the change delay action.'''
        cfg = self.meetingConfig
        # make advice addable and editable when item is 'proposed'
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('proposed'),
                                     self._stateMappingFor('validated')))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '5',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0'},
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '10',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '20',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # select delay of 5 days
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item._update_after_edit()
        # for now, delay is 5 days and 'row_id' is unique_id_123
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_123')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay'], '5')
        self.assertTrue(item.adviceIndex[self.vendors_uid]['optional'])
        form = item.restrictedTraverse('@@advice_delay_change_form').form_instance
        form.request['form.widgets.current_delay_row_id'] = u'unique_id_123'

        # first check that if we try to play the fennec, it raises Unauthorized
        form.request['form.widgets.new_delay_row_id'] = u'some_dummy_value'
        self.assertRaises(Unauthorized, form)
        # now change the delay, really
        form.request['form.widgets.new_delay_row_id'] = u'unique_id_789'
        # delay is changed to third custom adviser, aka 20 days
        form.handleSaveAdviceDelay(form, '')
        # not changed as comment is required
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_123')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay'], '5')
        # now apply with comment
        form.request['form.widgets.comment'] = u'My comment'
        form.handleSaveAdviceDelay(form, '')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_789')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay'], '20')
        # a special key save the fact that we saved delay of an automatic adviser
        # this should be 'False' for now as we changed an optional adviser delay
        self.assertFalse(item.adviceIndex[self.vendors_uid]['delay_for_automatic_adviser_changed_manually'])

        # it works also for automatic advices but only MeetingManagers may change it
        # makes it an automatic advice
        customAdvisers[0]['gives_auto_advice_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        # MeetingConfig._findLinkedRowsFor is ram cached, based on MC modified
        cfg.processForm({'dummy': ''})
        item.setOptionalAdvisers(())
        item._update_after_edit()
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_123')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay'], '5')
        self.assertFalse(item.adviceIndex[self.vendors_uid]['optional'])
        # if a normal user tries to change an automatic advice delay, it will raises Unauthorized
        self.assertRaises(Unauthorized, form.handleSaveAdviceDelay, form, '')
        # now as MeetingManager it works
        self.changeUser('pmManager')
        form.handleSaveAdviceDelay(form, '')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_789')
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay'], '20')
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_for_automatic_adviser_changed_manually'])

    def test_pm_ReinitAdviceDelayView(self):
        '''Test the view '@@advice-reinit-delay' that reinitialize the advice delay to 0.'''
        cfg = self.meetingConfig
        # make advice addable and editable when item is 'itemcreated'
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'), ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        customAdvisers = [{'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '5',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '0'},
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '10',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '20',
                           'delay_label': '',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # select delay of 5 days
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item._update_after_edit()
        # delay was started
        original_delay_started_on = item.getAdviceDataFor(item, self.vendors_uid)['delay_started_on']
        self.assertIsInstance(original_delay_started_on, datetime)
        # must be able to edit item to reinit delay
        self.proposeItem(item)
        self.request.set('advice', self.vendors_uid)
        view = item.restrictedTraverse('@@advice-reinit-delay')
        self.assertRaises(Unauthorized, view)
        self.changeUser('pmReviewer1')
        view()
        new_delay_started_on = item.getAdviceDataFor(item, self.vendors_uid)['delay_started_on']
        self.assertNotEqual(original_delay_started_on, new_delay_started_on)

    def test_pm_ConfigAdviceStates(self):
        '''
          This test that states defined in config.py in two constants
          ADVICE_STATES_ALIVE and ADVICE_STATES_ENDED
          consider every states of the workflow used for content_type 'meetingadvice'.
        '''
        adviceWF = self.wfTool.getWorkflowsFor('meetingadvice')
        # we have only one workflow for 'meetingadvice'
        self.assertEqual(len(adviceWF), 1)
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
        cfg.setAdviceConfidentialFor(('powerobservers', ))
        # make power observers able to see proposed items
        self._setPowerObserverStates(states=(self._stateMappingFor('proposed'), ))
        # first check default confidentiality value
        # create an item and ask advice of 'developers'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid, ))
        item._update_after_edit()
        # must be MeetingManager to be able to change advice confidentiality
        self.assertFalse(item.adapted().mayEditAdviceConfidentiality(self.developers_uid))
        # if creator tries to change advice confidentiality, he gets Unauthorized
        toggleView = item.restrictedTraverse('@@toggle_advice_is_confidential')
        self.assertRaises(Unauthorized, toggleView.toggle, UID='%s__%s' % (item.UID(), self.developers_uid))
        self.assertTrue(item.adviceIndex[self.developers_uid]['isConfidential'])
        cfg.setAdviceConfidentialityDefault(False)
        # ask 'vendors' advice
        item.setOptionalAdvisers((self.developers_uid, self.vendors_uid, ))
        item._update_after_edit()
        # still confidential for 'developers'
        self.assertTrue(item.adviceIndex[self.developers_uid]['isConfidential'])
        # but not by default for 'vendors'
        self.assertFalse(item.adviceIndex[self.vendors_uid]['isConfidential'])
        # so we have one confidential advice and one that is not confidential
        # but MeetingManagers may see both
        self.assertEqual(len(item.getAdvicesByType()[NOT_GIVEN_ADVICE_VALUE]), 2)
        # propose the item so power observers can see it
        self.proposeItem(item)

        # log as power observer and check what he may access
        self.changeUser('powerobserver1')
        # only the not confidential advice is visible
        advicesByType = item.getAdvicesByType()
        self.assertEqual(len(advicesByType[NOT_GIVEN_ADVICE_VALUE]), 1)
        self.assertEqual(advicesByType[NOT_GIVEN_ADVICE_VALUE][0]['id'], self.vendors_uid)

        # now give the advice so we check that trying to access a confidential
        # advice will raise Unauthorized
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(item,
                                                     'meetingadvice',
                                                     **{'advice_group': self.developers_uid,
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
        self.assertTrue(item.adapted().mayEditAdviceConfidentiality(self.developers_uid))
        self.assertTrue(item.adviceIndex[self.developers_uid]['isConfidential'])
        toggleView.toggle(UID='%s__%s' % (item.UID(), self.developers_uid))
        self.assertFalse(item.adviceIndex[self.developers_uid]['isConfidential'])

    def test_pm_MayTriggerGiveAdviceWhenItemIsBackToANotViewableState(self, ):
        '''Test that if an item is set back to a state the user that set it back can
           not view anymore, and that the advice turn from giveable to not giveable anymore,
           transitions triggered on advice that will 'giveAdvice'.'''
        cfg = self.meetingConfig
        # advice can be given when item is validated
        cfg.setItemAdviceStates((self._stateMappingFor('validated'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('validated'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('validated'), ))
        # create an item as vendors and give an advice as vendors on it
        # it is viewable by MeetingManager when validated
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        # validate the item and advice it
        self.validateItem(item)
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
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
            if transition.new_state_id == self._stateMappingFor('proposed'):
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
            'optionalAdvisers': (self.vendors_uid, )
        }
        item = self.create('MeetingItem', **data)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'positive',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})
        # 'pmReviewer2', as adviser, is able to toggle advice_hide_during_redaction
        self.assertFalse(advice.advice_hide_during_redaction)
        self.assertFalse(item.adviceIndex[self.vendors_uid]['hidden_during_redaction'])
        changeView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeView()
        self.assertTrue(advice.advice_hide_during_redaction)
        self.assertTrue(item.adviceIndex[self.vendors_uid]['hidden_during_redaction'])
        # when advice is hidden, trying to access the view will raise Unauthorized
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, advice.restrictedTraverse('view'))
        # back to not hidden
        self.changeUser('pmReviewer2')
        changeView()
        self.assertFalse(advice.advice_hide_during_redaction)
        self.assertFalse(item.adviceIndex[self.vendors_uid]['hidden_during_redaction'])
        # to use the change view, user must be able to edit the advice,
        # here, it is not the case for 'pmCreator1'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, changeView)
        # but the view is accessible
        self.assertTrue(advice.restrictedTraverse('view')())

    def test_pm_ChangeAdviceAskedAgainView(self):
        """Test the view that will change from advice asked_again/back to previous advice."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('proposed'), ])
        # set that default value of field 'advice_hide_during_redaction' will be True
        cfg.setDefaultAdviceHiddenDuringRedaction(['meetingadvice'])
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.vendors_uid, self.developers_uid, )
        }
        item = self.create('MeetingItem', **data)
        self.proposeItem(item)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})
        changeView = advice.restrictedTraverse('@@change-advice-asked-again')
        # 'asked_again' must be in usedAdviceTypes so the functionnality is activated
        self.assertTrue('asked_again' not in cfg.getUsedAdviceTypes())
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
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0])
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
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0])
        self.assertEqual(advice.advice_type, 'asked_again')
        # now it is available in vocabulary
        vocab = factory(advice)
        self.assertTrue('asked_again' in vocab)
        pr = self.portal.portal_repository
        # version 0 was saved
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0])
        # we may also revert to previous version
        self.assertFalse(item.adapted().mayAskAdviceAgain(advice))
        self.assertTrue(item.adapted().mayBackToPreviousAdvice(advice))
        # when an advice is 'asked_again', the field hidden_during_redaction
        # is set to the default defined in the MeetingConfig
        self.assertTrue('meetingadvice' in cfg.getDefaultAdviceHiddenDuringRedaction())
        self.assertTrue(advice.advice_hide_during_redaction)
        changeView()
        # when going back to previous version, a new version is done
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0, 1])
        self.assertEqual(advice.advice_type, 'negative')
        # advice was automatically shown
        self.assertFalse(advice.advice_hide_during_redaction)
        # ok, ask_again and send it again to 'pmReviewer2', he will be able to edit it
        # but before, edit the advice so it is historized again
        notify(ObjectModifiedEvent(advice))
        changeView()
        # this time a new version has been saved
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0, 1, 2])
        self.assertEqual(advice.advice_type, 'asked_again')
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
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0, 1, 2])
        # but works after when advice is no more 'asked_again'
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        advice.advice_type = 'positive'
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.backToState(item, 'itemcreated')
        self.assertEqual(pr.getHistoryMetadata(advice)._available, [0, 1, 2, 3])

    def test_pm_HistorizedAdviceIsNotDeletable(self):
        """When an advice has been historized (officially given or asked_again,
           so when versions exist), it can not be deleted by the advisers."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('itemcreated'), ])
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.vendors_uid, self.developers_uid, )
        }
        item = self.create('MeetingItem', **data)
        # give advice
        self.changeUser('pmAdviser1')
        developers_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': RichTextValue(u'My comment')})
        # for now advice is deletable
        advices_icons_infos = item.restrictedTraverse('@@advices-icons-infos')
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'positive')
        self.assertTrue(advices_icons_infos.mayDelete(developers_advice))
        # give advice
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'negative',
               'advice_hide_during_redaction': False,
               'advice_comment': RichTextValue(u'My comment')})
        # for now advice is deletable
        advices_icons_infos = item.restrictedTraverse('@@advices-icons-infos')
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'negative')
        self.assertTrue(advices_icons_infos.mayDelete(vendors_advice))

        # ask developers_advice again
        changeView = developers_advice.restrictedTraverse('@@change-advice-asked-again')
        self.changeUser('pmCreator1')
        changeView()
        self.assertEqual(developers_advice.advice_type, 'asked_again')
        # advice asker may obviously not delete it
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'asked_again')
        self.assertFalse(advices_icons_infos.mayDelete(developers_advice))
        # and advisers neither
        self.changeUser('pmAdviser1')
        self.assertFalse(advices_icons_infos.mayDelete(developers_advice))
        # even when advice_type is changed
        developers_advice.advice_type = 'positive'
        notify(ObjectModifiedEvent(developers_advice))
        advices_icons_infos(adviceType=u'positive')
        self.assertFalse(advices_icons_infos.mayDelete(developers_advice))

        # when an advice is officially given, it is historized so advice is no more deletable
        self.proposeItem(item)
        self.assertFalse(advices_icons_infos.mayDelete(developers_advice))
        self.changeUser('pmReviewer2')
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'negative')
        self.assertFalse(advices_icons_infos.mayDelete(vendors_advice))

    def test_pm_AdviceHistorizedWithItemDataWhenAdviceGiven(self):
        """When an advice is given, it is versioned and relevant item infos are saved.
           Moreover, advice is only versioned if it was modified."""
        cfg = self.meetingConfig
        # item data are saved if cfg.historizeItemDataWhenAdviceIsGiven
        self.assertTrue(cfg.getHistorizeItemDataWhenAdviceIsGiven())
        # make sure we know what item rich text fields are enabled
        cfg.setUsedItemAttributes(('description', 'detailedDescription', 'motivation', ))
        cfg.setItemAdviceStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('proposed'), ])
        # set that default value of field 'advice_hide_during_redaction' will be True
        cfg.setDefaultAdviceHiddenDuringRedaction(['meetingadvice'])
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.vendors_uid, self.developers_uid, ),
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
                                          **{'advice_group': self.vendors_uid,
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
        self.assertEqual(h_metadata._available, [0])
        previous = pr.retrieve(advice, 0).object
        self.assertEqual(previous.historized_item_data,
                         [{'field_name': 'title', 'field_content': 'Item to advice'},
                          {'field_name': 'description', 'field_content': '<p>Item description</p>'},
                          {'field_name': 'detailedDescription', 'field_content': '<p>Item detailed description</p>'},
                          {'field_name': 'motivation', 'field_content': '<p>Item motivation</p>'},
                          {'field_name': 'decision', 'field_content': '<p>Item decision</p>'}])
        # when giving advice for a second time, if advice is not edited, it is not versioned uselessly
        self.backToState(item, self._stateMappingFor('proposed'))
        self.assertEqual(advice.queryState(), 'advice_under_edit')
        self.validateItem(item)
        self.assertEqual(advice.queryState(), 'advice_given')
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0])

        # come back to 'proposed' and edit advice
        item.setDecision('<p>Another decision</p>')
        self.backToState(item, self._stateMappingFor('proposed'))
        notify(ObjectModifiedEvent(advice))
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0, 1])
        previous = pr.retrieve(advice, 1).object
        self.assertEqual(previous.historized_item_data,
                         [{'field_name': 'title', 'field_content': 'Item to advice'},
                          {'field_name': 'description', 'field_content': '<p>Item description</p>'},
                          {'field_name': 'detailedDescription', 'field_content': '<p>Item detailed description</p>'},
                          {'field_name': 'motivation', 'field_content': '<p>Item motivation</p>'},
                          {'field_name': 'decision', 'field_content': '<p>Another decision</p>'}])

    def test_pm_AdviceModificationDateKeptWhenAdviceHistorized(self):
        """Make sure historizing the advice will not change the advice modification date."""
        cfg = self.meetingConfig
        # item data are saved if cfg.historizeItemDataWhenAdviceIsGiven
        self.assertTrue(cfg.getHistorizeItemDataWhenAdviceIsGiven())
        cfg.setItemAdviceStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('proposed'), ])

        # create an item and ask the advice of group 'vendors'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        self.proposeItem(item)

        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})

        # advice is versioned when it is given, aka transition giveAdvice has been triggered
        self.changeUser('pmReviewer1')
        pr = api.portal.get_tool('portal_repository')
        self.assertFalse(pr.getHistoryMetadata(advice))
        advice_modified = advice.modified()
        self.assertTrue(isModifiedSinceLastVersion(advice))
        self.validateItem(item)
        self.assertTrue(pr.getHistoryMetadata(advice))
        self.assertFalse(isModifiedSinceLastVersion(advice))
        self.assertEqual(advice_modified, advice.modified())

    def test_pm_Get_advice_given_on(self):
        """This method will return the smallest of last event 'giveAdvice' and 'modified'.
           This will care that an advice that is edited out of the period the adviser may
           edit the advice is still using the correct given_on date."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('itemcreated'), ])

        # create an item and ask the advice of group 'vendors'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid,))

        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment')})

        advice_modified = advice.modified()
        self.assertEqual(advice.get_advice_given_on(), advice_modified)
        # propose item so transition 'giveAdvice' is triggered
        self.assertFalse(getLastWFAction(advice, 'giveAdvice'))
        self.proposeItem(item)
        self.assertTrue(getLastWFAction(advice, 'giveAdvice'))
        # still using the modified date
        self.assertEqual(advice.get_advice_given_on(), advice_modified)
        # if advice is modified when it is given, then the date it was given
        # (giveAdvice was triggered) will be used
        advice.notifyModified()
        self.assertNotEqual(advice.modified(), advice_modified)
        self.assertEqual(advice.get_advice_given_on(), getLastWFAction(advice, 'giveAdvice')['time'])

    def test_pm_AdviceHistorizedIfGivenAndItemChanged(self):
        """When an advice is given, if it was not historized and an item richText field
           is changed, it is versioned and relevant item infos are saved.  This way we are sure that
           historized infos about item are the one when the advice was given.
           Moreover, advice is only versioned if it was modified since last version."""
        cfg = self.meetingConfig
        # item data are saved if cfg.historizeItemDataWhenAdviceIsGiven
        self.assertTrue(cfg.getHistorizeItemDataWhenAdviceIsGiven())
        # make sure we know what item rich text fields are enabled
        cfg.setUsedItemAttributes(('description', 'detailedDescription', 'motivation', ))
        cfg.setItemAdviceStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('proposed'), ])
        # default value of field 'advice_hide_during_redaction' is False
        self.assertFalse(cfg.getDefaultAdviceHiddenDuringRedaction())

        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.vendors_uid, self.developers_uid, ),
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
                                          **{'advice_group': self.vendors_uid,
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
        self.assertEqual(item.getDetailedDescription(),
                         '<p>Item detailed description not active</p>')
        # it was not versioned because versionateAdviceIfGivenAndItemModified is False
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata, [])
        # activate and try again
        self.changeUser('siteadmin')
        cfg.setVersionateAdviceIfGivenAndItemModified(True)
        self.changeUser('pmReviewer1')
        item.processForm()
        # first version, item data was historized on it
        previous = pr.retrieve(advice, 0).object
        # we have item data before it was modified
        self.assertEqual(previous.historized_item_data,
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
        self.assertEqual(item.getDetailedDescription(), '<p>Item detailed description edited 2</p>')
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0])

        # when moving to 'validated', advice is 'adviceGiven', but not versioned again
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0])

        # but it is again if advice is edited
        self.changeUser('pmManager')
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        # validate item, this time advice is versioned again
        self.validateItem(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0, 1])

        # and once again back to proposed and edit item
        # not versioned because advice was not edited
        self.changeUser('pmManager')
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer1')
        self.request.form['detailedDescription'] = '<p>Item detailed description edited 3</p>'
        item.processForm({'detailedDescription': '<p>Item detailed description edited 3</p>'})
        self.assertEqual(item.getDetailedDescription(), '<p>Item detailed description edited 3</p>')
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0, 1])

        # right, back to proposed and use ajax edit
        self.changeUser('pmManager')
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        item.setFieldFromAjax('detailedDescription', '<p>Item detailed description edited 4</p>')
        self.assertEqual(item.getDetailedDescription(), '<p>Item detailed description edited 4</p>')
        # advice was versioned again
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0, 1, 2])
        # we have item data before it was modified
        previous = pr.retrieve(advice, 2).object
        self.assertEqual(previous.historized_item_data,
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

        # advice are no more versionated when annex is added/removed
        annex = self.addAnnex(item)
        # was already versionated so no more
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEqual(h_metadata._available, [0, 1, 2])
        # right edit the advice and remove the annex
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.deleteAsManager(annex.UID())
        # advice was not versioned again
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1, 2])
        # edit advice and add a new annex, advice will not be versionated
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        annex = self.addAnnex(item)
        h_metadata = pr.getHistoryMetadata(advice)
        self.assertEquals(h_metadata._available, [0, 1, 2])

    def _setupKeepAccessToItemWhenAdvice(self,
                                         value='default',
                                         give_advices_for=['vendors', 'developers']):
        """Setup for testing aroung 'keepAccessToItemWhenAdvice'."""
        # classic scenario is an item visible by advisers when it is 'proposed'
        # and no more when it goes back to 'itemcreated'
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('proposed'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('proposed'), ])
        cfg.setKeepAccessToItemWhenAdvice(value)

        # create an item, set it to 'proposed', give advice and set it back to 'itemcreated'
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to advice',
            'optionalAdvisers': (self.vendors_uid, self.developers_uid),
            'description': '<p>Item description</p>',
        }
        item = self.create('MeetingItem', **data)
        self.proposeItem(item)
        # give advices
        vendors_advice = None
        if 'vendors' in give_advices_for:
            self.changeUser('pmReviewer2')
            vendors_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.vendors_uid,
                   'advice_type': u'positive',
                   'advice_hide_during_redaction': False,
                   'advice_comment': RichTextValue(u'My comment')})
        developers_advice = None
        if 'developers' in give_advices_for:
            self.changeUser('pmAdviser1')
            developers_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.developers_uid,
                   'advice_type': u'positive',
                   'advice_hide_during_redaction': False,
                   'advice_comment': RichTextValue(u'My comment')})
        return item, vendors_advice, developers_advice

    def test_pm_KeepAccessToItemWhenAdviceIsGiven(self):
        """Test when MeetingConfig.keepAccessToItemWhenAdvice 'is_given',
           access to the item is kept if advice was given no matter the item is
           in a state where it should not be anymore."""

        cfg = self.meetingConfig
        item, vendors_advice, developers_advice = self._setupKeepAccessToItemWhenAdvice()

        # set item back to 'itemcreated', it will not be visible anymore by advisers
        self.changeUser('pmReviewer2')
        self.assertEqual(cfg.getKeepAccessToItemWhenAdvice(), 'default')
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertFalse(self.hasPermission(View, item))

        # activate keepAccessToItemWhenAdvice, then item is visible again
        cfg.setKeepAccessToItemWhenAdvice('is_given')
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # access is only kept if advice was given
        self.deleteAsManager(vendors_advice.UID())
        self.assertFalse(self.hasPermission(View, item))

    def test_pm_KeepAccessToItemWhenAdviceWasGiveable(self):
        """Test when MeetingConfig.keepAccessToItemWhenAdvice 'was_giveable',
           access to the item is kept if item was already in a state in which advice was giveable,
           no matter the item is in a state where it should not be anymore."""

        cfg = self.meetingConfig
        item, vendors_advice, developers_advice = \
            self._setupKeepAccessToItemWhenAdvice(give_advices_for=['developers'])

        # set item back to 'itemcreated', it will still be visible by advisers
        # even if advice was not given
        self.changeUser('pmReviewer2')
        self.assertEqual(cfg.getKeepAccessToItemWhenAdvice(), 'default')
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertFalse(self.hasPermission(View, item))

        # activate keepAccessToItemWhenAdvice, then item is visible again
        cfg.setKeepAccessToItemWhenAdvice('was_giveable')
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # access is also kept if advice was given
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))

    def test_pm_OrgDefinedKeepAccessToItemWhenAdviceOverridesMeetingConfigValues(self):
        '''organization.keep_access_to_item_when_advice will use or
           override the MeetingConfig value.'''
        cfg = self.meetingConfig
        item, vendors_advice, developers_advice = self._setupKeepAccessToItemWhenAdvice()

        # by default, the MeetingConfig value is used
        self.changeUser('pmReviewer2')
        self.assertEqual(self.vendors.get_keep_access_to_item_when_advice(),
                         'use_meetingconfig_value')
        self.assertEqual(cfg.getKeepAccessToItemWhenAdvice(), 'default')
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.backToState(item, self._stateMappingFor('itemcreated'))

        # override MeetingConfig value
        self.vendors.keep_access_to_item_when_advice = 'is_given'
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # this does not interact with other given advices
        self.changeUser('pmAdviser1')
        self.assertEqual(self.developers.get_keep_access_to_item_when_advice(),
                         'use_meetingconfig_value')
        self.assertEqual(self.developers.get_keep_access_to_item_when_advice(cfg),
                         'default')
        self.assertFalse(self.hasPermission(View, item))

        # override the other way round
        self.changeUser('pmReviewer2')
        self.vendors.keep_access_to_item_when_advice = 'use_meetingconfig_value'
        cfg.setKeepAccessToItemWhenAdvice('is_given')
        item.updateLocalRoles()
        self.assertTrue(self.hasPermission(View, item))

        # use MeetingConfig value that is True
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))

        # force disable keep access
        self.changeUser('pmReviewer2')
        self.vendors.keep_access_to_item_when_advice = 'default'
        item.updateLocalRoles()
        self.assertFalse(self.hasPermission(View, item))

        # this does not interact with other given advices, still using MeetingConfig value
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))

        # use was_giveable
        # remove vendors advice
        self.changeUser('siteadmin')
        self.deleteAsManager(developers_advice.UID())
        self.changeUser('pmAdviser1')
        self.assertFalse(self.hasPermission(View, item))
        self.developers.keep_access_to_item_when_advice = 'was_giveable'
        item.updateLocalRoles()
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
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()

        # give advice
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': self.vendors_uid,
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
        self.backToState(item, 'itemcreated')
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
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()

        # give advice
        self.changeUser('pmReviewer2')
        # creation time
        text = u'<p>Working external image <img src="%s"/>.</p>' % self.external_image2
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'positive',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(text)})
        self.assertTrue('1025-400x300.jpg' in advice.objectIds())

        # test using IObjectModifiedEvent event, aka using edit form
        text = '<p>Working external image <img src="%s"/>.</p>' % self.external_image4
        advice.advice_comment = RichTextValue(text)
        # notify modified
        notify(ObjectModifiedEvent(advice))
        self.assertTrue('1062-600x500.jpg' in advice.objectIds())

    def test_pm_ManualVersioningEnabledForMeetingAdvicePortalTypes(self):
        """ """
        portal_types = self.portal.portal_types
        portal_repository = self.portal.portal_repository
        for portal_type_id in portal_types:
            if portal_type_id.startswith('meetingadvice'):
                self.assertEqual(portal_repository._version_policy_mapping[portal_type_id],
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
        item.setOptionalAdvisers((self.vendors_uid, self.developers_uid, ))
        item._update_after_edit()

        # give 'vendors' advice and test
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(item,
                                                  'meetingadvice',
                                                  **{'advice_group': self.vendors_uid,
                                                     'advice_type': u'positive',
                                                     'advice_hide_during_redaction': False,
                                                     'advice_comment': RichTextValue(u'My comment')})
        self.assertEqual(item.getAdviceObj(self.vendors_uid), vendors_advice)
        self.assertIsNone(item.getAdviceObj(self.developers_uid))

    def _setupInheritedAdvice(self, addEndUsersAdvice=False):
        """ """
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': '',
              'available_on': '',
              'is_linked_to_previous_row': '0'},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '10',
              'delay_label': '',
              'available_on': '',
              'is_linked_to_previous_row': '1'}, ])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))

        # create 2 items and inheritate from an advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers((self.vendors_uid, '{0}__rowid__unique_id_123'.format(self.developers_uid)))
        item1.updateLocalRoles()
        self.changeUser('pmAdviser1')
        vendors_advice = createContentInContainer(
            item1,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmReviewer2')
        developers_advice = createContentInContainer(
            item1,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': RichTextValue(u'My comment')})
        if addEndUsersAdvice:
            self._setupEndUsersPowerAdvisers()
            self.changeUser('pmAdviser1')
            item1.updateLocalRoles()
            endusers_advice = createContentInContainer(
                item1,
                'meetingadvice',
                **{'advice_group': self.endUsers_uid,
                   'advice_type': u'positive',
                   'advice_hide_during_redaction': False,
                   'advice_comment': RichTextValue(u'My comment')})

        # link items and inherit
        self.changeUser('pmCreator1')
        item2 = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        res = (item1, item2, vendors_advice, developers_advice)
        if addEndUsersAdvice:
            res = res + (endusers_advice, )
        return res

    def _setupEndUsersPowerAdvisers(self):
        """ """
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        selected_orgs = list(api.portal.get_registry_record(ORGANIZATIONS_REGISTRY))
        selected_orgs.append(self.endUsers_uid)
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, selected_orgs)
        self._addPrincipalToGroup('pmAdviser1', '{0}_advisers'.format(self.endUsers_uid))
        cfg.setSelectableAdvisers(cfg.getSelectableAdvisers() + (self.endUsers_uid, ))
        cfg.setPowerAdvisersGroups((self.endUsers_uid, ))

    def test_pm_InheritedAdviceNotAskedAdvice(self):
        """Check that not_asked advices are inherited as well."""
        item1, item2, vendors_advice, developers_advice, enduser_advice = \
            self._setupInheritedAdvice(addEndUsersAdvice=True)
        # enable endUsers group and add advice to it
        self.changeUser('pmCreator1')
        item3 = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(len(item3.adviceIndex), 3)
        self.assertTrue(item3.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.endUsers_uid]['inherited'])
        # after an additional _updateAdvices, infos are still correct
        item3.updateLocalRoles()
        self.assertEqual(len(item3.adviceIndex), 3)
        self.assertTrue(item3.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.endUsers_uid]['inherited'])

    def test_pm_InheritedAdviceAccesses(self):
        """While an advice is marked as 'inherited', it will show another advice
           coming from another item, in this case, read access to current item are same as
           usual but advisers of the inherited advice will never be able to add/edit it."""
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        self.assertTrue(item2.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item2.adviceIndex[self.developers_uid]['inherited'])
        # advisers of vendors are able to see item2 but not able to add advice
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))
        # advices-icons view is correctly displayed
        self.assertTrue(item1.restrictedTraverse('advices-icons')())
        self.assertTrue(item2.restrictedTraverse('advices-icons')())
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))
        self.assertTrue(item1.restrictedTraverse('advices-icons')())
        self.assertTrue(item2.restrictedTraverse('advices-icons')())

        # not addable
        self.assertFalse(item2.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertFalse(item2.adviceIndex[self.developers_uid]['advice_addable'])

        # delay for delay aware advices are not started
        # delay aware
        self.assertTrue(item2.adviceIndex[self.developers_uid]['delay'])
        # not started
        self.assertIsNone(item2.adviceIndex[self.developers_uid]['delay_started_on'])

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
        self.assertEqual(item.getAdviceDataFor(item), {})

    def test_pm_GetAdviceDataForAdviceHiddenDuringRedaction(self):
        '''Test the getAdviceDataFor method p_hide_advices_under_redaction parameter.'''
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(['itemcreated', ])
        cfg.setItemAdviceEditStates(['itemcreated', ])
        cfg.setItemAdviceViewStates(['itemcreated', ])
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.vendors_uid, )
        }
        item = self.create('MeetingItem', **data)
        # give advice
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'positive',
                                             'advice_hide_during_redaction': False,
                                             'advice_comment': RichTextValue(u'My comment'),
                                             'advice_observations': RichTextValue(u'My observations'), })

        # if advice is not hidden, advisers as well as any other user may access advice comment
        advice_data = item.getAdviceDataFor(item, adviser_uid=self.vendors_uid)
        self.assertEqual(advice_data['type'], 'positive')
        self.assertEqual(advice_data['type_translated'], u'Positive')
        self.assertEqual(advice_data['comment'], 'My comment')
        self.assertEqual(advice_data['observations'], 'My observations')
        self.changeUser('pmCreator1')
        advice_data = item.getAdviceDataFor(item, adviser_uid=self.vendors_uid)
        self.assertEqual(advice_data['type'], 'positive')
        self.assertEqual(advice_data['type_translated'], u'Positive')
        self.assertEqual(advice_data['comment'], 'My comment')
        self.assertEqual(advice_data['observations'], 'My observations')

        # hide advice
        self.changeUser('pmReviewer2')
        changeView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeView()
        self.assertTrue(advice.advice_hide_during_redaction is True)
        # by default, hide_advices_under_redaction=True, it hides advice_type and comment
        # access by adviser
        # hidden data
        hidden_advice_data = item.getAdviceDataFor(
            item, adviser_uid=self.vendors_uid, show_hidden_advice_data_to_group_advisers=False)
        self.assertEqual(hidden_advice_data['type'], 'hidden_during_redaction')
        self.assertEqual(hidden_advice_data['type_translated'], u'Hidden during redaction')
        hidden_help_msg = translate(
            'advice_hidden_during_redaction_help',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(hidden_advice_data['comment'], hidden_help_msg)
        self.assertEqual(hidden_advice_data['observations'], hidden_help_msg)
        # access by adviser
        # shown data
        shown_advice_data = item.getAdviceDataFor(item, adviser_uid=self.vendors_uid)
        self.assertEqual(shown_advice_data['type'], 'positive')
        self.assertEqual(shown_advice_data['type_translated'], u'Positive')
        self.assertEqual(shown_advice_data['comment'], 'My comment')
        self.assertEqual(shown_advice_data['observations'], 'My observations')

        # access by non adviser
        # hidden data
        self.changeUser(item.Creator())
        hidden_advice_data = item.getAdviceDataFor(item, adviser_uid=self.vendors_uid)
        self.assertEqual(hidden_advice_data['type'], 'hidden_during_redaction')
        self.assertEqual(hidden_advice_data['type_translated'], u'Hidden during redaction')
        self.assertEqual(hidden_advice_data['comment'], hidden_help_msg)
        self.assertEqual(hidden_advice_data['observations'], hidden_help_msg)
        # access by non adviser
        # shown data
        shown_advice_data = item.getAdviceDataFor(
            item, adviser_uid=self.vendors_uid, hide_advices_under_redaction=False)
        self.assertEqual(shown_advice_data['type'], 'positive')
        self.assertEqual(shown_advice_data['type_translated'], u'Positive')
        self.assertEqual(shown_advice_data['comment'], 'My comment')
        self.assertEqual(shown_advice_data['observations'], 'My observations')

        # when advice is considered not_given because hidden during redaction, data is correct
        # hidden data
        self.validateItem(item)
        hidden_advice_data = item.getAdviceDataFor(item, adviser_uid=self.vendors_uid)
        self.assertEqual(hidden_advice_data['type'], 'considered_not_given_hidden_during_redaction')
        self.assertEqual(hidden_advice_data['type_translated'], u'Considered not given because hidden during redaction')
        considered_not_given_msg = translate(
            'advice_hidden_during_redaction_considered_not_given_help',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(hidden_advice_data['comment'], considered_not_given_msg)
        self.assertEqual(hidden_advice_data['observations'], considered_not_given_msg)

    def test_pm_GetAdviceDataForInheritedAdvice(self):
        '''Test the getAdviceDataFor method when the advice is inherited.'''
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        # item1 and item2 have same values except that inherited advice
        # have a 'adviceHolder' and is 'inherited', we patch item1 data to compare
        item1VendorsData = item1.getAdviceDataFor(item1, self.vendors_uid).copy()
        self.assertIsNone(item1VendorsData.get('adviceHolder'))
        self.assertFalse(item1VendorsData['inherited'])
        item1VendorsData['adviceHolder'] = item1
        item1VendorsData['inherited'] = True
        item1DevData = item1.getAdviceDataFor(item1, self.developers_uid).copy()
        self.assertIsNone(item1DevData.get('adviceHolder'))
        self.assertFalse(item1DevData['inherited'])
        item1DevData['adviceHolder'] = item1
        item1DevData['inherited'] = True
        item2VendorsData = item2.getAdviceDataFor(item2, self.vendors_uid).copy()
        item2DevData = item2.getAdviceDataFor(item2, self.developers_uid).copy()
        self.assertEqual(item1VendorsData, item2VendorsData)
        self.assertEqual(item1DevData, item2DevData)
        # adviceIndex is not impacted
        self.assertFalse('adviceHolder' in item1.adviceIndex)
        self.assertFalse('adviceHolder' in item2.adviceIndex.values())
        self.assertFalse('adviceHolder' in item1.adviceIndex)
        self.assertFalse('adviceHolder' in item2.adviceIndex.values())

    def test_pm_GetInheritedAdviceInfo(self):
        '''MeetingItem.getInheritedAdviceInfo will return advice info of original
           advice when inherit from.  Advice inheritance may be multiple as long as
           original advice exist, so we may have several chained predecessors.'''
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
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
        item1WithoutAdvice.setOptionalAdvisers(
            (self.vendors_uid, '{0}__rowid__unique_id_123'.format(self.developers_uid)))
        item1WithoutAdvice._update_after_edit()
        self.assertIsNone(item1WithoutAdvice.getInheritedAdviceInfo(self.vendors_uid))
        self.assertIsNone(item1WithoutAdvice.getInheritedAdviceInfo(self.developers_uid))

        # predecessor does not have given advices
        # but a not given advice is also inherited and may no more be given on new item
        item2WithAdvices = item1WithoutAdvice.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.changeUser('pmReviewer2')
        # may not add advice on item2WithAdvices
        self.assertFalse(item2WithAdvices.adviceIndex[self.developers_uid]['advice_addable'])
        self.assertFalse(item2WithAdvices.adviceIndex[self.vendors_uid]['advice_addable'])
        # add 'vendors' advice on item1WithoutAdvice
        createContentInContainer(item1WithoutAdvice,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.assertTrue(item2WithAdvices.getInheritedAdviceInfo(self.vendors_uid))
        self.assertTrue(item2WithAdvices.getInheritedAdviceInfo(self.developers_uid))

        # direct predecessor holds advices
        self.changeUser('pmCreator1')
        item3DirectPredecessor = item2WithAdvices.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        # we get adviceInfos + 'adviceHolder'
        inheritedItem3AdviceInfos = item3DirectPredecessor.getInheritedAdviceInfo(self.vendors_uid)
        self.assertEqual(inheritedItem3AdviceInfos['adviceHolder'], item1WithoutAdvice)
        inheritedItem3AdviceInfos.pop('adviceHolder')
        self.assertEqual(inheritedItem3AdviceInfos, item1WithoutAdvice.adviceIndex[self.vendors_uid])

        # now tries with a chain of predecessors, new item predecessor holding advice
        # is not the direct predecessor, we have one item in between
        item4ChainedPredecessor = item3DirectPredecessor.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        # vendors
        inheritedItem4VendorsAdviceInfos = item4ChainedPredecessor.getInheritedAdviceInfo(self.vendors_uid)
        self.assertEqual(inheritedItem4VendorsAdviceInfos['adviceHolder'], item1WithoutAdvice)
        inheritedItem4VendorsAdviceInfos.pop('adviceHolder')
        self.assertEqual(inheritedItem4VendorsAdviceInfos, item1WithoutAdvice.adviceIndex[self.vendors_uid])
        # developers
        inheritedItem4DevAdviceInfos = item4ChainedPredecessor.getInheritedAdviceInfo(self.developers_uid)
        self.assertEqual(inheritedItem4DevAdviceInfos['adviceHolder'], item1WithoutAdvice)
        inheritedItem4DevAdviceInfos.pop('adviceHolder')
        self.assertEqual(inheritedItem4DevAdviceInfos, item1WithoutAdvice.adviceIndex[self.developers_uid])

    def test_pm_InheritedAdviceUpdatedWhenInheritedAdviceChanged(self):
        '''When advices are inherited, it will behave correctly depending on original
           advice.  If original advice changes, item that inherits from it will be updated.'''
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        # add more items so we use multiple chains where predecessors may go
        # into various ways, for now we have :
        # item1 --- item2
        # add following cases :
        # item1 --- item1b --- item1b2
        #     --- item1c
        #     --- item2 --- item3
        item1b = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item1b2 = item1b.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item1c = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item1b.getPredecessor(), item1)
        self.assertEqual(item1b.getInheritedAdviceInfo(self.vendors_uid)['adviceHolder'], item1)
        item3 = item2.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item3.getInheritedAdviceInfo(self.vendors_uid)['adviceHolder'], item1)

        # remove 'vendors' advice of item1, the item1b, item1b2 and item1c are still inheriting it
        self.changeUser('pmReviewer2')
        self.portal.restrictedTraverse('@@delete_givenuid')(item1.getAdviceObj(self.vendors_uid).UID())
        self.assertTrue(item1b.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item1b.restrictedTraverse('advices-icons')())
        self.assertTrue(item1b2.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item1b2.restrictedTraverse('advices-icons')())
        self.assertTrue(item1c.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item1c.restrictedTraverse('advices-icons')())
        # and still ok for 'developers' advice
        self.assertTrue(item1b.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1b2.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1c.adviceIndex[self.developers_uid]['inherited'])
        # recomputed, advice are not addable on subitems, only on master item
        self.assertTrue(item1.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertFalse(item1b.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertFalse(item1b2.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertFalse(item1c.adviceIndex[self.vendors_uid]['advice_addable'])

    def test_pm_InheritedAdviceUpdatedWhenInheritedPowerAdviserAdviceRemoved(self):
        '''When advices are inherited, if we remove an advice that was given by a
           power adviser, everything continue to work correctly on vrious items.'''
        item1, item2, vendors_advice, developers_advice, enduser_advice = \
            self._setupInheritedAdvice(addEndUsersAdvice=True)
        self.assertTrue(item1.adviceIndex[self.endUsers_uid]['not_asked'])
        self.assertTrue(item2.adviceIndex[self.endUsers_uid]['inherited'])
        self.changeUser('pmAdviser1')
        self.portal.restrictedTraverse('@@delete_givenuid')(item1.getAdviceObj(self.endUsers_uid).UID())
        self.assertFalse(self.endUsers_uid in item2.adviceIndex)

    def test_pm_InheritedAdviceAddedAsPowerAdviserSentToOtherMCUsingDelayAwareAdvice(self):
        '''When advices are inherited, if an advice was given by a power adviser on item of
           MeetingConfig A and is sent to a MeetingConfig B for which a delay aware advice
           is configured for same adviser as power adviser of MeetingConfig A, everything works
           as expected and the inherited advice is shown correctly.'''
        cfg = self.meetingConfig
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'), ))
        cfg.setPowerAdvisersGroups((self.developers_uid, ))
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated')))
        self._setPowerObserverStates(states=(self._stateMappingFor('itemcreated'), ))
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg2.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': 'python:True',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])

        cfg.setContentsKeptOnSentToOtherMC(('advices', ))
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item1.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        # give advice
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        # send item to cfg2, this will keep power adviser advice instead asking delay aware advice
        item2 = item1.cloneToOtherMeetingConfig(cfg2Id)
        self.assertTrue(item2.adviceIndex[self.developers_uid]['inherited'])
        self.assertEqual(item2.adviceIndex[self.developers_uid]['delay'], '')
        # advice infos are displayed correctly on item
        self.assertTrue(
            item2.restrictedTraverse('@@advices-icons')())
        self.assertTrue(
            item2.restrictedTraverse('@@advices-icons-infos')(
                adviceType='positive'))
        # following updateLocalRoles are correct
        item2.updateLocalRoles()
        item2._update_after_edit()
        self.assertTrue(
            item2.restrictedTraverse('@@advices-icons')())
        self.assertTrue(
            item2.restrictedTraverse('@@advices-icons-infos')(
                adviceType='positive'))

    def test_pm_InheritedAdviceUpdatedWhenInheritedAdviceNoMoreAskedOnOriginalItem(self):
        '''When advices are inherited, it will behave correctly if we remove the asked advice
           from original item ('not_given' advice that was inherited).'''
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        self.assertTrue(self.developers_uid in item1.adviceIndex)
        self.assertTrue(item2.adviceIndex[self.developers_uid]['inherited'])
        # remove the optional advice asked
        self.deleteAsManager(item1.adviceIndex[self.developers_uid]['advice_uid'])
        item1.setOptionalAdvisers((self.vendors_uid, ))
        item1._update_after_edit()
        # item1 and item2 adviceIndex is correct
        self.assertFalse(self.developers_uid in item1.adviceIndex)
        # as still in optionalAdvisers, developers advice is asked again but no more inherited
        self.assertFalse(item2.adviceIndex[self.developers_uid]['inherited'])
        self.assertEqual(item2.adviceIndex[self.developers_uid]['type'], NOT_GIVEN_ADVICE_VALUE)

    def test_pm_InheritedAdviceUpdatedWhenInheritedItemRemoved(self):
        '''When advices are inherited, it will behave correctly depending on original
           item.  If item the advices are inherited from is removed, advices are updated.'''
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        # add more items so we use multiple chains where predecessors may go
        # into various ways, for now we have :
        # item1 --- item2
        # add following cases :
        # item1 --- item1b --- item1b2
        #     --- item1c
        #     --- item2 --- item3 --- item4
        item1b = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item1b2 = item1b.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item1c = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item1b.getPredecessor(), item1)
        self.assertEqual(item1b.getInheritedAdviceInfo(self.vendors_uid)['adviceHolder'], item1)
        item3 = item2.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item3.getInheritedAdviceInfo(self.vendors_uid)['adviceHolder'], item1)
        # item4 will inherits from both 'developers' and 'vendors' but
        # change this to only keep the 'vendors' advice
        item4 = item2.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item4.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid), ))
        del item4.adviceIndex[self.vendors_uid]
        item4.updateLocalRoles()
        self.assertFalse(self.vendors_uid in item4.adviceIndex)
        self.assertEqual(item4.getInheritedAdviceInfo(self.developers_uid)['adviceHolder'], item1)

        # remove item2, chain of predecessors is broken to item3 and item4,
        # these items will not inherit of any advice anymore
        self.assertTrue(item3.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item3.restrictedTraverse('advices-icons')())
        self.portal.restrictedTraverse('@@delete_givenuid')(item2.UID())
        self.assertFalse(item3.adviceIndex[self.vendors_uid]['inherited'])
        self.assertFalse(item3.adviceIndex[self.developers_uid]['inherited'])
        self.assertFalse(item4.adviceIndex[self.developers_uid]['inherited'])

        # recomputed, advice is addable, ...
        self.assertTrue(item3.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertTrue(item3.adviceIndex[self.developers_uid]['advice_addable'])
        self.assertTrue(item3.restrictedTraverse('advices-icons')())
        self.assertTrue(item4.adviceIndex[self.developers_uid]['advice_addable'])
        self.assertTrue(item4.restrictedTraverse('advices-icons')())
        # but still ok for item1b, item1b2 and item1c
        self.assertTrue(item1b.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item1b.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1b.restrictedTraverse('advices-icons')())
        self.assertTrue(item1b2.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item1b2.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1b2.restrictedTraverse('advices-icons')())
        self.assertTrue(item1c.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item1c.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1c.restrictedTraverse('advices-icons')())

        # now remove 'master' item1 that contains advices
        # every item1x are updated
        self.portal.restrictedTraverse('@@delete_givenuid')(item1.UID())
        self.assertFalse(item1b.adviceIndex[self.vendors_uid]['inherited'])
        self.assertFalse(item1b.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1b.restrictedTraverse('advices-icons')())
        self.assertFalse(item1b2.adviceIndex[self.vendors_uid]['inherited'])
        self.assertFalse(item1b2.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1b2.restrictedTraverse('advices-icons')())
        self.assertFalse(item1c.adviceIndex[self.vendors_uid]['inherited'])
        self.assertFalse(item1c.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item1c.restrictedTraverse('advices-icons')())

    def test_pm_InheritedWithHideNotViewableLinkedItemsTo(self):
        '''Access to inherited item is taking into account MeetingConfig.hideNotViewableLinkedItemsTo.'''
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        cfg = self.meetingConfig
        cfg.setHideNotViewableLinkedItemsTo(('powerobservers', ))
        self._setPowerObserverStates(states=(self._stateMappingFor('itemcreated'), ))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=(self._stateMappingFor('itemcreated'), ))
        self.changeUser('powerobserver1')
        advicesIconsInfosViewItem1 = item1.restrictedTraverse('advices-icons-infos')
        # call view so it initialize every attributes on self
        advicesIconsInfosViewItem1(adviceType='positive')
        advicesIconsInfosViewItem2 = item2.restrictedTraverse('advices-icons-infos')
        # call view so it initialize every attributes on self
        advicesIconsInfosViewItem2(adviceType='positive')
        # shown on the advices-icons
        self.assertTrue(advicesIconsInfosViewItem2.showLinkToInherited(item1))
        self.assertTrue('data-advice_id' in advicesIconsInfosViewItem2(adviceType='positive'))
        # not for adviceHolder
        self.assertFalse('data-advice_id' in advicesIconsInfosViewItem1(adviceType='positive'))

        # do item1 no more visible
        self.proposeItem(item1)
        self.assertFalse(self.hasPermission(View, item1))
        # not more shown on the advices-icons
        self.assertFalse(advicesIconsInfosViewItem2.showLinkToInherited(item1))
        self.assertFalse('data-advice_id' in advicesIconsInfosViewItem2(adviceType='positive'))

    def test_pm_AdviceAuthorDisplayedInAdviceInfos(self):
        """Test that the advice creator is displayed on the @@advices-icons-infos."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('itemcreated'), ])
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'developers'
        data = {
            'title': 'Item to advice',
            'category': 'maintenance',
            'optionalAdvisers': (self.developers_uid, )
        }
        item = self.create('MeetingItem', **data)

        self.changeUser('pmAdviser1')
        # before advice is given, creator is obviously not displayed
        advices_icons_infos = item.restrictedTraverse('@@advices-icons-infos')
        adviser_fullname = '<span>{0}</span>'.format(self.member.getProperty('fullname'))
        self.assertFalse(adviser_fullname in advices_icons_infos(adviceType=u'not_given'))
        createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': RichTextValue(u'My comment')})
        self.assertTrue(adviser_fullname in advices_icons_infos(adviceType=u'positive'))

    def test_pm_RemoveInheritedAdviceByMeetingManager(self):
        """A MeetingManager may remove an inherited advice as long as item is not decided."""
        cfg = self.meetingConfig
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        self.changeUser('pmManager')
        self.assertTrue(item2.adviceIndex[self.vendors_uid]['inherited'])
        # 1) test removing inheritance, make sure 'vendors' not in optionalAdvisers
        item2.setOptionalAdvisers(())
        self.request['form.widgets.advice_uid'] = unicode(self.vendors_uid, 'utf-8')
        self.request['form.widgets.inherited_advice_action'] = 'remove'
        form = item2.restrictedTraverse('@@advice-remove-inheritance').form_instance
        form.update()
        form.handleSaveRemoveAdviceInheritance(form, None)
        self.assertFalse(self.vendors_uid in item2.adviceIndex)

        # 2) test removing inheritance and asking advice locally
        # 2.1) as 'vendors' advice is askable, it works
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        self.changeUser('pmManager')
        self.assertTrue(item2.adviceIndex[self.vendors_uid]['inherited'])
        self.request['form.widgets.inherited_advice_action'] = 'ask_locally'
        form = item2.restrictedTraverse('@@advice-remove-inheritance').form_instance
        form.update()
        form.handleSaveRemoveAdviceInheritance(form, None)
        # asked locally and no more inherited
        self.assertTrue(item2.adviceIndex[self.vendors_uid])
        self.assertFalse(item2.adviceIndex[self.vendors_uid]['inherited'])

        # 2.2) if advice is not askable, advice inheritance is not removed
        cfg.setSelectableAdvisers(())
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        self.changeUser('pmManager')
        self.assertTrue(item2.adviceIndex[self.vendors_uid]['inherited'])
        self.request['form.widgets.inherited_advice_action'] = 'ask_locally'
        form = item2.restrictedTraverse('@@advice-remove-inheritance').form_instance
        form.update()
        form.handleSaveRemoveAdviceInheritance(form, None)
        # nothing was done as advice may not be asked locally
        self.assertTrue(item2.adviceIndex[self.vendors_uid]['inherited'])
        # a portal_message was added
        ask_locally_not_configured_msg = translate(
            'remove_advice_inheritance_ask_locally_not_configured',
            domain='PloneMeeting',
            context=self.request)
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[-1].message, ask_locally_not_configured_msg)

        # MeetingManager may remove inherited advice as long as item is not decided
        item2.setDecision(self.decisionText)
        meeting = self.create('Meeting', date=DateTime('2019/10/10'))
        advice_infos = form._advice_infos(data={'advice_uid': self.vendors_uid})
        self.assertTrue(advice_infos.mayRemoveInheritedAdvice())
        self.presentItem(item2)
        self.assertEqual(item2.queryState(), 'presented')
        self.assertTrue(advice_infos.mayRemoveInheritedAdvice())
        self.closeMeeting(meeting)
        self.assertTrue(item2.queryState() in cfg.getItemDecidedStates())
        self.assertFalse(advice_infos.mayRemoveInheritedAdvice())

    def test_pm_RemoveInheritedAdviceByAdviser(self):
        """An adviser may remove an inherited advice he is adviser for
           if item is in a state where advices may be removed (itemAdviceEditStates)."""
        cfg = self.meetingConfig
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        # pmReviewer2 is adviser for 'vendors'
        self.changeUser('pmReviewer2')
        self.assertTrue(item2.adviceIndex[self.vendors_uid]['inherited'])
        # 1) check 'remove', for now, not removeable because item not in relevant state
        item2.setOptionalAdvisers(())
        self.request['form.widgets.advice_uid'] = unicode(self.vendors_uid, 'utf-8')
        self.request['form.widgets.inherited_advice_action'] = 'remove'
        form = item2.restrictedTraverse('@@advice-remove-inheritance').form_instance
        form.update()
        self.assertRaises(Unauthorized, form.handleSaveRemoveAdviceInheritance, form, None)
        # add item review_state to itemAdviceEditStates
        cfg.setItemAdviceEditStates((item2.queryState(),))
        item2.updateLocalRoles()
        # still raises as removing advice inheritance not enabled in MeetingConfig
        self.assertRaises(Unauthorized, form.handleSaveRemoveAdviceInheritance, form, None)
        cfg.setInheritedAdviceRemoveableByAdviser(True)
        form.handleSaveRemoveAdviceInheritance(form, None)
        self.assertFalse(self.vendors_uid in item2.adviceIndex)
        # in this case, as adviser removed inherited advice, he does not have access anymore to item...
        self.assertFalse(self.hasPermission(View, item2))

    def test_pm_IndexAdvisersInheritedAdvice(self):
        '''Test the indexAdvisers of an inherited advice.  Values have to be same as original advice.'''
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()
        self.assertEqual(indexAdvisers(item1)(), indexAdvisers(item2)())

    def test_pm_ValidateOptionalAdvisersWithInheritedAdvices(self):
        """When an advice is inherited, it will not be possible to select an inherited
           advice on new item using a different row_id.
           We it will not be possible to ask an advice with delay if advice without delay is inherited
           and the other way round."""
        item1, item2, vendors_advice, developers_advice = self._setupInheritedAdvice()

        # when items in same MC, optionalAdvisers field value is kept
        self.assertEqual(item2.getAdviceDataFor(item2, self.vendors_uid)['row_id'], '')
        self.assertEqual(item2.getAdviceDataFor(item2, self.developers_uid)['row_id'], 'unique_id_123')
        self.assertEqual(item1.portal_type, item2.portal_type)
        # as optionalAdvisers are selected by default on copied item
        # it must validate as it, but we can not change an herited advice row_id
        self.failIf(item2.validate_optionalAdvisers(item2.getOptionalAdvisers()))
        self.failIf(item2.validate_optionalAdvisers((self.vendors_uid, )))
        self.failIf(item2.validate_optionalAdvisers(
            ('{0}__rowid__unique_id_123'.format(self.developers_uid), )))
        # fails when changing row_id
        inherited_select_error_msg = translate(
            'can_not_select_optional_adviser_same_group_as_inherited',
            domain='PloneMeeting',
            context=self.portal.REQUEST)
        self.assertEqual(
            item2.validate_optionalAdvisers(('{0}__rowid__unique_id_456'.format(
                self.developers_uid), )),
            inherited_select_error_msg)
        self.assertEqual(
            item2.validate_optionalAdvisers((self.developers_uid, )),
            inherited_select_error_msg)

        # items in different MCs, optionalAdvisers field value is not kept
        # select another row_id, mean non delay aware adviser of a delay aware adviser
        # or another delay for a delay aware adviser
        cfg = self.meetingConfig
        cfg.setContentsKeptOnSentToOtherMC((u'advices', ))
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated')))
        item1.setOtherMeetingConfigsClonableTo((cfg2Id, ))
        item3 = item1.cloneToOtherMeetingConfig(cfg2Id)
        self.assertNotEqual(item1.portal_type, item3.portal_type)
        # advices are kept
        self.assertTrue(item3.adviceIndex)
        # optionalAdvisers are not kept
        self.assertEqual(item3.getOptionalAdvisers(), ())
        # select another optionalAdviser for developers
        # when selecting the non custom advisers developers_uid
        self.assertEqual(item3.validate_optionalAdvisers((self.developers_uid, )),
                         inherited_select_error_msg)
        # when selecting a custom adviser for same adviser
        self.assertEqual(
            item3.validate_optionalAdvisers(('{0}__rowid__unique_id_456'.format(
                self.developers_uid), )),
            inherited_select_error_msg)
        # possible to select a new adviser
        self.failIf(item3.validate_optionalAdvisers((self.endUsers_uid, )))

    def test_pm_ItemModifiedWhenAdviceChanged(self):
        """When an advice is added/modified/removed/attribute changed,
           the item modification date is updated."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('proposed'),
                                     self._stateMappingFor('validated'), ))
        cfg.setEnableAdviceConfidentiality(True)
        cfg.setAdviceConfidentialityDefault(True)

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        self.proposeItem(item)
        # add advice for 'vendors'
        self.changeUser('pmReviewer2')
        item_modified_no_advice = item.modified()
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        item_modified_advice_new = item.modified()
        self.assertNotEqual(item_modified_no_advice, item_modified_advice_new)
        # edit advice
        notify(ObjectModifiedEvent(advice))
        item_modified_advice_modified = item.modified()
        self.assertNotEqual(item_modified_advice_new, item_modified_advice_modified)
        # remove advice
        self.deleteAsManager(advice.UID())
        item_modified_advice_deleted = item.modified()
        self.assertNotEqual(item_modified_advice_modified, item_modified_advice_deleted)
        # toggle confidentiality
        self.changeUser('pmManager')
        item.restrictedTraverse('@@toggle_advice_is_confidential').toggle(
            UID='%s__%s' % (item.UID(), advice.advice_group))
        item_modified_advice_confidential = item.modified()
        self.assertNotEqual(item_modified_advice_deleted, item_modified_advice_confidential)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAdvices, prefix='test_pm_'))
    return suite
