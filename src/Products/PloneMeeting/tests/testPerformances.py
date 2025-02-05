# -*- coding: utf-8 -*-
#
# File: testPerformances.py
#
# GNU General Public License (GPL)
#

from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_groups
from collective.eeafaceted.batchactions.utils import listify_uids
from datetime import datetime
from datetime import timedelta
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_user_fullname
from plone import api
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import down_or_up_wf
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import isPowerObserverForCfg
from profilehooks import timecall
from zope.event import notify


class testPerformances(PloneMeetingTestCase):
    '''Tests various aspects of performances.'''

    def setUp(self):
        # call parent setUp
        PloneMeetingTestCase.setUp(self)

    def _setupForDelayingItems(self, number_of_items, number_of_annexes):
        """ """
        meeting, uids = self._setupMeetingItemsWithAnnexes(number_of_items,
                                                           number_of_annexes,
                                                           present_items=True)
        # set the meeting in the 'decided' state
        self.decideMeeting(meeting)
        # in some wfs, deciding a meeting will accept every items...
        # set back items to the 'itemfrozen' state
        for itemInMeeting in meeting.get_items():
            if itemInMeeting.query_state() == 'itemfrozen':
                break
            self.do(itemInMeeting, 'backToItemFrozen')

        return meeting, uids

    def _setupMeetingItemsWithAnnexes(self,
                                      number_of_items,
                                      number_of_annexes,
                                      with_meeting=True,
                                      present_items=False,
                                      as_uids=True):
        cfg = self.meetingConfig
        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if 'no_publication' not in wfAdaptations:
            self.changeUser('siteadmin')
            wfAdaptations.append('no_publication')
            cfg.setWorkflowAdaptations(wfAdaptations)
            notify(ObjectEditedEvent(cfg))

        self.changeUser('pmManager')
        meeting = None
        if with_meeting:
            # create a meeting
            meeting = self.create('Meeting')
        data = {}
        uids = []
        items = []
        logger_threshold = 10
        created_items = 0
        total_created_items = 0
        for i in range(number_of_items):
            # display message in logger while creating many items
            created_items += 1
            total_created_items += 1
            if created_items == logger_threshold:
                if not number_of_annexes:
                    pm_logger.info('Created %d out of %d items' % (total_created_items, number_of_items))
                created_items = 0

            # create the item
            data['title'] = 'Item number %d' % i
            item = self.create('MeetingItem', **data)
            item.setDecision('<p>A decision</p>')
            # add annexes
            if number_of_annexes:
                for j in range(number_of_annexes):
                    self.addAnnex(item, annexTitle="Annex number %d" % j)
                pm_logger.info('Added %d annexes to the item number %s' %
                               (number_of_annexes, total_created_items))
            if present_items:
                self.presentItem(item)
            uids.append(item.UID())
            items.append(item)
        if as_uids:
            return meeting, uids
        else:
            return meeting, items

    def test_pm_Delay5ItemsWith0Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 0)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (5, 0))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay10ItemsWith0Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 0)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (10, 0))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay5ItemsWith5Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 5)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (5, 5))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay10ItemsWith5Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 5)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (10, 5))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay5ItemsWith10Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(5, 10)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (5, 10))
        self._delaySeveralItems(meeting, uids)

    def test_pm_Delay10ItemsWith10Annexes(self):
        '''While delaying an item, it is cloned with annexes.'''
        meeting, uids = self._setupForDelayingItems(10, 10)
        pm_logger.info('Delay %d items containing %d annexes in each.' % (10, 10))
        self._delaySeveralItems(meeting, uids)

    def _setItemReferenceFormat(self):
        """Compute metingDate, proposingGroup acronym and item number relativeTo meeting."""
        self.meetingConfig.setItemReferenceFormat(
            "python: here.restrictedTraverse('pm_unrestricted_methods').getLinkedMeetingDate().strftime('%Y%m%d') + "
            "'/' + here.getProposingGroup(True).getAcronym() + '/' + "
            "str(here.getItemNumber(relativeTo='meeting', for_display=True))")

    def test_pm_Update250ItemsItemReference(self):
        '''Update the itemReference of 250 items.'''
        self._setItemReferenceFormat()
        meeting, uids = self._setupMeetingItemsWithAnnexes(250, 0, with_meeting=True, present_items=True)

        # item references are only updated once meeting is frozen
        # freeze meeting but defer references update
        # update every items
        pm_logger.info('Freezing meeting without update_item_references.')
        self.request.set('defer_Meeting_update_item_references', True)
        self.freezeMeeting(meeting)
        self.request.set('defer_Meeting_update_item_references', False)
        # update every items
        pm_logger.info(
            'Updating item references for %d items presented in a meeting starting from item number %s.' % (250, 0))
        self._updateItemReferences(meeting)
        # update items starting from 100th item
        pm_logger.info(
            'Updating item references for %d items presented in a meeting starting from item number %s.' % (250, 100))
        self._updateItemReferences(meeting, start_number=100 * 100)
        # update items starting from 200th item
        pm_logger.info(
            'Updating item references for %d items presented in a meeting starting from item number %s.' % (250, 200))
        self._updateItemReferences(meeting, start_number=200 * 100)

    @timecall
    def _updateItemReferences(self, meeting, start_number=0):
        '''Helper method that actually compute every items itemReference for p_meeting.'''
        # set back every items reference to '' so the entire process including reindex of SearchableText is done
        for item in meeting.get_items():
            item.setItemReference('')
        meeting.update_item_references(start_number=start_number)

    def test_pm_Present50ItemsWithoutAnnexesSeveralTimes(self):
        '''While presenting items, these items are inserted in a given order.
           In this test, as every items use same 'proposingGroup', same 'privacy'
           and same 'listType' every items are evaluated each time and
           every new is finally added at the end of the meeting.
           We present 50 by 50 items successively in same meeting'''
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.' % (50, 0))
        # use 'complex' inserting method
        self.meetingConfig.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_list_type',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_privacy',
                                                          'reverse': '0'},
                                                         {'insertingMethod': 'on_proposing_groups',
                                                          'reverse': '0'},))
        meeting, items = self._setupMeetingItemsWithAnnexes(50, 0, as_uids=False)
        # called when no item in the meeting
        self._presentSeveralItems(items)
        # called second times whith items in the meeting
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.'
                       % (50, meeting.number_of_items()))
        dummy_meeting, items = self._setupMeetingItemsWithAnnexes(50, 0, with_meeting=False, as_uids=False)
        self._presentSeveralItems(items)
        # called third times whith items in the meeting
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.'
                       % (50, meeting.number_of_items()))
        dummy_meeting, items = self._setupMeetingItemsWithAnnexes(50, 0, with_meeting=False, as_uids=False)
        self._presentSeveralItems(items)
        # called fourth times whith items in the meeting
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.'
                       % (50, meeting.number_of_items()))
        dummy_meeting, items = self._setupMeetingItemsWithAnnexes(50, 0, with_meeting=False, as_uids=False)
        self._presentSeveralItems(items)

    def test_pm_SendSeveralItemsWithAnnexesToAnotherMC(self):
        '''We will freeze a meeting containing 50 items from which 25 need to be send
           to another MC.  Every items contain 5 annexes.'''
        pm_logger.info('Freezing a meeting containing %d items and sending %d items to another MC.' % (50, 25))
        cfg = self.meetingConfig
        self._enableField('category', enable=False)
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                           'reverse': '0'}, ))
        cfg2 = self.meetingConfig2
        self._enableField('category', cfg=cfg2, enable=False)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))
        cfg2Id = cfg2.getId()
        # make items sent to config2 automatically presented in the next meeting
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        cfg.setItemAutoSentToOtherMCStates((u'itemfrozen', ))
        meeting, items = self._setupMeetingItemsWithAnnexes(50, 5, present_items=True, as_uids=False)
        # make 25 items sendable to another MC
        for item in items[0:25]:
            item.setOtherMeetingConfigsClonableTo((self.meetingConfig2.getId(), ))
            item.reindexObject(idxs=['sentToInfos', ])

        # create meeting in cfg2 in which items will be presented
        self.setMeetingConfig(cfg2Id)
        meeting2 = self.create('Meeting', date=datetime.now() + timedelta(days=1))
        self.assertFalse(meeting2.get_items())

        # freeze the meeting, this will do the job
        self._freezeMeetingAndSendItemsToAnotherMC(meeting)

        # make sure meeting2 has items
        self.assertEquals(len(meeting2.get_items()), 25)

    @timecall
    def _delaySeveralItems(self, meeting, uids):
        '''Helper method that actually delays the items.'''
        brains = api.content.find(UID=uids)
        for brain in brains:
            obj = brain.getObject()
            api.content.transition(obj=obj, transition='delay')

    @timecall
    def _presentSeveralItems(self, items):
        '''Present the p_items in p_meeting.'''
        for item in items:
            self.presentItem(item)

    @timecall
    def _freezeMeetingAndSendItemsToAnotherMC(self, meeting):
        '''Freeze given p_meeting.'''
        self.freezeMeeting(meeting)

    def test_pm_ComputeItemNumberWithSeveralNotClosedMeetings(self):
        '''Check performances while looking for the current item number using
           MeetingItem.getItemNumber(relativeTo='meetingConfig') that will query previous
           existing meetings to get the item number.'''
        self.changeUser('pmManager')
        # create 30 meetings containing 150 items in each
        data = {}
        meetings = []
        number_of_meetings = 5
        number_of_items = 10
        pm_logger.info('Adding %d meetings with %d items in each' % (number_of_meetings, number_of_items))
        for i in range(number_of_meetings):
            pm_logger.info('Creating meeting %d of %s' % (i + 1, number_of_meetings))
            meeting = self.create('Meeting', date=datetime.now() + timedelta(i + 1))
            meetings.append(meeting)
            for j in range(number_of_items):
                data['title'] = 'Item number %d' % j
                item = self.create('MeetingItem', **data)
                item.setDecision('<p>A decision</p>')
                # present the item
                self.presentItem(item)
        # now we have number_of_meetings meetings containing number_of_items items
        # test with the last created meeting
        self._computeItemNumbersForMeeting(meeting)
        # now close meeting at half of existing meetings
        meetingAtHalf = meetings[int(number_of_meetings / 2)]
        self.closeMeeting(meetingAtHalf)
        self._computeItemNumbersForMeeting(meeting)
        # now close meeting at 90% of created meetings that is the most obvious usecase
        meetingAt90Percent = meetings[int(number_of_meetings * 0.9)]
        self.closeMeeting(meetingAt90Percent)
        self._computeItemNumbersForMeeting(meeting)
        # now close penultimate meeting (the meeting just before the meeting the item is in) and test again
        meetingPenultimate = meetings[number_of_meetings - 2]
        self.closeMeeting(meetingPenultimate)
        self._computeItemNumbersForMeeting(meeting)
        # finally close the meeting we will compute items numbers
        self.closeMeeting(meeting)
        self._computeItemNumbersForMeeting(meeting)

    @timecall
    def _computeItemNumbersForMeeting(self, meeting):
        '''Helper method that actually compute item number for every items of the given p_meeting.'''
        for item in meeting.get_items():
            item.getItemNumber(relativeTo='meetingConfig')

    def _setupForOrgs(self, number_of_orgs):
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # remove existing groups and add our own
        # make what necessary for groups to be removable...
        cfg.setOrderedGroupsInCharge(())
        cfg.setSelectableCopyGroups(())
        cfg.setSelectableAdvisers(())
        cfg2.setOrderedGroupsInCharge(())
        cfg2.setSelectableCopyGroups(())
        cfg2.setSelectableAdvisers(())
        orgs = get_organizations(only_selected=True)
        for org in orgs:
            self._select_organization(org.UID(), remove=True)
            for ploneGroup in get_plone_groups(org.UID()):
                for memberId in ploneGroup.getGroupMemberIds():
                    ploneGroup.removeMember(memberId)
        # remove items defined in the tool
        self._removeConfigObjectsFor(cfg, folders=['recurringitems', 'itemtemplates', 'categories'])
        self._removeConfigObjectsFor(cfg2, folders=['recurringitems', 'itemtemplates', 'categories'])

        # remove groups
        self._removeOrganizations()
        # create groups
        for i in range(number_of_orgs):
            org = self.create('organization', id=i, title='Org %d' % i)
            self._select_organization(org.UID())

    def test_pm_get_organizations_caching(self):
        '''Test collective.contact.plonegroup.utils.get_organizations caching.'''
        for n in [10, 100, 250]:
            # first test with 10 orgs
            self._setupForOrgs(n)
            pm_logger.info('get_organizations called 1 time with %d activated orgs.' % n)
            # first call, even when asking caching, it is not as never computed but it is cached
            pm_logger.info('No caching.')
            self._get_organizations(times=1, caching=True)
            # second time, cached
            pm_logger.info('Caching.')
            self._get_organizations(times=1, caching=True)
            # remove cache
            self.cleanMemoize()
            pm_logger.info('get_organizations called 100 times with %d activated orgs.' % n)
            pm_logger.info('No caching.')
            self._get_organizations(times=100, caching=False)
            # second time, cached
            pm_logger.info('Caching.')
            self._get_organizations(times=100, caching=True)
            # remove cache
            self.cleanMemoize()

    @timecall
    def _get_organizations(self, times=1, caching=True):
        ''' '''
        for time in range(times):
            get_organizations(not_empty_suffix='advisers', caching=caching)

    def test_pm_get_organization_caching(self):
        '''Test collective.contact.plonegroup.utils.get_organization caching.
           Check if faster than using catalog unrestricted.'''
        # test with 100 orgs
        self._setupForOrgs(100)
        pm_logger.info('get_organization called 1000 time with 100 activated orgs.')
        # with caching=False
        pm_logger.info('No caching.')
        self._get_organization(times=1000, caching=False)
        # with caching=True
        pm_logger.info('Caching.')
        self._get_organization(times=1000, caching=True)

    @timecall
    def _get_organization(self, times=1, caching=True):
        ''' '''
        for time in range(times):
            get_organization(self.vendors_uid, caching=caching)

    def test_pm_SpeedGetMeetingConfig(self):
        '''Test ToolPloneMeeting.getMeetingConfig method performances.
           We call the method 2000 times, this is what happens when displaying
           a meeting containing 100 items.'''
        # create an item
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # call getMeetingConfig 2000 times with item
        self._getMeetingConfigOnTool(item, 2000)
        # call getMeetingConfig 2000 times with item parent
        self._getMeetingConfigOnTool(item.aq_inner.aq_parent, 2000)
        # call getMeetingConfig 2000 times with searches_items folder
        self._getMeetingConfigOnTool(item.aq_inner.aq_parent.searches_items, 2000)

    @timecall
    def _getMeetingConfigOnTool(self, context, times=1):
        ''' '''
        for time in range(times):
            self.tool.getMeetingConfig(context)

    def test_pm_SpeedSetManuallyLinkedItems(self):
        '''Test MeetingItem.setManuallyLinkedItems method performances.'''

        meeting1, items1 = self._setupMeetingItemsWithAnnexes(10, 0, as_uids=False)
        meeting2, items2 = self._setupMeetingItemsWithAnnexes(10, 0, as_uids=False)
        meeting3, items3 = self._setupMeetingItemsWithAnnexes(10, 0, as_uids=False)
        meeting4, items4 = self._setupMeetingItemsWithAnnexes(10, 0, as_uids=False)
        meeting5, items5 = self._setupMeetingItemsWithAnnexes(10, 0, as_uids=False)
        item = items1[0]
        linked_items = items1[1:] + items2 + items3 + items4 + items5
        linked_item_uids = [linked_item.UID() for linked_item in linked_items]
        # set with caching
        pm_logger.info('setManuallyLinkedItems with cahing=True (1).')
        self._setManuallyLinkedItemsOnItem(item, linked_item_uids)
        # set without caching
        item.setManuallyLinkedItems([])
        pm_logger.info('setManuallyLinkedItems with cahing=False (1).')
        self._setManuallyLinkedItemsOnItem(item, linked_item_uids, caching=False)
        # set with caching second time
        item.setManuallyLinkedItems([])
        pm_logger.info('setManuallyLinkedItems with cahing=True (2).')
        self._setManuallyLinkedItemsOnItem(item, linked_item_uids)
        # set without caching second time
        item.setManuallyLinkedItems([])
        pm_logger.info('setManuallyLinkedItems with cahing=False (2).')
        self._setManuallyLinkedItemsOnItem(item, linked_item_uids, caching=False)

    @timecall
    def _setManuallyLinkedItemsOnItem(self, item, linked_item_uids, caching=True):
        ''' '''
        item.setManuallyLinkedItems(linked_item_uids, caching=caching)

    def test_pm_SpeedIsManager(self):
        '''Test ToolPloneMeeting.isManager method performances.
           Need to comment manually ram.cache on ToolPloneMeeting.isManager
           to see difference.  Performance is better with @ram.cache.'''
        # create an item
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self._isManager(item, 2000)

    @timecall
    def _isManager(self, context, times=1):
        ''' '''
        for time in range(times):
            self.tool.isManager(self.meetingConfig)
            self.tool.isManager(realManagers=True)

    def test_pm_GetAuthenticatedMember(self):
        '''Test performance between portal_membership.getAuthenticatedMember and
           plone_portal_state.member() and api.user.get_current.'''
        # create an item
        self.changeUser('pmManager')
        # call getAuthenticatedMember 2000 times
        self._portalMembershipGetAuthenticatedMember(2000)
        # call plone_portal_state.member() 2000 times
        self._plonePortalStateMember(2000)
        # call api.user.get_current() 2000 times
        self._apiUserGetCurrent(2000)
        # call utils.get_current_user_id() 2000 times with
        # AUTHENTICATED_USER set
        self._utilsGetCurrentUserId(2000)
        self.request.set("AUTHENTICATED_USER", None)
        # call utils.get_current_user_id() 2000 times with
        # AUTHENTICATED_USER not set, will use api.user.get_current()
        self._utilsGetCurrentUserId(2000)

    @timecall
    def _portalMembershipGetAuthenticatedMember(self, times=1):
        ''' '''
        for time in range(times):
            getToolByName(self.portal, 'portal_membership').getAuthenticatedMember()

    @timecall
    def _plonePortalStateMember(self, times=1):
        ''' '''
        for time in range(times):
            self.portal.restrictedTraverse('@@plone_portal_state').member()

    @timecall
    def _apiUserGetCurrent(self, times=1):
        ''' '''
        for time in range(times):
            api.user.get_current()

    @timecall
    def _utilsGetCurrentUserId(self, times=1):
        ''' '''
        for time in range(times):
            get_current_user_id()

    def _setupForMeetingCategories(self, number_of_categories, withUsingGroups=False):
        self.changeUser('admin')
        # remove items in the tool and categories
        self._removeConfigObjectsFor(self.meetingConfig, folders=['recurringitems', 'itemtemplates', 'categories'])
        # create categories
        for i in range(number_of_categories):
            catObj = self.create('meetingcategory',
                                 id=i,
                                 title='Category %d' % i)
            if withUsingGroups:
                catObj.setUsingGroups(('developers', ))
            catObj._at_creation_flag = False
            catObj.at_post_create_script()

    def test_pm_GetCategoriesCaching(self):
        '''Test MeetingConfig.getCategories caching.'''
        times = 1000
        self._enableField('category')
        # first test with 10 groups without usingGroups
        self._setupForMeetingCategories(10, withUsingGroups=False)
        pm_logger.info('getCategories called %d times with %d activated groups, without usingGroups.'
                       % (times, 10))
        pm_logger.info('Not cached..')
        self._getCategoriesOnMeetingConfig(times=times)
        # second time, cached
        pm_logger.info('Cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # remove cache
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")

        # first test with 10 groups with usingGroups
        self._setupForMeetingCategories(10, withUsingGroups=True)
        pm_logger.info('getCategories called %d times with %d activated groups, with usingGroups.'
                       % (times, 10))
        pm_logger.info('No cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # second time, cached
        pm_logger.info('Cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # remove cache
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")

        # test with 100 categories without usingGroups
        self._setupForMeetingCategories(100, withUsingGroups=False)
        pm_logger.info('getCategories called %d times with %d activated groups, without usingGroups.'
                       % (times, 100))
        pm_logger.info('No cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # second time, cached
        pm_logger.info('Cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # remove cache
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")

        # test with 100 categories with usingGroups
        self._setupForMeetingCategories(100, withUsingGroups=True)
        pm_logger.info('getCategories called %d times with %d activated groups, with usingGroups.'
                       % (times, 100))
        pm_logger.info('No cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # second time, cached
        pm_logger.info('Cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # remove cache
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")

        # test with 250 categories without usingGroups
        self._setupForMeetingCategories(250, withUsingGroups=False)
        pm_logger.info('getCategories called %d times with %d activated groups, without usingGroups.'
                       % (times, 250))
        pm_logger.info('No cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # second time, cached
        pm_logger.info('Cached.')
        self._getCategoriesOnMeetingConfig(times=times)
        # remove cache
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")

        # test with 250 categories with usingGroups
        self._setupForMeetingCategories(250, withUsingGroups=True)
        pm_logger.info('getCategories called %d times with %d activated groups, with usingGroups.'
                       % (times, 250))
        pm_logger.info('No cached.')
        self._getCategoriesOnMeetingConfig(times=1000)
        # second time, cached
        pm_logger.info('Cached.')
        self._getCategoriesOnMeetingConfig(times=1000)
        # remove cache
        invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")

    @timecall
    def _getCategoriesOnMeetingConfig(self, times=1):
        ''' '''
        for time in range(times):
            self.meetingConfig.getCategories(userId='pmManager', onlySelectable=True)

    def _setupItemsForUpdateLocalRoles(self, add_advices=True, add_annexes=True):
        '''Call.update_local_roles on items holding many annexes and advices.'''
        # configure several auto asked advices and manually asked advices
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        if add_advices:
            # create some groups in charge
            gic_uids = []
            for i in range(1, 11):
                gic = self.create(
                    'organization',
                    id='groupincharge{0}'.format(i),
                    Title='Group in charge {0}'.format(i),
                    acronym='GIC{0}'.format(i))
                gic_uids.append(gic.UID())
            # set the groups in charge, in charge of developers
            self.developers.groups_in_charge = gic_uids
            # configure customAdvisers
            custom_advisers = []
            for gic_uid in gic_uids:
                custom_advisers.append(
                    {'gives_auto_advice_on':
                        "python:'{0}' in item.getGroupsInCharge(fromOrgIfEmpty=True)".format(gic_uid),
                     'org': gic_uid,
                     'for_item_created_from': '2019/10/15',
                     'row_id': 'row_id__{0}'.format(gic_uid)})
            cfg.setCustomAdvisers(custom_advisers)

        self.changeUser('pmManager')
        # create 50 items with 20 annexes
        number_of_items = 50
        number_of_annexes = 0
        if add_annexes:
            number_of_annexes = 20
        meeting, items = self._setupMeetingItemsWithAnnexes(
            number_of_items=number_of_items,
            number_of_annexes=number_of_annexes,
            with_meeting=False,
            as_uids=False)
        return items

    def test_pm_UpdateLocalRolesOn50ItemsWith0AnnexesAnd0Advices(self):
        '''Call.update_local_roles on items without any annexes or advices.'''
        items = self._setupItemsForUpdateLocalRoles(add_advices=False,
                                                    add_annexes=False)
        number_of_advices = 0
        for item in items:
            self.assertEqual(len(item.adviceIndex), number_of_advices)

        # call update local roles 2 times
        uids = listify_uids([item.UID() for item in items])
        number_of_annexes = 0
        for item in items:
            self.assertEqual(len(get_annexes(item)), number_of_annexes)

        pm_logger.info(
            'Call 1 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)
        pm_logger.info(
            'Call 2 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)

    def test_pm_UpdateLocalRolesOn50ItemsWith20AnnexesAnd0Advices(self):
        '''Call.update_local_roles on items with 20 annexes and 0 advices.'''
        items = self._setupItemsForUpdateLocalRoles(add_advices=False,
                                                    add_annexes=True)
        number_of_advices = 0
        for item in items:
            self.assertEqual(len(item.adviceIndex), number_of_advices)

        # call update local roles 2 times
        uids = listify_uids([item.UID() for item in items])
        number_of_annexes = 20
        for item in items:
            self.assertEqual(len(get_annexes(item)), number_of_annexes)

        pm_logger.info(
            'Call 1 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)
        pm_logger.info(
            'Call 2 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)

    def test_pm_UpdateLocalRolesOn50ItemsWith0AnnexesAnd10Advices(self):
        '''Call.update_local_roles on items with 0 annexes and 10 advices.'''
        items = self._setupItemsForUpdateLocalRoles(add_advices=True,
                                                    add_annexes=False)
        number_of_advices = 10
        for item in items:
            self.assertEqual(len(item.adviceIndex), number_of_advices)

        # call update local roles 2 times
        uids = listify_uids([item.UID() for item in items])
        number_of_annexes = 0
        for item in items:
            self.assertEqual(len(get_annexes(item)), number_of_annexes)
        pm_logger.info(
            'Call 1 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)
        pm_logger.info(
            'Call 2 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)

    def test_pm_UpdateLocalRolesOn50ItemsWith20AnnexesAnd10Advices(self):
        '''Call.update_local_roles on items with 20 annexes and 10 advices.'''
        items = self._setupItemsForUpdateLocalRoles(add_advices=True,
                                                    add_annexes=True)
        number_of_advices = 10
        for item in items:
            self.assertEqual(len(item.adviceIndex), number_of_advices)

        # call update local roles 2 times
        uids = listify_uids([item.UID() for item in items])
        number_of_annexes = 20
        for item in items:
            self.assertEqual(len(get_annexes(item)), number_of_annexes)

        pm_logger.info(
            'Call 1 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)
        pm_logger.info(
            'Call 2 to.update_local_roles on 50 items holding '
            '{0} annexes and {1} auto asked advices.'.format(number_of_annexes, number_of_advices))
        self._updateItemLocalRoles(uids)

    @timecall
    def _updateItemLocalRoles(self, uids):
        '''Helper method that actually update local roles on items.'''
        self.tool.update_all_local_roles(**{'UID': uids})

    def test_pm_DuplicateItemWith50Annexes(self):
        '''Duplicate an item containing 50 annexes.'''
        dummy_meeting, items = self._setupMeetingItemsWithAnnexes(
            2, 50, with_meeting=False, as_uids=False)
        for item in items:
            # duplicate it 2 times
            pm_logger.info('Duplicate item first time without annexes.')
            self._duplicateItem(item)
            pm_logger.info('Duplicate item first time with annexes.')
            self._duplicateItem(item, copyAnnexes=True)
            pm_logger.info('Duplicate item second time without annexes.')
            self._duplicateItem(item)
            pm_logger.info('Duplicate item second time with annexes.')
            self._duplicateItem(item, copyAnnexes=True)

    @timecall
    def _duplicateItem(self, item, copyAnnexes=False):
        '''Helper method that actually duplicated given p_item.'''
        item.clone(copyAnnexes=copyAnnexes)

    def test_pm_SpeedGetMeeting(self):
        '''Test MeetingItem.getMeeting method performances.
           We call the method 2000 times, this is what happens when displaying
           a dashboard of 100 items.'''
        self.changeUser('pmManager')
        self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        # call getMeeting 2000 times wihout caching
        self._getMeetingOnItem(item, 2000, caching=False)
        # call getMeeting 2000 times with caching
        self._getMeetingOnItem(item, 2000, caching=True)

    @timecall
    def _getMeetingOnItem(self, item, times=1, caching=True):
        ''' '''
        pm_logger.info(
            'Call {0} times, with caching={1}'.format(times, caching))
        for time in range(times):
            item.getMeeting(only_uid=False, caching=caching)

    def test_pm_ToolGroupIsNotEmpty(self):
        '''Test ToolPloneMeeting.group_is_not_empty method performances.
           More performant without ram.cache'''
        self.changeUser('pmManager')
        # call group_is_not_empty 2000 times
        self._tool_group_is_not_empty(self.vendors_uid, "creators", times=1000)

    @timecall
    def _tool_group_is_not_empty(self, org_uid, suffix, times=1):
        ''' '''
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            self.tool.group_is_not_empty(self.vendors_uid, "creators")

    def test_pm_SpeedGetMemberInfo(self):
        '''Test MembershipTool.getMemberInfo that is monkeypatched.
           This needs to be done manually, enable or disable ram.cache decorator.'''
        self.changeUser('pmManager')
        # call getMemberInfo 1000 times
        membership = api.portal.get_tool('portal_membership')
        self._get_member_info(membership, times=1000)

    @timecall
    def _get_member_info(self, membership, times=1):
        ''' '''
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            membership.getMemberInfo("pmManager")

    def test_pm_SpeedGetUserFullname(self):
        '''Test imio.helpers.content.get_user_fullname.'''
        self.changeUser('pmManager')
        # call get_user_fullname 1000 times
        self._get_user_fullname(times=1000)

    @timecall
    def _get_user_fullname(self, userId="pmManager", times=1):
        ''' '''
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            get_user_fullname(userId)

    def test_pm_SpeedItemQueryState(self):
        '''Test MeetingItem.query_state.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # get a large workflow_history
        self.validateItem(item)
        self.backToState(item, 'itemcreated')
        self.validateItem(item)
        self.backToState(item, 'itemcreated')
        self.validateItem(item)
        # call query_state 1000 times
        self._query_state(item, times=1000)

    @timecall
    def _query_state(self, item, times=1):
        ''' '''
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            item.query_state()

    def test_pm_SpeedIsPowerObserverForCfg(self):
        '''Test utils.isPowerObserverForCfg.'''
        self.changeUser('pmManager')
        # call it 1000 times
        self._isPowerObserverForCfg(times=1000)

    @timecall
    def _isPowerObserverForCfg(self, times=1):
        ''' '''
        cfg = self.meetingConfig
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            isPowerObserverForCfg(cfg)
            isPowerObserverForCfg(cfg, ["powerobservers"])
            isPowerObserverForCfg(cfg, ["restrictedpowerobservers"])
            isPowerObserverForCfg(cfg, ["powerobservers", "restrictedpowerobservers"])

    def test_pm_SpeedUserIsAmong(self):
        '''Test ToolPloneMeeting.userIsAmong.'''
        self.changeUser('pmManager')
        # call it 1000 times
        self._userIsAmong(times=1000)

    @timecall
    def _userIsAmong(self, times=1):
        ''' '''
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            self.tool.userIsAmong(["advisers"])
            self.tool.userIsAmong(["creators", "reviewers"])
            self.tool.userIsAmong(["powerobservers"])

    def test_pm_SpeedUtilsdown_or_up_wf(self):
        '''Test utils.down_or_up_wf for MeetingItem.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # get a larger workflow_history
        self.validateItem(item)
        self.backToState(item, 'itemcreated')
        self.validateItem(item)
        self.backToState(item, 'itemcreated')
        self.validateItem(item)
        # call down_or_up_wf 1000 times
        self._down_or_up_wf(item, times=1000)

    @timecall
    def _down_or_up_wf(self, item, times=1):
        ''' '''
        pm_logger.info('Call {0} times'.format(times))
        for time in range(times):
            down_or_up_wf(item)

    def test_pm_CheckAndHasPermission(self):
        '''Test _checkPermission and user.has_permission.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # call _checkPermission 1000 times
        self._check_permission(item, times=1000)
        # call user.has_permission 1000 times
        self._user_has_permission(item, times=1000)

    @timecall
    def _check_permission(self, item, times=1):
        ''' '''
        pm_logger.info('Call _checkPermission {0} times'.format(times))
        for time in range(times):
            _checkPermission("ModifyPortalContent", item)

    @timecall
    def _user_has_permission(self, item, times=1):
        ''' '''
        pm_logger.info('Call user.has_permission {0} times'.format(times))
        for time in range(times):
            self.member.has_permission("ModifyPortalContent", item)

    def test_pm_Speed_getLastValidationState(self):
        '''Test MeetingItemWorkflowConditions._getLastValidationState.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        wf_conditions = item.wfConditions()
        # call _getLastValidationState 1000 times
        self._check__getLastValidationState(wf_conditions, times=1000)

    @timecall
    def _check__getLastValidationState(self, wf_conditions, times=1):
        ''' '''
        pm_logger.info('Call _getLastValidationState {0} times'.format(times))
        for time in range(times):
            wf_conditions._getLastValidationState()

    def test_pm_Speed_get_full_title(self):
        '''Test organization.get_full_title.'''
        self.changeUser('pmManager')
        org = get_organizations()[0]
        # call get_full_title 1000 times
        self._check_get_full_title(org, times=1000)

    @timecall
    def _check_get_full_title(self, org, times=1):
        ''' '''
        pm_logger.info('Call organization.get_full_title {0} times'.format(times))
        for time in range(times):
            org.get_full_title()

    def test_pm_Speed_AsyncLoadItemAssemblyAndSignatures(self):
        """Test when loading @@load_item_assembly_and_signatures
           with 40 assemby members and 25 votes."""
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        # create 40 new held positions
        pm_logger.info('Creating 40 held positions...')
        for i in range(40):
            person = self.create('person')
            self.create('held_position',
                        folder=person,
                        label=str(i),
                        usages=['assemblyMember'],
                        defaults=['present', 'voter'])
        self._setUpOrderedContacts()
        # now create an item with 1 vote and one with 25 votes
        pm_logger.info('Creating meeting, items and votes...')
        self.changeUser('pmManager')
        public_item1 = self.create('MeetingItem')
        public_item25 = self.create('MeetingItem')
        secret_item1 = self.create('MeetingItem', pollType='secret')
        secret_item25 = self.create('MeetingItem', pollType='secret')
        meeting = self.create('Meeting')
        self.presentItem(public_item1)
        self.presentItem(public_item25)
        self.presentItem(secret_item1)
        self.presentItem(secret_item25)
        # setup public votes
        voters = meeting.get_voters()
        public_votes = public_item1.get_item_votes()[0]
        for voter in voters:
            public_votes['voters'][voter] = "yes"
        meeting.set_item_public_vote(public_item1, public_votes, 0)
        for i in range(25):
            meeting.set_item_public_vote(public_item25, public_votes, i)

        # setup secret votes
        secret_votes = secret_item1.get_item_votes()[0]
        secret_votes['votes']['abstain'] = 20
        secret_votes['votes']['no'] = 10
        secret_votes['votes']['yes'] = 5
        meeting.set_item_secret_vote(secret_item1, secret_votes, 0)
        for i in range(25):
            meeting.set_item_secret_vote(secret_item25, secret_votes, i)
        self._check_load_item_assembly_and_signatures(public_item1, True, 1)
        self._check_load_item_assembly_and_signatures(public_item25, True, 25)
        self._check_load_item_assembly_and_signatures(secret_item1, False, 1)
        self._check_load_item_assembly_and_signatures(secret_item25, False, 25)

    @timecall
    def _check_load_item_assembly_and_signatures(self, item, public=True, votes=1):
        ''' '''
        public = "public" if public else "secret"
        pm_logger.info('Call @@load_item_assembly_and_signatures for "{0}" '
                       'item with "{1}" vote(s)'.format(public, votes))
        item.restrictedTraverse('@@load_item_assembly_and_signatures')()

    def test_pm_Speed_MeetingConfigEdit(self):
        """Check editing a MeetingConfig, especially when using
           MeetingConfig.usingGroups as this will update every existing
           meetings and add local roles of selected usingGroups."""
        self.changeUser("siteadmin")
        cfg = self.meetingConfig
        # create 100 groups
        org_uids = []
        pm_logger.info('Creating 100 organizations...')
        for i in range(100):
            org = self.create('organization', id=i, title='Org %d' % i)
            org_uid = org.UID()
            self._select_organization(org_uid)
            org_uids.append(org_uid)
        pm_logger.info('Done.')
        cfg.setUsingGroups(org_uids)
        # create 250 meetings
        pm_logger.info('Creating 100 meetings...')
        for i in range(100):
            self.create('Meeting', date=datetime.now() + timedelta(i + 1))
        pm_logger.info('Done.')
        self._check_meeting_config_edit()

    @timecall
    def _check_meeting_config_edit(self):
        ''' '''
        pm_logger.info('Save MeetingConfig')
        notify(ObjectEditedEvent(self.meetingConfig))


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPerformances, prefix='test_pm_'))
    return suite
