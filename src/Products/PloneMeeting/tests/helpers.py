# -*- coding: utf-8 -*-
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


class PloneMeetingTestingHelpers:
    '''Stub class that provides some helper methods about testing.'''

    TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_1 = TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_2 = ('propose', )
    TRANSITIONS_FOR_PROPOSING_ITEM_1 = TRANSITIONS_FOR_PROPOSING_ITEM_2 = ('propose', 'prevalidate', )

    TRANSITIONS_FOR_VALIDATING_ITEM_1 = TRANSITIONS_FOR_VALIDATING_ITEM_2 = ('propose', 'validate', )
    TRANSITIONS_FOR_PREVALIDATING_ITEM_1 = TRANSITIONS_FOR_PREVALIDATING_ITEM_2 = ('propose', 'prevalidate', )
    TRANSITIONS_FOR_PRESENTING_ITEM_1 = TRANSITIONS_FOR_PRESENTING_ITEM_2 = ('propose', 'validate', 'present', )

    TRANSITIONS_FOR_PUBLISHING_MEETING_1 = TRANSITIONS_FOR_PUBLISHING_MEETING_2 = ('publish', )
    TRANSITIONS_FOR_FREEZING_MEETING_1 = TRANSITIONS_FOR_FREEZING_MEETING_2 = ('publish', 'freeze', )
    TRANSITIONS_FOR_DECIDING_MEETING_1 = TRANSITIONS_FOR_DECIDING_MEETING_2 = ('publish', 'freeze', 'decide', )
    TRANSITIONS_FOR_CLOSING_MEETING_1 = TRANSITIONS_FOR_CLOSING_MEETING_2 = ('publish',
                                                                             'freeze',
                                                                             'decide',
                                                                             'close', )
    TRANSITIONS_FOR_ACCEPTING_ITEMS_MEETING_1 = TRANSITIONS_FOR_ACCEPTING_ITEMS_MEETING_2 = ('publish', 'freeze', )
    BACK_TO_WF_PATH_1 = BACK_TO_WF_PATH_2 = {
        # Meeting
        'created': ('backToFrozen',
                    'backToPublished',
                    'backToCreated',),
        # MeetingItem
        'itemcreated': ('backToItemFrozen',
                        'backToPresented',
                        'backToValidated',
                        'backToProposed',
                        'backToItemCreated', ),
        'proposed': ('backToItemFrozen',
                     'backToPresented',
                     'backToValidated',
                     'backToProposed', ),
        'validated': ('backToItemFrozen',
                      'backToPresented',
                      'backToValidated', ),
        'presented': ('backToItemFrozen',
                      'backToItemPublished',
                      'backToPresented', )}

    WF_STATE_NAME_MAPPINGS = {'itemcreated': 'itemcreated',
                              'proposed_first_level': 'proposed',
                              'proposed': 'proposed',
                              'validated': 'validated',
                              'presented': 'presented'}

    WF_TRANSITION_NAME_MAPPINGS = {
        'backToItemCreated': 'backToItemCreated',
        'backToProposed': 'backToProposed', }

    # in which state an item must be after a particular meeting transition?
    ITEM_WF_STATE_AFTER_MEETING_TRANSITION = {'publish_decisions': 'confirmed',
                                              'close': 'confirmed', }

    def _createMeetingWithItems(self, withItems=True, meetingDate=DateTime()):
        '''Create a meeting with a bunch of items.'''
        meeting = self.create('Meeting', date=meetingDate)
        # a meeting could be created with items if it has
        # recurring items...  But we can also add some more...
        if withItems:
            item1 = self.create('MeetingItem')  # id=o2
            item1.setProposingGroup('vendors')
            item1.setAssociatedGroups(('developers',))
            item1.setPrivacy('public')
            item1.setCategory('research')
            item2 = self.create('MeetingItem')  # id=o3
            item2.setProposingGroup('developers')
            item2.setPrivacy('public')
            item2.setCategory('development')
            item3 = self.create('MeetingItem')  # id=o4
            item3.setProposingGroup('vendors')
            item3.setPrivacy('secret')
            item3.setCategory('development')
            item4 = self.create('MeetingItem')  # id=o5
            item4.setProposingGroup('developers')
            item4.setPrivacy('secret')
            item4.setCategory('events')
            item5 = self.create('MeetingItem')  # id=o6
            item5.setProposingGroup('vendors')
            item5.setPrivacy('public')
            item5.setCategory('events')
            for item in (item1, item2, item3, item4, item5):
                item.setDecision('<p>A decision</p>')
                self.presentItem(item)
        return meeting

    def _getTransitionsToCloseAMeeting(self):
        """ """
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        return getattr(self, ('TRANSITIONS_FOR_CLOSING_MEETING_%d' % meetingConfigNumber))

    def _getNecessaryMeetingTransitionsToAcceptItem(self):
        '''Returns the necessary transitions to trigger on the Meeting before being
           able to accept an item.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        return getattr(self, ('TRANSITIONS_FOR_ACCEPTING_ITEMS_MEETING_%d' % meetingConfigNumber))

    def _getTransitionToReachState(self, obj, state):
        '''Given a state, return a transition that will set the obj in this state.'''
        wf = self.wfTool.getWorkflowsFor(obj)[0]
        res = ''
        availableTransitions = self.transitions(obj)
        for transition in wf.transitions.values():
            if not transition.id in availableTransitions:
                continue
            if transition.new_state_id == state:
                res = transition.id
                break
        return res

    def proposeItem(self, item, first_level=False):
        '''Propose passed p_item using TRANSITIONS_FOR_PROPOSING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PROPOSING_ITEM_x is 1 or 2.
           If p_first_level is True, we will use TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_x,
           this makes it possible to reach an intermediate propose level.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        if first_level:
            self._doTransitionsFor(item,
                                   getattr(self,
                                           ('TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_%d' % meetingConfigNumber)))
        else:
            self._doTransitionsFor(item,
                                   getattr(self,
                                           ('TRANSITIONS_FOR_PROPOSING_ITEM_%d' % meetingConfigNumber)))

    def prevalidateItem(self, item):
        '''Prevalidate passed p_item using TRANSITIONS_FOR_PREVALIDATING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PREVALIDATING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(item, getattr(self, ('TRANSITIONS_FOR_PREVALIDATING_ITEM_%d' % meetingConfigNumber)))

    def validateItem(self, item):
        '''Validate passed p_item using TRANSITIONS_FOR_VALIDATING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_VALIDATING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(item, getattr(self, ('TRANSITIONS_FOR_VALIDATING_ITEM_%d' % meetingConfigNumber)))

    def presentItem(self, item):
        '''Present passed p_item using TRANSITIONS_FOR_PRESENTING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PRESENTING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(item, getattr(self, ('TRANSITIONS_FOR_PRESENTING_ITEM_%d' % meetingConfigNumber)))

    def publishMeeting(self, meeting):
        '''Publish passed p_meeting using TRANSITIONS_FOR_PUBLISHING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PUBLISHING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(meeting, getattr(self, ('TRANSITIONS_FOR_PUBLISHING_MEETING_%d' % meetingConfigNumber)))

    def freezeMeeting(self, meeting):
        '''Freeze passed p_meeting using TRANSITIONS_FOR_FREEZING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_FREEZING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(meeting, getattr(self, ('TRANSITIONS_FOR_FREEZING_MEETING_%d' % meetingConfigNumber)))

    def decideMeeting(self, meeting):
        '''Decide passed p_meeting using TRANSITIONS_FOR_DECIDING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_DECIDING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(meeting, getattr(self, ('TRANSITIONS_FOR_DECIDING_MEETING_%d' % meetingConfigNumber)))

    def closeMeeting(self, meeting):
        '''Close passed p_meeting using TRANSITIONS_FOR_CLOSING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_CLOSING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(meeting, getattr(self, ('TRANSITIONS_FOR_CLOSING_MEETING_%d' % meetingConfigNumber)))

    def backToState(self, itemOrMeeting, state):
        """Set the p_item back to p_state.
           Given p_state MUST BE original state name, aka state existing in PloneMeeting workflow."""
        # if a wf path is defined in BACK_TO_WF_PATH_x to go to relevant state, use it
        # if not, trigger every 'backToXXX' existing transition
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        BACK_TO_WF_PATH = getattr(self, 'BACK_TO_WF_PATH_%d' % meetingConfigNumber)
        useDefinedWfPath = False
        if state in BACK_TO_WF_PATH:
            transitions = BACK_TO_WF_PATH[state]
            useDefinedWfPath = True
        # check if a mapping exist for state name
        if state in self.WF_STATE_NAME_MAPPINGS:
            state = self.WF_STATE_NAME_MAPPINGS[state]
        # do things as admin to avoid permission issues
        currentUser = self.member.getId()
        self.changeUser('admin')
        while not itemOrMeeting.queryState() == state:
            if not useDefinedWfPath:
                transitions = self.transitions(itemOrMeeting)
            for tr in transitions:
                if (tr.startswith('back') or useDefinedWfPath) and tr in self.transitions(itemOrMeeting):
                    self.do(itemOrMeeting, tr)
                    break
        self.changeUser(currentUser)

    def _doTransitionsFor(self, itemOrMeeting, transitions):
        """Helper that just trigger given p_transitions on given p_itemOrMeeting."""
        # do things as admin to avoid permission issues
        currentUser = self.member.getId()
        self.changeUser('admin')
        for tr in transitions:
            if tr in self.transitions(itemOrMeeting):
                self.do(itemOrMeeting, tr)
        self.changeUser(currentUser)

    def _determinateUsedMeetingConfigNumber(self):
        """Helper method that check if we use meetingConfig or meetingConfig2."""
        if self.meetingConfig.getId() == self.meetingConfig2.getId():
            # we are using meetingConfig2
            return 2
        return 1

    def _removeAllMembers(self, group, members):
        """Allow to remove all members from a group.
           Overrided to do it as 'Manager' to be able not
           to change permissions ever lines"""
        from plone.app.testing.helpers import setRoles
        currentMember = self.portal.portal_membership.getAuthenticatedMember()
        currentMemberRoles = currentMember.getRoles()
        setRoles(self.portal, currentMember.getId(), currentMemberRoles + ['Manager', ])
        for member in members:
            group.removeMember(member)
        setRoles(self.portal, currentMember.getId(), currentMemberRoles)

    def _addAllMembers(self, group, members):
        """Allow to add again all the members from a group.
           Overrided to do it as 'Manager' to be able not
           to change permissions ever lines"""
        from plone.app.testing.helpers import setRoles
        currentMember = self.portal.portal_membership.getAuthenticatedMember()
        currentMemberRoles = currentMember.getRoles()
        setRoles(self.portal, currentMember.getId(), currentMemberRoles + ['Manager', ])
        for member in members:
            group.addMember(member)
        setRoles(self.portal, currentMember.getId(), currentMemberRoles)
