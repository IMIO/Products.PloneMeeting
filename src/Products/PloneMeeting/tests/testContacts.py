# -*- coding: utf-8 -*-
#
# File: testMeeting.py
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
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class testContacts(PloneMeetingTestCase):
    '''Tests various aspects of contacts management.'''

    def setUp(self):
        ''' '''
        super(testContacts, self).setUp()
        # add contacts using the CSV import
        self.changeUser('siteadmin')
        # enable attendees and signatories fields for Meeting
        cfg = self.meetingConfig
        cfg.setUsedMeetingAttributes(('attendees', 'excused', 'absents', 'signatories', ))
        # select orderedContacts
        cfg.setOrderedContacts(cfg.listSelectableContacts().keys())

    def test_pm_OrderedContacts(self):
        ''' '''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # we have selectable contacts
        self.assertTrue(cfg.getOrderedContacts())
        # create meeting and select attendees on it
        meeting = self.create('Meeting', date=DateTime())
        # contacts are still in correct order
        self.assertEqual(cfg.getOrderedContacts(), meeting.getAttendees())

    def test_pm_MeetingGetAllUsedHeldPositions(self):
        ''' '''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        # returns attendees, excused, absents, ...
        self.assertEqual(
            meeting.orderedContacts.keys(),
            [hp.UID() for hp in meeting.getAllUsedHeldPositions()])
        # for now, include_new=True does not change anything
        self.assertEqual(
            meeting.getAllUsedHeldPositions(),
            meeting.getAllUsedHeldPositions(include_new=True))
        # add a new hp in configuration
        self.changeUser('siteadmin')
        person = self.portal.contacts.get('alain-alain')
        orga = self.portal.contacts.get(PLONEGROUP_ORG)
        intids = getUtility(IIntIds)
        new_hp = api.content.create(
            container=person, type='held_position', label='New held position',
            title='New held position', position=RelationValue(intids.getId(orga)),
            usages=['assemblyMember'])
        self.changeUser('pmManager')
        # still no new value as not selected in MeetingConfig.orderedContacts
        self.assertEqual(
            meeting.getAllUsedHeldPositions(),
            meeting.getAllUsedHeldPositions(include_new=True))
        # select new hp
        cfg.setOrderedContacts(cfg.listSelectableContacts().keys())
        self.assertEqual(
            meeting.getAllUsedHeldPositions() + (new_hp, ),
            meeting.getAllUsedHeldPositions(include_new=True))
        # unselect everything on MeetingConfig, all values still available on meeting
        cfg.setOrderedContacts(())
        self.assertEqual(
            meeting.getAllUsedHeldPositions(), meeting.getAttendees(theObjects=True))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testContacts, prefix='test_pm_'))
    return suite
