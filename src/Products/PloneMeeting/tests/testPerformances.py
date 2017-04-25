# -*- coding: utf-8 -*-
#
# File: testPerformances.py
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

from DateTime import DateTime
from profilehooks import timecall

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from PloneMeetingTestCase import pm_logger


class testPerformances(PloneMeetingTestCase):
    '''Tests various aspects of performances.'''

    def setUp(self):
        # call parent setUp
        PloneMeetingTestCase.setUp(self)

    def _setupForDelayingItems(self, number_of_items, number_of_annexes):
        """ """
        meeting, uids = self._setupMeetingItemsWithAnnexes(number_of_items, number_of_annexes, present_items=True)
        # set the meeting in the 'decided' state
        self.decideMeeting(meeting)
        # in some wfs, deciding a meeting will accept every items...
        # set back items to the 'itemfrozen' state
        for itemInMeeting in meeting.getItems():
            if itemInMeeting.queryState() == 'itemfrozen':
                break
            self.do(itemInMeeting, 'backToItemFrozen')

        return meeting, uids

    def _setupMeetingItemsWithAnnexes(self, number_of_items, number_of_annexes, with_meeting=True, present_items=False):
        self.changeUser('pmManager')
        meeting = None
        if with_meeting:
            # create a meeting
            meeting = self.create('Meeting', date='2007/12/11 09:00:00')
        data = {}
        uids = []
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
            uids.append(item.UID())
            item.setDecision('<p>A decision</p>')
            # add annexes
            if number_of_annexes:
                for j in range(number_of_annexes):
                    self.addAnnex(item, annexTitle="Annex number %d" % j)
                pm_logger.info('Added %d annexes to the item number %s' %
                               (number_of_annexes, total_created_items))
            if present_items:
                self.presentItem(item)
        return meeting, uids

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
        pm_logger.info('Freezing meeting without updateItemReferences.')
        self.request.set('defer_Meeting_updateItemReferences', True)
        self.freezeMeeting(meeting)
        self.request.set('defer_Meeting_updateItemReferences', False)
        # update every items
        pm_logger.info(
            'Updating item references for %d items presented in a meeting starting from item number %s.' % (250, 0))
        self._updateItemReferences(meeting)
        # update items starting from 100th item
        pm_logger.info(
            'Updating item references for %d items presented in a meeting starting from item number %s.' % (250, 100))
        self._updateItemReferences(meeting, startNumber=100*100)
        # update items starting from 200th item
        pm_logger.info(
            'Updating item references for %d items presented in a meeting starting from item number %s.' % (250, 200))
        self._updateItemReferences(meeting, startNumber=200*100)

    @timecall
    def _updateItemReferences(self, meeting, startNumber=0):
        '''Helper method that actually compute every items itemReference for p_meeting.'''
        # set back every items reference to '' so the entire process including reindex of SearchableText is done
        for item in meeting.getItems():
            item.setItemReference('')
        meeting.updateItemReferences(startNumber=startNumber)

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
        meeting, uids = self._setupMeetingItemsWithAnnexes(50, 0)
        items = [brain.getObject() for brain in self.portal.portal_catalog(UID=uids)]
        # called when no item in the meeting
        self._presentSeveralItems(items)
        # called second times whith items in the meeting
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.'
                       % (50, len(meeting.getRawItems())))
        dummy_meeting, uids = self._setupMeetingItemsWithAnnexes(50, 0, with_meeting=False)
        items = [brain.getObject() for brain in self.portal.portal_catalog(UID=uids)]
        self._presentSeveralItems(items)
        # called third times whith items in the meeting
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.'
                       % (50, len(meeting.getRawItems())))
        dummy_meeting, uids = self._setupMeetingItemsWithAnnexes(50, 0, with_meeting=False)
        items = [brain.getObject() for brain in self.portal.portal_catalog(UID=uids)]
        self._presentSeveralItems(items)
        # called fourth times whith items in the meeting
        pm_logger.info('Presenting %d items without annexes in a meeting containing %d items.'
                       % (50, len(meeting.getRawItems())))
        dummy_meeting, uids = self._setupMeetingItemsWithAnnexes(50, 0, with_meeting=False)
        items = [brain.getObject() for brain in self.portal.portal_catalog(UID=uids)]
        self._presentSeveralItems(items)

    def test_pm_SendSeveralItemsWithAnnexesToAnotherMC(self):
        '''We will freeze a meeting containing 50 items from which 25 need to be send
           to another MC.  Every items contain 5 annexes.'''
        pm_logger.info('Freezing a meeting containing %d items and sending %d items to another MC.' % (50, 25))
        cfg = self.meetingConfig
        cfg.setUseGroupsAsCategories(True)
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                           'reverse': '0'}, ))
        cfg2 = self.meetingConfig2
        cfg2.setUseGroupsAsCategories(True)
        cfg2.setInsertingMethodsOnAddItem(({'insertingMethod': 'on_proposing_groups',
                                            'reverse': '0'}, ))
        cfg2Id = cfg2.getId()
        # make items sent to config2 automatically presented in the next meeting
        cfg.setMeetingConfigsToCloneTo(({'meeting_config': '%s' % cfg2Id,
                                         'trigger_workflow_transitions_until': '%s.%s' %
                                         (cfg2Id, 'present')},))
        cfg.setItemAutoSentToOtherMCStates((u'itemfrozen', ))
        meeting, uids = self._setupMeetingItemsWithAnnexes(50, 5, present_items=True)
        items = meeting.getItems()
        # make 50 items sendable to another MC
        for item in items[0:25]:
            item.setOtherMeetingConfigsClonableTo((self.meetingConfig2.getId(), ))
            item.reindexObject(idxs=['sentToInfos', ])

        # create meeting in cfg2 in which items will be presented
        self.setMeetingConfig(cfg2Id)
        now = DateTime()
        meeting2 = self.create('Meeting', date=now + 1)
        self.assertFalse(meeting2.getItems())

        # freeze the meeting, this will do the job
        self._freezeMeetingAndSendItemsToAnotherMC(meeting)

        # make sure meeting2 has items
        self.assertEquals(len(meeting2.getItems()), 25)

    @timecall
    def _delaySeveralItems(self, meeting, uids):
        '''Helper method that actually delays the items.'''
        decideView = meeting.restrictedTraverse('@@decide-several-items')
        decideView(uids=uids, transition='delay')

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
            pm_logger.info('Creating meeting %d of %s' % (i+1, number_of_meetings))
            meeting = self.create('Meeting', date='2007/12/%d 09:00:00' % (i + 1))
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
        meetingAtHalf = meetings[int(number_of_meetings/2)]
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
        for item in meeting.getItems():
            item.getItemNumber(relativeTo='meetingConfig')

    def _setupForMeetingGroups(self, number_of_groups):
        self.changeUser('admin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # remove existing groups and add our own
        # make what necessary for groups to be removable...
        cfg.setSelectableCopyGroups(())
        cfg.setSelectableAdvisers(())
        cfg2.setSelectableCopyGroups(())
        cfg2.setSelectableAdvisers(())
        for mGroup in self.tool.objectValues('MeetingGroup'):
            for ploneGroup in mGroup.getPloneGroups():
                for memberId in ploneGroup.getGroupMemberIds():
                    ploneGroup.removeMember(memberId)
        # remove items defined in the tool
        self._removeConfigObjectsFor(cfg)
        self._removeConfigObjectsFor(cfg2)

        # remove groups
        ids_to_remove = []
        for group in self.tool.objectValues('MeetingGroup'):
            ids_to_remove.append(group.getId())
        self.tool.manage_delObjects(ids=ids_to_remove)
        # create groups
        for i in range(number_of_groups):
            groupId = self.tool.invokeFactory('MeetingGroup', id=i, title='Group %d' % i)
            group = getattr(self.tool, groupId)
            group._at_creation_flag = False
            group.at_post_create_script()

    def test_pm_GetMeetingGroupsCaching(self):
        '''Test ToolPloneMeeting.getMeetingGroups caching.'''
        # first test with 10 groups
        self._setupForMeetingGroups(10)
        pm_logger.info('getMeetingGroups called 1 time with %d activated groups.' % 10)
        # first call, even when asking caching, it is not as never computed but it is cached
        pm_logger.info('No caching.')
        self._getMeetingGroupsOnTool(times=1, caching=True)
        # second time, cached
        pm_logger.info('Caching.')
        self._getMeetingGroupsOnTool(times=1, caching=True)
        # remove cache
        self.cleanMemoize()
        pm_logger.info('getMeetingGroups called 100 times with %d activated groups.' % 10)
        pm_logger.info('No caching.')
        self._getMeetingGroupsOnTool(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getMeetingGroupsOnTool(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # test with 100 groups
        self._setupForMeetingGroups(100)
        pm_logger.info('getMeetingGroups called 1 time with %d activated groups.' % 100)
        # first call, even when asking caching, it is not as never computed but it is cached
        pm_logger.info('No caching.')
        self._getMeetingGroupsOnTool(times=1, caching=True)
        # second time, cached
        pm_logger.info('Caching.')
        self._getMeetingGroupsOnTool(times=1, caching=True)
        # remove cache
        self.cleanMemoize()
        pm_logger.info('getMeetingGroups called 100 times with %d activated groups.' % 100)
        pm_logger.info('No caching.')
        self._getMeetingGroupsOnTool(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getMeetingGroupsOnTool(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # test with 250 groups
        self._setupForMeetingGroups(250)
        pm_logger.info('getMeetingGroups called 1 time with %d activated groups.' % 250)
        # first call, even when asking caching, it is not as never computed but it is cached
        pm_logger.info('No caching.')
        self._getMeetingGroupsOnTool(times=1, caching=True)
        # second time, cached
        pm_logger.info('Caching.')
        self._getMeetingGroupsOnTool(times=1, caching=True)
        # remove cache
        self.cleanMemoize()
        pm_logger.info('getMeetingGroups called 100 times with %d activated groups.' % 250)
        pm_logger.info('No caching.')
        self._getMeetingGroupsOnTool(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getMeetingGroupsOnTool(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

    @timecall
    def _getMeetingGroupsOnTool(self, times=1, caching=True):
        ''' '''
        for time in range(times):
            self.tool.getMeetingGroups(notEmptySuffix='advisers', caching=caching)

    def test_pm_GetMeetingConfig(self):
        '''Test ToolPloneMeeting.getMeetingConfig method performances.
           We call the method 2000 times, this is what happens when displaying
           a meeting containing 100 items.'''
        # create an item
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # call getMeetingConfig 2000 times wihout caching
        self._getMeetingConfigOnTool(item, 2000, caching=False)
        # call getMeetingConfig 2000 times with caching
        self._getMeetingConfigOnTool(item, 2000, caching=True)

    @timecall
    def _getMeetingConfigOnTool(self, context, times=1, caching=True):
        ''' '''
        for time in range(times):
            self.tool.getMeetingConfig(context, caching=caching)

    def test_pm_GetAuthenticatedMember(self):
        '''Test performance between portal_membership.getAuthenticatedMember and
           plone_portal_state.member().'''
        # create an item
        self.changeUser('pmManager')
        # call getAuthenticatedMember 2000 times
        self._portalMembershipGetAuthenticatedMember(2000)
        # call plone_portal_state.member() 2000 times
        self._plonePortalStateMember(2000)

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

    def _setupForMeetingCategories(self, number_of_categories, withUsingGroups=False):
        self.changeUser('admin')
        # remove items in the tool and categories
        self._removeConfigObjectsFor(self.meetingConfig, folders=['recurringitems', 'itemtemplates', 'categories'])
        # create categories
        for i in range(number_of_categories):
            catId = self.meetingConfig.categories.invokeFactory('MeetingCategory', id=i, title='Category %d' % i)
            catObj = getattr(self.meetingConfig.categories, catId)
            if withUsingGroups:
                catObj.setUsingGroups(('developers', ))
            catObj._at_creation_flag = False
            catObj.at_post_create_script()

    def test_pm_GetCategoriesCaching(self):
        '''Test MeetingConfig.getCategories caching.'''
        self.meetingConfig.setUseGroupsAsCategories(False)
        # first test with 10 groups without usingGroups
        self._setupForMeetingCategories(10, withUsingGroups=False)
        pm_logger.info('getCategories called 100 times with %d activated groups, without usingGroups.' % 10)
        pm_logger.info('No caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # first test with 10 groups with usingGroups
        self._setupForMeetingCategories(10, withUsingGroups=True)
        pm_logger.info('getCategories called 100 times with %d activated groups, with usingGroups.' % 10)
        pm_logger.info('No caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # test with 100 categories without usingGroups
        self._setupForMeetingCategories(100, withUsingGroups=False)
        pm_logger.info('getCategories called 100 times with %d activated groups, without usingGroups.' % 100)
        pm_logger.info('No caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # test with 100 categories with usingGroups
        self._setupForMeetingCategories(100, withUsingGroups=True)
        pm_logger.info('getCategories called 100 times with %d activated groups, with usingGroups.' % 100)
        pm_logger.info('No caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # test with 250 categories without usingGroups
        self._setupForMeetingCategories(250, withUsingGroups=False)
        pm_logger.info('getCategories called 100 times with %d activated groups, without usingGroups.' % 250)
        pm_logger.info('No caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

        # test with 250 categories with usingGroups
        self._setupForMeetingCategories(250, withUsingGroups=True)
        pm_logger.info('getCategories called 100 times with %d activated groups, with usingGroups.' % 250)
        pm_logger.info('No caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=False)
        # second time, cached
        pm_logger.info('Caching.')
        self._getCategoriesOnMeetingConfig(times=100, caching=True)
        # remove cache
        self.cleanMemoize()

    @timecall
    def _getCategoriesOnMeetingConfig(self, times=1, caching=True):
        ''' '''
        for time in range(times):
            self.meetingConfig.getCategories(userId='pmManager', caching=caching)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPerformances, prefix='test_pm_'))
    return suite
