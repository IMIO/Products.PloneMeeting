# -*- coding: utf-8 -*-
#
# File: testMeetingFileType.py
#
# Copyright (c) 2007-2013 by Imio.be
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

from OFS.ObjectManager import BeforeDeleteException
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testMeetingFileType(PloneMeetingTestCase):
    '''Tests the MeetingFileType class methods.'''

    def test_pm_CanNotRemoveLinkedMeetingFileType(self):
        '''While removing a MeetingFileType, it should raise if it is used by a MeetingFile...'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        meetingFileType = annex.getMeetingFileType()
        self.changeUser('admin')
        # if we try to remove this meetingFileType, it raises an Exception
        meetingFileTypesFolder = meetingFileType.aq_inner.aq_parent
        self.assertRaises(BeforeDeleteException,
                          meetingFileTypesFolder.manage_delObjects,
                          [meetingFileType.getId(), ])
        # we can remove a MeetingFileType that is not linked to anything...
        meetingFileTypesFolder.manage_delObjects(['item-annex', ])
        # if we remove the MeetingFile linked to the MeetingFileType, we can remove it
        item.manage_delObjects([annex.getId(), ])
        meetingFileTypesFolder.manage_delObjects([meetingFileType.getId(), ])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingFileType, prefix='test_pm_'))
    return suite
