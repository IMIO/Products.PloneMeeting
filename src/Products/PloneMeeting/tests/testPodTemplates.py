# -*- coding: utf-8 -*-
#
# File: testPodTemplates.py
#
# Copyright (c) 2008 by PloneGov
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

from plone.app.testing import login
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testPodTemplates(PloneMeetingTestCase):
    '''Tests various aspects of document generation through POD templates.'''

    def test_pm_Conditions(self):
        '''Tests the conditions and permissions defined for each POD
           template.'''
        # Create an item as creator
        login(self.portal, 'pmManager')
        item = self.create('MeetingItem')
        podTemplates = self.meetingConfig.getAvailablePodTemplates(item)
        self.assertEquals(len(podTemplates), 1)
        self.assertEquals(podTemplates[0].Title(), 'Meeting item')
        self.validateItem(item)
        meeting = self.create('Meeting', date='2008/06/23 15:39:00')
        podTemplates = self.meetingConfig.getAvailablePodTemplates(meeting)
        self.assertEquals(len(podTemplates), 1)
        self.assertEquals(podTemplates[0].Title(), 'Meeting agenda')
        self.presentItem(item)
        item.setDecision('Decision')
        self.decideMeeting(meeting)
        podTemplates = self.meetingConfig.getAvailablePodTemplates(meeting)
        self.assertEquals(len(podTemplates), 2)
        self.assertEquals(podTemplates[1].Title(), 'Meeting decisions')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPodTemplates, prefix='test_pm_'))
    return suite
