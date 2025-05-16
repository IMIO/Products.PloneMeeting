# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.iconifiedcategory.utils import get_categorized_elements
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import get_user_fullname
from imio.helpers.content import richtextval
from imio.history.interfaces import IImioHistory
from imio.history.utils import getLastAction
from imio.history.utils import getLastWFAction
from os import path
from plone import api
from plone.dexterity.schema import SchemaInvalidatedEvent
from plone.dexterity.utils import createContentInContainer
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.config import AddAdvice
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import ADVICE_STATES_ENDED
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.indexes import indexAdvisers
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import get_advice_alive_states
from Products.PloneMeeting.utils import isModifiedSinceLastVersion
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.statusmessages.interfaces import IStatusMessage
from zope.component import getAdapter
from zope.component import getMultiAdapter
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
            'category': 'development'
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
        self.create('Meeting')
        for item in (item1, item2, item3):
            self.presentItem(item)
        self.assertEqual(item1.query_state(), self._stateMappingFor('presented'))
        self.assertEqual(item2.query_state(), self._stateMappingFor('presented'))
        self.assertEqual(item3.query_state(), self._stateMappingFor('presented'))
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
            'category': 'development'
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
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([self.vendors_uid], []))
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
        form.request.form['advice_comment'] = richtextval(u'My comment')
        form.createAndAdd(form.request.form)
        self.assertEqual(item1.hasAdvices(), True)
        # 'pmReviewer2' has no more addable advice (as already given) but has now an editable advice
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], [self.vendors_uid]))
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
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], [self.vendors_uid]))
        self.failUnless(self.hasPermission(ModifyPortalContent, given_advice))
        # another member of the same _advisers group may also edit the given advice
        self.changeUser('pmManager')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], [self.vendors_uid]))
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
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([self.vendors_uid], []))

        # if advices are disabled in the meetingConfig, getAdvicesGroupsInfosForUser is emtpy
        self.changeUser('admin')
        self.meetingConfig.setUseAdvices(False)
        self.changeUser('pmReviewer2')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([], []))
        self.changeUser('admin')
        self.meetingConfig.setUseAdvices(True)

        # activate advices again and this time remove the fact that we asked the advice
        self.changeUser('pmReviewer2')
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([self.vendors_uid], []))
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
                                             'advice_comment': richtextval(u'My comment')})
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
        self.assertFalse(self.hasPermission(ModifyPortalContent, advice))
        self.assertFalse(self.hasPermission(DeleteObjects, advice))
        self.assertFalse(self.hasPermission(DeleteObjects, annex))

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
                                                        'advice_comment': richtextval(u'My comment')})
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
                                                     'advice_comment': richtextval(u'My comment')})
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
            'category': 'development',
            'optionalAdvisers': (self.vendors_uid,)
        }
        item1 = self.create('MeetingItem', **data)
        # check than the adviser can see the item
        self.changeUser('pmReviewer2')
        self.failUnless(self.hasPermission(View, item1))
        self.assertEqual(item1.getAdvicesGroupsInfosForUser(), ([self.vendors_uid], []))
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
            'category': 'development',
            'optionalAdvisers': (self.vendors_uid,)
        }
        item = self.create('MeetingItem', **data)
        self.failIf(item.willInvalidateAdvices())
        self.proposeItem(item)
        # login as adviser and add an advice
        self.changeUser('pmReviewer2')
        self.assertEqual(item.getAdvicesGroupsInfosForUser(), ([self.vendors_uid], []))
        # give an advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
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
        item.setFieldFromAjax('description', item.getDecision() + '<p>Another new line</p>')
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
        # advice does not exist anymore and has been correctly unindexed
        self.assertEqual(len(self.catalog(path="/".join(item.getPhysicalPath()))), 1)
        # given the advice again so we can check other case where advices are invalidated
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
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
                                    'advice_comment': richtextval(u'My comment')})
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
                                    'advice_comment': richtextval(u'My comment')})
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
        # an advice can be given or edited when an item is 'proposed'
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((
            self.developers_uid,
            '{0}__rowid__unique_id_123'.format(self.vendors_uid), ))
        item.update_local_roles()
        # no advice to give as item is 'itemcreated'
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['{0}_advice_not_giveable'.format(self.developers_uid),
                 '{0}_advice_not_giveable__not_given'.format(self.developers_uid),
                 '{0}_advice_not_giveable__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_not_giveable__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'delay__{0}_advice_not_giveable'.format(self.vendors_uid),
                 'delay__{0}_advice_not_giveable__not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_giveable__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_not_giveable__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(
                    self.developers_uid)])
        )
        self.proposeItem(item)
        item.reindexObject()
        self.changeUser('pmAdviser1')
        # now advice are giveable but not given
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['{0}_advice_not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(
                    self.developers_uid)]))
        itemUID = item.UID()
        brains = self.catalog(
            indexAdvisers='{0}_advice_not_given'.format(self.developers_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        brains = self.catalog(indexAdvisers='delay_row_id__unique_id_123')
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        # create the advice
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        # now that an advice has been given for the developers group, the indexAdvisers has been updated
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_under_edit'.format(self.developers_uid),
                 u'{0}_advice_under_edit__positive'.format(self.developers_uid),
                 '{0}_advice_under_edit__positive__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_under_edit__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'not_given',
                 u'positive',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 u'real_org_uid__{0}__positive'.format(self.developers_uid),
                 'real_org_uid__{0}__positive__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(
                    self.developers_uid)])
        )
        brains = self.catalog(indexAdvisers='{0}_advice_under_edit'.format(self.developers_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)

        # turn advice to hidden during redaction
        changeHiddenDuringRedactionView = advice.restrictedTraverse(
            '@@change-advice-hidden-during-redaction')
        changeHiddenDuringRedactionView()
        self.assertTrue(advice.advice_hide_during_redaction)
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_hidden_during_redaction'.format(self.developers_uid),
                 '{0}_advice_hidden_during_redaction__hidden_during_redaction'.format(
                    self.developers_uid),
                 '{0}_advice_hidden_during_redaction__hidden_during_redaction'
                    '__userid__entireadvisersgroup'.format(self.developers_uid),
                 '{0}_advice_hidden_during_redaction__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_under_edit'.format(self.developers_uid),
                 '{0}_advice_under_edit__hidden_during_redaction'.format(self.developers_uid),
                 '{0}_advice_under_edit__hidden_during_redaction__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_under_edit__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'hidden_during_redaction',
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__hidden_during_redaction'.format(self.developers_uid),
                 'real_org_uid__{0}__hidden_during_redaction__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(self.developers_uid)])
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
            sorted([
                'considered_not_given_hidden_during_redaction',
                'delay__{0}_advice_not_giveable'.format(self.vendors_uid),
                'delay__{0}_advice_not_giveable__not_given'.format(self.vendors_uid),
                'delay__{0}_advice_not_giveable__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                'delay__{0}_advice_not_giveable__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                'delay_row_id__unique_id_123',
                'delay_row_id__unique_id_123__not_given',
                'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                '{0}_advice_given'.format(self.developers_uid),
                '{0}_advice_given__considered_not_given_hidden_during_redaction'.format(
                    self.developers_uid),
                '{0}_advice_given__considered_not_given_hidden_during_redaction'
                '__userid__entireadvisersgroup'.format(self.developers_uid),
                '{0}_advice_given__userid__entireadvisersgroup'.format(self.developers_uid),
                'not_given',
                'real_org_uid__{0}'.format(self.developers_uid),
                'real_org_uid__{0}__considered_not_given_hidden_during_redaction'.format(
                    self.developers_uid),
                'real_org_uid__{0}__considered_not_given_hidden_during_redaction'
                '__userid__entireadvisersgroup'.format(self.developers_uid),
                'real_org_uid__{0}__userid__entireadvisersgroup'.format(self.developers_uid)])
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
                ['delay__{0}_advice_under_edit'.format(self.vendors_uid),
                 u'delay__{0}_advice_under_edit__positive'.format(self.vendors_uid),
                 'delay__{0}_advice_under_edit__positive__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_under_edit__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 u'delay_row_id__unique_id_123__positive',
                 'delay_row_id__unique_id_123__positive__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'not_given',
                 u'positive',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(
                    self.developers_uid)])
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
                ['delay__{0}_advice_given'.format(self.vendors_uid),
                 u'delay__{0}_advice_given__positive'.format(self.vendors_uid),
                 'delay__{0}_advice_given__positive__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 u'delay_row_id__unique_id_123__positive',
                 'delay_row_id__unique_id_123__positive__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_not_giveable'.format(self.developers_uid),
                 '{0}_advice_not_giveable__not_given'.format(self.developers_uid),
                 '{0}_advice_not_giveable__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_not_giveable__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'not_given',
                 u'positive',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(
                    self.developers_uid)])
        )
        # ask a given advice again
        self.changeUser('pmCreator1')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                [
                    'asked_again',
                    'delay__{0}_advice_given'.format(self.vendors_uid),
                    'delay__{0}_advice_given__asked_again'.format(self.vendors_uid),
                    'delay__{0}_advice_given__asked_again__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_given__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_not_giveable'.format(self.vendors_uid),
                    'delay__{0}_advice_not_giveable__asked_again'.format(self.vendors_uid),
                    'delay__{0}_advice_not_giveable__asked_again__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_not_giveable__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay_row_id__unique_id_123',
                    'delay_row_id__unique_id_123__asked_again',
                    'delay_row_id__unique_id_123__asked_again__userid__entireadvisersgroup',
                    'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                    '{0}_advice_not_giveable'.format(self.developers_uid),
                    '{0}_advice_not_giveable__not_given'.format(self.developers_uid),
                    '{0}_advice_not_giveable__not_given__userid__entireadvisersgroup'.format(
                        self.developers_uid),
                    '{0}_advice_not_giveable__userid__entireadvisersgroup'.format(
                        self.developers_uid),
                    'not_given',
                    'real_org_uid__{0}'.format(self.developers_uid),
                    'real_org_uid__{0}__not_given'.format(self.developers_uid),
                    'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                        self.developers_uid),
                    'real_org_uid__{0}__userid__entireadvisersgroup'.format(self.developers_uid)])
        )
        # put it back to a state where it is editable
        self.proposeItem(item)
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['asked_again',
                 'delay__{0}_advice_asked_again'.format(self.vendors_uid),
                 'delay__{0}_advice_asked_again__asked_again'.format(self.vendors_uid),
                 'delay__{0}_advice_asked_again__asked_again__userid__entireadvisersgroup'.format(
                     self.vendors_uid),
                 'delay__{0}_advice_asked_again__userid__entireadvisersgroup'.format(
                     self.vendors_uid),
                 'delay__{0}_advice_under_edit'.format(self.vendors_uid),
                 'delay__{0}_advice_under_edit__asked_again'.format(self.vendors_uid),
                 'delay__{0}_advice_under_edit__asked_again__userid__entireadvisersgroup'.format(
                     self.vendors_uid),
                 'delay__{0}_advice_under_edit__userid__entireadvisersgroup'.format(
                     self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__asked_again',
                 'delay_row_id__unique_id_123__asked_again__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                     self.developers_uid),
                 '{0}_advice_not_given__userid__entireadvisersgroup'.format(self.developers_uid),
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                     self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(self.developers_uid)])
        )
        # delete the advice as Manager as it was historized
        self.changeUser('siteadmin')
        item.restrictedTraverse('@@delete_givenuid')(advice.UID())
        self.changeUser('pmAdviser1')
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay__{0}_advice_not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(self.developers_uid)])
        )
        # the index in the portal_catalog is updated too
        brains = self.catalog(
            indexAdvisers='delay__{0}_advice_not_given'.format(self.vendors_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        brains = self.catalog(
            indexAdvisers='{0}_advice_not_given'.format(self.developers_uid))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, itemUID)
        # if a delay-aware advice delay is exceeded, it is indexed with an ending '2'
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2012, 01, 01)
        item.update_local_roles()
        self.assertEqual(
            sorted(indexAdvisers.callable(item)),
            sorted(
                ['delay__{0}_advice_delay_exceeded'.format(self.vendors_uid),
                 'delay__{0}_advice_delay_exceeded__not_given'.format(self.vendors_uid),
                 'delay__{0}_advice_delay_exceeded__not_given__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay__{0}_advice_delay_exceeded__userid__entireadvisersgroup'.format(
                    self.vendors_uid),
                 'delay_row_id__unique_id_123',
                 'delay_row_id__unique_id_123__not_given',
                 'delay_row_id__unique_id_123__not_given__userid__entireadvisersgroup',
                 'delay_row_id__unique_id_123__userid__entireadvisersgroup',
                 '{0}_advice_not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given'.format(self.developers_uid),
                 '{0}_advice_not_given__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 '{0}_advice_not_given__userid__entireadvisersgroup'.format(self.developers_uid),
                 'not_given',
                 'real_org_uid__{0}'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given'.format(self.developers_uid),
                 'real_org_uid__{0}__not_given__userid__entireadvisersgroup'.format(
                    self.developers_uid),
                 'real_org_uid__{0}__userid__entireadvisersgroup'.format(self.developers_uid)])
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
        item1.update_local_roles()
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers((self.developers_uid, ))
        item2.update_local_roles()
        item3 = self.create('MeetingItem')
        item3.setOptionalAdvisers(())
        item3.update_local_roles()

        # query not_given advices
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='not_given')]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
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
                                    'advice_comment': richtextval(u'My comment')})
        # query not given and positive advices
        self.changeUser('pmCreator1')
        # item1 still have vendors advice not given
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='not_given')]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['not_given', 'positive'])]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__not_given'.format(self.developers_uid))]),
            set([item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__positive'.format(self.developers_uid))]),
            set([item1.UID()]))
        self.assertEqual(
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
                                    'advice_comment': richtextval(u'My comment')})
        # query not given and positive advices
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['not_given'])]),
            set([item1.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['positive'])]),
            set([item1.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers=['negative'])]),
            set([item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}'.format(self.developers_uid))]),
            set([item1.UID(), item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__negative'.format(self.developers_uid))]),
            set([item2.UID()]))
        self.assertEqual(
            set([brain.UID for brain in self.catalog(
                indexAdvisers='real_org_uid__{0}__positive'.format(self.developers_uid))]),
            set([item1.UID()]))
        self.assertEqual(
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

        # now make sure an adviser of 'vendors' may add his advice and.update_local_roles
        # in MeetingItem._updateAdvices, this is why we call getAutomaticAdvisersData
        # with api.env.adopt_roles(['Reader', ])
        self.proposeItem(item)
        item.update_local_roles()
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.changeUser('pmReviewer2')
        item.update_local_roles()
        # 'vendors' is still in adviceIndex, the TAL expr could be evaluated correctly
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.assertEqual(item.getAdvicesGroupsInfosForUser(),
                         ([self.vendors_uid], []))
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})

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
        cfg = self.meetingConfig
        cfg.setCustomAdvisers([{'row_id': 'unique_id_123',
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
        self.assertFalse(item.adviceIndex[self.vendors_uid]['optional'])
        self.assertEqual(item.getAutomaticAdvisersData()[0]['org_uid'], self.vendors_uid)
        # now give the advice
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        item.setBudgetRelated(False)
        item._update_after_edit()
        # the automatic advice is still there even if no more returned by getAutomaticAdvisersData
        self.assertTrue(self.vendors_uid in item.adviceIndex)
        self.assertFalse(item.adviceIndex[self.vendors_uid]['optional'])
        self.assertFalse(item.getAutomaticAdvisersData())

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
                [{'delay': '',
                  'delay_left_alert': '',
                  'delay_label': '',
                  'gives_auto_advice_on_help_message': '',
                  'is_delay_calendar_days': False,
                  'org_uid': self.developers_uid,
                  'org_title': u'Developers',
                  'row_id': 'unique_id_456',
                  'userids': []}])
        )
        # define one condition for which the date is > than current item CreationDate
        futureDate = DateTime() + 1
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': futureDate.strftime('%Y/%m/%d'),
              'delay': '',
              'delay_left_alert': '',
              'delay_label': '',
              'userids': []}, ])
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
              'delay_label': '',
              'userids': []}, ])
        self.assertEqual(item.getAutomaticAdvisersData(),
                         [{'delay': '',
                           'delay_left_alert': '',
                           'delay_label': '',
                           'gives_auto_advice_on_help_message': '',
                           'is_delay_calendar_days': False,
                           'org_uid': self.developers_uid,
                           'org_title': u'Developers',
                           'row_id': 'unique_id_123',
                           'userids': []}])
        # now define a 'for_item_created_until' that is in the past
        # relative to the item created date
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': 'not:item/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '2013/01/01',
              'is_delay_calendar_days': '0',
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
                                             'advice_comment': richtextval(u'My comment')})
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
                                             'advice_comment': richtextval(u'My comment')})
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
                                             'advice_comment': richtextval(u'My comment')})
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
            'category': 'development'
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
        self.assertEqual(item.query_state(), self._stateMappingFor('validated'))
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
        self.create('Meeting')
        saved_developers_start_date = item.adviceIndex[self.developers_uid]['delay_started_on']
        saved_vendors_start_date = item.adviceIndex[self.vendors_uid]['delay_started_on']
        self.presentItem(item)
        self.assertEqual(item.query_state(), self._stateMappingFor('presented'))
        self.assertEqual(item.adviceIndex[self.developers_uid]['delay_started_on'], saved_developers_start_date)
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_started_on'], saved_vendors_start_date)
        # the 'delay_stopped_on' is now set on the delay-aware advice
        self.assertTrue(isinstance(item.adviceIndex[self.developers_uid]['delay_stopped_on'], datetime))
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_stopped_on'] is None)
        # if we excute the transition that will reinitialize dates, it is 'backToItemCreated'
        self.assertEqual(cfg.getTransitionsReinitializingDelays(),
                         (self._transitionMappingFor('backToItemCreated'), ))
        self.backToState(item, self._stateMappingFor('itemcreated'))
        self.assertEqual(item.query_state(), self._stateMappingFor('itemcreated'))
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
        item.update_local_roles()
        # if delay is negative, we show complete delay
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'], 5)
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['delay_status'], 'timed_out')
        self.assertFalse(self.hasPermission(AddAdvice, item))
        # recover delay, add the advice and check the 'edit' behaviour
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now()
        item.update_local_roles()
        self.assertTrue(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] > 0)
        self.assertTrue(self.hasPermission(AddAdvice, item))
        # add the advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_comment': richtextval(u'My comment')})
        self.assertEqual(item.adviceIndex[self.vendors_uid]['row_id'], 'unique_id_123')
        # advice is editable as delay is not exceeded
        self.assertTrue(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] > 0)
        self.assertTrue(self.hasPermission(ModifyPortalContent, advice))
        # now make sure the advice is no more editable when delay is exceeded
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2012, 1, 1)
        item.update_local_roles()
        # when delay is exceeded, left_delay is complete delay so we show it in red
        # we do not show the exceeded delay because it could be very large (-654?)
        # and represent nothing...
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'], 5)
        # 'delay_status' is 'timed_out'
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['delay_status'], 'timed_out')
        self.assertFalse(self.hasPermission(ModifyPortalContent, advice))
        self.changeUser('pmReviewer1')
        changeView = advice.restrictedTraverse('@@change-advice-asked-again')
        changeView()
        # if left_delay < 0, set to delay
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2012, 1, 1)
        item.update_local_roles()
        self.assertEqual(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'], 5)
        # but if still time left, correct delay is displayed
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now() - timedelta(3)
        item.update_local_roles()
        # depending on when test is launched
        self.assertTrue(item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] > 0 and
                        item.getDelayInfosForAdvice(self.vendors_uid)['left_delay'] < 5)

    def test_pm_OrgDefinedItemAdviceStatesValuesOverridesMeetingConfigValues(self):
        '''Advices are giveable/editable/viewable depending on defined item states on the MeetingConfig,
           these states can be overrided locally for a particular organization so this particluar organization
           will be able to add an advice in different states than one defined globally on the MeetingConfig.'''
        # by default, nothing defined on the organization, the MeetingConfig states are used
        # getItemAdviceStates on a organziation returns values of the meetingConfig
        # if nothing is defined on the organziation
        self.assertFalse(self.vendors.get_item_advice_states())
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
        self.assertEqual(item.query_state(), self._stateMappingFor('proposed'))
        # the advice is giveable by the vendors
        self.changeUser('pmReviewer2')
        self.assertTrue(self.vendors_uid in item.getAdvicesGroupsInfosForUser()[0])
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
        self.assertTrue(self.vendors_uid not in item.getAdvicesGroupsInfosForUser()[0])
        # now validate the item and the advice is giveable
        self.changeUser('pmManager')
        self.validateItem(item)
        self.changeUser('pmReviewer2')
        self.assertEqual(item.query_state(), self._stateMappingFor('validated'))
        self.assertTrue(self.vendors_uid in item.getAdvicesGroupsInfosForUser()[0])

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
        self.assertFalse(isPowerObserverForCfg(cfg))
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
        item.update_local_roles()
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
                                    'advice_comment': richtextval(u'My comment')})

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
        item.update_local_roles()
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
        item.update_local_roles()
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
        self.tool.notifyModified()
        self.assertEqual(self.tool.getNonWorkingDayNumbers(), [6, ])
        item.update_local_roles()
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
        self.tool.notifyModified()
        year, month, day = holiday_changing_delay.split('/')
        self.assertEqual(self.tool.getHolidaysAs_datetime(),
                         [datetime(2012, 5, 6), datetime(int(year), int(month), int(day)), ])
        # this should increase delay of one day, so as original limit_date_9_days
        item.update_local_roles()
        self.assertEqual(limit_date_9_days, item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'])
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'still_time')

        # now add one unavailable day for end of delay
        # for now, limit_date ends day number 2, so wednesday
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'].weekday(), 2)
        self.tool.setDelayUnavailableEndDays(('wed', ))
        # the method getUnavailableWeekDaysNumbers is ram.cached, check that it is correct when changed
        self.tool.notifyModified()
        self.assertEqual(self.tool.getUnavailableWeekDaysNumbers(), [2, ])
        item.update_local_roles()
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
        self.tool.notifyModified()
        # change 'delay_started_on' manually and check that last day, the advice is 'still_giveable'
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now() - timedelta(7)
        item.update_local_roles()
        # we are the last day
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['limit_date'].day, datetime.now().day)
        self.assertEqual(item.adviceIndex[self.vendors_uid]['delay_infos']['delay_status'], 'still_time')
        # one day more and it is not giveable anymore...
        item.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now() - timedelta(8)
        item.update_local_roles()
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

    def test_pm_is_delay_calendar_days(self):
        """Test when is_delay_calendar_days then delay is computed in calendar days."""
        cfg = self.meetingConfig
        # make advice giveable when item is proposed
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'), ))
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': '',
              'is_delay_calendar_days': '0'},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': '',
              'is_delay_calendar_days': '1'}])
        self.changeUser('pmCreator1')
        item = self.create(
            'MeetingItem',
            optionalAdvisers=['{0}__rowid__unique_id_123'.format(self.vendors_uid),
                              '{0}__rowid__unique_id_456'.format(self.developers_uid)])
        vendors_advice_infos = item.adviceIndex.get(self.vendors_uid)
        self.assertFalse(vendors_advice_infos['is_delay_calendar_days'])
        dev_advice_infos = item.adviceIndex.get(self.developers_uid)
        self.assertTrue(dev_advice_infos['is_delay_calendar_days'])
        # both advices have a delay of 10 days but the one computed in calendar days
        # will be shorter because it ignores weekends, holidays, ...
        # same sart, dfferent end
        self.assertEqual(vendors_advice_infos['delay_infos']['delay_started_on_localized'],
                         dev_advice_infos['delay_infos']['delay_started_on_localized'])
        # limit_date is a clear day like datetime.datetime(2025, 4, 28, 23, 59, 59)
        self.assertTrue(vendors_advice_infos['delay_infos']['limit_date'] >
                        dev_advice_infos['delay_infos']['limit_date'])

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
                           'is_delay_calendar_days': '0',
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
                            'is_delay_calendar_days': '0',
                            'available_on': '',
                            'is_linked_to_previous_row': '1'},
                           {'row_id': 'unique_id_789',
                            'org': self.vendors_uid,
                            'gives_auto_advice_on': '',
                            'for_item_created_from': '2012/01/01',
                            'for_item_created_until': '',
                            'delay': '20',
                            'delay_label': '',
                            'is_delay_calendar_days': '1',
                            'available_on': '',
                            'is_linked_to_previous_row': '1'}, ]
        cfg.setCustomAdvisers(customAdvisers)
        # we need to cleanRamCacheFor _findLinkedRowsFor used by listSelectableDelays
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        # the delay may still be edited when the user can edit the item
        # except if it is an automatic advice for wich only MeetingManagers may change delay
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
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
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
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
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # test the 'available_on' behaviour
        self.backToState(item, self._stateMappingFor('proposed'))
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_stopped_on'] is None)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # now define a 'available_on' for third row
        # first step, something that is False
        customAdvisers[2]['available_on'] = 'python:False'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # a wrong TAL expression for 'available_on' does not break anything
        customAdvisers[2]['available_on'] = 'python:here.someUnexistingMethod()'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # second step, something that is True
        customAdvisers[2]['available_on'] = 'python:True'
        cfg.setCustomAdvisers(customAdvisers)
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        # now test the particular expression that makes a custom adviser
        # useable when changing delays but not in other cases
        customAdvisers[2]['available_on'] = "python:item.REQUEST.get('managing_available_delays', False)"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())

        # the mayEdit variable is available in the expression, it is True if current
        # user may edit item, False otherwise
        customAdvisers[2]['available_on'] = "mayEdit"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ('unique_id_789', '20', u'', True)])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())
        customAdvisers[2]['available_on'] = "not:mayEdit"
        cleanRamCacheFor('Products.PloneMeeting.MeetingConfig._findLinkedRowsFor')
        cfg.setCustomAdvisers(customAdvisers)
        self.assertEqual(availableDelaysView.listSelectableDelays(),
                         [('unique_id_456', '10', u'', False), ])
        # access to delay changes history
        self.assertTrue(availableDelaysView._mayAccessDelayChangesHistory())

        # access to delay changes history is only for adviser, proposingGroup and MeetingManagers
        # adviser
        self.changeUser('pmReviewer2')
        self.assertEqual(item.getAdvicesGroupsInfosForUser(),
                         ([self.vendors_uid], []))
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
                           'delay_label': 'h\xc3\xa9h\xc3\xa9',
                           'available_on': '',
                           'is_linked_to_previous_row': '0'},
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '10',
                           'delay_label': 'h\xc3\xa9h\xc3\xa9',
                           'available_on': '',
                           'is_linked_to_previous_row': '1'},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'for_item_created_until': '',
                           'delay': '20',
                           'delay_label': 'h\xc3\xa9h\xc3\xa9',
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
        form = item.restrictedTraverse('@@advice-delay-change-form').form_instance
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
        # check that form is correctly displayed
        form.request['new_delay_row_id'] = u'unique_id_123'
        form.update()
        self.assertTrue(u"(h\xe9h\xe9)" in form.render())

    def test_pm_AdviceProposingGroupComment(self):
        '''Test the view '@@advice_proposing_group_comment_form' form that will
           let editors of the proposingGroup add a comment on an asked advice.'''
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        # make advice addable when item is itemcreated and give access to copyGroups
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'),
                                 self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'),
                                     self._stateMappingFor('proposed'), ))
        cfg.setKeepAccessToItemWhenAdvice("was_giveable")
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((self._stateMappingFor('itemcreated'),
                                     self._stateMappingFor('proposed'), ))
        cfg.setEnableAdviceProposingGroupComment(True)
        # create item and ask advices
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', decision=self.decisionText)
        item.setOptionalAdvisers((self.developers_uid, self.vendors_uid, ))
        item.setCopyGroups((self.vendors_creators, ))
        item._update_after_edit()
        # add comment to developers advice
        comment = u"Proposing group comment héhé"
        self.request['advice_id'] = unicode(self.developers_uid)
        form = item.restrictedTraverse('@@advice_proposing_group_comment_form').form_instance
        self.request.form['form.widgets.advice_uid'] = unicode(self.developers_uid)
        # first set None, it is saved as u""
        self.request.form['form.widgets.proposing_group_comment'] = None
        form.update()
        form.handleSave(form, None)
        self.assertEqual(item.adviceIndex[self.developers_uid]['proposing_group_comment'], u"")
        # now set a real text
        form = item.restrictedTraverse('@@advice_proposing_group_comment_form').form_instance
        self.request['form.widgets.proposing_group_comment'] = comment
        form.update()
        data = form.extractData()[0]
        form.handleSave(form, None)
        self.assertEqual(item.adviceIndex[self.developers_uid]['proposing_group_comment'], comment)

        def _check(mayView=True, mayEdit=False):
            """ """
            form = item.restrictedTraverse('@@advice_proposing_group_comment_form').form_instance
            form._init(data)
            if mayView:
                self.assertTrue(form.mayViewProposingGroupComment())
            else:
                self.assertFalse(form.mayViewProposingGroupComment())
            if mayEdit:
                self.assertTrue(form.mayEditProposingGroupComment())
                self.assertIsNone(form.update())
            else:
                self.assertRaises(Unauthorized, form.update)

        # member of another group may not view comment
        self.changeUser('pmCreator2')
        _check(mayView=False, mayEdit=False)
        # advisers may view comment but not edit it
        self.changeUser('pmAdviser1')
        _check(mayView=True, mayEdit=False)
        # vendors adviser may see item but not comment
        self.changeUser('pmReviewer2')
        _check(mayView=False, mayEdit=False)
        # still editable when item no more editable but advice addable/editable
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        _check(mayView=True, mayEdit=True)
        # no more editable when item no more editable nor advice addable/editable
        self.validateItem(item)
        form = item.restrictedTraverse('@@advice_proposing_group_comment_form').form_instance
        _check(mayView=True, mayEdit=False)
        # still viewable by advisers
        self.changeUser('pmAdviser1')
        _check(mayView=True, mayEdit=False)
        # visible and editable by MeetingManagers
        self.changeUser('pmManager')
        _check(mayView=True, mayEdit=True)
        # but no more when item is decided
        meeting = self.create('Meeting')
        self.presentItem(item)
        _check(mayView=True, mayEdit=True)
        self.closeMeeting(meeting)
        self.assertEqual(item.query_state(), "accepted")
        _check(mayView=True, mayEdit=False)
        # still viewable by proposingGroup and advisers
        self.changeUser('pmCreator1')
        _check(mayView=True, mayEdit=False)
        self.changeUser('pmAdviser1')
        _check(mayView=True, mayEdit=False)

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
          This test alive and ended states consider every states of the workflow
          used for portal_types 'meetingadvice'.
        '''
        adviceWF = self.wfTool.getWorkflowsFor('meetingadvice')
        # we have only one workflow for 'meetingadvice'
        self.assertEqual(len(adviceWF), 1)
        everyStates = adviceWF[0].states.keys()
        statesOfConfig = get_advice_alive_states() + ADVICE_STATES_ENDED
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
                                                        'advice_comment': richtextval(u'My comment')})
        # if powerobserver tries to access the Title of the confidential advice
        # displayed in particular on the advice view, it raises Unauthorized
        self.changeUser('powerobserver1')
        self.assertRaises(Unauthorized, developers_advice.Title)
        advice_view = developers_advice.restrictedTraverse('@@view')
        self.assertRaises(Unauthorized, advice_view)

        # if the adviser is also powerobserver, he may access the advice nevertheless
        self._addPrincipalToGroup('pmAdviser1', '%s_powerobservers' % cfg.getId())
        self.changeUser('pmAdviser1')
        self.assertTrue(advice_view())
        # he may trigger the "Delete with comments" action, and the classic Delete is not available
        rendered_ap = developers_advice.restrictedTraverse('@@actions_panel')()
        self.assertFalse("delete_givenuid" in rendered_ap)
        self.assertTrue("delete_with_comments" in rendered_ap)

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
                                    'advice_comment': richtextval(u'My comment')})
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
            'category': 'development',
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
                                             'advice_comment': richtextval(u'My comment')})
        # 'pmReviewer2', as adviser, is able to toggle advice_hide_during_redaction
        self.assertFalse(advice.advice_hide_during_redaction)
        self.assertFalse(item.adviceIndex[self.vendors_uid]['hidden_during_redaction'])
        # historized
        history_name = 'advice_hide_during_redaction_history'
        self.assertFalse(base_hasattr(advice, history_name))
        changeView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeView()
        self.assertEqual(getattr(advice, history_name)[0]['action'], 'to_hidden_during_redaction_action')
        self.assertTrue(advice.advice_hide_during_redaction)
        self.assertTrue(item.adviceIndex[self.vendors_uid]['hidden_during_redaction'])
        # when advice is hidden, trying to access the view will raise Unauthorized
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized, advice.restrictedTraverse('view'))
        # back to not hidden
        self.changeUser('pmReviewer2')
        changeView()
        self.assertEqual(getattr(advice, history_name)[0]['action'], 'to_hidden_during_redaction_action')
        self.assertEqual(getattr(advice, history_name)[1]['action'], 'to_not_hidden_during_redaction_action')
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
        # default value of field 'advice_hide_during_redaction' will be True
        cfg.setDefaultAdviceHiddenDuringRedaction(['meetingadvice'])
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'development',
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
                                             'advice_comment': richtextval(u'My comment')})
        changeView = advice.restrictedTraverse('@@change-advice-asked-again')
        # 'asked_again' is always enabled
        self.assertFalse('asked_again' in cfg.getUsedAdviceTypes())
        self.changeUser('pmManager')
        self.assertTrue(item.adapted().mayAskAdviceAgain(advice))

        # advice can not be asked_again if current user may not edit the item
        self.changeUser('pmCreator1')
        self.assertFalse(item.adapted().mayAskAdviceAgain(advice))
        self.assertFalse(item.adapted().mayBackToPreviousAdvice(advice))
        self.assertRaises(Unauthorized, changeView)

        # send advice back to creator so advice may be asked_again
        # never historized
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        self.assertIsNone(getLastAction(adapter))
        self.backToState(item, 'itemcreated')
        # advice was historized
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time1 = last_action['time']
        self.assertTrue(item.adapted().mayAskAdviceAgain(advice))
        self.assertFalse(item.adapted().mayBackToPreviousAdvice(advice))
        # for now 'advice_hide_during_redaction' is False
        self.assertFalse(advice.advice_hide_during_redaction)
        # 'asked_again' term is not in advice_type_vocabulary as it is not selectable manually
        factory = queryUtility(
            IVocabularyFactory,
            u'Products.PloneMeeting.content.advice.advice_type_vocabulary')
        vocab = factory(advice)
        self.assertFalse('asked_again' in vocab)
        # right, ask advice again
        changeView()
        # advice was not historized again because it was not modified
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time1, last_action['time'])
        self.assertEqual(advice.advice_type, 'asked_again')
        # now it is available in vocabulary
        vocab = factory(advice)
        self.assertTrue('asked_again' in vocab)
        # version 0 was saved
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time1, last_action['time'])
        # we may also revert to previous version
        self.assertFalse(item.adapted().mayAskAdviceAgain(advice))
        self.assertTrue(item.adapted().mayBackToPreviousAdvice(advice))
        # when an advice is 'asked_again', the field hidden_during_redaction
        # is set to the default defined in the MeetingConfig
        self.assertTrue('meetingadvice' in cfg.getDefaultAdviceHiddenDuringRedaction())
        # when "asked_again", advice_hide_during_redaction is set to True on edit
        # so for now it is still False
        self.assertFalse(advice.advice_hide_during_redaction)
        changeView()
        # when going back to previous version, advice is not historized
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time2 = last_action['time']
        self.assertEqual(last_action_time1, last_action_time2)
        # old values are set back
        self.assertEqual(advice.advice_type, 'negative')
        self.assertFalse(advice.advice_hide_during_redaction)
        # ok, ask_again and send it again to 'pmReviewer2', he will be able to edit it
        # but before, edit the advice so it is historized again
        notify(ObjectModifiedEvent(advice))
        changeView()
        # this time advice is historized again
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time3 = last_action['time']
        self.assertNotEqual(last_action_time2, last_action_time3)
        self.assertEqual(advice.advice_type, 'asked_again')
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, advice))
        # when editing, the advice_hide_during_redaction is set to True
        advice_edit = advice.restrictedTraverse('@@edit')
        advice_edit.update()
        self.assertEqual(advice_edit.widgets['advice_hide_during_redaction'].value, ['true'])
        # when an advice is 'asked_again', it is not historized twice even
        # if advice was edited in between, an advice 'asked_again' is like 'never given'
        # this will avoid that previous advice of an advice 'asked_again' is also
        # an advice 'asked_again'...
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.backToState(item, 'itemcreated')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time3, last_action['time'])
        # but works after when advice is no more 'asked_again'
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        advice.advice_type = 'positive'
        # editing an advice that is no more asked_again will not set 'advice_hide_during_redaction'
        self.assertFalse(advice.advice_hide_during_redaction)
        advice_edit = advice.restrictedTraverse('@@edit')
        advice_edit.update()
        self.assertEqual(advice_edit.widgets['advice_hide_during_redaction'].value, ['false'])
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.backToState(item, 'itemcreated')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time4 = last_action['time']
        self.assertNotEqual(last_action_time3, last_action_time4)

    def _setUpHistorizedAdvice(self):
        """ """
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('itemcreated')])
        cfg.setItemAdviceEditStates([self._stateMappingFor('itemcreated')])
        cfg.setItemAdviceViewStates([self._stateMappingFor('itemcreated'), self._stateMappingFor('proposed')])
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates([self._stateMappingFor('proposed')])
        self._setPowerObserverStates(states=(self._stateMappingFor('proposed'), ))
        self.changeUser('pmCreator1')
        # create an item and ask the advice of group 'vendors'
        data = {
            'title': 'Item to advice',
            'category': 'development',
            'optionalAdvisers': (self.vendors_uid, self.developers_uid, )
        }
        item = self.create('MeetingItem', **data)
        # give advice
        self.changeUser('pmAdviser1')
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': richtextval(u'My comment')})
        return item, advice

    def test_pm_HistorizedAdviceIsNotDeletable(self):
        """When an advice has been historized (officially given or asked_again,
           so when versions exist), it can not be deleted by the advisers."""
        item, dev_advice = self._setUpHistorizedAdvice()
        # for now advice is deletable
        advices_icons_infos = item.restrictedTraverse('@@advices-icons-infos')
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'positive')
        self.assertTrue(advices_icons_infos.mayDelete(dev_advice))
        # give advice
        self.changeUser('pmReviewer2')
        vendors_advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'negative',
               'advice_hide_during_redaction': False,
               'advice_comment': richtextval(u'My comment')})
        # for now advice is deletable
        advices_icons_infos = item.restrictedTraverse('@@advices-icons-infos')
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'negative')
        self.assertTrue(advices_icons_infos.mayDelete(vendors_advice))

        # ask developers_advice again
        changeView = dev_advice.restrictedTraverse('@@change-advice-asked-again')
        self.changeUser('pmCreator1')
        changeView()
        self.assertEqual(dev_advice.advice_type, 'asked_again')
        # advice asker may obviously not delete it
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'asked_again')
        self.assertFalse(advices_icons_infos.mayDelete(dev_advice))
        # and advisers neither
        self.changeUser('pmAdviser1')
        self.assertFalse(advices_icons_infos.mayDelete(dev_advice))
        # even when advice_type is changed
        dev_advice.advice_type = 'positive'
        notify(ObjectModifiedEvent(dev_advice))
        advices_icons_infos(adviceType=u'positive')
        self.assertFalse(advices_icons_infos.mayDelete(dev_advice))

        # when an advice is officially given, it is historized so advice is no more deletable
        self.proposeItem(item)
        self.assertFalse(advices_icons_infos.mayDelete(dev_advice))
        self.changeUser('pmReviewer2')
        # some values are initialized when view is called (__call__)
        advices_icons_infos(adviceType=u'negative')
        self.assertFalse(advices_icons_infos.mayDelete(vendors_advice))

    def test_pm_AdviceHistorizedPreviewAccess(self):
        """By default only (Meeting)Managers may access an historized advice preview."""

        def _check(viewable=True):
            """ """
            advice_preview = advice.restrictedTraverse('@@history-event-preview')(last_action)
            if viewable:
                self.assertTrue("@@advice_given_history_view" in advice_preview)
                self.assertTrue(advice.restrictedTraverse('@@advice_given_history_view')(
                    float(last_action['time'])))
            else:
                self.assertFalse("@@advice_given_history_view" in advice_preview)
                self.assertRaises(
                    Unauthorized,
                    advice.restrictedTraverse('@@advice_given_history_view'),
                    float(last_action['time']))

        item, advice = self._setUpHistorizedAdvice()
        # historize advice
        self.changeUser('pmCreator1')
        item.setCopyGroups((self.vendors_observers, ))
        self.proposeItem(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertTrue(last_action)
        # viewable for MeetingManagers
        self.changeUser('pmManager')
        _check()
        # viewable for proposingGroup members
        self.changeUser('pmCreator1')
        _check()
        # viewable for the advisers of the asked advice
        self.changeUser('pmAdviser1')
        _check()
        # not viewable for copy groups
        self.changeUser('pmObserver2')
        _check(False)
        # not viewable by powerobservers
        self.changeUser('powerobserver1')
        _check(False)
        # not viewable by other advisers
        self.changeUser('pmReviewer2')
        _check(False)

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
            'category': 'development',
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
                                             'advice_comment': richtextval(u'My comment')})
        # advice is historized when it is given, aka transition giveAdvice has been triggered
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        self.assertIsNone(getLastAction(adapter))
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time1 = last_action['time']
        # first version, item data was historized on it
        self.assertEqual(last_action['item_data'],
                         [{'field_name': 'title', 'field_content': 'Item to advice'},
                          {'field_name': 'description', 'field_content': '<p>Item description</p>'},
                          {'field_name': 'detailedDescription', 'field_content': '<p>Item detailed description</p>'},
                          {'field_name': 'motivation', 'field_content': '<p>Item motivation</p>'},
                          {'field_name': 'decision', 'field_content': '<p>Item decision</p>'}])
        # when giving advice for a second time, if advice is not edited, it is not versioned uselessly
        self.backToState(item, self._stateMappingFor('proposed'))
        self.assertEqual(advice.query_state(), 'advice_under_edit')
        self.validateItem(item)
        self.assertEqual(advice.query_state(), 'advice_given')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time1, last_action['time'])

        # come back to 'proposed' and edit advice
        item.setDecision('<p>Another decision</p>')
        self.backToState(item, self._stateMappingFor('proposed'))
        notify(ObjectModifiedEvent(advice))
        self.validateItem(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertNotEqual(last_action_time1, last_action['time'])
        self.assertEqual(last_action['item_data'],
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
                                             'advice_comment': richtextval(u'My comment')})

        # advice is versioned when it is given, aka transition giveAdvice has been triggered
        self.changeUser('pmReviewer1')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        self.assertIsNone(getLastAction(adapter))
        advice_modified = advice.modified()
        self.assertTrue(isModifiedSinceLastVersion(advice))
        self.validateItem(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        self.assertTrue(getLastAction(adapter))
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
                                             'advice_comment': richtextval(u'My comment')})

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
            'category': 'development',
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
                                             'advice_comment': richtextval(u'My comment')})
        # advice will be versioned if the item is edited
        # this is only the case if cfg.historizeAdviceIfGivenAndItemModified is True
        self.changeUser('siteadmin')
        cfg.setHistorizeAdviceIfGivenAndItemModified(False)
        self.changeUser('pmReviewer1')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        self.assertIsNone(getLastAction(adapter))
        self.request.form['detailedDescription'] = '<p>Item detailed description not active</p>'
        item.processForm()
        self.assertEqual(item.getDetailedDescription(),
                         '<p>Item detailed description not active</p>')
        # it was not versioned because historizeAdviceIfGivenAndItemModified is False
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        self.assertIsNone(getLastAction(adapter))
        # activate and try again
        self.changeUser('siteadmin')
        cfg.setHistorizeAdviceIfGivenAndItemModified(True)
        self.changeUser('pmReviewer1')
        item.processForm()
        # first version, item data was historized on it
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time1 = last_action['time']
        # we have item data before it was modified
        self.assertEqual(last_action['item_data'],
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

        # when editing item a second time, if advice is not edited, it is not historized uselessly
        self.request.form['detailedDescription'] = '<p>Item detailed description edited 2</p>'
        item.processForm({'detailedDescription': '<p>Item detailed description edited 2</p>'})
        self.assertEqual(item.getDetailedDescription(), '<p>Item detailed description edited 2</p>')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time1, last_action['time'])

        # when moving to 'validated', advice is 'adviceGiven', but not historized again
        self.validateItem(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time1, last_action['time'])

        # but it is again if advice is edited
        self.changeUser('pmManager')
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        # validate item, this time advice is historized again
        self.validateItem(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time2 = last_action['time']
        self.assertNotEqual(last_action_time1, last_action_time2)

        # and once again back to proposed and edit item
        # not versioned because advice was not edited
        self.changeUser('pmManager')
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer1')
        self.request.form['detailedDescription'] = '<p>Item detailed description edited 3</p>'
        item.processForm({'detailedDescription': '<p>Item detailed description edited 3</p>'})
        self.assertEqual(item.getDetailedDescription(), '<p>Item detailed description edited 3</p>')
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time2, last_action['time'])

        # right, back to proposed and use ajax edit
        self.changeUser('pmManager')
        self.backToState(item, self._stateMappingFor('proposed'))
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        item.setFieldFromAjax('detailedDescription', '<p>Item detailed description edited 4</p>')
        self.assertEqual(item.getDetailedDescription(), '<p>Item detailed description edited 4</p>')
        # advice was historized again
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        last_action_time3 = last_action['time']
        self.assertNotEqual(last_action_time2, last_action_time3)
        # we have item data before it was modified
        self.assertEqual(last_action['item_data'],
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

        # advice are no more historized when annex is added/removed
        annex = self.addAnnex(item)
        # was already historized so no more
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time3, last_action['time'])
        # right edit the advice and remove the annex
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        self.deleteAsManager(annex.UID())
        # advice was not historized again
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time3, last_action['time'])
        # edit advice and add a new annex, advice will not be historized
        self.changeUser('pmReviewer2')
        notify(ObjectModifiedEvent(advice))
        self.changeUser('pmReviewer1')
        annex = self.addAnnex(item)
        adapter = getAdapter(advice, IImioHistory, 'advice_given')
        last_action = getLastAction(adapter)
        self.assertEqual(last_action_time3, last_action['time'])

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
                   'advice_comment': richtextval(u'My comment')})
        developers_advice = None
        if 'developers' in give_advices_for:
            self.changeUser('pmAdviser1')
            developers_advice = createContentInContainer(
                item,
                'meetingadvice',
                **{'advice_group': self.developers_uid,
                   'advice_type': u'positive',
                   'advice_hide_during_redaction': False,
                   'advice_comment': richtextval(u'My comment')})
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
        item.update_local_roles()
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
        item.update_local_roles()
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
        item.update_local_roles()
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
        item.update_local_roles()
        self.assertTrue(self.hasPermission(View, item))

        # use MeetingConfig value that is True
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))

        # force disable keep access
        self.changeUser('pmReviewer2')
        self.vendors.keep_access_to_item_when_advice = 'default'
        item.update_local_roles()
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
        item.update_local_roles()
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
                                                     'advice_comment': richtextval(u'My comment')})
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
                                             'advice_comment': richtextval(text)})
        self.assertTrue('1025-400x300.jpg' in advice.objectIds())

        # test using IObjectModifiedEvent event, aka using edit form
        text = '<p>Working external image <img src="%s"/>.</p>' % self.external_image4
        advice.advice_comment = richtextval(text)
        # notify modified
        notify(ObjectModifiedEvent(advice))
        self.assertTrue('1062-600x500.jpg' in advice.objectIds())

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
                                                     'advice_comment': richtextval(u'My comment')})
        self.assertEqual(item.getAdviceObj(self.vendors_uid), vendors_advice)
        self.assertIsNone(item.getAdviceObj(self.developers_uid))

    def _setupInheritedAdvice(self, addEndUsersAdvice=False, addAnnexesToVendorsAdvice=False):
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
        item1.update_local_roles()
        self.changeUser('pmAdviser1')
        vendors_advice = createContentInContainer(
            item1,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': richtextval(u'My comment')})
        if addAnnexesToVendorsAdvice:
            self._enable_annex_config(vendors_advice)
            annexNotConfidential = self.addAnnex(vendors_advice, annexTitle='Annex not confidential')
            annexConfidential = self.addAnnex(vendors_advice, annexTitle='Annex confidential')
            annexConfidential.confidential = True
            notify(ObjectModifiedEvent(annexConfidential))

        self.changeUser('pmReviewer2')
        developers_advice = createContentInContainer(
            item1,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': richtextval(u'My comment')})

        if addEndUsersAdvice:
            self._setupEndUsersPowerAdvisers()
            self.changeUser('pmAdviser1')
            item1.update_local_roles()
            endusers_advice = createContentInContainer(
                item1,
                'meetingadvice',
                **{'advice_group': self.endUsers_uid,
                   'advice_type': u'positive',
                   'advice_hide_during_redaction': False,
                   'advice_comment': richtextval(u'My comment')})

        # link items and inherit
        self.changeUser('pmCreator1')
        item2 = item1.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        res = (item1, item2, vendors_advice, developers_advice)
        if addEndUsersAdvice:
            res += (endusers_advice, )
        if addAnnexesToVendorsAdvice:
            res += (annexConfidential, annexNotConfidential)
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
        # @@display-inherited-item-infos
        display_view = item3.restrictedTraverse('@@display-inherited-item-infos')
        item1_url = item1.absolute_url()
        self.assertTrue(item1_url in display_view(self.developers_uid))
        self.assertTrue(item1_url in display_view(self.vendors_uid))
        self.assertTrue(item1_url in display_view(self.endUsers_uid))
        # after an additional _updateAdvices, infos are still correct
        item3.update_local_roles()
        self.assertEqual(len(item3.adviceIndex), 3)
        self.assertTrue(item3.adviceIndex[self.developers_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.vendors_uid]['inherited'])
        self.assertTrue(item3.adviceIndex[self.endUsers_uid]['inherited'])

    def test_pm_InheritedAdviceAdvisersAccesses(self):
        """When an advice is marked as 'inherited', it will show another advice
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

    def test_pm_InheritedAdviceViewerAccesses(self):
        """When an advice is marked as 'inherited', it will show another advice
           coming from another item, in this case, read access to current item are same as
           usual but viewers of the inherited advice are able to see it and to download annexes."""
        cfg = self.meetingConfig
        item1, item2, vendors_advice, developers_advice, annexConfidential, annexNotConfidential = \
            self._setupInheritedAdvice(addAnnexesToVendorsAdvice=True)
        # check with a power observer only able to see item2
        self.changeUser('siteadmin')
        self._setPowerObserverStates(
            states=(self._stateMappingFor('itemcreated'), ),
            access_on="python: item.UID() == '{0}'".format(item2.UID()))
        item1.update_local_roles()
        item2.update_local_roles()
        self.changeUser("powerobserver1")
        self.assertFalse(self.hasPermission(View, item1))
        self.assertTrue(self.hasPermission(View, item2))
        # advice popup viewable
        # in this case, PUBLISHED is the item
        self.request['PUBLISHED'] = item2
        self.assertTrue(item2.restrictedTraverse('advices-icons')())
        self.assertTrue(item2.restrictedTraverse(
            '@@advices-icons-infos')(adviceType='positive'))
        # advice annexes are downloadable if not confidential
        categorized_elements = get_categorized_elements(vendors_advice)
        self.assertEqual(len(categorized_elements), 1)
        self.assertEqual(categorized_elements[0]['UID'], annexNotConfidential.UID())
        category_uid = categorized_elements[0]['category_uid']
        # in this case, PUBLISHED is the advice and the item is the referer
        self.request['PUBLISHED'] = vendors_advice
        self.request['HTTP_REFERER'] = item2.absolute_url()
        infos = vendors_advice.restrictedTraverse(
            '@@categorized-childs-infos')(category_uid=category_uid, filters={}).strip()
        self.assertTrue(infos)
        download_view = annexNotConfidential.restrictedTraverse('@@download')
        self.assertTrue(download_view())
        # confidential annexes on advices are not viewable by powerobservers
        download_view = annexConfidential.restrictedTraverse('@@download')
        self.assertFalse(cfg.getAdviceAnnexConfidentialVisibleFor())
        self.assertRaises(Unauthorized, download_view)
        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        item1.__ac_local_roles__.clear()
        item1.update_local_roles()
        self.assertTrue(download_view())
        # another user could not access the annex
        self.changeUser("restrictedpowerobserver1")
        self.assertFalse(self.hasPermission(View, item1))
        self.assertFalse(self.hasPermission(View, item2))
        download_view = annexNotConfidential.restrictedTraverse('@@download')
        self.assertRaises(Unauthorized, download_view)
        download_view = annexConfidential.restrictedTraverse('@@download')
        self.assertRaises(Unauthorized, download_view)

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
            'category': 'development',
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
                                             'advice_comment': richtextval(u'My comment'),
                                             'advice_observations': richtextval(u'My observations'), })

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
        self.assertTrue(advice.advice_hide_during_redaction)
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
                                    'advice_comment': richtextval(u'My comment')})
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
        self.assertEqual(item1b.get_predecessor(), item1)
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
                                    'advice_comment': richtextval(u'My comment')})
        # send item to cfg2, this will keep power adviser advice instead asking delay aware advice
        item2 = item1.cloneToOtherMeetingConfig(cfg2Id)
        self.assertTrue(item2.adviceIndex[self.developers_uid]['inherited'])
        self.assertEqual(item2.adviceIndex[self.developers_uid]['delay'], '5')
        # advice infos are displayed correctly on item
        self.assertTrue(
            item2.restrictedTraverse('@@advices-icons')())
        self.assertTrue(
            item2.restrictedTraverse('@@advices-icons-infos')(
                adviceType='positive'))
        # following.update_local_roles are correct
        item2.update_local_roles()
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
        self.assertEqual(item1b.get_predecessor(), item1)
        self.assertEqual(item1b.getInheritedAdviceInfo(self.vendors_uid)['adviceHolder'], item1)
        item3 = item2.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        self.assertEqual(item3.getInheritedAdviceInfo(self.vendors_uid)['adviceHolder'], item1)
        # item4 will inherits from both 'developers' and 'vendors' but
        # change this to only keep the 'vendors' advice
        item4 = item2.clone(setCurrentAsPredecessor=True, inheritAdvices=True)
        item4.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid), ))
        del item4.adviceIndex[self.vendors_uid]
        item4.update_local_roles()
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
            'category': 'development',
            'optionalAdvisers': (self.developers_uid, )
        }
        item = self.create('MeetingItem', **data)

        self.changeUser('pmAdviser1')
        # advice is addable
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue("Add an advice" in advices_icons())
        # before advice is given, creator is obviously not displayed
        advices_icons_infos = item.restrictedTraverse('@@advices-icons-infos')
        adviser_fullname = u'<span>{0}</span>'.format(get_user_fullname(self.member.getId()))
        self.assertFalse(adviser_fullname in advices_icons_infos(adviceType=u'not_given'))
        createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_hide_during_redaction': False,
               'advice_comment': richtextval(u'My comment')})
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
        # invalidate cache for item advices vocabulary used by MeetingItem.showOptionalAdvisers
        notify(ObjectEditedEvent(cfg))
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
        meeting = self.create('Meeting')
        advice_infos = form._advice_infos(data={'advice_uid': self.vendors_uid})
        self.assertTrue(advice_infos.mayRemoveInheritedAdvice())
        self.presentItem(item2)
        self.assertEqual(item2.query_state(), 'presented')
        self.assertTrue(advice_infos.mayRemoveInheritedAdvice())
        self.closeMeeting(meeting)
        self.assertTrue(item2.query_state() in cfg.getItemDecidedStates())
        self.assertFalse(advice_infos.mayRemoveInheritedAdvice())
        # still doable as Manager
        self.changeUser('siteadmin')
        self.assertTrue(advice_infos.mayRemoveInheritedAdvice())

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
        cfg.setItemAdviceEditStates((item2.query_state(),))
        item2.update_local_roles()
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
                                             'advice_comment': richtextval(u'My comment')})
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

    def test_pm_AdviceDelayNotReinitializedWhenGiven(self):
        """When a WF transition from MeetingConfig.transitionsReinitializingDelays
           occurs, advice delay is only reinitialized if advice was not given."""
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2021/04/01',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2021/04/01',
              'delay': '5',
              'delay_label': ''}, ])
        # ask both advice but give only one
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((
            '{0}__rowid__unique_id_123'.format(self.vendors_uid),
            '{0}__rowid__unique_id_456'.format(self.developers_uid), ))
        item._update_after_edit()
        self.proposeItem(item)
        # delay started for both advices
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_started_on'])
        self.assertTrue(item.adviceIndex[self.developers_uid]['delay_started_on'])
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        self.backToState(item, 'itemcreated')
        # advice delay of not given advice was reinitialized
        self.assertTrue(item._advice_is_given(self.vendors_uid))
        self.assertTrue(item.adviceIndex[self.vendors_uid]['delay_started_on'])
        self.assertFalse(item._advice_is_given(self.developers_uid))
        self.assertIsNone(item.adviceIndex[self.developers_uid]['delay_started_on'])
        # asking advice again will reinitialize delay
        changeView = advice.restrictedTraverse('@@change-advice-asked-again')
        changeView()
        self.assertFalse(item._advice_is_given(self.vendors_uid))
        self.assertIsNone(item.adviceIndex[self.vendors_uid]['delay_started_on'])
        # the delay is only reinitialized if it was not timed out
        self.proposeItem(item)
        item.adviceIndex[self.developers_uid]['delay_started_on'] = \
            item.adviceIndex[self.developers_uid]['delay_started_on'] - timedelta(days=20)
        saved_delay_started_on = item.adviceIndex[self.developers_uid]['delay_started_on']
        self.backToState(item, 'itemcreated')
        self.assertFalse(item._advice_is_given(self.developers_uid))
        # delay was not reinitialized
        self.assertEqual(item.adviceIndex[self.developers_uid]['delay_started_on'],
                         saved_delay_started_on)

    def test_pm_AutoAdviceAfterClone(self):
        '''Test that when an item is cloned and new item does not
           get the automatic advice, it does not break.'''
        cfg = self.meetingConfig
        proposed_state_id = self._stateMappingFor('proposed')
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on':
                'python: item.query_state() == "{0}"'.format(proposed_state_id),
              'for_item_created_from': '2021/07/12',
              'delay': '',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': 'python: True',
              'for_item_created_from': '2016/07/12',
              'delay': '',
              'delay_label': ''}, ])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # developers advice was asked
        self.assertEqual(item.adviceIndex.keys(), [self.developers_uid])
        self.proposeItem(item)
        # vendors advice was asked
        self.assertEqual(sorted(item.adviceIndex.keys()),
                         sorted([self.developers_uid, self.vendors_uid]))
        new_item = item.clone()
        # clone does not break and developers advice was asked
        self.assertEqual(new_item.adviceIndex.keys(), [self.developers_uid])

    def test_pm_AdviserNotAbleToAddAnnexToItem(self):
        """This test a bug that was fixed becaues we used the "Contributor" role
           to manage annexes and advices "Add" permissions, now we use role
           "MeetingAdviser" to manage add advice permission."""
        cfg = self.meetingConfig
        cfg.setCustomAdvisers([])
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid, ))
        item._update_after_edit()

        # pmAdviser is able to add advice but not annexes
        self.changeUser('pmAdviser1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(self.hasPermission(AddPortalContent, item))
        self.assertTrue(self.hasPermission(AddAdvice, item))
        self.assertFalse(self.hasPermission(AddAnnex, item))
        self.assertFalse(self.hasPermission(AddAnnexDecision, item))

    def test_pm_AdvicesIconsCaching(self):
        """Test @@advices-icons caching."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceEditStates([self._stateMappingFor('itemcreated'), ])
        cfg.setItemAdviceViewStates([self._stateMappingFor('itemcreated'), ])
        cfg.setPowerAdvisersGroups((self.vendors_uid, ))
        self._setPowerObserverStates(states=(self._stateMappingFor('itemcreated'), ))
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((self._stateMappingFor('itemcreated'), ))
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('itemcreated', ))
        cfg.setRestrictAccessToSecretItems(True)
        self.assertTrue('restrictedpowerobservers' in cfg.getRestrictAccessToSecretItemsTo())

        # create an item and ask the advice of group 'developers'
        self.changeUser('pmCreator1')
        data = {
            'title': 'Item to advice',
            'category': 'development',
            'optionalAdvisers': (self.developers_uid, ),
            'copyGroups': (self.vendors_advisers, ),
            'privacy': 'secret'
        }
        item = self.create('MeetingItem', **data)
        # not able to add advice
        advices_icons_content = "Not given yet"
        add_advice_action = "++add++meetingadvice"
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons_content in advices_icons())
        self.assertFalse(add_advice_action in advices_icons())

        # test for an adviser
        self.changeUser('pmAdviser1')
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons_content in advices_icons())
        self.assertTrue(add_advice_action in advices_icons())

        # reviewer
        self.changeUser('pmReviewer1')
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons_content in advices_icons())
        self.assertFalse(add_advice_action in advices_icons())

        # power adviser
        self.changeUser('pmReviewer2')
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons_content in advices_icons())
        self.assertTrue(add_advice_action in advices_icons())

        # when using restrictAccessToSecretItemsTo
        self.changeUser('restrictedpowerobserver1')
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertFalse(advices_icons_content in advices_icons())
        self.assertFalse(add_advice_action in advices_icons())

        # MeetingManager
        # make it no more adviser and power adviser
        self._removePrincipalFromGroups('pmManager', [self.developers_advisers])
        self._removePrincipalFromGroups('pmManager', [self.vendors_advisers])
        self.changeUser('pmManager')
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons_content in advices_icons())
        self.assertFalse(add_advice_action in advices_icons())

        # Manager
        self.changeUser('siteadmin')
        advices_icons = item.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons_content in advices_icons())
        self.assertFalse(add_advice_action in advices_icons())

    def test_pm_AdvicesInfosOnItemTemplate(self):
        """Test that the advices icons infos are correctly displayed in an
           itemTemplate for which proposingGroup may be empty and adviceIndex
           is partially computed."""
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        self.changeUser('templatemanager1')
        itemTemplate = cfg.getItemTemplates(as_brains=False)[0]
        self.assertEqual(itemTemplate.getProposingGroup(), '')
        itemTemplate.setOptionalAdvisers(
            (self.developers_uid,
             '{0}__rowid__unique_id_123'.format(self.vendors_uid)))
        itemTemplate._update_after_edit()
        advices_icons = itemTemplate.restrictedTraverse('@@advices-icons')
        self.assertTrue(advices_icons())
        advices_icons_infos = itemTemplate.restrictedTraverse('@@advices-icons-infos')
        self.assertTrue(advices_icons_infos('not_given'))

    def test_pm_DeletingAdviceSavedToItemHistory(self):
        """When an advice is deleted, a line is added to the item history."""
        item, advice = self._setUpHistorizedAdvice()
        self.assertFalse(item.deleted_children_history)
        self.assertTrue(advice in item.objectValues())
        self.request.form['uid'] = advice.UID()
        self.request.form['comment'] = "My comment"
        view = advice.restrictedTraverse('@@delete_with_comments')
        view.apply(None)
        # advice was deleted
        self.assertFalse(advice in item.objectValues())
        # deletion was historized
        self.assertTrue(item.deleted_children_history[0]['action'], "delete_advice")
        self.assertTrue(item.deleted_children_history[0]['comments'], "My comment")
        # when duplicating item, history is empty
        cloned_item = item.clone()
        self.assertFalse(cloned_item.deleted_children_history)

    def test_pm_AdviceAccountingCommitmentBehavior(self):
        """The advice_accounting_commitment behavior may be enabled on meetingadvice,
           this will add field accounting_commitment that is taken into account in
           adviceIndex and by getAdviceDataFor."""
        # without the behavior, keys are there but value is None
        item, advice = self._setupItemWithAdvice()
        self.assertIsNone(item.adviceIndex[self.vendors_uid]['accounting_commitment'])
        self.assertIsNone(item.getAdviceDataFor(item)[self.vendors_uid]['accounting_commitment'])
        # enable behavior
        behaviors = self.portal.portal_types[advice.portal_type].behaviors
        behaviors += ('Products.PloneMeeting.behaviors.advice.IAdviceAccountingCommitmentBehavior', )
        self.portal.portal_types[advice.portal_type].behaviors = behaviors
        notify(SchemaInvalidatedEvent(advice.portal_type))
        item.update_local_roles()
        self.assertIsNone(item.adviceIndex[self.vendors_uid]['accounting_commitment'])
        self.assertIsNone(item.getAdviceDataFor(item)[self.vendors_uid]['accounting_commitment'])
        # define an accounting_commitment
        advice.advice_accounting_commitment = richtextval(u'My accounting commitment')
        item.update_local_roles()
        self.assertEqual(
            item.adviceIndex[self.vendors_uid]['accounting_commitment'],
            u'My accounting commitment')
        self.assertEqual(
            item.getAdviceDataFor(item)[self.vendors_uid]['accounting_commitment'],
            u'My accounting commitment')
        # also managed when 'hidden_during_redaction'
        advice.advice_hide_during_redaction = True
        item.update_local_roles()
        # visible by advisers
        self.assertEqual(
            item.getAdviceDataFor(item)[self.vendors_uid]['accounting_commitment'],
            u'My accounting commitment')
        # not visible by non members of the advisers group
        self.changeUser('pmCreator1')
        hidden_help_msg = translate(
            'advice_hidden_during_redaction_help',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(
            item.getAdviceDataFor(item)[self.vendors_uid]['accounting_commitment'],
            hidden_help_msg)

    def test_pm_advice_show_history(self):
        """Test the contenthistory.show_history() for advice that will depend
           on MeetingConfig.hideHistoryTo parameter."""
        cfg = self.meetingConfig
        # without the behavior, keys are there but value is None
        item, advice = self._setupItemWithAdvice()
        # visible by advice advisers, powerobservers, proposingGroup
        contenthistory = getMultiAdapter((advice, self.request), name='contenthistory')
        self.assertTrue(contenthistory.show_history())
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())
        # always visible to MeetingManagers
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())

        # hide it to powerobservers
        cfg.setHideHistoryTo(('meetingadvice.powerobservers', ))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertFalse(contenthistory.show_history())
        # still visible to advisers, proposing group
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())

        # hide it to everyone
        cfg.setHideHistoryTo(('meetingadvice.everyone', ))
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertFalse(contenthistory.show_history())
        # still visible to advisers
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())
        # no more visible to proposing group
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertFalse(contenthistory.show_history())
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(View, advice))
        self.assertTrue(contenthistory.show_history())

    def test_pm_get_advice_given_by(self):
        """Show info "Given by" on advice."""
        item, advice = self._setupItemWithAdvice()
        view = item.restrictedTraverse('@@advice-infos')
        view(advice.advice_group,
             False,
             item.adapted().getCustomAdviceMessageFor(
                 item.adviceIndex[advice.advice_group]))
        # with default advice workflow, we do not manage advice_given_by
        # as we only know who created the advice
        self.assertIsNone(view.get_advice_given_by())

    def test_pm_send_suffixes_and_owner_mail_if_relevant(self):
        """Test that the mail is sent when an advice is edited."""
        cfg = self.meetingConfig
        cfg.setMailItemEvents(('advice_edited__reviewers',))
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.request['debug_sendMailIfRelevant'] = True
        sent = item.send_suffixes_and_owner_mail_if_relevant("advice_edited")
        self.assertEqual(len(sent), 1)
        self.assertIn(u'M. PMReviewer One <pmreviewer1@plonemeeting.org>', sent[0][0])
        cfg.setMailItemEvents(())
        sent = item.send_suffixes_and_owner_mail_if_relevant("advice_edited")
        self.assertEqual(len(sent), 0)
        cfg.setMailItemEvents(('advice_edited__reviewers',))
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
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        self.assertIn(u'M. PMReviewer One <pmreviewer1@plonemeeting.org>',
                      self.request["debug_sendMailIfRelevant_result"][0])

        cfg.setMailItemEvents(())
        self.request["debug_sendMailIfRelevant_result"] = None
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, self.developers_uid, ))
        item._update_after_edit()

        # give 'vendors' advice and test
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': richtextval(u'My comment')})
        self.assertIsNone(self.request["debug_sendMailIfRelevant_result"])
        # owner
        cfg.setMailItemEvents(('advice_edited__Owner',))
        self.changeUser('pmManager')
        sent = item.send_suffixes_and_owner_mail_if_relevant("advice_edited")
        self.assertEqual(len(sent[0][0]), 1)
        self.assertEqual(sent[0][0][0], u'M. PMCreator One <pmcreator1@plonemeeting.org>')

        # in meeting, not necessary to put in meeting, just testing the mail event
        cfg.setMailItemEvents(('advice_edited__Owner', 'advice_edited_in_meeting__creators'))
        sent = item.send_suffixes_and_owner_mail_if_relevant("advice_edited_in_meeting")
        self.assertEqual(len(sent[0][0]), 2)
        self.assertEqual(sent[0][0][0], u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>')
        self.assertEqual(sent[0][0][1], u'M. PMCreator One <pmcreator1@plonemeeting.org>')

    def test_pm_AdviceMandatoriness(self):
        """When using MeetingConfig.enforceAdviceMandatoriness, an item
           may only be presented if auto or delay-aware advices are positive."""
        cfg = self.meetingConfig
        cfg.setEnforceAdviceMandatoriness(True)
        item1, item2, vendors_advice, developers_advice = \
            self._setupInheritedAdvice()
        self.changeUser('pmManager')
        self.create('Meeting')
        self.presentItem(item1)
        self.assertEqual(item1.query_state(), 'presented')
        self.presentItem(item2)
        self.assertEqual(item2.query_state(), 'presented')


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAdvices, prefix='test_pm_'))
    return suite
