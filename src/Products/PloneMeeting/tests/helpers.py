# -*- coding: utf-8 -*-
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


class PloneMeetingTestingHelpers:
    '''Stub class that provides some helper methods about testing.'''

    TRANSITIONS_FOR_PROPOSING_ITEM_1 = TRANSITIONS_FOR_PROPOSING_ITEM_2 = ('propose', )
    TRANSITIONS_FOR_VALIDATING_ITEM_1 = TRANSITIONS_FOR_VALIDATING_ITEM_2 = ('propose', 'validate', )
    TRANSITIONS_FOR_PRESENTING_ITEM_1 = TRANSITIONS_FOR_PRESENTING_ITEM_2 = ('propose', 'validate', 'present', )
    BACK_TO_WF_PATH = {'proposed': ('backToItemFrozen', 'backToPresented', 'backToValidated', 'backToProposed', ),
                       'validated': ('backToItemFrozen', 'backToPresented', 'backToValidated', )}
    WF_STATE_NAME_MAPPINGS = {'proposed': 'proposed',
                              'validated': 'validated'}

    def _createMeetingWithItems(self):
        '''Create a meeting with a bunch of items.'''
        currentUser = self.portal.portal_membership.getAuthenticatedMember().getId()
        self.changeUser('admin')
        meetingDate = DateTime()
        meeting = self.create('Meeting', date=meetingDate)
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
            self.presentItem(item)
        self.changeUser(currentUser)
        return meeting

    def proposeItem(self, item):
        '''Validate passed p_item using TRANSITIONS_FOR_PROPOSING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PROPOSING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(item, getattr(self, ('TRANSITIONS_FOR_PROPOSING_ITEM_%d' % meetingConfigNumber)))

    def validateItem(self, item):
        '''Validate passed p_item using TRANSITIONS_FOR_VALIDATING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_VALIDATING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(item, getattr(self, ('TRANSITIONS_FOR_VALIDATING_ITEM_%d' % meetingConfigNumber)))

    def presentItem(self, item):
        '''Validate passed p_item using TRANSITIONS_FOR_PRESENTING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PRESENTING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(item, getattr(self, ('TRANSITIONS_FOR_PRESENTING_ITEM_%d' % meetingConfigNumber)))

    def backToState(self, itemOrMeeting, state):
        """Set the p_item back to p_state."""
        # if a wf path is defined in BACK_TO_WF_PATH to go to relevant state, use it
        # if not, trigger every 'backToXXX' existing transition
        useDefinedWfPath = False
        if state in self.BACK_TO_WF_PATH:
            transitions = self.BACK_TO_WF_PATH[state]
            useDefinedWfPath = True
        else:
            transitions = self.transitions(itemOrMeeting)
        # check if a mapping exist for state name
        if state in self.WF_STATE_NAME_MAPPINGS:
            state = self.WF_STATE_NAME_MAPPINGS[state]
        while not itemOrMeeting.queryState() == state:
            if not useDefinedWfPath:
                transitions = self.transitions(itemOrMeeting)
            for tr in transitions:
                if tr.startswith('back') and (useDefinedWfPath and tr in self.transitions(itemOrMeeting)):
                    self.do(itemOrMeeting, tr)
                    break

    def _doTransitionsFor(self, itemOrMeeting, transitions):
        """Helper that just trigger given p_transitions on given p_itemOrMeeting."""
        currentUser = self.portal.portal_membership.getAuthenticatedMember().getId()
        # do things as admin to avoid permission issues
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
