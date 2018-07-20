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

from collective.contact.plonegroup.config import PLONEGROUP_ORG
from DateTime import DateTime
from plone import api
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from z3c.relationfield.relation import RelationValue
from zExceptions import Redirect
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

    def test_pm_CanNotDeleteUsedHeldPosition(self):
        ''' '''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        person = self.portal.contacts.get('alain-alain')
        hp = person.get_held_positions()[0]
        hp_uid = hp.UID()
        self.assertTrue(hp_uid in meeting.getAttendees())
        # hp not deletable because used in MC and meeting
        self.changeUser('siteadmin')
        self.assertRaises(Redirect, api.content.delete, hp)

        # unselect from MeetingConfig.orderedContacts,
        # still not deletable because used by a meeting
        orderedContacts = list(cfg.getOrderedContacts())
        orderedContacts.remove(hp_uid)
        cfg.setOrderedContacts(orderedContacts)
        self.assertRaises(Redirect, api.content.delete, hp)

        # unselect hp from meeting, now it is deletable
        del meeting.orderedContacts[hp.UID()]
        self.assertFalse(hp_uid in meeting.getAttendees())
        api.content.delete(hp)
        self.assertFalse(person.get_held_positions())

    def test_pm_ItemAbsents(self):
        '''Item absents management, byebye and welcome item attendees.'''
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        meeting_attendees = meeting.getAttendees()
        self.assertTrue(meeting_attendees)
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item1_uid = item1.UID()
        item2_uid = item2.UID()
        self.presentItem(item1)
        self.presentItem(item2)

        # for now attendees are the same on meeting and items
        self.assertEqual(meeting_attendees, item1.getAttendees())
        self.assertEqual(meeting_attendees, item2.getAttendees())
        self.assertFalse(meeting.getItemAbsents())
        self.assertFalse(meeting.getItemAbsents(by_absents=True))

        # byebye person on item1 and item2
        person = self.portal.contacts.get('alain-alain')
        hp = person.get_held_positions()[0]
        hp_uid = hp.UID()
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form')
        byebye_form.person_uid = hp_uid
        byebye_form.apply_until_item_number = 200
        self.assertFalse(item1.getItemAbsents())
        self.assertFalse(item2.getItemAbsents())
        byebye_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertEqual(item2.getItemAbsents(), (hp_uid, ))
        self.assertEqual(
            sorted(meeting.getItemAbsents().keys()),
            sorted([item1_uid, item2_uid]))
        self.assertEqual(meeting.getItemAbsents(by_absents=True).keys(), [hp_uid])
        self.assertEqual(
            sorted(meeting.getItemAbsents(by_absents=True)[hp_uid]),
            sorted([item1_uid, item2_uid]))

        # welcome person on item2
        welcome_form = item2.restrictedTraverse('@@item_welcome_attendee_form')
        welcome_form.person_uid = hp_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertFalse(item2.getItemAbsents())

        # when an item is removed from meeting,
        # itemAbsents info regarding this item are removed as well
        self.assertTrue(item1_uid in meeting.itemAbsents)
        self.backToState(item1, 'validated')
        self.assertFalse(item1_uid in meeting.itemAbsents)

    def test_pm_MeetingGetItemAbsents(self):
        '''Test the Meeting.getItemAbsents method.'''
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        meeting_attendees = meeting.getAttendees()
        self.assertTrue(meeting_attendees)
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.presentItem(item1)
        self.presentItem(item2)

        # for now attendees are the same on meeting and items
        self.assertEqual(meeting_attendees, item1.getAttendees())
        self.assertEqual(meeting_attendees, item2.getAttendees())

        # byebye person on item1 and item2
        person = self.portal.contacts.get('alain-alain')
        hp = person.get_held_positions()[0]
        hp_uid = hp.UID()
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form')
        byebye_form.person_uid = hp_uid
        byebye_form.apply_until_item_number = 200
        self.assertFalse(item1.getItemAbsents())
        self.assertFalse(item2.getItemAbsents())
        byebye_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertEqual(item2.getItemAbsents(), (hp_uid, ))

        # welcome person on item2
        welcome_form = item2.restrictedTraverse('@@item_welcome_attendee_form')
        welcome_form.person_uid = hp_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertFalse(item2.getItemAbsents())

        # when an item is removed from meeting,
        # itemAbsents info regarding this item are removed as well
        item1_uid = item1.UID()
        self.assertTrue(item1_uid in meeting.itemAbsents)
        self.backToState(item1, 'validated')
        self.assertFalse(item1_uid in meeting.itemAbsents)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testContacts, prefix='test_pm_'))
    return suite
