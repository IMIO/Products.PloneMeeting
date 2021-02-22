# -*- coding: utf-8 -*-
#
# File: testUtils.py
#
# GNU General Public License (GPL)
#

from collective.contact.plonegroup.utils import get_plone_group
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.PloneMeeting.utils import validate_item_assembly_value


ASSEMBLY_CORRECT_VALUE = u'[[Text]][[Text]]'
ASSEMBLY_WRONG_VALUE = u'[[Text Text'


class testUtils(PloneMeetingTestCase):
    '''Tests the utils methods.'''

    def test_pm_Validate_item_assembly_value(self):
        """This will check the itemAssembly validity regarding [[ and ]]."""
        # empty value
        self.assertTrue(validate_item_assembly_value(u''))
        # correct values
        self.assertTrue(validate_item_assembly_value(ASSEMBLY_CORRECT_VALUE))
        self.assertTrue(validate_item_assembly_value(u'[[Text]] Text Text [[Text]]'))
        self.assertTrue(validate_item_assembly_value(u'[[Text]] Text Text [[Text]]'))
        self.assertTrue(validate_item_assembly_value(u'Text Text Text [[Text]]'))
        self.assertTrue(validate_item_assembly_value(u'[[Text]] Text Text Text'))
        self.assertTrue(validate_item_assembly_value(u'Text Text [[Text]] Text'))
        # wrong values
        self.assertFalse(validate_item_assembly_value(ASSEMBLY_WRONG_VALUE))
        self.assertFalse(validate_item_assembly_value(u'[[Text [[Text'))
        self.assertFalse(validate_item_assembly_value(u'[[Text [[Text'))
        self.assertFalse(validate_item_assembly_value(u']]Text [[Text'))
        self.assertFalse(validate_item_assembly_value(u'Text [[Text'))
        self.assertFalse(validate_item_assembly_value(u'Text Text]]'))

        # we have a special case, if REQUEST contains 'initial_edit', then validation
        # is bypassed, this let's edit an old wrong value
        self.request.set('initial_edit', u'1')
        self.assertTrue(validate_item_assembly_value(ASSEMBLY_WRONG_VALUE))

    def test_pm_Set_field_from_ajax(self):
        """Work on AT and DX."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'), ))

        # item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        new_value = "<p>My item description.</p>"
        self.assertEqual(item.Description(), "")
        self.assertFalse(self.catalog(Description="my item description"))
        set_field_from_ajax(item, 'description', new_value)
        self.assertEqual(item.Description(), new_value)
        self.assertEqual(self.catalog(Description="my item description")[0].UID, item.UID())
        self.assertEqual(self.catalog(SearchableText="my item description")[0].UID, item.UID())

        # meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        new_value = "<p>My meeting notes.</p>"
        self.assertIsNone(meeting.notes)
        self.assertFalse(self.catalog(SearchableText="my meeting notes"))
        set_field_from_ajax(meeting, 'notes', new_value)
        self.assertEqual(meeting.notes.output, new_value)
        self.assertEqual(self.catalog(SearchableText="my meeting notes")[0].UID, meeting.UID())

        # advice
        self.changeUser('pmReviewer2')
        advice = self.addAdvice(item, advice_comment=u"")
        new_value = "<p>My advice comment.</p>"
        self.assertEqual(advice.advice_comment.raw, u"")
        self.assertFalse(self.catalog(SearchableText="my advice comment"))
        set_field_from_ajax(advice, 'advice_comment', new_value)
        self.assertEqual(advice.advice_comment.output, new_value)

    def test_pm_SendMailIfRelevant(self):
        """ """
        cfg = self.meetingConfig
        cfg.setMailMode("deactivated")
        self.changeUser('pmManager')
        self.create("Meeting")
        item = self.create("MeetingItem", title="My item")
        self.presentItem(item)
        params = {"obj": item,
                  "event": "itemPresented",
                  "permissionOrSuffixOrRoleOrGroupIds": "creators",
                  "isSuffix": True,
                  "debug": True}
        # disabled
        self.assertIsNone(sendMailIfRelevant(**params))
        # enabled but not selected
        cfg.setMailMode("activated")
        self.assertIsNone(sendMailIfRelevant(**params))
        # enabled and selected
        cfg.setMailItemEvents(("itemPresented", ))
        self.assertTrue(sendMailIfRelevant(**params))
        recipients, subject, body = sendMailIfRelevant(**params)
        dev_creators = get_plone_group(self.developers_uid, 'creators')
        self.assertEqual(dev_creators.getMemberIds(),
                         ['pmCreator1', 'pmCreator1b', 'pmManager'])
        # not sent to action triggerer
        self.assertEqual(recipients,
                         [u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
                          u'M. PMCreator One <pmcreator1@plonemeeting.org>'])
        self.assertEqual(
            subject,
            u"{0} - Item has been inserted into a meeting - My item".format(
                cfg.Title()))
        self.assertEqual(
            body,
            u"This meeting may still be under construction and is potentially inaccessible.  "
            u"The item is entitled \"My item\". You can access this item here: {0}.".format(
                item.absolute_url()))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testUtils, prefix='test_pm_'))
    return suite
