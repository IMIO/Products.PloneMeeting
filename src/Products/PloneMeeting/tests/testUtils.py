# -*- coding: utf-8 -*-
#
# File: testUtils.py
#
# GNU General Public License (GPL)
#

from collective.contact.plonegroup.utils import get_plone_group
from DateTime import DateTime
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import sendMailIfRelevant
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

    def test_pm_SendMailIfRelevant(self):
        """ """
        cfg = self.meetingConfig
        cfg.setMailMode("deactivated")
        self.changeUser('pmManager')
        self.create("Meeting", date=DateTime("2020/11/25"))
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
