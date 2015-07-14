# -*- coding: utf-8 -*-
#
# File: testMeetingFile.py
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

from Products.CMFCore.permissions import ModifyPortalContent
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testMeetingFile(PloneMeetingTestCase):
    '''Tests the MeetingFileType class methods.'''

    def test_pm_MayChangeToPrint(self):
        '''By default, mayChangeToPrint is only if toPrint activated
           and user may edit the meetingFile.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # not activated in the cfg, not changeable
        self.assertFalse(cfg.getEnableAnnexToPrint())
        self.assertFalse(annex.adapted().mayChangeToPrint())
        cfg.setEnableAnnexToPrint(True)
        self.assertTrue(annex.adapted().mayChangeToPrint())
        # propose it, no more editable and no more mayChangeToPrint
        self.proposeItem(item)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(annex.adapted().mayChangeToPrint())

    def test_pm_MayChangeConfidentiality(self):
        '''By default, mayChangeConfidentiality is only if activated
           and user may edit the meetingFile and is a Manager.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # not activated in the cfg and user is not a Manager
        self.assertFalse(cfg.getEnableAnnexConfidentiality())
        self.assertFalse(annex.adapted().mayChangeConfidentiality())
        cfg.setEnableAnnexConfidentiality(True)
        self.assertFalse(annex.adapted().mayChangeConfidentiality())
        # validate it so pmManager may see it
        self.validateItem(item)
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(annex.adapted().mayChangeConfidentiality())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingFile, prefix='test_pm_'))
    return suite
