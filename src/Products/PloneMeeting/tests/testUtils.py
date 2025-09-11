# -*- coding: utf-8 -*-
#
# File: testUtils.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_plone_group
from ftw.labels.interfaces import ILabeling
from imio.helpers.content import richtextval
from os import path
from plone.app.controlpanel.events import ConfigurationChangedEvent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import EXECUTE_EXPR_VALUE
from Products.PloneMeeting.ftw_labels.utils import get_labels
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import duplicate_portal_type
from Products.PloneMeeting.utils import escape
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.PloneMeeting.utils import org_id_to_uid
from Products.PloneMeeting.utils import sendMail
from Products.PloneMeeting.utils import sendMailIfRelevant
from Products.PloneMeeting.utils import set_dx_value
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.PloneMeeting.utils import transformAllRichTextFields
from Products.PloneMeeting.utils import validate_item_assembly_value
from zope.event import notify
from zope.schema._bootstrapinterfaces import WrongType


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
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'), ))
        cfg.setItemAdviceViewStates((self._stateMappingFor('proposed'), ))

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
        # will raise Unauthorized if user can not edit
        self.proposeItem(item)
        self.assertRaises(Unauthorized, set_field_from_ajax, item, 'description', new_value)

        # meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        new_value = "<p>My meeting notes.</p>"
        self.assertIsNone(meeting.notes)
        self.assertFalse(self.catalog(SearchableText="my meeting notes"))
        set_field_from_ajax(meeting, 'notes', new_value)
        self.assertEqual(meeting.notes.output, new_value)
        self.assertEqual(self.catalog(SearchableText="my meeting notes")[0].UID, meeting.UID())
        # will raise Unauthorized if user can not edit
        self.closeMeeting(meeting)
        self.assertRaises(Unauthorized, set_field_from_ajax, meeting, 'notes', new_value)

        # advice
        self.changeUser('pmReviewer2')
        advice = self.addAdvice(item, advice_comment=u"")
        new_value = "<p>My advice comment.</p>"
        self.assertEqual(advice.advice_comment.raw, u"")
        self.assertFalse(self.catalog(SearchableText="my advice comment"))
        set_field_from_ajax(advice, 'advice_comment', new_value)
        self.assertEqual(advice.advice_comment.output, new_value)
        # will raise Unauthorized if user can not edit
        self.validateItem(item)
        self.assertRaises(Unauthorized, set_field_from_ajax, item, 'description', new_value)

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

        # deactivated
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
                safe_unicode(cfg.Title())))
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
        # test also that custom state/transition title works
        self._updateItemValidationLevel(
            cfg,
            level=self._stateMappingFor('proposed'),
            state_title="New proposed title",
            leading_transition_title="New propose title")

        self.changeUser('pmManager')
        item = self.create("MeetingItem", title="My item")
        self.proposeItem(item)
        params = {"obj": item,
                  "event": "item_state_changed_validate",
                  "value": [self.developers_creators, self.vendors_creators],
                  "isGroupIds": True,
                  "debug": True}

        recipients, subject, body = sendMailIfRelevant(**params)
        # config wf state/transition title is correctly used
        self.assertTrue("New proposed title" in subject)
        self.assertTrue("New propose title" in subject)
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

    def _default_permission_mail_recipents(self):
        return [u'M. Budget Impact Editor <budgetimpacteditor@plonemeeting.org>',
                u'M. PMCreator One <pmcreator1@plonemeeting.org>',
                u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
                u'M. PMObserver One <pmobserver1@plonemeeting.org>',
                u'M. PMReviewer One <pmreviewer1@plonemeeting.org>',
                u'M. Power Observer1 <powerobserver1@plonemeeting.org>',
                u'Site administrator <siteadmin@plonemeeting.org>']

    def _modify_permission_mail_recipents(self):
        return [u'M. PMCreator One <pmcreator1@plonemeeting.org>',
                u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
                u'Site administrator <siteadmin@plonemeeting.org>']

    def test_pm_SendMailIfRelevantIsPermission(self):
        """ """
        cfg = self.meetingConfig
        cfg.setMailMode("activated")
        cfg.setMailItemEvents(("item_state_changed_validate", ))

        self.changeUser('pmManager')
        item = self.create("MeetingItem", title="My item")
        params = {"obj": item,
                  "event": "item_state_changed_validate",
                  "value": View,
                  "isPermission": True,
                  "debug": True}

        recipients, subject, body = sendMailIfRelevant(**params)
        # not sent to action triggerer
        self.assertEqual(sorted(recipients), self._default_permission_mail_recipents())
        # check for editors
        params["value"] = ModifyPortalContent
        recipients, subject, body = sendMailIfRelevant(**params)
        self.assertEqual(sorted(recipients), self._modify_permission_mail_recipents())

    def test_pm_SendMailMeetingConfigTitle(self):
        """Variable "meetingConfigTitle" used in mail subject will include
           MeetingConfig.groupConfig when relevant."""
        config_groups = (
            {'row_id': 'unique_id_1',
             'label': 'ConfigGroup1',
             'full_label': 'Config group 1'},
            {'row_id': 'unique_id_2',
             'label': 'ConfigGroup2',
             'full_label': 'Config group 2'},
            {'row_id': 'unique_id_3',
             'label': 'ConfigGroup3',
             'full_label': 'Config group 3'},
        )
        self.tool.setConfigGroups(config_groups)
        cfg = self.meetingConfig
        # "test" mailMode will return computed elements
        cfg.setMailMode('test')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        obj, body, recipients, from_address, subject, attachments, translation_mapping = \
            sendMail([], item, '')
        # no config group, simple title
        self.assertEqual(translation_mapping['meetingConfigTitle'],
                         safe_unicode(cfg.Title()))
        # config group but different config title, simple title
        cfg.setConfigGroup('unique_id_3')
        obj, body, recipients, from_address, subject, attachments, translation_mapping = \
            sendMail([], item, '')
        self.assertEqual(translation_mapping['meetingConfigTitle'],
                         safe_unicode(cfg.Title()))
        # with several same config title, config group is preprended
        self.meetingConfig2.setTitle(cfg.Title())
        obj, body, recipients, from_address, subject, attachments, translation_mapping = \
            sendMail([], item, '')
        self.assertEqual(translation_mapping['meetingConfigTitle'],
                         u'Config group 3 - %s' % safe_unicode(cfg.Title()))
        # if "full_label" is empty, it is not preprended
        config_groups[-1]['full_label'] = ''
        self.tool.setConfigGroups(config_groups)
        obj, body, recipients, from_address, subject, attachments, translation_mapping = \
            sendMail([], item, '')
        self.assertEqual(translation_mapping['meetingConfigTitle'],
                         safe_unicode(cfg.Title()))

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

    def test_pm_TransformAllRichTextFields(self):
        """Test that it does not alterate field content, especially
           links to internal content or image that uses resolveuid."""

        # MeetingItem AT
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # add image
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        file_handler = open(file_path, 'r')
        data = file_handler.read()
        file_handler.close()
        img_id = item.invokeFactory('Image', id='dot.gif', title='Image', file=data)
        img = getattr(item, img_id)

        # link to image using resolveuid
        text = '<p>Internal image <img src="resolveuid/{0}" />.</p>'.format(img.UID())
        item.setDescription(text)
        self.assertEqual(item.objectIds(), ['dot.gif'])
        transformAllRichTextFields(item)
        self.assertEqual(item.getRawDescription(), text)
        transformAllRichTextFields(item, onlyField="description")
        self.assertEqual(item.getRawDescription(), text)

        # Meeting DX
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # add image
        img_id = meeting.invokeFactory('Image', id='dot.gif', title='Image', file=data)
        img = getattr(meeting, img_id)

        # link to image using resolveuid
        text = '<p>Internal image <img src="resolveuid/{0}" />.</p>'.format(img.UID())
        meeting.observations = richtextval(text)
        self.assertEqual(meeting.objectIds(), ['dot.gif'])
        transformAllRichTextFields(meeting)
        self.assertEqual(meeting.observations.raw, text)
        transformAllRichTextFields(meeting, onlyField="observations")
        self.assertEqual(meeting.observations.raw, text)

    def test_pm_Set_dx_value(self):
        """utils.set_dx_value will set a value on a DX content and check if current
           user has the permission and if the value does validate."""
        cfg = self.meetingConfig
        self._enableField('meeting_number', related_to='Meeting')
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # if user able to set, data must validate
        # here first_item_number needs an integer
        self.assertEqual(meeting.first_item_number, -1)
        self.assertRaises(WrongType, set_dx_value, meeting, "first_item_number", "a")
        set_dx_value(meeting, "first_item_number", 50)
        self.assertEqual(meeting.first_item_number, 50)
        # can not do it if does not have the permission
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertRaises(WrongType, set_dx_value, meeting, "first_item_number", "a")
        self.assertRaises(Unauthorized, set_dx_value, meeting, "first_item_number", 55)
        # parameter raise_unauthorized may be False
        set_dx_value(meeting, "first_item_number", 55, raise_unauthorized=False)
        # the value is not changed anyway
        self.assertEqual(meeting.first_item_number, 50)
        # make sure it is useable in TAL expressions
        self.changeUser('pmManager')
        cfg.setOnMeetingTransitionItemActionToExecute(
            [{'meeting_transition': 'freeze',
              'item_action': EXECUTE_EXPR_VALUE,
              'tal_expression':
                'python: pm_utils.set_dx_value(meeting, "meeting_number", 25)'}, ])
        self.assertEqual(meeting.meeting_number, -1)
        self.freezeMeeting(meeting)
        # if was initialized to "1" by doFreeze but onMeetingTransitionItemActionToExecute
        # did nothing because it is applied on each items and there are no items!
        # So when using it to update meeting we really need to make sure the work done
        # is only done one time
        self.assertEqual(meeting.meeting_number, 1)
        # set it back to -1 so we make sure onMeetingTransitionItemActionToExecute
        # is done after doFreeze
        meeting.meeting_number = -1
        self.do(meeting, 'backToCreated')
        item = self.create('MeetingItem', decision=self.decisionText)
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.assertEqual(meeting.meeting_number, 25)

    def test_pm_get_labels(self):
        """Test the ToolPloneMeeting.get_labels method
           that will return ftw.labels active_labels."""
        self.changeUser("pmCreator1")
        item = self.create("MeetingItem")
        self.assertEqual(get_labels(item), {})
        labeling = ILabeling(item)
        labeling.update(['label'])
        labeling.pers_update(['suivi'], True)
        self.assertEqual(get_labels(item), {'label': 'Label', 'suivi': 'Suivi'})
        self.assertEqual(get_labels(item, False), {'label': 'Label'})
        self.assertEqual(get_labels(item, "only"), {'suivi': 'Suivi'})

    def test_pm_IsPowerObserverForCfg(self):
        """ """
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.assertFalse(isPowerObserverForCfg(cfg))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['powerobservers']))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['restrictedpowerobservers']))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['powerobservers', 'restrictedpowerobservers']))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['unknown']))
        self.changeUser('powerobserver1')
        self.assertTrue(isPowerObserverForCfg(cfg))
        self.assertTrue(isPowerObserverForCfg(
            cfg, power_observer_types=['powerobservers']))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['restrictedpowerobservers']))
        self.assertTrue(isPowerObserverForCfg(
            cfg, power_observer_types=['powerobservers', 'restrictedpowerobservers']))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['unknown']))
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(isPowerObserverForCfg(cfg))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['powerobservers']))
        self.assertTrue(isPowerObserverForCfg(
            cfg, power_observer_types=['restrictedpowerobservers']))
        self.assertTrue(isPowerObserverForCfg(
            cfg, power_observer_types=['powerobservers', 'restrictedpowerobservers']))
        self.assertFalse(isPowerObserverForCfg(
            cfg, power_observer_types=['unknown']))


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testUtils, prefix='test_pm_'))
    return suite
