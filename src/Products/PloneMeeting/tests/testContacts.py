# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_groups
from DateTime import DateTime
from datetime import date
from imio.helpers.content import disable_link_integrity_checks
from imio.helpers.content import get_vocab
from imio.helpers.content import validate_fields
from OFS.ObjectManager import BeforeDeleteException
from plone import api
from Products.CMFCore.permissions import View
from Products.PloneMeeting.content.directory import IPMDirectory
from Products.PloneMeeting.content.source import PMContactSourceBinder
from Products.PloneMeeting.Extensions.imports import import_contacts
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield.relation import RelationValue
from zExceptions import Redirect
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import Invalid
from zope.intid.interfaces import IIntIds

import os
import Products.PloneMeeting
import transaction


class testContacts(PloneMeetingTestCase):
    '''Tests various aspects of contacts management.'''

    def setUp(self):
        ''' '''
        super(testContacts, self).setUp()
        self.changeUser('siteadmin')
        # enable attendees and signatories fields for Meeting
        cfg = self.meetingConfig
        cfg.setUsedMeetingAttributes(('attendees', 'excused', 'absents', 'signatories', ))
        # enable itemInitiator fields for MeetingItem
        cfg.setUsedItemAttributes(('attendees', 'excused', 'absents', 'signatories', 'itemInitiator'))
        # select orderedContacts
        ordered_contacts = cfg.getField('orderedContacts').Vocabulary(cfg).keys()
        cfg.setOrderedContacts(ordered_contacts)

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
        person = self.portal.contacts.get('person1')
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
        ordered_contacts = cfg.getField('orderedContacts').Vocabulary(cfg).keys()
        cfg.setOrderedContacts(ordered_contacts)
        self.assertEqual(
            meeting.getAllUsedHeldPositions() + (new_hp, ),
            meeting.getAllUsedHeldPositions(include_new=True))
        # unselect everything on MeetingConfig, all values still available on meeting
        cfg.setOrderedContacts(())
        self.assertEqual(
            meeting.getAllUsedHeldPositions(), meeting.getAttendees(theObjects=True))

    def test_pm_CanNotRemoveUsedHeldPosition(self):
        ''' '''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        # test that held positition cannot be delete if used for assembly
        meeting = self.create('Meeting', date=DateTime())
        person = self.portal.contacts.get('person1')
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

        # test that held positition cannot be delete if used for itemInitiator
        cfg.setOrderedItemInitiators((hp_uid,))
        item = self.create('MeetingItem', date=DateTime())
        self.presentItem(item)
        item.setItemInitiator((hp_uid,))

        # hp not deletable because used in MC and meeting item
        self.changeUser('siteadmin')
        self.assertRaises(Redirect, api.content.delete, hp)

        # unselect from MeetingConfig.orderedItemInitiators,
        # still not deletable because used by a meeting item
        orderedItemInitiators = list(cfg.getOrderedItemInitiators())
        orderedItemInitiators.remove(hp_uid)
        cfg.setOrderedItemInitiators(orderedItemInitiators)
        self.assertRaises(Redirect, api.content.delete, hp)

        # unselect hp from meeting item, now it is deletable
        item.setItemInitiator(())

        # assert held position can be properly deleted
        api.content.delete(hp)
        self.assertFalse(person.get_held_positions())

    def test_pm_MayChangeAttendees(self):
        '''Only MeetingManagers may change attendees when item in a meeting.'''
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        # attendees not signatories
        meeting_attendees = [hp for hp in meeting.getAttendees()
                             if hp not in meeting.getSignatories()]
        self.assertTrue(meeting_attendees)
        byebye_form = item.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_nonattendee_form = item.restrictedTraverse('@@item_byebye_nonattendee_form').form_instance
        signatory_form = item.restrictedTraverse('@@item_redefine_signatory_form').form_instance
        signatory_form.person_uid = meeting_attendees[0]
        signatory_form.meeting = meeting
        welcome_form = item.restrictedTraverse('@@item_welcome_attendee_form').form_instance
        welcome_nonattendee_form = item.restrictedTraverse('@@item_welcome_nonattendee_form').form_instance
        remove_signatory_form = item.restrictedTraverse('@@item_remove_redefined_signatory_form').form_instance

        def _check(username, should=True):
            ''' '''
            self.changeUser(username)
            if should:
                self.assertTrue(byebye_form.mayChangeAttendees())
                self.assertTrue(byebye_nonattendee_form.mayChangeAttendees())
                self.assertTrue(signatory_form.mayChangeAttendees())
                self.assertTrue(welcome_form.mayChangeAttendees())
                self.assertTrue(welcome_nonattendee_form.mayChangeAttendees())
                self.assertTrue(remove_signatory_form.mayChangeAttendees())
        # False for everybody when item not in a meeting
        _check('pmManager', should=False)
        _check('pmCreator1', should=False)
        self.presentItem(item)
        # MeetingManagers may when item in a meeting
        _check('pmManager')
        _check('pmCreator1', should=False)
        self.closeMeeting(meeting)
        # False for everybody when meeting is closed
        _check('pmManager', should=False)
        _check('pmCreator1', should=False)

    def test_pm_ItemAbsentsAndExcusedAndNonAttendees(self):
        '''Item absents management (itemAbsents, itemExcused, nonAttendees),
           byebye and welcome forms.'''
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
        self.assertFalse(meeting.getItemAbsents(by_persons=True))
        self.assertFalse(meeting.getItemExcused())
        self.assertFalse(meeting.getItemExcused(by_persons=True))

        # byebye person on item1 and item2
        hp1_uid = meeting_attendees[0]
        hp2_uid = meeting_attendees[1]
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_nonattendee_form = item1.restrictedTraverse('@@item_byebye_nonattendee_form').form_instance
        byebye_form.meeting = meeting
        byebye_nonattendee_form.meeting = meeting
        byebye_form.person_uid = hp1_uid
        byebye_nonattendee_form.person_uid = hp1_uid
        byebye_form.not_present_type = 'absent'
        byebye_form.apply_until_item_number = 200
        byebye_nonattendee_form.apply_until_item_number = 200
        self.assertFalse(item1.getItemAbsents())
        self.assertFalse(item2.getItemAbsents())
        # set hp1 absent
        byebye_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp1_uid, ))
        self.assertEqual(item2.getItemAbsents(), (hp1_uid, ))
        self.assertEqual(
            sorted(meeting.getItemAbsents().keys()),
            sorted([item1_uid, item2_uid]))
        self.assertEqual(meeting.getItemAbsents(by_persons=True).keys(), [hp1_uid])
        self.assertEqual(
            sorted(meeting.getItemAbsents(by_persons=True)[hp1_uid]),
            sorted([item1_uid, item2_uid]))
        # set hp1 non attendee
        byebye_nonattendee_form._doApply()
        self.assertEqual(item1.getItemNonAttendees(), (hp1_uid, ))
        self.assertEqual(item2.getItemNonAttendees(), (hp1_uid, ))
        self.assertEqual(
            sorted(meeting.getItemNonAttendees().keys()),
            sorted([item1_uid, item2_uid]))
        self.assertEqual(meeting.getItemNonAttendees(by_persons=True).keys(), [hp1_uid])
        self.assertEqual(
            sorted(meeting.getItemNonAttendees(by_persons=True)[hp1_uid]),
            sorted([item1_uid, item2_uid]))
        # set hp2 excused
        byebye_form.person_uid = hp2_uid
        byebye_form.not_present_type = 'excused'
        byebye_form.apply_until_item_number = 100
        byebye_form._doApply()
        # absent
        self.assertEqual(item1.getItemAbsents(), (hp1_uid, ))
        self.assertEqual(item2.getItemAbsents(), (hp1_uid, ))
        self.assertEqual(
            sorted(meeting.getItemAbsents().keys()),
            sorted([item1_uid, item2_uid]))
        self.assertEqual(meeting.getItemAbsents(by_persons=True).keys(), [hp1_uid])
        self.assertEqual(
            sorted(meeting.getItemAbsents(by_persons=True)[hp1_uid]),
            sorted([item1_uid, item2_uid]))
        # excused
        self.assertEqual(item1.getItemExcused(), (hp2_uid, ))
        self.assertEqual(item2.getItemExcused(), ())
        self.assertEqual(
            sorted(meeting.getItemExcused().keys()),
            sorted([item1_uid]))
        self.assertEqual(meeting.getItemExcused(by_persons=True).keys(), [hp2_uid])
        self.assertEqual(
            sorted(meeting.getItemExcused(by_persons=True)[hp2_uid]),
            sorted([item1_uid]))
        # non attendees
        self.assertEqual(item1.getItemNonAttendees(), (hp1_uid, ))
        self.assertEqual(item2.getItemNonAttendees(), (hp1_uid, ))
        self.assertEqual(
            sorted(meeting.getItemNonAttendees().keys()),
            sorted([item1_uid, item2_uid]))
        self.assertEqual(meeting.getItemNonAttendees(by_persons=True).keys(), [hp1_uid])
        self.assertEqual(
            sorted(meeting.getItemNonAttendees(by_persons=True)[hp1_uid]),
            sorted([item1_uid, item2_uid]))

        # welcome hp1 on item2
        welcome_form = item2.restrictedTraverse('@@item_welcome_attendee_form').form_instance
        welcome_form.meeting = meeting
        welcome_form.person_uid = hp1_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertEqual(item1.getItemAbsents(), (hp1_uid, ))
        self.assertEqual(item1.getItemNonAttendees(), (hp1_uid, ))
        self.assertFalse(item2.getItemAbsents())
        # welcome hp1 on item1
        welcome_form = item1.restrictedTraverse('@@item_welcome_attendee_form').form_instance
        welcome_form.meeting = meeting
        welcome_form.person_uid = hp1_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertFalse(item1.getItemAbsents())
        self.assertEqual(item1.getItemNonAttendees(), (hp1_uid, ))
        self.assertFalse(item2.getItemAbsents())
        # welcome hp2 on item1
        welcome_form = item1.restrictedTraverse('@@item_welcome_attendee_form').form_instance
        welcome_form.meeting = meeting
        welcome_form.person_uid = hp2_uid
        welcome_form.apply_until_item_number = u''
        welcome_form._doApply()
        self.assertFalse(item1.getItemExcused())
        self.assertFalse(item2.getItemExcused())
        self.assertEqual(item1.getItemNonAttendees(), (hp1_uid, ))
        # welcome non attendee hp1 on item1 and item2
        welcome_nonattendee_form = item1.restrictedTraverse('@@item_welcome_nonattendee_form').form_instance
        welcome_nonattendee_form.meeting = meeting
        welcome_nonattendee_form.person_uid = hp1_uid
        welcome_nonattendee_form.apply_until_item_number = u'200'
        welcome_nonattendee_form._doApply()
        self.assertFalse(item1.getItemExcused())
        self.assertFalse(item2.getItemExcused())
        self.assertFalse(item1.getItemAbsents())
        self.assertFalse(item2.getItemAbsents())
        self.assertFalse(item1.getItemNonAttendees())
        self.assertFalse(item2.getItemNonAttendees())

    def test_pm_CanNotSetItemAbsentAndExcusedSamePerson(self):
        """ """
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
        # set hp1 absent for item1 and item2
        # then set hp1 excused for item2
        person1 = self.portal.contacts.get('person1')
        hp1 = person1.get_held_positions()[0]
        hp1_uid = hp1.UID()
        # set hp1 absent for item1 and item2
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_form.meeting = meeting
        byebye_form.person_uid = hp1_uid
        byebye_form.not_present_type = 'absent'
        byebye_form.apply_until_item_number = 200
        byebye_form._doApply()
        self.assertEqual(
            sorted(meeting.getItemAbsents(by_persons=True)[hp1_uid]),
            sorted([item1_uid, item2_uid]))
        # then set hp1 excused for item2
        # nothing is done
        byebye_form = item2.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_form.meeting = meeting
        byebye_form.person_uid = hp1_uid
        byebye_form.not_present_type = 'excused'
        byebye_form.apply_until_item_number = ''
        byebye_form._doApply()
        self.assertFalse(meeting.getItemExcused(by_persons=True))

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
        person = self.portal.contacts.get('person3')
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
        absent = self.portal.contacts.get('person2').get_held_positions()[0]
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
        person = self.portal.contacts.get('person1')
        hp = person.get_held_positions()[0]
        hp_uid = hp.UID()
        byebye_form = item1.restrictedTraverse('@@item_byebye_attendee_form').form_instance
        byebye_form.meeting = meeting
        byebye_form.person_uid = hp_uid
        byebye_form.not_present_type = 'absent'
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

    def _setup_print_signatories_by_position(self):
        # Add a position_type
        self.portal.contacts.position_types += (
            {"token": u"dg",
             "name": u"Directeur Général|Directeurs Généraux|"
                     u"Directrice Générale|Directrices Générales"},
            {"token": u"super",
             "name": u"Super-héro|Super-héros|"
                     u"Super-héroine|Super-héroines"},
        )
        person1 = self.portal.contacts.get("person1")
        person1.firstname = "Jane"
        person1.lastname = "Doe"
        person1.gender = u"F"
        person1.person_title = u"Miss"

        signatory1 = person1.get_held_positions()[0]
        signatory1.position_type = u"dg"
        signatory1.secondary_position_type = u"super"
        signatory1.label = u""

        # No gender/person_title and no position_type, no secondary_position_type
        person4 = self.portal.contacts.get("person4")
        person4.firstname = "John"
        person4.lastname = "Doe"
        person4.gender = u""
        person4.person_title = u""

        signatory2 = person4.get_held_positions()[0]
        signatory2.label = u"Président"

        # prepare 2 more signatories (but not setted as such, yet)
        person2 = self.portal.contacts.get("person2")
        signatory3 = person2.get_held_positions()[0]
        signatory3.label = u"Signatory3"

        person3 = self.portal.contacts.get("person3")
        signatory4 = person3.get_held_positions()[0]
        signatory4.label = u"Signatory4"

    def test_pm_print_signatories_by_position(self):
        self._setup_print_signatories_by_position()

        self.changeUser("pmManager")
        meeting = self.create("Meeting", date=DateTime())
        item = self.create("MeetingItem")

        # On MeetingItem
        view = item.restrictedTraverse("document-generation")
        helper = view.get_generation_context_helper()
        # print_signatories_by_position shouldn"t fail if the item is not in a meeting
        self.assertEqual(len(helper.print_signatories_by_position()), 0)
        self.presentItem(item)

        printed_signatories = helper.print_signatories_by_position(ender=".")
        self.assertEqual(
            printed_signatories,
            {
                0: u"La Directrice Générale,",
                1: u"Jane Doe.",
                2: u"Président,",  # No position_type, so no prefix
                3: u"John Doe.",
            }
        )
        printed_signatories = helper.print_signatories_by_position(
            signature_format=(u"prefixed_secondary_position_type", u"person_with_title", u"XXX", u"gender"),
            separator=""
        )
        self.assertEqual(
            printed_signatories,
            {
                0: u"La Super-héroine",
                1: u"Miss Jane Doe",
                2: u"XXX",
                3: u"F",
                4: u"Président",  # John Doe has no gender, no title and no secondary_position_type
                5: u"John Doe",
                6: u"XXX",
                7: u""
            }
        )

        # On Meeting, with 4 signatories
        view = meeting.restrictedTraverse("document-generation")
        helper = view.get_generation_context_helper()

        # Add two more signatories
        contacts = meeting.orderedContacts.items()
        signatory3 = contacts[1][1]
        # Set an absurd value to see if it will be correctly sorted
        signatory3["signature_number"] = "10"
        signatory3["signer"] = True
        signatory4 = contacts[2][1]
        signatory4["signer"] = True
        signatory4["signature_number"] = "22"  # Same here

        printed_signatories = helper.print_signatories_by_position(
            signature_format=(u"position_type",),
            ender=None
        )
        self.assertEqual(
            printed_signatories,
            {
                0: u"Directrice Générale",
                1: u"Président",
                2: u"Signatory3",
                3: u"Signatory4"
            }
        )
        # When asking for secondary_position_type, if not available,
        # it falls back to position_type automatically
        person3 = self.portal.contacts.get("person3")
        signatory4 = person3.get_held_positions()[0]
        signatory4.label = None
        signatory4.position_type = u'super'
        signatory4.secondary_position_type = None

        printed_signatories = helper.print_signatories_by_position(
            signature_format=(u"prefixed_secondary_position_type",),
            ender=None
        )
        self.assertEqual(
            printed_signatories,
            {
                # secondary_position_type
                0: u"La Super-héroine",
                # label
                1: u"Président",
                # label
                2: u"Signatory3",
                # position_type fallback from secondary_position_type
                3: u"Le Super-héro"
            }
        )

    def _setupInAndOutAttendees(self):
        """Setup a meeting with items and in and out (non) attendees."""
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        meeting_attendees = meeting.getAttendees()
        self.assertTrue(meeting_attendees)
        item1 = self.create('MeetingItem')
        item1_uid = item1.UID()
        item2 = self.create('MeetingItem')
        item2_uid = item2.UID()
        item3 = self.create('MeetingItem')
        item3_uid = item3.UID()
        self.presentItem(item1)
        self.presentItem(item2)
        self.presentItem(item3)
        self.assertEqual(meeting.getItems(ordered=True), [item1, item2, item3])
        meeting.itemAbsents[item1_uid] = [meeting_attendees[0]]
        meeting.itemExcused[item2_uid] = [meeting_attendees[0], meeting_attendees[1]]
        meeting.itemNonAttendees[item2_uid] = [meeting_attendees[0]]
        meeting.itemAbsents[item3_uid] = [meeting_attendees[1], meeting_attendees[2]]
        return meeting, meeting_attendees, item1, item2, item3

    def test_pm_ItemInAndOutAttendees(self):
        '''Returns information for an item about attendees and non attendees
           that entered/left the meeting before/after current item.'''
        meeting, meeting_attendees, item1, item2, item3 = self._setupInAndOutAttendees()
        self.assertEqual(
            item1.getInAndOutAttendees(theObjects=False),
            {'attendee_again_after': (),
             'attendee_again_before': (),
             'entered_after': (),
             'entered_before': (),
             'left_after': (meeting_attendees[1],),
             'left_before': (meeting_attendees[0],),
             'non_attendee_before': (),
             'non_attendee_after': (meeting_attendees[0],)})
        self.assertEqual(
            item2.getInAndOutAttendees(theObjects=False),
            {'attendee_again_after': (meeting_attendees[0],),
             'attendee_again_before': (),
             'entered_after': (meeting_attendees[0],),
             'entered_before': (),
             'left_after': (meeting_attendees[2],),
             'left_before': (meeting_attendees[1],),
             'non_attendee_before': (meeting_attendees[0],),
             'non_attendee_after': ()})
        self.assertEqual(
            item3.getInAndOutAttendees(theObjects=False),
            {'attendee_again_after': (),
             'attendee_again_before': (meeting_attendees[0],),
             'entered_after': (),
             'entered_before': (meeting_attendees[0],),
             'left_after': (),
             'left_before': (meeting_attendees[2],),
             'non_attendee_before': (),
             'non_attendee_after': ()})

    def test_pm_Print_in_and_out_attendees(self):
        """Test the print_in_and_out_attendees method."""
        meeting, meeting_attendees, item1, item2, item3 = self._setupInAndOutAttendees()
        view = item1.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        # merge_in_and_out_types=False
        self.assertEqual(
            helper.print_in_and_out_attendees(merge_in_and_out_types=False),
            {'attendee_again_after': '',
             'attendee_again_before': '',
             'entered_after': '',
             'entered_before': '',
             'left_after': u'<p>Monsieur Person2FirstName Person2LastName quitte la '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'left_before': u'<p>Monsieur Person1FirstName Person1LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>',
             'non_attendee_after': u'<p>Monsieur Person1FirstName Person1LastName ne '
                u'participe plus \xe0 la s\xe9ance apr\xe8s la discussion du point.</p>',
             'non_attendee_before': ''})
        helper.context = item2
        self.assertEqual(
            helper.print_in_and_out_attendees(merge_in_and_out_types=False),
            {'attendee_again_after': u'<p>Monsieur Person1FirstName Person1LastName participe '
                u'\xe0 nouveau \xe0 la s\xe9ance apr\xe8s la discussion du point.</p>',
             'attendee_again_before': '',
             'entered_after': u'<p>Monsieur Person1FirstName Person1LastName entre en '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'entered_before': '',
             'left_after': u'<p>Monsieur Person3FirstName Person3LastName quitte la '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'left_before': u'<p>Monsieur Person2FirstName Person2LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>',
             'non_attendee_after': '',
             'non_attendee_before': u'<p>Monsieur Person1FirstName Person1LastName ne '
                u'participe plus \xe0 la s\xe9ance avant la discussion du point.</p>'})
        helper.context = item3
        self.assertEqual(
            helper.print_in_and_out_attendees(merge_in_and_out_types=False),
            {'attendee_again_after': '',
             'attendee_again_before': u'<p>Monsieur Person1FirstName Person1LastName participe '
                u'\xe0 nouveau \xe0 la s\xe9ance avant la discussion du point.</p>',
             'entered_after': '',
             'entered_before': u'<p>Monsieur Person1FirstName Person1LastName rentre en '
                u's\xe9ance avant la discussion du point.</p>',
             'left_after': '',
             'left_before': u'<p>Monsieur Person3FirstName Person3LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>',
             'non_attendee_after': '',
             'non_attendee_before': ''})
        # merge_in_and_out_types=False
        helper.context = item1
        self.assertEqual(
            helper.print_in_and_out_attendees(merge_in_and_out_types=True),
            {'entered_after': '',
             'entered_before': '',
             'left_after': u'<p>Monsieur Person2FirstName Person2LastName quitte la '
                u's\xe9ance apr\xe8s la discussion du point.</p>'
                u'<p>Monsieur Person1FirstName Person1LastName ne participe plus \xe0 la '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'left_before': u'<p>Monsieur Person1FirstName Person1LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>'})
        helper.context = item2
        self.assertEqual(
            helper.print_in_and_out_attendees(merge_in_and_out_types=True),
            {'entered_after': u'<p>Monsieur Person1FirstName Person1LastName entre en '
                u's\xe9ance apr\xe8s la discussion du point.</p>'
                u'<p>Monsieur Person1FirstName Person1LastName participe \xe0 nouveau \xe0 la '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'entered_before': '',
             'left_after': u'<p>Monsieur Person3FirstName Person3LastName quitte la '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'left_before': u'<p>Monsieur Person2FirstName Person2LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>'
                u'<p>Monsieur Person1FirstName Person1LastName ne participe plus \xe0 la '
                u's\xe9ance avant la discussion du point.</p>'})
        helper.context = item3
        self.assertEqual(
            helper.print_in_and_out_attendees(merge_in_and_out_types=True),
            {'entered_after': '',
             'entered_before': u'<p>Monsieur Person1FirstName Person1LastName rentre en '
                u's\xe9ance avant la discussion du point.</p>'
                u'<p>Monsieur Person1FirstName Person1LastName participe \xe0 nouveau \xe0 la '
                u's\xe9ance avant la discussion du point.</p>',
             'left_after': '',
             'left_before': u'<p>Monsieur Person3FirstName Person3LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>'})

    def test_pm_Print_in_and_out_attendees_custom_patterns(self):
        """Test the print_in_and_out_attendees method."""
        meeting, meeting_attendees, item1, item2, item3 = self._setupInAndOutAttendees()
        view = item1.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        # no custom_patterns
        self.assertEqual(
            helper.print_in_and_out_attendees(),
            {'entered_after': '',
             'entered_before': '',
             'left_after': u'<p>Monsieur Person2FirstName Person2LastName quitte la '
                u's\xe9ance apr\xe8s la discussion du point.</p>'
                u'<p>Monsieur Person1FirstName Person1LastName ne participe plus \xe0 la '
                u's\xe9ance apr\xe8s la discussion du point.</p>',
             'left_before': u'<p>Monsieur Person1FirstName Person1LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>'})
        # custom_patterns, merge_in_and_out_types=True
        self.assertEqual(
            helper.print_in_and_out_attendees(
                custom_patterns={'left_after': 'Custom pattern left_after',
                                 'non_attendee_after': 'Custom pattern non_attendee_after',
                                 'left_before': 'Custom pattern left_before'}),
            {'entered_after': '',
             'entered_before': '',
             'left_after': u'<p>Custom pattern left_after</p>'
                u'<p>Custom pattern non_attendee_after</p>',
             'left_before': u'<p>Custom pattern left_before</p>'})
        # custom_patterns, merge_in_and_out_types=False
        self.assertEqual(
            helper.print_in_and_out_attendees(
                custom_patterns={'left_after': 'Custom pattern left_after',
                                 'non_attendee_after': 'Custom pattern non_attendee_after',
                                 'left_before': 'Custom pattern left_before'},
                merge_in_and_out_types=False),
            {'attendee_again_after': '',
             'attendee_again_before': '',
             'entered_after': '',
             'entered_before': '',
             'left_after': u'<p>Custom pattern left_after</p>',
             'left_before': u'<p>Custom pattern left_before</p>',
             'non_attendee_after': u'<p>Custom pattern non_attendee_after</p>',
             'non_attendee_before': ''})

        # partial custom_patterns, merge_in_and_out_types=False
        self.assertEqual(
            helper.print_in_and_out_attendees(
                custom_patterns={'left_after': 'Custom pattern left_after',
                                 'non_attendee_after': 'Custom pattern non_attendee_after'},
                merge_in_and_out_types=False),
            {'attendee_again_after': '',
             'attendee_again_before': '',
             'entered_after': '',
             'entered_before': '',
             'left_after': u'<p>Custom pattern left_after</p>',
             'left_before': u'<p>Monsieur Person1FirstName Person1LastName quitte la '
                u's\xe9ance avant la discussion du point.</p>',
             'non_attendee_after': u'<p>Custom pattern non_attendee_after</p>',
             'non_attendee_before': ''})

    def test_pm_Print_attendees(self):
        """Basic test for the print_attendees method."""
        meeting, meeting_attendees, item1, item2, item3 = self._setupInAndOutAttendees()
        # item
        view = item1.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        self.assertEqual(
            helper.print_attendees(),
            u'Monsieur Person1FirstName Person1LastName, '
            u'Assembly member 1, <strong>absent pour ce point</strong><br />'
            u'Monsieur Person2FirstName Person2LastName, '
            u'Assembly member 2, <strong>pr\xe9sent</strong><br />'
            u'Monsieur Person3FirstName Person3LastName, '
            u'Assembly member 3, <strong>pr\xe9sent</strong><br />'
            u'Monsieur Person4FirstName Person4LastName, '
            u'Assembly member 4 &amp; 5, <strong>pr\xe9sent</strong>')
        # meeting
        view = meeting.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        self.assertEqual(
            helper.print_attendees(),
            u'Monsieur Person1FirstName Person1LastName, Assembly member 1, '
            u'<strong>pr\xe9sent</strong><br />'
            u'Monsieur Person2FirstName Person2LastName, Assembly member 2, '
            u'<strong>pr\xe9sent</strong><br />'
            u'Monsieur Person3FirstName Person3LastName, Assembly member 3, '
            u'<strong>pr\xe9sent</strong><br />'
            u'Monsieur Person4FirstName Person4LastName, Assembly member 4 &amp; 5, '
            u'<strong>pr\xe9sent</strong>')

    def test_pm_Print_attendees_by_type(self):
        """Basic test for the print_attendees method."""
        meeting, meeting_attendees, item1, item2, item3 = self._setupInAndOutAttendees()
        # item
        view = item1.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        self.assertEqual(
            helper.print_attendees_by_type(),
            u'<strong><u>Pr\xe9sents&nbsp;:</u></strong><br />'
            u'Monsieur Person2FirstName Person2LastName, Assembly member 2, '
            u'Monsieur Person3FirstName Person3LastName, Assembly member 3, '
            u'Monsieur Person4FirstName Person4LastName, Assembly member 4 &amp; 5;<br />'
            u'<strong><u>Absent pour ce point&nbsp;:</u></strong><br />'
            u'Monsieur Person1FirstName Person1LastName, Assembly member 1;')
        # meeting
        view = meeting.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        self.assertEqual(
            helper.print_attendees_by_type(),
            u'<strong><u>Pr\xe9sents&nbsp;:</u></strong><br />'
            u'Monsieur Person1FirstName Person1LastName, Assembly member 1, '
            u'Monsieur Person2FirstName Person2LastName, Assembly member 2, '
            u'Monsieur Person3FirstName Person3LastName, Assembly member 3, '
            u'Monsieur Person4FirstName Person4LastName, Assembly member 4 &amp; 5;')

    def test_pm_ItemContactsWhenItemRemovedFromMeeting(self):
        '''When an item is removed from a meeting, redefined informations
           regarding item absents/excused and signatories are reinitialized.'''
        cfg = self.meetingConfig
        # remove recurring items
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        item_with_absent = self.create('MeetingItem')
        self.presentItem(item_with_absent)
        item_with_excused = self.create('MeetingItem')
        self.presentItem(item_with_excused)

        # add an item absent
        absent = self.portal.contacts.get('person1')
        absent_hp = absent.get_held_positions()[0]
        absent_hp_uid = absent_hp.UID()
        meeting.itemAbsents[item_with_absent.UID()] = [absent_hp_uid]
        self.assertTrue(absent_hp_uid in meeting.getItemAbsents(by_persons=True))

        # add an item excused
        excused = self.portal.contacts.get('person1')
        excused_hp = excused.get_held_positions()[0]
        excused_hp_uid = excused_hp.UID()
        meeting.itemExcused[item_with_excused.UID()] = [excused_hp_uid]
        self.assertTrue(excused_hp_uid in meeting.getItemExcused(by_persons=True))

        # redefine signatories on item
        signer = self.portal.contacts.get('person2')
        signer_hp = signer.get_held_positions()[0]
        signer_hp_uid = signer_hp.UID()
        meeting.itemSignatories[item_with_absent.UID()] = {'1': signer_hp_uid}
        self.assertTrue(signer_hp_uid in item_with_absent.getItemSignatories())

        # remove items from meeting, everything is reinitialized
        # absent
        self.backToState(item_with_absent, 'validated')
        self.assertFalse(absent_hp_uid in meeting.getItemAbsents(by_persons=True))
        self.assertFalse(signer_hp_uid in item_with_absent.getItemSignatories())
        self.assertFalse(item_with_absent.getItemAbsents())
        self.assertFalse(item_with_absent.redefinedItemAssemblies())
        self.assertFalse(item_with_absent.getItemSignatories())
        # excused
        self.backToState(item_with_excused, 'validated')
        self.assertFalse(excused_hp_uid in meeting.getItemExcused(by_persons=True))
        self.assertFalse(signer_hp_uid in item_with_excused.getItemSignatories())
        self.assertFalse(item_with_excused.getItemExcused())
        self.assertFalse(item_with_excused.redefinedItemAssemblies())
        self.assertFalse(item_with_excused.getItemSignatories())

    def test_pm_HeldPositionPositionsSourceDoNotShowOrgsInsidePlonegroup(self):
        """The source for field held_position.position will display
           organizations outside own_org including own_org."""
        # create an organization outside own_org
        self.changeUser('siteadmin')
        outside_org = api.content.create(
            container=self.portal.contacts,
            type='organization',
            id='org-outside-own-org',
            title='Organization outside own org')
        binder = PMContactSourceBinder()
        source = binder(self.portal)
        self.assertTrue(self.own_org.UID() in [term.brain.UID for term in source.search('')])
        self.assertTrue(outside_org.UID() in [term.brain.UID for term in source.search('')])
        self.assertFalse(self.developers_uid in [term.brain.UID for term in source.search('')])
        self.assertFalse(self.vendors_uid in [term.brain.UID for term in source.search('')])
        self.assertFalse(self.endUsers_uid in [term.brain.UID for term in source.search('')])

    def test_pm_CanNotRemoveUsedOrganization(self):
        '''While removing an organization from own organization,
           it should raise if it is used somewhere...'''
        disable_link_integrity_checks()
        cfg = self.meetingConfig
        cfg.setSelectableAdvisers(())
        cfg2 = self.meetingConfig2
        self.changeUser('pmManager')
        # delete recurring items, just keep item templates
        self._removeConfigObjectsFor(cfg, folders=['recurringitems', ])
        # make sure cfg2 does not interact...
        self._removeConfigObjectsFor(cfg2)
        # create an item
        item = self.create('MeetingItem')
        # default used proposingGroup is 'developers'
        self.assertEqual(item.getProposingGroup(), self.developers_uid)

        # now try to remove corresponding organization
        self.changeUser('admin')

        # 1) fails because used in the configuration, in
        # selectableCopyGroups, selectableAdvisers, customAdvisers, powerAdvisersGroups or usingGroups
        self.failIf(cfg.getCustomAdvisers())
        self.failIf(cfg.getPowerAdvisersGroups())
        self.failIf(cfg.getSelectableAdvisers())
        self.failIf(cfg.getOrderedAssociatedOrganizations())
        self.failIf(cfg.getOrderedGroupsInCharge())
        self.failUnless(self.developers_reviewers in cfg.getSelectableCopyGroups())
        can_not_delete_organization_meetingconfig = \
            translate('can_not_delete_organization_meetingconfig',
                      domain="plone",
                      mapping={'cfg_url': cfg.absolute_url()},
                      context=self.request)
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove selectableCopyGroups from the meetingConfigs
        cfg.setSelectableCopyGroups(())
        cfg2.setSelectableCopyGroups(())

        # define selectableAdvisers, the exception is also raised
        cfg.setSelectableAdvisers((self.developers_uid, ))
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove selectableAdvisers
        cfg.setSelectableAdvisers(())

        # define customAdvisers, the exception is also raised
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'delay': '5', }, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove customAdvisers
        cfg.setCustomAdvisers([])

        # define powerAdvisersGroups, the exception is also raised
        cfg.setPowerAdvisersGroups([self.developers_uid, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove powerAdvisersGroups
        cfg.setPowerAdvisersGroups([])

        # define usingGroups, the exception is also raised
        cfg.setUsingGroups([self.developers_uid, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove usingGroups
        cfg.setUsingGroups([])

        # define orderedAssociatedOrganizations, the exception is also raised
        cfg.setOrderedAssociatedOrganizations([self.developers_uid, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove orderedAssociatedOrganizations
        cfg.setOrderedAssociatedOrganizations([])

        # define orderedGroupsInCharge, the exception is also raised
        cfg.setOrderedGroupsInCharge([self.developers_uid, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove orderedGroupsInCharge
        cfg.setOrderedGroupsInCharge([])

        # 2) fails because the corresponding Plone groups are not empty
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        can_not_delete_organization_plonegroup = \
            translate('can_not_delete_organization_plonegroup',
                      mapping={'member_id': 'pmAdviser1'},
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_organization_plonegroup)
        # so remove every users of these groups
        for ploneGroup in get_plone_groups(self.developers_uid):
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # check that it works if left users in the Plone groups are
        # "not found" users, aka when you delete a user from Plone without removing him
        # before from groups he is in, a special "not found" user will still be assigned to the groups...
        # to test, add a new user, assign it to the developers_creators group, remove the user
        # it should not complain about 'can_not_delete_organization_plonegroup'
        self._make_not_found_user()
        # but it does not raise an exception with message 'can_not_delete_organization_plonegroup'
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)

        self.assertNotEquals(cm.exception.message, can_not_delete_organization_plonegroup)
        can_not_delete_organization_meetingitem = \
            translate('can_not_delete_organization_meetingitem',
                      mapping={'item_url': item.absolute_url()},
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # 3) complains about a linked meetingitem
        # checks on the item are made around :
        # item.getProposingGroup
        # item.getAssociatedGroups
        # item.getGroupsInCharge
        # item.adviceIndex
        # item.getCopyGroups
        # item.itemInitiator
        # so check the 6 possible "states"

        # first check when the item is using 'proposingGroup', it is the case here
        # for item, make sure other conditions are False
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(())
        self.assertTrue(self.developers_advisers not in item.adviceIndex)
        item.setCopyGroups(())
        item.setItemInitiator(())
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)

        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # now check with item having associatedGroups
        item.setProposingGroup(self.vendors_uid)
        item.setAssociatedGroups((self.developers_uid, ))
        item.setOptionalAdvisers(())
        self.assertTrue(self.developers_advisers not in item.adviceIndex)
        item.setCopyGroups(())
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # now check with item having optionalAdvisers
        item.setProposingGroup(self.vendors_uid)
        item.setAssociatedGroups(())
        item.setOptionalAdvisers((self.developers_uid, ))
        self.assertTrue(self.developers_advisers not in item.adviceIndex)
        item.setCopyGroups(())
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # check with groupsInCharge
        item.setProposingGroup(self.vendors_uid)
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(())
        self.assertTrue(self.developers_advisers not in item.adviceIndex)
        self._setUpGroupsInCharge(item, groups=[self.developers_uid])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # check with item having itemInitiator
        self._tearDownGroupsInCharge(item)
        item.setItemInitiator((self.developers_uid, ))
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # check with item having copyGroups
        item.setItemInitiator(())
        cfg.setUseCopies(True)
        item.setCopyGroups((self.developers_reviewers, ))
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message, can_not_delete_organization_meetingitem)

        # remove copyGroups
        item.setCopyGroups(())
        item._update_after_edit()
        # unselect organizations from plonegroup configuration so it works...
        self._select_organization(self.developers_uid, remove=True)
        self.portal.restrictedTraverse('@@delete_givenuid')(
            self.developers_uid, catch_before_delete_exception=False)
        # the group is actually removed
        self.failIf(self.developers in self.own_org)

        # 4) fails when used in a meetingcategory.using_groups or meetingcategory.groups_in_charge
        # usingGroups
        cat = cfg2.categories.subproducts
        self.assertTrue(self.vendors_uid in cat.using_groups)
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message,
                         translate('can_not_delete_organization_meetingcategory',
                                   domain='plone',
                                   mapping={'url': cat.absolute_url()},
                                   context=self.portal.REQUEST))
        cat.using_groups = ()
        # groupsInCharge
        cat.groups_in_charge = [self.vendors_uid]
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message,
                         translate('can_not_delete_organization_meetingcategory',
                                   domain='plone',
                                   mapping={'url': cat.absolute_url()},
                                   context=self.portal.REQUEST))
        cat.groups_in_charge = []

        # 5) removing a used group in the configuration fails too
        # remove item because it uses 'vendors'
        item.aq_inner.aq_parent.manage_delObjects([item.getId()])
        self.assertEqual(cfg.itemtemplates.template2.getProposingGroup(), self.vendors_uid)
        # then fails because corresponding Plone groups are not empty...
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)

        can_not_delete_organization_plonegroup = \
            translate('can_not_delete_organization_plonegroup',
                      mapping={'member_id': 'pmManager'},
                      domain="plone",
                      context=self.request)
        self.assertEqual(cm.exception.message, can_not_delete_organization_plonegroup)
        # so remove them...
        for ploneGroup in get_plone_groups(self.vendors_uid):
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)

        # 6) then fails because used by an item present in the configuration
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)
        self.maxDiff = None
        self.assertEqual(cm.exception.message,
                         translate('can_not_delete_organization_config_meetingitem',
                                   domain='plone',
                                   mapping={'item_url': cfg.itemtemplates.template2.absolute_url()},
                                   context=self.portal.REQUEST))
        # change proposingGroup but use org in templateUsingGroups
        cfg.itemtemplates.template2.setProposingGroup(self.developers_uid)
        cfg.itemtemplates.template2.setTemplateUsingGroups((self.vendors_uid, ))
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message,
                         translate('can_not_delete_organization_config_meetingitem',
                                   domain='plone',
                                   mapping={'item_url': cfg.itemtemplates.template2.absolute_url()},
                                   context=self.portal.REQUEST))
        # unselect organizations from plonegroup configuration so it works...
        cfg.itemtemplates.template2.setTemplateUsingGroups(())
        self._select_organization(self.vendors_uid, remove=True)
        # now it works...
        self.portal.restrictedTraverse('@@delete_givenuid')(
            self.vendors_uid, catch_before_delete_exception=False)
        # the group is actually removed
        self.failIf(self.vendors in self.own_org)

    def test_pm_CanNotRemoveOrganizationUsedAsGroupsInCharge(self):
        '''While removing an organization, it should raise if
           it is used as groups_in_charge of another organization.'''
        self.changeUser('siteadmin')
        org1 = self.create('organization', id='org1', title='Org 1', acronym='O1')
        org2 = self.create('organization', id='org2', title='Org 2', acronym='O2')
        org2_uid = org2.UID()
        org1.groups_in_charge = [org2_uid]
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                org2_uid, catch_before_delete_exception=False)
        self.assertEqual(cm.exception.message,
                         translate('can_not_delete_organization_groupsincharge',
                                   domain='plone',
                                   mapping={'org_url': org1.absolute_url()},
                                   context=self.portal.REQUEST))

    def test_pm_DeactivatedOrgCanNoMoreBeUsed(self):
        """
          Check that when an organiztion is unselected (deactivated), it is no more useable in any
          functionnality of the application...
        """
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # delete the 'vendors' group so we are sure that methods and conditions
        # we need to remove every items using the 'vendors' group before being able to remove it...
        self.changeUser('admin')
        # make sure cfg2 does not interact...
        self._removeConfigObjectsFor(cfg2)
        cfg.itemtemplates.manage_delObjects(['template2', ])
        # and remove 'vendors_reviewers' from every MeetingConfig.selectableCopyGroups
        # and 'vendors' from every MeetingConfig.selectableAdvisers
        cfg.setSelectableCopyGroups((self.developers_reviewers, ))
        cfg2.setSelectableAdvisers((self.developers_uid, ))
        cfg2.setSelectableCopyGroups((self.developers_reviewers, ))
        cfg2.setSelectableAdvisers((self.developers_uid, ))
        # and remove users from vendors Plone groups
        for ploneGroup in get_plone_groups(self.vendors_uid):
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # unselect it
        self._select_organization(self.vendors_uid, remove=True)
        # remove it from subproducts category usingGroups
        cfg2.categories.subproducts.using_groups = ()
        # now we can delete it...
        self.portal.restrictedTraverse('@@delete_givenuid')(
            self.vendors_uid, catch_before_delete_exception=False)
        self.changeUser('pmManager')
        # create an item so we can test vocabularies
        item = self.create('MeetingItem')
        advisers_vocab_factory = get_vocab(
            item,
            'Products.PloneMeeting.vocabularies.itemoptionaladvicesvocabulary',
            only_factory=True)
        self.assertTrue(self.developers_uid in item.Vocabulary('associatedGroups')[0])
        self.assertTrue(self.developers_uid in item.listProposingGroups())
        self.assertTrue(self.developers_reviewers in item.Vocabulary('copyGroups')[0])
        self.assertTrue(self.developers_uid in advisers_vocab_factory(item))
        self.assertTrue(self.tool.userIsAmong(['creators']))
        # after deactivation, the group is no more useable...
        self.changeUser('admin')
        self._select_organization(self.developers_uid, remove=True)
        self.changeUser('pmManager')
        self.assertFalse(self.developers_uid in item.Vocabulary('associatedGroups')[0])
        # remove proposingGroup or it will appear in the vocabulary as 'developers' is currently used...
        item.setProposingGroup('')
        self.assertFalse(self.developers_uid in item.listProposingGroups())
        self.assertFalse(self.developers_reviewers in item.Vocabulary('copyGroups')[0])
        self.assertFalse(self.developers_uid in advisers_vocab_factory(item))
        self.assertFalse(self.tool.userIsAmong(['creators']))

    def test_pm_RedefinedCertifiedSignatures(self):
        """organization.certified_signatures may override what is defined on a MeetingConfig,
           either partially (one signature, the other is taken from MeetingConfig) or completely."""
        cfg = self.meetingConfig
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'held_position': '_none_',
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg.setCertifiedSignatures(certified)
        # called without computed=True, the actual values defined on the MeetingGroup is returned
        self.assertEqual(self.vendors.get_certified_signatures(), [])
        # with a cfg, cfg values are returned if not overrided
        self.assertEqual(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                         ['Function1', 'Name1', 'Function2', 'Name2'])

        # redefine one signature
        group_certified = [
            {'signature_number': '2',
             'name': u'Redefined name2',
             'function': u'Redefined function2',
             'held_position': None,
             'date_from': None,
             'date_to': None},
        ]
        # it validates
        self.vendors.certified_signatures = group_certified
        self.assertFalse(validate_fields(self.vendors))
        self.assertEqual(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                         ['Function1', 'Name1', 'Redefined function2', 'Redefined name2'])

        # redefine every signatures
        group_certified = [
            {'signature_number': '1',
             'name': u'Redefined name1',
             'function': u'Redefined function1',
             'held_position': None,
             'date_from': None,
             'date_to': None},
            {'signature_number': '2',
             'name': u'Redefined name2',
             'function': u'Redefined function2',
             'held_position': None,
             'date_from': None,
             'date_to': None},
        ]
        self.vendors.certified_signatures = group_certified
        self.assertFalse(validate_fields(self.vendors))
        self.assertEqual(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                         ['Redefined function1', 'Redefined name1',
                          'Redefined function2', 'Redefined name2'])

        # redefine a third signature
        group_certified = [
            {'signature_number': '1',
             'name': u'Redefined name1',
             'function': u'Redefined function1',
             'held_position': None,
             'date_from': None,
             'date_to': None},
            {'signature_number': '2',
             'name': u'Redefined name2',
             'function': u'Redefined function2',
             'held_position': None,
             'date_from': None,
             'date_to': None},
            {'signature_number': '3',
             'name': u'Redefined name3',
             'function': u'Redefined function3',
             'held_position': None,
             'date_from': None,
             'date_to': None},
        ]
        self.vendors.certified_signatures = group_certified
        self.assertFalse(validate_fields(self.vendors))
        self.assertEqual(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                         ['Redefined function1', 'Redefined name1',
                          'Redefined function2', 'Redefined name2',
                          'Redefined function3', 'Redefined name3'])

        # redefine a third signature but not the second
        group_certified = [
            {'signature_number': '1',
             'name': u'Redefined name1',
             'function': u'Redefined function1',
             'held_position': None,
             'date_from': None,
             'date_to': None},
            {'signature_number': '3',
             'name': u'Redefined name3',
             'function': u'Redefined function3',
             'held_position': None,
             'date_from': None,
             'date_to': None},
        ]
        self.vendors.certified_signatures = group_certified
        self.assertFalse(validate_fields(self.vendors))
        self.assertEqual(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                         ['Redefined function1', 'Redefined name1',
                          'Function2', 'Name2',
                          'Redefined function3', 'Redefined name3'])

        # period validity is taken into account
        # redefine a third signature but not the second
        group_certified = [
            {'signature_number': '1',
             'name': u'Redefined name1',
             'function': u'Redefined function1',
             'held_position': None,
             'date_from': date(2015, 1, 1),
             'date_to': date(2015, 5, 5)},
            {'signature_number': '3',
             'name': u'Redefined name3',
             'function': u'Redefined function3',
             'held_position': None,
             'date_from': None,
             'date_to': None},
        ]
        self.vendors.certified_signatures = group_certified
        self.assertFalse(validate_fields(self.vendors))
        self.assertEqual(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                         ['Function1', 'Name1',
                          'Function2', 'Name2',
                          'Redefined function3', 'Redefined name3'])

    def test_pm_OwnOrgNotDeletable(self):
        """The own_org element is not deletable using delete_uid."""
        self.changeUser('siteadmin')
        self.assertRaises(
            Unauthorized,
            self.portal.restrictedTraverse('@@delete_givenuid'), self.own_org.UID())

    def test_pm_DeactivateOrganization(self):
        """Deactivating an organization will remove every Plone groups from
           every MeetingConfig.selectableCopyGroups field."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('admin')
        # for now, the 'developers_reviewers' is in self.meetingConfig.selectableCopyGroups
        self.assertTrue(self.developers_reviewers in cfg.getSelectableCopyGroups())
        self.assertTrue(self.developers_reviewers in cfg2.getSelectableCopyGroups())
        # when deactivated, it is no more the case...
        self._select_organization(self.developers_uid, remove=True)
        self.assertTrue(self.developers_reviewers not in cfg.getSelectableCopyGroups())
        self.assertTrue(self.developers_reviewers not in cfg2.getSelectableCopyGroups())

    def test_pm_WarnUserWhenAddingNewOrgOutiseOwnOrg(self):
        """ """
        # when added in directory or organization ouside own_org, a message is displayed
        for location in (self.portal.contacts, self.developers):
            add_view = location.restrictedTraverse('++add++organization')
            add_view.ti = self.portal.portal_types.organization
            self.request['PUBLISHED'] = add_view
            messages = IStatusMessage(self.request).show()
            self.assertEqual(len(messages), 0)
            add_view.update()
            messages = IStatusMessage(self.request).show()
            self.assertEqual(len(messages), 1)
            warning_msg = translate(msgid="warning_adding_org_outside_own_org",
                                    domain='PloneMeeting',
                                    context=self.request)
            self.assertEqual(messages[-1].message, warning_msg)
        # when added in own_org, no warning
        add_view = self.own_org.restrictedTraverse('++add++organization')
        add_view.ti = self.portal.portal_types.organization
        self.request['PUBLISHED'] = add_view
        add_view.update()
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 0)

    def test_pm_ImportContactsCSV(self):
        """ """
        contacts = self.portal.contacts
        # initialy, we have 4 persons and 4 held_positions
        own_org = get_own_organization()
        self.assertIsNone(own_org.acronym)
        self.assertEqual(len(api.content.find(context=contacts, portal_type='organization')), 4)
        self.assertEqual(len(api.content.find(context=contacts, portal_type='person')), 4)
        self.assertEqual(len(api.content.find(context=contacts, portal_type='held_position')), 4)
        path = os.path.join(os.path.dirname(Products.PloneMeeting.__file__), 'profiles/testing')
        output = import_contacts(self.portal, path=path)
        self.assertEqual(output, 'You must be a zope manager to run this script')
        self.changeUser('siteadmin')
        output = import_contacts(self.portal, path=path)
        self.assertEqual(output, 'You must be a zope manager to run this script')

        # import contacts as Zope admin
        self.changeUser('admin')
        import_contacts(self.portal, path=path)
        # we imported 10 organizations and 15 persons/held_positions
        self.assertEqual(len(api.content.find(context=contacts, portal_type='organization')), 13)
        self.assertEqual(len(api.content.find(context=contacts, portal_type='person')), 19)
        self.assertEqual(len(api.content.find(context=contacts, portal_type='held_position')), 19)
        # organizations are imported with an acronym
        self.assertEqual(own_org.acronym, u'OwnOrg')
        org_gc = contacts.get('groupe-communes')
        self.assertEqual(org_gc.acronym, u'GComm')
        # hp of agent-interne is correctly linked to plonegroup-organization
        own_org = get_own_organization()
        agent_interne_hp = contacts.get('agent-interne').objectValues()[0]
        self.assertEqual(agent_interne_hp.portal_type, 'held_position')
        self.assertEqual(agent_interne_hp.get_organization(), own_org)
        # we can import organizations into another, we imported 4 orgs under my org
        self.assertEqual(
            [org.id for org in own_org.objectValues()],
            ['developers',
             'vendors',
             'endUsers',
             'service-1',
             'service-2',
             'service-associe-1',
             'service-associe-2'])

    def test_pm_Gender_and_number_from_position_type(self):
        """Return gender/number values depending on used position type."""
        self.changeUser('siteadmin')
        self.portal.contacts.position_types = [
            {'token': u'default', 'name': u'D\xe9faut'},
            {'token': u'admin', 'name': u'Administrateur|Administrateurs|Administratrice|Administratrices'},
            {'token': u'alderman', 'name': u'\xc9chevin|\xc9chevins|\xc9chevine|\xc9chevines'}]
        person = self.portal.contacts.get('person1')
        hp = person.get_held_positions()[0]
        hp.position_type = u'default'
        self.assertEqual(
            hp.gender_and_number_from_position_type(),
            {'FP': u'D\xe9faut',
             'FS': u'D\xe9faut',
             'MP': u'D\xe9faut',
             'MS': u'D\xe9faut'})
        hp.position_type = u'admin'
        self.assertEqual(
            hp.gender_and_number_from_position_type(),
            {'FP': u'Administratrices',
             'FS': u'Administratrice',
             'MP': u'Administrateurs',
             'MS': u'Administrateur'})
        hp.position_type = u'alderman'
        self.assertEqual(
            hp.gender_and_number_from_position_type(),
            {'FP': u'\xc9chevines',
             'FS': u'\xc9chevine',
             'MP': u'\xc9chevins',
             'MS': u'\xc9chevin'})
        hp.position_type = u''
        self.assertEqual(
            hp.gender_and_number_from_position_type(),
            {'FP': u'',
             'FS': u'',
             'MP': u'',
             'MS': u''})

    def test_pm_Get_prefix_for_gender_and_number(self):
        """Add relevant prefix before position_type depending
           on gender/number and taking into account first letter (vowel/consonant)."""
        self.changeUser('siteadmin')
        self.portal.contacts.position_types = [
            {'token': u'default', 'name': u'D\xe9faut'},
            {'token': u'admin', 'name': u'Administrateur|Administrateurs|Administratrice|Administratrices'},
            {'token': u'director', 'name': u'Directeur|Directeurs|Directrice|Directrices'}]
        person = self.portal.contacts.get('person1')
        hp = person.get_held_positions()[0]
        hp.position_type = u'admin'
        self.assertEqual(hp.label, u'Assembly member 1')
        self.assertEqual(hp.get_prefix_for_gender_and_number(), '')
        hp.label = u'Administrateur'
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"L'")
        hp.label = u'Administratrice'
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"L'")
        hp.position_type = u'director'
        self.assertEqual(hp.label, u'Administratrice')
        self.assertEqual(hp.get_prefix_for_gender_and_number(), '')
        hp.label = u'Directeur'
        self.assertEqual(person.gender, u'M')
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"Le ")
        hp.label = u'Directrice'
        person.gender = u'F'
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"La ")
        # when no label defined, label is taken from selected position_type
        hp.label = u''
        hp.position_type = u'admin'
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"L'")
        self.assertEqual(hp.get_prefix_for_gender_and_number(include_value=True), u"L'Administratrice")
        hp.position_type = u'director'
        person.gender = u'M'
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"Le ")
        person.gender = u'F'
        person.person_title = u'Madame'
        self.assertEqual(hp.get_prefix_for_gender_and_number(), u"La ")
        # include_value and include_person_title
        self.assertEqual(hp.get_prefix_for_gender_and_number(include_value=True), u"La Directrice")
        # prefix first letter is lowerized
        self.assertEqual(
            hp.get_prefix_for_gender_and_number(include_value=True, include_person_title=True),
            u'Madame la Directrice')

        # we may give a position_type_attr, this is usefull when using field secondary_position_type
        self.assertIsNone(hp.secondary_position_type)
        # when position_type_attr value is None, fallback to 'position_type' by default
        self.assertEqual(hp.get_prefix_for_gender_and_number(
            include_value=True,
            position_type_attr='secondary_position_type'),
            u'La Directrice')
        self.assertEqual(hp.get_prefix_for_gender_and_number(
            include_value=True,
            position_type_attr='secondary_position_type',
            fallback_position_type_attr=None),
            u'')
        hp.secondary_position_type = u'admin'
        # include_value and include_person_title
        self.assertEqual(hp.get_prefix_for_gender_and_number(
            include_value=True, position_type_attr='secondary_position_type'),
            u"L'Administratrice")
        # prefix first letter is lowerized
        self.assertEqual(
            hp.get_prefix_for_gender_and_number(include_value=True,
                                                include_person_title=True,
                                                position_type_attr='secondary_position_type'),
            u"Madame l'Administratrice")

    def test_pm_RemoveNotSelectedOrganization(self):
        """Check that removing a not selected organization works correctly."""
        self.changeUser('siteadmin')
        own_org = get_own_organization()

        # create a new organization
        new_org = self.create('organization', id='new_org', title=u'New org', acronym='NO1')
        new_org_id = new_org.getId()
        # remove it
        own_org.manage_delObjects([new_org_id])

    def test_pm_InactiveHeldPositionsStillViewableOnMeeting(self):
        """If an held_position is disabled, it is still viewable on existing meetings."""
        cfg = self.meetingConfig
        # give access to powerobservers to meeting when it is created
        self._setPowerObserverStates(
            field_name='meeting_states',
            states=(self._stateMappingFor('created', meta_type='Meeting'),))
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        meeting_attendees = meeting.getAttendees(theObjects=True)
        self.assertEqual(len(meeting_attendees), 4)
        hp = meeting_attendees[0]
        # deactivate an held_position
        self.changeUser('siteadmin')
        self.do(hp, 'deactivate')
        # still viewable by MeetingManagers
        self.changeUser('pmManager')
        meeting_attendees = meeting.getAttendees(theObjects=True)
        self.assertEqual(len(meeting_attendees), 4)
        # and other users
        self.changeUser('pmCreator1')
        meeting_attendees = meeting.getAttendees(theObjects=True)
        self.assertEqual(len(meeting_attendees), 4)
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, meeting))
        meeting_attendees = meeting.getAttendees(theObjects=True)
        self.assertEqual(len(meeting_attendees), 4)

    def test_pm_directory_position_types_invariant(self):
        class DummyData(object):
            def __init__(self, context, position_types):
                self.__context__ = context
                self.position_types = position_types

        position_types = self.portal.contacts.position_types
        self.assertEqual(position_types, [{'token': 'default', 'name': u'D\xe9faut'}])
        hp = self.portal.contacts.person1.held_pos1
        self.assertEqual(hp.position_type, 'default')
        invariant = IPMDirectory.getTaggedValue('invariants')[0]

        # can not remove used position_type
        data = DummyData(self.portal.contacts, position_types=[])
        with self.assertRaises(Invalid) as cm:
            invariant(data)
        error_msg = translate(
            msgid="removed_position_type_in_use_error",
            mapping={'removed_position_type': hp.position_type,
                     'hp_url': hp.absolute_url()},
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(cm.exception.message, error_msg)

        # adding new value or removing an unused one is ok
        position_types2 = position_types + [{'token': 'default2', 'name': u'D\xe9faut2'}]
        self.portal.contacts.position_types = position_types2
        data = DummyData(self.portal.contacts, position_types2)
        self.assertIsNone(invariant(data))
        data = DummyData(self.portal.contacts, position_types)
        self.assertIsNone(invariant(data))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testContacts, prefix='test_pm_'))
    return suite
