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

from AccessControl import Unauthorized
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
        org = self.portal.contacts.get(PLONEGROUP_ORG)
        intids = getUtility(IIntIds)
        new_hp = api.content.create(
            container=person, type='held_position', label='New held position',
            title='New held position', position=RelationValue(intids.getId(org)),
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
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_form.meeting = meeting
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
        welcome_form = item2.restrictedTraverse('@@item_welcome_attendee_form').form_instance
        welcome_form.meeting = meeting
        welcome_form.person_uid = hp_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertFalse(item2.getItemAbsents())

    def test_pm_ItemSignatories(self):
        '''Item signatories management, define item signatory and remove item signatory.'''
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        meeting_signatories = meeting.getSignatories()
        self.assertTrue(meeting_signatories)
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item1_uid = item1.UID()
        item2_uid = item2.UID()
        self.presentItem(item1)
        self.presentItem(item2)

        # for now signatories are the same on meeting and items
        self.assertEqual(meeting_signatories, item1.getItemSignatories())
        self.assertEqual(meeting_signatories, item2.getItemSignatories())
        self.assertFalse(meeting.getItemSignatories())
        self.assertFalse(item1.getItemSignatories(real=True))
        self.assertFalse(item2.getItemSignatories(real=True))

        # redefine signatory person on item1 and item2
        person = self.portal.contacts.get('alain-alain')
        hp = person.get_held_positions()[0]
        hp_uid = hp.UID()
        signatory_form = item1.restrictedTraverse('@@item_redefine_signatory_form').form_instance
        signatory_form.meeting = meeting
        signatory_form.person_uid = hp_uid
        signatory_form.apply_until_item_number = 200
        signatory_form.signature_number = '1'
        signatory_form._doApply()

        self.assertEqual(item1.getItemSignatories(real=True), {hp_uid: '1'})
        self.assertEqual(item2.getItemSignatories(real=True), {hp_uid: '1'})
        self.assertTrue(hp_uid in item1.getItemSignatories())
        self.assertTrue(hp_uid in item2.getItemSignatories())
        meeting_item_signatories = meeting.getItemSignatories()
        self.assertTrue(item1_uid in meeting_item_signatories)
        self.assertTrue(item2_uid in meeting_item_signatories)

        # remove redefined signatory on item2
        remove_signatory_form = item2.restrictedTraverse('@@item_remove_redefined_signatory_form').form_instance
        remove_signatory_form.meeting = meeting
        remove_signatory_form.person_uid = hp_uid
        remove_signatory_form.apply_until_item_number = u''
        remove_signatory_form._doApply()
        self.assertTrue(hp_uid in item1.getItemSignatories())
        self.assertFalse(hp_uid in item2.getItemSignatories())
        meeting_item_signatories = meeting.getItemSignatories()
        self.assertTrue(item1_uid in meeting_item_signatories)
        self.assertFalse(item2_uid in meeting_item_signatories)

        # trying to define a forbidden signatory (already signatory on meeting or not present)
        # will raise Unauthorized
        # 1) already signatory, try to define meeting signatory 2 as item signatory 2
        meeting_signatory_2_uid = meeting.getSignatories(by_signature_number=True)['2']
        signatory_form.person_uid = meeting_signatory_2_uid
        self.assertRaises(Unauthorized, signatory_form._doApply)

        # set an attendee absent on item and try to select him as signatory on item1
        absent = self.portal.contacts.get('yves-pays').get_held_positions()[0]
        absent_uid = absent.UID()
        meeting.orderedContacts[absent_uid]['attendee'] = False
        meeting.orderedContacts[absent_uid]['excused'] = True
        self.assertTrue(absent_uid in meeting.getExcused())
        signatory_form.person_uid = absent_uid

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
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_form.meeting = meeting
        byebye_form.person_uid = hp_uid
        byebye_form.apply_until_item_number = 200
        self.assertFalse(item1.getItemAbsents())
        self.assertFalse(item2.getItemAbsents())
        byebye_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertEqual(item2.getItemAbsents(), (hp_uid, ))

        # welcome person on item2
        welcome_form = item2.restrictedTraverse('@@item_welcome_attendee_form').form_instance
        welcome_form.meeting = meeting
        welcome_form.person_uid = hp_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp_uid, ))
        self.assertFalse(item2.getItemAbsents())

    def test_pm_ItemContactsWhenItemRemovedFromMeeting(self):
        '''When an item is removed from a meeting, redefined informations
           regarding item absents and signatories are reinitialized.'''
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        item = self.create('MeetingItem')
        self.presentItem(item)

        # add an item absent
        absent = self.portal.contacts.get('alain-alain')
        absent_hp = absent.get_held_positions()[0]
        absent_hp_uid = absent_hp.UID()
        meeting.itemAbsents[item.UID()] = [absent_hp_uid]
        self.assertTrue(absent_hp_uid in meeting.getItemAbsents(by_absents=True))

        # redefine signatories on item
        signer = self.portal.contacts.get('yves-pays')
        signer_hp = signer.get_held_positions()[0]
        signer_hp_uid = signer_hp.UID()
        meeting.itemSignatories[item.UID()] = {'1': signer_hp_uid}
        self.assertTrue(signer_hp_uid in item.getItemSignatories())

        # remove item from meeting, everything is reinitialized
        self.backToState(item, 'validated')
        self.assertFalse(absent_hp_uid in meeting.getItemAbsents(by_absents=True))
        self.assertFalse(signer_hp_uid in item.getItemSignatories())
        self.assertFalse(item.getItemAbsents())
        self.assertFalse(item.redefinedItemAssemblies())
        self.assertFalse(item.getItemSignatories())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testContacts, prefix='test_pm_'))
    return suite
