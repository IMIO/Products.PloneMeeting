# -*- coding: utf-8 -*-
#
# File: testUtils.py
#
# GNU General Public License (GPL)
#

from collective.contact.plonegroup.utils import get_plone_group
from plone.app.controlpanel.events import ConfigurationChangedEvent
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import duplicate_portal_type
from Products.PloneMeeting.utils import escape
from Products.PloneMeeting.utils import org_id_to_uid
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.PloneMeeting.utils import validate_item_assembly_value
from zope.event import notify


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
        item = self.create("MeetingItem", title="My item")
        params = {"obj": item,
                  "event": "itemPresented",
                  "value": "creators",
                  "isSuffix": True,
                  "debug": True}

        # disabled
        self.assertIsNone(sendMailIfRelevant(**params))
        # enabled but not selected
        cfg.setMailMode("activated")
        self.assertIsNone(sendMailIfRelevant(**params))
        # enabled and selected
        cfg.setMailItemEvents(("itemPresented", ))
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

    def test_pm_SendMailIfRelevantIsGroupIds(self):
        """ """
        cfg = self.meetingConfig
        cfg.setMailMode("activated")
        cfg.setMailItemEvents(("item_state_changed_validate", ))

        self.changeUser('pmManager')
        item = self.create("MeetingItem", title="My item")
        params = {"obj": item,
                  "event": "item_state_changed_validate",
                  "value": [self.developers_creators, self.vendors_creators],
                  "isGroupIds": True,
                  "debug": True}

        recipients, subject, body = sendMailIfRelevant(**params)
        dev_creators = get_plone_group(self.developers_uid, 'creators')
        self.assertEqual(dev_creators.getMemberIds(),
                         ['pmCreator1', 'pmCreator1b', 'pmManager'])
        vendors_creators = get_plone_group(self.vendors_uid, 'creators')
        self.assertEqual(vendors_creators.getMemberIds(), ['pmCreator2'])
        # not sent to action triggerer
        self.assertEqual(recipients,
                         [u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
                          u'M. PMCreator One <pmcreator1@plonemeeting.org>',
                          u'M. PMCreator Two <pmcreator2@plonemeeting.org>'])

    def test_pm_SendMailIfRelevantIsUserIds(self):
        """ """
        cfg = self.meetingConfig
        cfg.setMailMode("activated")
        cfg.setMailItemEvents(("item_state_changed_validate", ))

        self.changeUser('pmManager')
        item = self.create("MeetingItem", title="My item")
        params = {"obj": item,
                  "event": "item_state_changed_validate",
                  "value": ['pmObserver1', 'pmManager', 'pmCreator2'],
                  "isUserIds": True,
                  "debug": True}

        recipients, subject, body = sendMailIfRelevant(**params)
        # not sent to action triggerer
        self.assertEqual(recipients,
                         [u'M. PMObserver One <pmobserver1@plonemeeting.org>',
                          u'M. PMCreator Two <pmcreator2@plonemeeting.org>'])

    def test_pm_org_id_to_uid(self):
        """Test the utils.org_id_to_uid function."""
        self.changeUser('pmManager')
        # org UID
        self.assertIsNone(org_id_to_uid(''))
        self.assertEqual(org_id_to_uid(self.developers.getId()), self.developers_uid)
        self.assertEqual(org_id_to_uid(self.vendors.getId()), self.vendors_uid)
        # org UID with suffix
        dev_id_creators = "{0}_creators".format(self.developers.getId())
        dev_uid_creators = "{0}_creators".format(self.developers.UID())
        self.assertEqual(org_id_to_uid(dev_id_creators), dev_uid_creators)
        ven_id_creators = "{0}_creators".format(self.vendors.getId())
        ven_uid_creators = "{0}_creators".format(self.vendors.UID())
        self.assertEqual(org_id_to_uid(ven_id_creators), ven_uid_creators)
        # raise_on_error
        self.assertRaises(KeyError, org_id_to_uid, "wrong/path")
        self.assertIsNone(org_id_to_uid("wrong/path", raise_on_error=False))

    def test_pm_duplicate_portal_type(self):
        """Test the utils.duplicate_portal_type function."""
        self.changeUser('siteadmin')
        new_portal_type = duplicate_portal_type("MeetingItem", "MeetingItemDummy")
        self.assertEqual(new_portal_type.id, "MeetingItemDummy")
        self.assertEqual(new_portal_type.title, "MeetingItemDummy")
        # there was a bug, categorized_elements from collective.iconifiedcategory
        # was computed on every IItem, and a portal_type is a IItem...
        self.assertFalse('categorized_elements' in new_portal_type.__dict__)

    def test_pm_escape(self):
        self.assertEqual(escape('Test < & > are replaced with HTML "entities"'),
                         'Test &lt; &amp; &gt; are replaced with HTML &quot;entities&quot;')
        self.assertEqual(escape('<h1>We have no respect for <em><strong>HTML tags</strong></em> either</h1>'),
                         '&lt;h1&gt;We have no respect for &lt;em&gt;&lt;strong&gt;'
                         'HTML tags&lt;/strong&gt;&lt;/em&gt; either&lt;/h1&gt;')

    def test_pm_GetMemberInfo(self):
        """Test portal_membership.getMemberInfo as is it monkeypatched to add caching."""
        pm = self.portal.portal_membership
        self.changeUser("pmManager")
        self.assertEqual(pm.getMemberInfo("pmManager")["fullname"], 'M. PMManager')
        self.member.setMemberProperties({"fullname": "M. PMManager New"})
        # still not changed as cache was not invalidated
        self.assertEqual(pm.getMemberInfo("pmManager")["fullname"], 'M. PMManager')
        notify(ConfigurationChangedEvent(self.portal, self.request))
        self.assertEqual(pm.getMemberInfo("pmManager")["fullname"], 'M. PMManager New')


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testUtils, prefix='test_pm_'))
    return suite
