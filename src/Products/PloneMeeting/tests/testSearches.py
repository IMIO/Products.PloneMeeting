# -*- coding: utf-8 -*-
#
# File: testMeetingConfig.py
#
# GNU General Public License (GPL)
#

from collective.compoundcriterion.interfaces import ICompoundCriterionFilter
from collective.eeafaceted.collectionwidget.utils import getCollectionLinkCriterion
from DateTime import DateTime
from datetime import datetime
from datetime import timedelta
from ftw.labels.interfaces import ILabeling
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import richtextval
from plone import api
from plone.app.querystring.querybuilder import queryparser
from plone.dexterity.utils import createContentInContainer
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.adapters import _find_nothing_query
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import getAdvicePortalTypes
from zope.component import getAdapter
from zope.component import getAdapters
from zope.event import notify


class testSearches(PloneMeetingTestCase):
    '''Tests the adapters used for searches.'''

    def test_pm_DefaultSelectedSearch(self):
        '''Test that the 'meetingAppDefaultView' defined in the MeetingConfig data
           is correctly applied to the collection-link widget on the facetednavigation view.'''
        # selected meetingAppDefaultView is 'searchallitems'
        cfg = self.meetingConfig
        searchallitems = cfg.searches.searches_items.searchallitems
        collectionCriterion = getCollectionLinkCriterion(cfg.searches)
        self.assertEqual(collectionCriterion.default, searchallitems.UID())

    def test_pm_SearchItemsOfMyGroups(self):
        '''Test the 'items-of-my-groups' adapter that returns items using proposingGroup
           the current user is in.'''
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        # siteadmin is not member of any PloneMeeting groups
        adapter = getAdapter(cfg, ICompoundCriterionFilter, name='items-of-my-groups')
        self.changeUser('siteadmin')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': []},
                          'portal_type': {'query': itemTypeName}})

        # pmManager is member of 'developers' and 'vendors'
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsofmygroups')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': [self.developers_uid, self.vendors_uid]},
                          'portal_type': {'query': itemTypeName}})

        # pmCreator1 is member of 'developers'
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsofmygroups')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': [self.developers_uid]},
                          'portal_type': {'query': itemTypeName}})

        # a deactivated group is still listed
        self.changeUser('siteadmin')
        self._select_organization(self.developers_uid, remove=True)
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsofmygroups')
        self.assertEqual(adapter.query,
                         {'getProposingGroup': {'query': [self.developers_uid, self.vendors_uid]},
                          'portal_type': {'query': itemTypeName}})

    def test_pm_SearchItemsToAdviceAdapter(self):
        '''Test the 'items-to-advice' adapter that should return a list of items
           a user has to give an advice for.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'delay': '5', }, ])
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-advice')
        # admin is not adviser
        self.assertEqual(adapter.query,
                         {'indexAdvisers': {'query': []},
                          'portal_type': {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEqual(
            adapter.query,
            {'indexAdvisers': {
                'query': ['{0}_advice_not_given'.format(self.developers_uid),
                          'delay__{0}_advice_not_given'.format(self.developers_uid),
                          '{0}_advice_asked_again'.format(self.developers_uid),
                          'delay__{0}_advice_asked_again'.format(self.developers_uid),
                          '{0}_advice_hidden_during_redaction'.format(self.developers_uid),
                          'delay__{0}_advice_hidden_during_redaction'.format(self.developers_uid)]},
                'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchallitemstoadvice"
        collection = cfg.searches.searches_items.searchallitemstoadvice
        # by default, no item to advice...
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.results())
        # an advice can be given when an item is 'proposed'
        self.assertEqual(cfg.getItemAdviceStates(), (self._stateMappingFor('proposed'), ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(
            (self.developers_uid, '{0}__rowid__unique_id_123'.format(self.vendors_uid)))
        item._update_after_edit()
        # as the item is "itemcreated", advices are not givable
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.results())
        # now propose the item
        self.changeUser('pmCreator1')
        self.proposeItem(item)
        # only advisers can give an advice, so a creator for example will not see it
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.results())
        # now test as advisers
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEqual(len(collection.results()), 1)
        self.assertEqual(collection.results()[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmAdviser1 gives his advice
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.results())
        # pmReviewer2 is adviser for 'vendors', delay-aware advices are also returned
        self.changeUser('pmReviewer2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEqual(len(collection.results()), 1)
        self.assertEqual(collection.results()[0].UID, item.UID())
        # when an advice on an item is given, the item is no more returned by searchItemsToAdvice
        # so pmReviewer2 gives his advice
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': self.vendors_uid,
                                             'advice_type': u'negative',
                                             'advice_comment': richtextval(u'My comment')})
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.failIf(collection.results())

        # ask advice again, it will appear to 'pmReviewer2' in the query
        self.backToState(item, 'itemcreated')
        self.changeUser('pmCreator1')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEqual(len(collection.results()), 1)
        self.assertEqual(collection.results()[0].UID, item.UID())

        # a given advice that is 'hidden_during_redaction' is also found by this search
        advice.advice_type = u'positive'
        changeView = advice.restrictedTraverse('@@change-advice-hidden-during-redaction')
        changeView()
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstoadvice')
        self.assertEqual(len(collection.results()), 1)
        self.assertEqual(collection.results()[0].UID, item.UID())

    def test_pm_SearchItemsToAdviceWithoutHiddenDuringRedactionAdapter(self):
        '''Test the 'items-to-advice-without-hidden-during-redaction' adapter
           that should return a list of items a user has to give an advice for but not
           advice currently hidden during redaction.'''
        # just check query as full search is tested in test_pm_SearchItemsToAdviceAdapter
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        cfg = self.meetingConfig
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-advice-without-hidden-during-redaction')
        itemTypeName = cfg.getItemTypeName()
        self.assertEqual(
            adapter.query,
            {'indexAdvisers': {
                'query': ['{0}_advice_not_given'.format(self.developers_uid),
                          'delay__{0}_advice_not_given'.format(self.developers_uid),
                          '{0}_advice_asked_again'.format(self.developers_uid),
                          'delay__{0}_advice_asked_again'.format(self.developers_uid)]},
                'portal_type': {'query': itemTypeName}})

    def test_pm_SearchMyItemsToAdviceAdapter(self):
        '''Test the 'my-items-to-advice' adapter that should return
           a list of items a user has to give an advice for.
           This will return only items for which advice is asked to entire group or
           asked to current user.
           Advice asked to another user will not be returned.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))
        originalCustomAdvisers = {'row_id': 'unique_id_123',
                                  'org': self.vendors_uid,
                                  'gives_auto_advice_on': '',
                                  'for_item_created_from': '2012/01/01',
                                  'for_item_created_until': '',
                                  'gives_auto_advice_on_help_message': '',
                                  'delay': '10',
                                  'delay_left_alert': '',
                                  'delay_label': 'Delay label', }
        cfg.setCustomAdvisers([originalCustomAdvisers])
        cfg.setSelectableAdviserUsers((self.vendors_uid, ))
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'), ))
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='my-items-to-advice')
        # admin is not adviser
        self.assertEqual(adapter.query,
                         {'indexAdvisers': {'query': []},
                          'portal_type': {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmReviewer2')
        self.assertEqual(
            adapter.query,
            {'indexAdvisers': {
                'query': [
                    '{0}_advice_not_given__userid__pmReviewer2'.format(
                        self.vendors_uid),
                    '{0}_advice_not_given__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_not_given__userid__pmReviewer2'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_not_given__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    '{0}_advice_asked_again__userid__pmReviewer2'.format(
                        self.vendors_uid),
                    '{0}_advice_asked_again__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_asked_again__userid__pmReviewer2'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_asked_again__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    '{0}_advice_hidden_during_redaction__userid__pmReviewer2'.format(
                        self.vendors_uid),
                    '{0}_advice_hidden_during_redaction__userid__entireadvisersgroup'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_hidden_during_redaction__userid__pmReviewer2'.format(
                        self.vendors_uid),
                    'delay__{0}_advice_hidden_during_redaction__userid__entireadvisersgroup'.format(
                        self.vendors_uid)]},
                'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchmyitemstoadvice"
        myitemstoadvice = cfg.searches.searches_items.searchmyitemstoadvice
        itemstoadvice = cfg.searches.searches_items.searchallitemstoadvice
        # by default, no item to advice...
        self.failIf(myitemstoadvice.results())
        self.failIf(itemstoadvice.results())

        # create 3 items to advice
        # one with advice asked to entire vendors advisers
        # one with advice asked to pmAdviser1
        # one with advice asked to another vendors adviser "pmManager"
        self.changeUser('pmCreator1')
        self.create(
            'MeetingItem',
            optionalAdvisers=(self.vendors_uid, ))
        self.create(
            'MeetingItem',
            optionalAdvisers=('{0}__userid__pmReviewer2'.format(self.vendors_uid), ))
        self.create(
            'MeetingItem',
            optionalAdvisers=('{0}__userid__pmManager'.format(self.vendors_uid), ))

        # pmReviewer2 will only get item1/item2 in the "searchmyitemstoadvice" collection
        # the "searchallitemstoadvice" collection will return the 3 items
        self.changeUser('pmReviewer2')
        self.assertEqual(len(myitemstoadvice.results()), 2)
        self.assertEqual(len(itemstoadvice.results()), 3)

    def test_pm_SearchAdvisedItems(self):
        '''Test the 'advised-items' adapter.  This should return a list of items
           a user has already give an advice for.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()
        cfg.setUsedAdviceTypes(cfg.getUsedAdviceTypes() + ('asked_again', ))

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='advised-items')
        # admin is not adviser
        self.assertEqual(adapter.query,
                         {'indexAdvisers': {'query': []},
                          'portal_type': {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        indexAdvisers = []
        adviceStates = []
        for portal_type in getAdvicePortalTypes():
            adviceWF = self.wfTool.getWorkflowsFor(portal_type.id)[0]
            adviceStates += adviceWF.states.keys()
        # remove duplicates
        adviceStates = tuple(set(adviceStates))
        for adviceState in adviceStates:
            indexAdvisers.append('{0}_{1}'.format(self.developers_uid, adviceState))
            indexAdvisers.append('delay__{0}_{1}'.format(self.developers_uid, adviceState))

        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.assertEqual(adapter.query,
                         {'indexAdvisers': {'query': indexAdvisers},
                          'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchalladviseditems"
        collection = cfg.searches.searches_items.searchalladviseditems
        # by default, no advised item...
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failIf(collection.results())
        # an advice can be given when an item is 'proposed'
        self.assertEqual(cfg.getItemAdviceStates(), (self._stateMappingFor('proposed'), ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers((self.developers_uid,))
        self.proposeItem(item1)
        # give an advice
        self.changeUser('pmAdviser1')
        advice = createContentInContainer(item1,
                                          'meetingadvice',
                                          **{'advice_group': self.developers_uid,
                                             'advice_type': u'positive',
                                             'advice_comment': richtextval(u'My comment')})
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(collection.results())
        # another user will not see given advices
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failIf(collection.results())
        # other advisers of the same group will also see advised items
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(collection.results())
        # now create a second item and ask advice to the vendors (pmManager)
        # it will be returned for pmManager but not for pmAdviser1
        self.changeUser('pmCreator1')
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers((self.vendors_uid,))
        self.proposeItem(item2)
        self.changeUser('pmManager')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(len(collection.results()) == 2)
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(len(collection.results()) == 1)
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failIf(collection.results())

        # ask advice again to 'pmAdviser1'
        # if an advice is asked again, it stiil appears in the given advice
        # this way, if advice is asked again but no directly giveable, it is
        # still found in proposed search
        self.backToState(item1, 'itemcreated')
        advice.restrictedTraverse('@@change-advice-asked-again')()
        self.proposeItem(item1)
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditems')
        self.failUnless(len(collection.results()) == 1)
        self.assertEqual(collection.results()[0].UID, item1.UID())

    def test_pm_SearchAdvisedItemsWithDelay(self):
        '''Test the 'advised-items-with-delay' adapter.  This should return a list
           of items a user has already give a delay-aware advice for.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='advised-items-with-delay')
        # admin is not adviser
        self.assertEqual(adapter.query,
                         {'indexAdvisers': {'query': []},
                          'portal_type': {'query': itemTypeName}})
        # as adviser, query is correct
        self.changeUser('pmAdviser1')
        adviceStates = []
        for portal_type in getAdvicePortalTypes():
            adviceWF = self.wfTool.getWorkflowsFor(portal_type.id)[0]
            adviceStates += adviceWF.states.keys()
        # remove duplicates
        adviceStates = tuple(set(adviceStates))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.assertEqual(adapter.query,
                         {'indexAdvisers': {'query':
                          ['delay__{0}_{1}'.format(
                           self.developers_uid, adviceState) for adviceState in adviceStates]},
                          'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchalladviseditemswithdelay"
        collection = cfg.searches.searches_items.searchalladviseditemswithdelay
        # by default, no advised item...
        self.changeUser('pmAdviser1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failIf(collection.results())
        # an advice can be given when an item is 'proposed'
        self.assertEqual(cfg.getItemAdviceStates(), (self._stateMappingFor('proposed'), ))
        # create an item to advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers((self.developers_uid,))
        self.proposeItem(item1)
        # give a non delay-aware advice
        self.changeUser('pmAdviser1')
        createContentInContainer(item1,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # non delay-aware advices are not found
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failIf(collection.results())
        # now create a second item and ask a delay-aware advice
        self.changeUser('admin')
        originalCustomAdvisers = {'row_id': 'unique_id_123',
                                  'org': self.developers_uid,
                                  'gives_auto_advice_on': '',
                                  'for_item_created_from': '2012/01/01',
                                  'for_item_created_until': '',
                                  'gives_auto_advice_on_help_message': '',
                                  'delay': '10',
                                  'delay_left_alert': '',
                                  'delay_label': 'Delay label', }
        cfg.setCustomAdvisers([originalCustomAdvisers, ])
        self.changeUser('pmCreator1')
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid),))
        self.proposeItem(item2)
        self.changeUser('pmAdviser1')
        createContentInContainer(item2,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # pmManager will see 2 items and pmAdviser1, just one, none for a non adviser
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failUnless(len(collection.results()) == 1)
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_adviseditemswithdelay')
        self.failIf(collection.results())

    def test_pm_SearchItemsInCopy(self):
        '''Test the 'items-in-copy' adapter.  This should return a list of items
           a user is in copy of.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((self._stateMappingFor('proposed'), 'validated', ))

        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-in-copy')
        # admin does not belong to any group
        self.assertEqual(adapter.query,
                         {'getCopyGroups': {'query': []},
                          'portal_type': {'query': itemTypeName}})
        # as creator, query is correct
        self.changeUser('pmCreator1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.assertEqual(adapter.query,
                         {'getCopyGroups': {
                          'query': sorted(['AuthenticatedUsers', self.developers_creators])},
                          'portal_type': {'query': itemTypeName}})

        # now do the query
        # this adapter is used by the "searchallitemsincopy"
        collection = cfg.searches.searches_items.searchallitemsincopy
        # create an item and set another proposing group in copy of
        item = self.create('MeetingItem')
        # give a view access to members of vendors, like pmReviewer2
        item.setCopyGroups((self.vendors_reviewers, ))
        item._update_after_edit()
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.failIf(collection.results())
        # connect as a member of 'developers_reviewers'
        self.changeUser('pmReviewer2')
        # the item is not proposed so not listed
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.failIf(collection.results())
        # propose the item, it will be listed
        self.proposeItem(item)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemsincopy')
        self.failUnless(collection.results())

    def test_pm_SearchItemsInCopyWithAutoCopyGroups(self):
        '''Test the 'items-in-copy' adapter when using auto copyGroups.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((self._stateMappingFor('proposed'), 'validated', ))
        # configure an auto copyGroup, vendors_reviewers will be set
        # as auto copyGroup for every items
        self.vendors.as_copy_group_on = u"python: ['reviewers']"

        # this adapter is used by the "searchallitemsincopy"
        collection = cfg.searches.searches_items.searchallitemsincopy
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.assertEqual(item.getAllCopyGroups(auto_real_plone_group_ids=True),
                         (self.vendors_reviewers, ))
        self.proposeItem(item)
        self.changeUser('pmReviewer2')
        self.failUnless(collection.results())

    def test_pm_show_copy_groups_search(self):
        """Test MeetingConfig.show_copy_groups_search used to show items in copy searches."""
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        self.assertEqual(cfg.getSelectableCopyGroups(),
                         (self.developers_reviewers, self.vendors_reviewers))
        self.changeUser('pmCreator1')
        self.assertFalse(cfg.show_copy_groups_search())
        self.changeUser('pmReviewer2')
        self.assertTrue(cfg.show_copy_groups_search())
        # not shown if copyGroups not used
        self._enableField('copyGroups', enable=False)
        self.changeUser('pmCreator1')
        self.assertFalse(cfg.show_copy_groups_search())
        self.changeUser('pmReviewer2')
        self.assertFalse(cfg.show_copy_groups_search())

    def test_pm_SearchMyItemsTakenOver(self):
        '''Test the 'my-items-taken-over' method.  This should return
           a list of items a user has taken over.'''
        self.changeUser('admin')
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((self._stateMappingFor('proposed'), 'validated', ))

        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='my-items-taken-over')
        # query is correct
        self.changeUser('pmManager')
        self.assertEqual(adapter.query,
                         {'portal_type': {'query': itemTypeName},
                          'getTakenOverBy': {'query': 'pmManager'}})

        # now do the query
        # this adapter is used by the "searchmyitemstakenover"
        collection = cfg.searches.searches_items.searchmyitemstakenover
        item = self.create('MeetingItem')
        # by default nothing is returned
        self.failIf(collection.results())
        # now take item over
        item.setTakenOverBy(self.member.getId())
        item.reindexObject(idxs=['getTakenOverBy', ])
        # now it is returned
        self.failUnless(collection.results())
        # takenOverBy is set back to '' on each transition
        self.proposeItem(item)
        self.assertTrue(not item.getTakenOverBy())
        self.failIf(collection.results())

        # query is not cached (this was the case before and there was a bug
        # because using forevercache and member_id changed
        self.changeUser('pmCreator1')
        self.assertEqual(adapter.query,
                         {'portal_type': {'query': itemTypeName},
                          'getTakenOverBy': {'query': 'pmCreator1'}})

    def _searchItemsToValidateOfHighestHierarchicLevelReviewerInfo(self, cfg):
        """ """
        return ['{0}__reviewprocess__{1}'.format(self.developers_uid,
                                                 self._stateMappingFor('proposed'))]

    def test_pm_SearchItemsToValidateOfHighestHierarchicLevel(self):
        '''Test the searchItemsToValidateOfHighestHierarchicLevel method.
           This should return a list of items a user ***really*** has to validate.
           Items to validate are items for which user is a reviewer and only regarding
           his higher hierarchic level.
           So a reviewer level 1 and level 2 will only see items in level 2, a reviewer in level
           1 (only) will only see items in level 1.'''
        self.changeUser('admin')
        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        # first test the generated query
        self.changeUser('pmManager')
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-highest-hierarchic-level')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        reviewProcessInfo = self._searchItemsToValidateOfHighestHierarchicLevelReviewerInfo(cfg)
        self.assertEqual(
            adapter.query,
            {'reviewProcessInfo':
                {'query': reviewProcessInfo},
             'portal_type': {'query': itemTypeName}})

        reviewers = cfg.reviewersFor()
        # activate 'prevalidation' if necessary
        if 'prereviewers' not in reviewers:
            self._enablePrevalidation(cfg)
        reviewers = cfg.reviewersFor()
        self.assertTrue('prereviewers' in reviewers)
        # now do the query
        # this adapter is used by the "searchitemstovalidate"
        collection = cfg.searches.searches_items.searchitemstovalidate
        # create an item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # jump to first level of validation
        self.do(item, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.results())
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failUnless(collection.results())
        # now as 'pmReviewerLevel2', the item should not be returned
        # as he only see items of his highest hierarchic level
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.results())
        # pass the item to second last level of hierarchy, where 'pmReviewerLevel2' is reviewer for
        self.changeUser('pmReviewerLevel1')
        # jump to last level of validation
        self.proposeItem(item)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.results())
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failUnless(collection.results())

        # now give a view on the item by 'pmReviewer2' and check if, as a reviewer,
        # the search does returns him the item, it should not as he is just a reviewer
        # but not able to really validate the new item
        self._enableField('copyGroups')
        review_states = reviewers[reviewers.keys()[0]]
        if 'prereviewers' in reviewers:
            review_states += ('prevalidated',)
        cfg.setItemCopyGroupsStates(review_states)
        item.setCopyGroups((self.vendors_reviewers, ))
        item._update_after_edit()
        self.changeUser('pmReviewer2')
        # the user can see the item
        self.failUnless(self.hasPermission(View, item))
        # but the search will not return it
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failIf(collection.results())
        # if the item is validated, it will not appear for pmReviewer1 anymore
        self.changeUser('pmReviewer1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofhighesthierarchiclevel')
        self.failUnless(collection.results())
        self.validateItem(item)
        self.failIf(collection.results())

    def test_pm_SearchItemsToValidateOfHighestHierarchicLevelReturnsEveryLevels(self):
        '''When a user is developers_level3reviewers and vendors_level2reviewers,
           both groups must be queried.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        # make sure we use default itemWFValidationLevels,
        # useful when test executed with custom profile
        self._setUpDefaultItemWFValidationLevels(cfg)
        self._enablePrevalidation(cfg)

        # make pmReviewer2 is vendors_prereviewers and developers_reviewers
        # add pmReviewer2 to developers_reviewers
        self.changeUser('pmReviewer2')
        member_groups = [grp_id for grp_id in self.member.getGroups()
                         if grp_id != 'AuthenticatedUsers']
        self._removePrincipalFromGroups('pmReviewer2', member_groups)
        self._addPrincipalToGroup('pmReviewer2', self.developers_reviewers)
        self._addPrincipalToGroup('pmReviewer2', self.vendors_prereviewers)
        self.assertItemsEqual(
            self.member.getGroups(),
            ['AuthenticatedUsers', self.developers_reviewers, self.vendors_prereviewers])

        # generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-highest-hierarchic-level')
        query = adapter.query
        self.assertEqual(len(query['reviewProcessInfo']['query']), 2)
        self.assertTrue('{0}__reviewprocess__prevalidated'.format(self.developers_uid)
                        in query['reviewProcessInfo']['query'])
        self.assertTrue('{0}__reviewprocess__proposed'.format(self.vendors_uid)
                        in query['reviewProcessInfo']['query'])

    def test_pm_SearchItemsToValidateOfMyReviewerGroups(self):
        '''Test the 'items-to-validate-of-my-reviewer-groups' adapter.
           This should return a list of items a user could validate at any level,
           so not only his highest hierarchic level.  This will return finally every items
           corresponding to Plone reviewer groups the user is in.'''
        cfg = self.meetingConfig
        self.changeUser('admin')

        # activate the 'pre_validation' wfAdaptation if it exists in current profile...
        # if not, then reviewers must be at least 2 elements long
        reviewers = cfg.reviewersFor()
        if not len(reviewers) > 1:
            self._enablePrevalidation(cfg)
        reviewers = cfg.reviewersFor()
        if not len(reviewers) > 1:
            pm_logger.info("Could not launch test 'test_pm_SearchItemsToValidateOfMyReviewerGroups' "
                           "because we need at least 2 levels of item validation.")

        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-my-reviewer-groups')
        # if user si not a reviewer, we want the search to return
        # nothing so the query uses an unknown review_state
        itemTypeName = cfg.getItemTypeName()
        self.assertEqual(adapter.query, _find_nothing_query(itemTypeName))
        # for a reviewer, query is correct
        self.changeUser('pmReviewer1')
        # only reviewer for highest level
        reviewers = cfg.reviewersFor()
        self._removeUsersFromEveryGroups(['pmReviewer1'])
        self._addPrincipalToGroup('pmReviewer1',
                                  "{0}_{1}".format(self.developers_uid, reviewers.keys()[0]))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        query = adapter.query
        query['reviewProcessInfo']['query'].sort()
        states = reviewers.values()[0]
        self.assertEqual({'portal_type': {'query': itemTypeName},
                          'reviewProcessInfo': {
                          'query': sorted(['{0}__reviewprocess__{1}'.format(self.developers_uid, state)
                                           for state in states])}},
                         adapter.query)

        # now do the query
        # this adapter is not used by default, but is intended to be used with
        # the "searchitemstovalidate" collection so use it with it
        collection = cfg.searches.searches_items.searchitemstovalidate
        patchedQuery = list(collection.query)
        patchedQuery[0]['v'] = 'items-to-validate-of-my-reviewer-groups'
        collection.query = patchedQuery

        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failIf(collection.results())
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.assertEqual(collection.results().length, 2)
        # as second level user, he will not see items of first level also
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.failIf(collection.results())

        # define 'pmReviewerLevel2' as a prereviewer (first validation level reviewer)
        self._turnUserIntoPrereviewer(self.member)
        # change again to 'pmReviewerLevel2' so changes in his groups are taken into account
        self.changeUser('pmReviewerLevel2')
        # he can access first validation level items
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.assertEqual(collection.results().length, 2)
        # move item1 to last validation level
        self.proposeItem(item1)
        # both items still returned by the search for 'pmReviewerLevel2'
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.assertEqual(collection.results().length, 2)
        # but now, the search only returns item2 to 'pmReviewerLevel1'
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofmyreviewergroups')
        self.assertEqual(collection.results().length, 1)
        self.failUnless(collection.results()[0].UID == item2.UID())

    def runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest(self):
        '''
          Helper method for activating the test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels
          test when called from a subplugin.
        '''
        return False

    def _searchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsReviewerInfo(self, cfg):
        """ """
        reviewers = cfg.reviewersFor()
        reviewer_states = reviewers[cfg._highestReviewerLevel(self.member.getGroups())]
        return ['{0}__reviewprocess__{1}'.format(self.developers_uid, reviewer_state)
                for reviewer_state in reviewer_states]

    def test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels(self):
        '''Test the searchItemsToValidateOfEveryReviewerLevelsAndLowerLevels method.
           This will return items to validate of his highest hierarchic level and every levels
           under, even if user is not in the corresponding Plone reviewer groups.'''
        cfg = self.meetingConfig
        # check if self.runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest() is True
        if not self.runSearchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsTest():
            pm_logger.info(
                "Test 'test_pm_SearchItemsToValidateOfEveryReviewerLevelsAndLowerLevels' was bypassed.")
            return
        self._enablePrevalidation(cfg, enable_extra_suffixes=True)
        itemTypeName = cfg.getItemTypeName()
        # create 2 items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.do(item1, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        self.do(item2, self.TRANSITIONS_FOR_PROPOSING_ITEM_1[0])
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-validate-of-every-reviewer-levels-and-lower-levels')
        self.changeUser('pmObserver1')
        self.assertEqual(adapter.query, _find_nothing_query(itemTypeName))
        # now do the query
        # this adapter is not used by default, but is intended to be used with
        # the "searchitemstovalidate" collection so use it with it
        collection = cfg.searches.searches_items.searchitemstovalidate
        patchedQuery = list(collection.query)
        patchedQuery[0]['v'] = 'items-to-validate-of-every-reviewer-levels-and-lower-levels'
        collection.query = patchedQuery
        self.failIf(collection.results())
        # as first level user, he will see items
        self.changeUser('pmReviewerLevel1')
        # find state to use for current reviewer
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        reviewProcessInfo = self._searchItemsToValidateOfEveryReviewerLevelsAndLowerLevelsReviewerInfo(cfg)
        self.assertEqual(adapter.query,
                         {'portal_type': {'query': itemTypeName},
                          'reviewProcessInfo': {'query': reviewProcessInfo}})
        self.failUnless(len(collection.results()) == 2)
        # as second level user, he will also see items because items are from lower reviewer levels
        self.changeUser('pmReviewerLevel2')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.failUnless(len(collection.results()) == 2)

        # now propose item1, both items are still viewable to 'pmReviewerLevel2', but 'pmReviewerLevel1'
        # will only see item of 'his' highest hierarchic level
        self.proposeItem(item1)
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.failUnless(len(collection.results()) == 2)
        self.changeUser('pmReviewerLevel1')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstovalidateofeveryreviewerlevelsandlowerlevels')
        self.failUnless(len(collection.results()) == 1)
        self.failUnless(collection.results()[0].UID == item2.UID())

    def test_pm_SearchItemsToCorrect(self):
        '''Test the 'items-to-correct' CompoundCriterion adapter.  This should return
           a list of items in state 'returned_to_proposing_group' the current user is able to edit.'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['return_to_proposing_group']):
            pm_logger.info("Bypassing test test_pm_SearchItemsToCorrect because it "
                           "needs the 'return_to_proposing_group' wfAdaptation.")
            return

        itemTypeName = cfg.getItemTypeName()
        self.changeUser('siteadmin')
        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-correct')
        # wfAdaptation 'return_to_proposing_group' is not enabled
        self.assertEqual(adapter.query, _find_nothing_query(itemTypeName))
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if 'return_to_proposing_group' not in wfAdaptations:
            wfAdaptations.append('return_to_proposing_group')
        cfg.setWorkflowAdaptations(wfAdaptations)
        notify(ObjectEditedEvent(cfg))

        # normally this search is not available to users that are not able to correct items
        # nevertheless, if a user is not able to edit items to correct, the special
        # query 'return nothing' is returned
        self.assertEqual(adapter.query, _find_nothing_query(itemTypeName))
        self.changeUser('pmManager')
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        self.assertEqual(
            adapter.query,
            {'portal_type': {'query': itemTypeName},
             'reviewProcessInfo': {
             'query': ['{0}__reviewprocess__returned_to_proposing_group'.format(self.developers_uid)]}})

        # it returns only items the current user is able to correct
        # create an item for developers and one for vendors and 'return' it to proposingGroup
        self.create('Meeting')
        developersItem = self.create('MeetingItem')
        self.assertEqual(developersItem.getProposingGroup(), self.developers_uid)
        self.presentItem(developersItem)
        self.changeUser('pmCreator2')
        vendorsItem = self.create('MeetingItem')
        self.assertEqual(vendorsItem.getProposingGroup(), self.vendors_uid)
        self.changeUser('pmManager')
        self.presentItem(vendorsItem)
        collection = cfg.searches.searches_items.searchitemstocorrect
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        self.failIf(collection.results())
        self.do(developersItem, 'return_to_proposing_group')
        self.do(vendorsItem, 'return_to_proposing_group')

        # pmManager may only edit developersItem
        self.assertTrue(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        res = collection.results()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == developersItem.UID())

        # pmCreator2 may only edit vendorsItem
        self.changeUser('pmCreator2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrect')
        res = collection.results()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == vendorsItem.UID())

        # when an item is corrected, it appears in the correcteditems search
        collection = cfg.searches.searches_items.searchcorrecteditems
        self.assertEqual(len(collection.results()), 0)
        self.do(vendorsItem, 'backTo_presented_from_returned_to_proposing_group')
        self.assertEqual(len(collection.results()), 1)

    def test_pm_SearchItemsToCorrectToValidateOfHighestHierarchicLevel(self):
        '''Test the 'items-to-correct-to-validate-of-highest-hierarchic-level'
           CompoundCriterion adapter. This should return a list of items in state
           'returned_to_proposing_group_proposed' the current user is able to edit.'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['return_to_proposing_group_with_last_validation']):
            pm_logger.info(
                "Bypassing test test_pm_SearchItemsToCorrectToValidateHighestHierarchicLevel because it "
                "needs the 'return_to_proposing_group_with_last_validation' wfAdaptation.")
            return

        itemTypeName = cfg.getItemTypeName()
        self.changeUser('siteadmin')
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if 'return_to_proposing_group_with_last_validation' not in wfAdaptations:
            wfAdaptations.append('return_to_proposing_group_with_last_validation')
        # desactivate simple return to proposing group wf
        if 'return_to_proposing_group' in wfAdaptations:
            wfAdaptations.remove('return_to_proposing_group')
        cfg.setWorkflowAdaptations(wfAdaptations)
        notify(ObjectEditedEvent(cfg))

        # first test the generated query
        self.changeUser('pmManager')
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-correct-to-validate-of-highest-hierarchic-level')
        self.assertEqual(adapter.query, {
            'reviewProcessInfo':
            {'query': ['{0}__reviewprocess__returned_to_proposing_group_{1}'.format(
                self.developers_uid, self._stateMappingFor('proposed'))]},
            'portal_type': {'query': itemTypeName}})

        # it returns only items the current user is able to correct
        # create an item for developers and one for vendors and 'return' it to proposingGroup
        self.create('Meeting')
        developersItem = self.create('MeetingItem')
        self.assertEqual(developersItem.getProposingGroup(), self.developers_uid)
        self.presentItem(developersItem)
        self.changeUser('pmCreator2')
        vendorsItem = self.create('MeetingItem')
        self.assertEqual(vendorsItem.getProposingGroup(), self.vendors_uid)
        self.changeUser('pmManager')
        self.presentItem(vendorsItem)
        collection = cfg.searches.searches_items.searchitemstocorrecttovalidate
        cleanRamCacheFor('Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        self.failIf(collection.results())
        self.do(developersItem, 'return_to_proposing_group')
        self.do(vendorsItem, 'return_to_proposing_group')

        self.changeUser('pmCreator1')
        self.do(developersItem, 'goTo_returned_to_proposing_group_' + self._stateMappingFor('proposed'))
        self.changeUser('pmCreator2')
        self.do(vendorsItem, 'goTo_returned_to_proposing_group_' + self._stateMappingFor('proposed'))
        self.changeUser('pmManager')

        # pmManager may only edit developersItem
        self.assertTrue(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        res = collection.results()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == developersItem.UID())

        # pmCreator2 can't edit vendorsItem
        self.changeUser('pmCreator2')
        self.assertTrue(not self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        res = collection.results()
        self.failUnless(len(res) == 0)

        # pmReviewer2 may only edit vendorsItem
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofhighesthierarchiclevel')
        res = collection.results()
        self.failUnless(len(res) == 1)
        self.failUnless(res[0].UID == vendorsItem.UID())

    def test_pm_SearchAllItemsToValidateOfHighestHierarchicLevel(self):
        '''Test the 'all-items-to-validate-of-highest-hierarchic-level'
           CompoundCriterion adapter. This should return every items the user is able to validate
           so items that are 'proposed' and items that are 'returned_to_proposing_group_proposed'.'''
        # specify that copyGroups can see the item when it is proposed
        cfg = self.meetingConfig
        if not self._check_wfa_available(['return_to_proposing_group_with_last_validation']):
            pm_logger.info(
                "Bypassing test test_pm_SearchAllItemsToValidateHighestHierarchicLevel because it "
                "needs the 'return_to_proposing_group_with_last_validation' wfAdaptation.")
            return
        itemTypeName = cfg.getItemTypeName()
        self.changeUser('pmManager')
        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='all-items-to-validate-of-highest-hierarchic-level')
        states = self._get_query_review_process(cfg)[-1:]
        query = sorted(['{0}__reviewprocess__{1}'.format(self.developers_uid, state)
                        for state in states])
        query += sorted(['{0}__reviewprocess__returned_to_proposing_group_{1}'.format(self.developers_uid, state)
                         for state in states])
        self.assertEqual({'portal_type': {'query': [itemTypeName]},
                          'reviewProcessInfo': {'query': query}},
                         adapter.query)

    def _test_reviewer_groups(self, developersItem, vendorsItem, collection):
        self.changeUser('pmCreator1')
        self.do(developersItem,
                'goTo_returned_to_proposing_group_{}'.format(self._stateMappingFor('proposed_first_level')))
        self.changeUser('pmCreator2')
        self.do(vendorsItem,
                'goTo_returned_to_proposing_group_{}'.format(self._stateMappingFor('proposed_first_level')))

        self.changeUser('pmCreator1')
        # pmManager can't edit developersItem
        self.assertFalse(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        self.assertEqual(collection.results().length, 0)

        # pmCreator2 can't edit vendorsItem
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        self.assertEqual(collection.results().length, 0)

        self.changeUser('admin')
        self.do(developersItem, 'goTo_returned_to_proposing_group_prevalidated')
        self.do(vendorsItem, 'goTo_returned_to_proposing_group_prevalidated')

        # pmReviewer1 may only edit developersItem
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(ModifyPortalContent, developersItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        res = collection.results()
        self.assertEqual(res.length, 1)
        self.assertEqual(res[0].UID, developersItem.UID())

        # pmReviewer2 may only edit vendorsItem
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(ModifyPortalContent, vendorsItem))
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        res = collection.results()
        self.assertEqual(res.length, 1)
        self.assertEqual(res[0].UID, vendorsItem.UID())

    def test_pm_SearchItemsToCorrectToValidateOfEveryReviewerGroups(self):
        '''Test the 'items-to-correct-to-validate-of-every-reviewer-groups'
           CompoundCriterion adapter.  This should return a list of items in state
           'returned_to_proposing_group_proposed' the current user is able to edit.'''
        if not self._check_wfa_available(['return_to_proposing_group_with_all_validations']):
            pm_logger.info(
                "Bypassing test test_pm_SearchItemsToCorrectToValidateOfEveryReviewerGroups because it "
                "needs the 'return_to_proposing_group_with_all_validations' wfAdaptation.")
            return

        cfg = self.meetingConfig
        itemTypeName = cfg.getItemTypeName()

        self.changeUser('siteadmin')
        # first test the generated query
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-to-correct-to-validate-of-every-reviewer-groups')
        # wfAdaptation 'return_to_proposing_group_with_last_validation' is not enabled
        self.assertEqual(adapter.query, _find_nothing_query(itemTypeName))
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if 'return_to_proposing_group_with_all_validations' not in wfAdaptations:
            wfAdaptations.append('return_to_proposing_group_with_all_validations')
        # deactivate simple return to proposing group wf
        if 'return_to_proposing_group' in wfAdaptations:
            wfAdaptations.remove('return_to_proposing_group')
        cfg.setWorkflowAdaptations(wfAdaptations)
        self._enablePrevalidation(cfg)
        notify(ObjectEditedEvent(cfg))

        # normally this search is not available to users that are not able to review items
        # nevertheless, if a user is in not able to edit items to correct in proposed, the special
        # query 'return nothing' is returned
        self.assertEqual(adapter.query, _find_nothing_query(itemTypeName))
        self.changeUser('pmManager')
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        states = self._get_query_review_process(cfg)[1:]
        query = sorted(['{0}__reviewprocess__returned_to_proposing_group_{1}'.format(
                        self.developers_uid, state) for state in states])
        self.assertEqual({
            'portal_type': {'query': itemTypeName},
            'reviewProcessInfo': {'query': query}},
            adapter.query)

        # it returns only items the current user is able to correct
        # create an item for developers and one for vendors and 'return' it to proposingGroup
        self.create('Meeting')
        developers_item = self.create('MeetingItem')
        self.assertEqual(developers_item.getProposingGroup(), self.developers_uid)
        self.changeUser('pmCreator2')
        vendors_item = self.create('MeetingItem')
        self.assertEqual(vendors_item.getProposingGroup(), self.vendors_uid)
        # present items
        self.changeUser('pmManager')
        self.presentItem(developers_item)
        self.presentItem(vendors_item)
        collection = cfg.searches.searches_items.searchitemstocorrecttovalidateoffeveryreviewergroups
        cleanRamCacheFor(
            'Products.PloneMeeting.adapters.query_itemstocorrecttovalidateofeveryreviewerlevelsandlowerlevels')
        self.failIf(collection.results())

        self.do(developers_item, 'return_to_proposing_group')
        self.do(vendors_item, 'return_to_proposing_group')

        self._test_reviewer_groups(developers_item, vendors_item, collection)

    def _get_query_review_process(self, cfg):
        return [state['state'] for state in cfg.getItemWFValidationLevels()
                if state['enabled'] == '1' and state['state']]

    def test_pm_SearchAllItemsToValidateOfEveryReviewerGroups(self):
        '''Test the 'all-items-to-validate-of-every-reviewer-groups'
           CompoundCriterion adapter. This should return every items the user is able to validate
           so items that are 'proposed' and items that are 'returned_to_proposing_group_proposed'.'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['return_to_proposing_group_with_all_validations']):
            pm_logger.info(
                "Bypassing test test_pm_SearchAllItemsToValidateOfEveryReviewerGroups because it "
                "needs the 'return_to_proposing_group_with_all_validations' wfAdaptation.")
            return

        itemTypeName = cfg.getItemTypeName()
        self._enablePrevalidation(cfg)

        self.changeUser('pmManager')
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='all-items-to-validate-of-every-reviewer-groups')
        states = self._get_query_review_process(cfg)[1:]
        query = sorted(['{0}__reviewprocess__{1}'.format(self.developers_uid, state)
                        for state in states])
        query += sorted(['{0}__reviewprocess__returned_to_proposing_group_{1}'.format(self.developers_uid, state)
                         for state in states])
        self.assertEqual({'portal_type': {'query': [itemTypeName]},
                          'reviewProcessInfo': {'query': query}},
                         adapter.query)

    def test_pm_SearchUnreadItems(self):
        '''Test the 'items-with-negative-personal-labels' adapter.
           This should return a list of items for which current user did not checked the 'lu' label.'''
        cfg = self.meetingConfig
        cfg.setEnableLabels(True)
        collection = cfg.searches.searches_items.searchunreaditems

        # create item, not 'lu' by default
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.reindexObject(idxs=['labels'])
        # for now item is not 'lu'
        self.assertEqual(len(collection.results()), 1)
        # make item 'lu'
        labeling = ILabeling(item)
        labeling.pers_update(['lu'], True)
        item.reindexObject(idxs=['labels'])
        self.assertEqual(len(collection.results()), 0)

    def test_pm_CompoundCriterionAdapterItemsWithNegativePreviousIndex(self):
        '''Test the 'items-with-negative-previous-index' adapter.
           Here we will try to get items that do not have a certain advice asked.'''
        cfg = self.meetingConfig
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'delay': '10', }, ])
        # this will return items for which developers 10 days delay advice was not asked
        # or vendors advice was not asked
        collection = cfg.searches.searches_items.searchallitems
        query = collection.query
        query.append({u'i': u'indexAdvisers',
                      u'o': u'plone.app.querystring.operation.selection.is',
                      u'v': [u'delay_row_id__unique_id_123',
                             u'real_org_uid__{0}'.format(self.vendors_uid)]})
        query.append({u'i': u'CompoundCriterion',
                      u'o': u'plone.app.querystring.operation.compound.is',
                      u'v': [u'items-with-negative-previous-index']})
        collection.setQuery(query)
        self.assertEqual(
            queryparser.parseFormquery(collection, collection.getQuery())[u'indexAdvisers'],
            {'not': [u'delay_row_id__unique_id_123',
                     u'real_org_uid__{0}'.format(self.vendors_uid)]})

        # test
        self.changeUser('pmCreator1')
        self.assertEqual(len(collection.results()), 0)
        item = self.create('MeetingItem')
        self.assertEqual(len(collection.results()), 1)
        # ask advices
        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid), ))
        item._update_after_edit()
        item.reindexObject(idxs=['indexAdvisers'])
        self.assertEqual(len(collection.results()), 0)
        item.setOptionalAdvisers(())
        item._update_after_edit()
        item.reindexObject(idxs=['indexAdvisers'])
        self.assertEqual(len(collection.results()), 1)
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        item.reindexObject(idxs=['indexAdvisers'])
        self.assertEqual(len(collection.results()), 0)

    def test_pm_DashboardCollectionsAreEditable(self):
        """This will ensure created DashboardCollections are editable.
           It could not be the case when using a wrong query."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        brains = api.content.find(context=cfg.searches, portal_type='DashboardCollection')
        for brain in brains:
            collection = brain.getObject()
            self.assertTrue(collection.restrictedTraverse('edit')())

    def test_pm_SearchLastDecisions(self):
        '''Test the 'last-decisions' CompoundCriterion adapter.
           This should decided meetings from 60 days in the past to 60 days in the future.'''
        cfg = self.meetingConfig
        meetingTypeName = cfg.getMeetingTypeName()

        # siteadmin is not member of any PloneMeeting groups
        collection = cfg.searches.searches_decisions.searchlastdecisions

        adapter = getAdapter(collection, ICompoundCriterionFilter, name='last-decisions')
        self.changeUser('siteadmin')
        # meeting_date minmax is correct, first date is 60 days before and second 60 days after now
        self.assertTrue(adapter.query['meeting_date']['query'][0] < DateTime() - 59)
        self.assertTrue(adapter.query['meeting_date']['query'][1] > DateTime() + 59)
        self.assertEqual(adapter.query['portal_type']['query'], [meetingTypeName])

        # decided meetings in the future and in the past are found
        self.changeUser('pmManager')
        self.failIf(collection.results())
        now = datetime.now()
        past_meeting = self.create('Meeting', date=now - timedelta(days=45))
        future_meeting = self.create('Meeting', date=now + timedelta(days=45))
        self.failIf(collection.results())
        self.decideMeeting(past_meeting)
        self.decideMeeting(future_meeting)
        result_uids = [brain.UID for brain in collection.results()]
        self.assertTrue(past_meeting.UID() in result_uids)
        self.assertTrue(future_meeting.UID() in result_uids)

    def test_pm_EverySearchesUseDifferentCachedMethod(self):
        """Make sure a different method is used for caching because every adapters
           use the "query" method but ram.cache would have one single cache entry
           because it's key is module path + method name so
           Products.PloneMeeting.adapters.query."""
        cfg = self.meetingConfig
        adapters = getAdapters([cfg], ICompoundCriterionFilter)
        query_aliases = []
        for adapter_name, adapter_instance in adapters:
            query_methods = [method_name for method_name in dir(adapter_instance)
                             if method_name.startswith('query_')]
            # there must be at least one query_... method that is an alias for query
            self.assertTrue(
                query_methods,
                "No query_xxx methdod for {0}".format(adapter_name))
            # make sure the query_... method is an alias for query
            found_alias = False
            for query_method in query_methods:
                adapter_class = adapter_instance.__class__
                if getattr(adapter_class, query_method) == adapter_class.query:
                    found_alias = True
                    break
            self.assertTrue(found_alias,
                            "Alias not found for {0}".format(adapter_name))
            # keep the query_method alias
            query_aliases.append(query_method)
        # there may not be 2 same query aliases
        self.assertEqual(sorted(query_aliases), sorted(set(query_aliases)))

    def test_pm_SearchItemsOfMyCommitteesAndItemsOfMyCommitteesEditable(self):
        '''Test the 'items-of-my-committees' and 'items-of-my-committees-editable'
           adapters that should return a list of items current user is committee
           editor for.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setItemCommitteesStates(['itemcreated'])
        cfg.setItemCommitteesViewStates(['validated'])
        itemTypeName = cfg.getItemTypeName()
        # configure committees editors
        self._setUpCommitteeEditor(cfg)

        # items-of-my-committees
        # first test the generated query, admin is not a committee editor
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-of-my-committees')
        self.assertEqual(adapter.query,
                         {'committees_index': {'query': []},
                          'portal_type': {'query': itemTypeName}})
        self.changeUser('pmCreator2')
        self.assertEqual(adapter.query,
                         {'committees_index': {'query': ['committee_1']},
                          'portal_type': {'query': itemTypeName}})
        # now create items and test that the search
        self.changeUser('pmManager')
        editable_item = self.create('MeetingItem', committees=['committee_1'])
        viewable_item = self.create('MeetingItem', committees=['committee_1'])
        # a third item, not viewable by pmCreator2
        self.create('MeetingItem')
        self.validateItem(viewable_item)
        collection = cfg.searches.searches_items.searchitemsofmycommittees
        # pmManager is not a committee editor
        self.failIf(collection.results())
        self.changeUser('pmCreator2')
        res = collection.results()
        self.assertEqual(sorted([brain.UID for brain in res]),
                         sorted([viewable_item.UID(), editable_item.UID()]))

        # items-of-my-committees-editable
        # first test the generated query, admin is not a committee editor
        adapter = getAdapter(cfg,
                             ICompoundCriterionFilter,
                             name='items-of-my-committees-editable')
        self.assertEqual(adapter.query,
                         {'committees_index': {'query': ['committee_1']},
                          'portal_type': {'query': itemTypeName},
                          'review_state': {'query': ('itemcreated', )}})
        collection = cfg.searches.searches_items.searchitemsofmycommitteeseditable
        res = collection.results()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].UID, editable_item.UID())

    def test_pm_SearchLivingItems(self):
        '''Test the 'living-items' CompoundCriterion adapter.
           Returns every items that are not decided.'''
        cfg = self.meetingConfig
        collection = cfg.searches.searches_items.searchlivingitems
        self.changeUser('pmManager')
        item = self.create('MeetingItem', decision=self.decisionText)
        self.assertTrue(item.UID() in [brain.UID for brain in collection.results()])
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.assertTrue(item.UID() in [brain.UID for brain in collection.results()])
        self.decideMeeting(meeting)
        self.assertTrue(item.UID() in [brain.UID for brain in collection.results()])
        self.closeMeeting(meeting)
        self.assertEqual(item.query_state(), 'accepted')
        self.assertTrue(item.query_state() in cfg.getItemDecidedStates())
        self.assertFalse(item.UID() in [brain.UID for brain in collection.results()])

    def test_pm_json_collections_count(self):
        """Test the @@json_collections_count, essentially because it is cached thru
           PMRenderTermView.number_of_items.
           Test also that caching works when using a "myitems" like collection as
           user_id is taken into account in the invalidation key in this case."""
        # disable every showNumberOfItems so no search is enabled by custom profile
        cfg = self.meetingConfig
        for collection in cfg.searches.searches_items.objectValues():
            collection.showNumberOfItems = False
        self.changeUser("pmCreator1")
        view = self.getMeetingFolder().restrictedTraverse("@@json_collections_count")
        self.assertEqual(view(), '{"criterionId": "c1", "countByCollection": []}')
        item = self.create("MeetingItem")
        self.assertEqual(view(), '{"criterionId": "c1", "countByCollection": []}')
        searchmyitems = cfg.searches.searches_items.searchmyitems
        searchmyitems_uid = searchmyitems.UID()
        searchmyitems.showNumberOfItems = True
        self.assertEqual(
            view(),
            '{"criterionId": "c1", "countByCollection": [{"count": 1, "uid": "%s"}]}' % searchmyitems_uid)
        self.changeUser("pmCreator1b", clean_memoize=False)
        view = self.getMeetingFolder().restrictedTraverse("@@json_collections_count")
        self.assertEqual(
            view(),
            '{"criterionId": "c1", "countByCollection": [{"count": 0, "uid": "%s"}]}' % searchmyitems_uid)
        self.changeUser("pmCreator1", clean_memoize=False)
        self.deleteAsManager(item.UID())
        view = self.getMeetingFolder().restrictedTraverse("@@json_collections_count")
        self.assertEqual(
            view(),
            '{"criterionId": "c1", "countByCollection": [{"count": 0, "uid": "%s"}]}' % searchmyitems_uid)


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSearches, prefix='test_pm_'))
    return suite
