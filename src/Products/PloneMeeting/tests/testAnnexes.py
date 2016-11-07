# -*- coding: utf-8 -*-
#
# File: testAnnexes.py
#
# Copyright (c) 2016 by Imio.be
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
from DateTime import DateTime
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.indexes import SearchableText
from Products.PloneMeeting.profiles.testing import import_data
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import update_annexes
from Products.PloneMeeting.MeetingConfig import PROPOSINGGROUPPREFIX
from Products.PloneMeeting.MeetingConfig import SUFFIXPROFILEPREFIX


class testAnnexes(PloneMeetingTestCase):
    '''Tests various aspects of annexes management.'''

    def test_pm_MayChangeAnnexConfidentiality(self):
        '''May change if :
           - confidentiality enabled;
           - has the Modify portal content permission;
           - is a MeetingManager.
           '''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        self.assertFalse(annex.confidential)
        self.assertTrue(self.hasPermission(ModifyPortalContent, annex))
        annex_config = get_config_root(annex)
        annex_group = get_group(annex_config, annex)

        self.assertFalse(annex_group.confidentiality_activated)
        view = annex.restrictedTraverse('@@iconified-confidential')
        self.assertRaises(Unauthorized,
                          view.set_values, {'confidential': 'true'})
        # enable confidentiality
        annex_group.confidentiality_activated = True
        # now it fails because not a MeetingManager
        self.assertFalse(self.tool.isManager(annex))
        self.assertRaises(Unauthorized,
                          view.set_values, {'confidential': 'true'})

        # right, now as a MeetingManager, it works
        self.changeUser('pmManager')
        view.set_values({'confidential': 'true'})
        self.assertTrue(annex.confidential)

    def _setupConfidentialityOnItemAnnexes(self):
        """ """
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex_config = get_config_root(item)
        annex_group = get_group(annex_config, item)
        annex_group.confidentiality_activated = True
        annexes_table = item.restrictedTraverse('@@iconifiedcategory')
        categorized_child = item.restrictedTraverse('@@categorized-childs')

        annexNotConfidential = self.addAnnex(item, annexTitle='Annex not confidential')
        annexConfidential = self.addAnnex(item, annexTitle='Annex confidential')
        annexConfidential.confidential = True
        notify(ObjectModifiedEvent(annexConfidential))
        return item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForBudgetImpactEditors(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        # give budget impact editors view on item
        item.__ac_local_roles__['{0}_{1}'.format(cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)] = 'Reader'

        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_budgetimpacteditors', ))
        update_annexes(item)

        self.changeUser('budgetimpacteditor')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        cfg.setItemPowerObserversStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        item.updateLocalRoles()

        self.changeUser('powerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForRestrictedPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        cfg.setItemRestrictedPowerObserversStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        item.updateLocalRoles()

        self.changeUser('restrictedpowerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForAdvisers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        cfg.setItemAdviceStates((item_initial_state, ))
        cfg.setItemAdviceEditStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('reader_advices', ))
        item.setOptionalAdvisers(('developers', ))
        item.updateLocalRoles()

        self.changeUser('pmAdviser1')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForCopyGroups(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('reader_copy_groups', ))
        item.setCopyGroups(('vendors_reviewers', ))
        item.updateLocalRoles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForGroupInCharge(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        proposingGroup = item.getProposingGroup(theObject=True)
        cfg.setItemGroupInChargeStates(item_initial_state)

        # does not fail in no group in charge
        self.assertFalse(proposingGroup.getGroupInChargeAt())
        cfg.setItemAnnexConfidentialVisibleFor(('reader_groupincharge', ))
        update_annexes(item)
        proposingGroup.setGroupInCharge(({'group_id': 'vendors', 'date_to': ''},))
        item.updateLocalRoles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForProposingGroupSuffixes(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        # validate the item so it is visible by every roles of the proposing group
        self.validateItem(item)
        self.assertEqual(item.queryState(), 'validated')

        proposingGroupSuffixes = [k for k in cfg.listItemAnnexConfidentialVisibleFor()
                                  if k.startswith(PROPOSINGGROUPPREFIX)]
        for proposingGroupSuffix in proposingGroupSuffixes:
            cfg.setItemAnnexConfidentialVisibleFor((proposingGroupSuffix, ))
            update_annexes(item)
            # get a user from the right 'developers' subgroup
            username = getattr(import_data.developers,
                               proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, ''))[0].id
            self.changeUser(username)
            if not self.hasPermission(View, item):
                pm_logger.info("Could not test if '%s' can access confidential "
                               "annexes because he may not see the item !" % self.member.getId())
                continue
            self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                      annexes_table, categorized_child)

    def _checkElementConfidentialAnnexAccess(self,
                                             cfg,
                                             obj,
                                             annexNotConfidential,
                                             annexConfidential,
                                             annexes_table,
                                             categorized_child):
        """ """
        self.assertTrue(self.hasPermission(View, obj))
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        cfg.setItemAnnexConfidentialVisibleFor(())
        cfg.setAdviceAnnexConfidentialVisibleFor(())
        cfg.setMeetingAnnexConfidentialVisibleFor(())
        update_annexes(obj)
        self._checkMayNotAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                   annexes_table, categorized_child)

    def _checkMayAccessConfidentialAnnexes(self,
                                           obj,
                                           annexNotConfidential,
                                           annexConfidential,
                                           annexes_table,
                                           categorized_child):
        """ """
        # current user may see every annexes
        self.assertEqual(set([elt['UID'] for elt in get_categorized_elements(obj)]),
                         set((annexNotConfidential.UID(),
                              annexConfidential.UID())))
        self.assertTrue('Annex not confidential' in annexes_table())
        self.assertTrue('Annex confidential' in annexes_table())
        self.assertTrue('Annex not confidential' in categorized_child())
        self.assertTrue('Annex confidential' in categorized_child())

    def _checkMayNotAccessConfidentialAnnexes(self,
                                              item,
                                              annexNotConfidential,
                                              annexConfidential,
                                              annexes_table,
                                              categorized_child):
        """ """
        # confidential annexes not viewable
        self.assertEqual([elt['UID'] for elt in get_categorized_elements(item)],
                         [annexNotConfidential.UID()])
        self.assertTrue('Annex not confidential' in annexes_table())
        self.assertFalse('Annex confidential' in annexes_table())
        self.assertTrue('Annex not confidential' in categorized_child())
        self.assertFalse('Annex confidential' in categorized_child())

    def _setupConfidentialityOnAdviceAnnexes(self):
        """ """
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state

        cfg.setItemAdviceStates((item_initial_state, ))
        cfg.setItemAdviceEditStates((item_initial_state, ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.updateLocalRoles()
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.tool.vendors.getId(),
               'advice_type': u'positive',
               'advice_comment': RichTextValue(u'My comment')})
        annex_config = get_config_root(advice)
        annex_group = get_group(annex_config, advice)
        annex_group.confidentiality_activated = True

        annexes_table = advice.restrictedTraverse('@@iconifiedcategory')
        categorized_child = advice.restrictedTraverse('@@categorized-childs')

        annexNotConfidential = self.addAnnex(advice, annexTitle='Annex not confidential')
        annexConfidential = self.addAnnex(advice, annexTitle='Annex confidential')
        annexConfidential.confidential = True
        notify(ObjectModifiedEvent(annexConfidential))
        return item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForAdviserGroup(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setAdviceAnnexConfidentialVisibleFor(('adviser_group', ))
        update_annexes(advice)

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForBudgetImpactEditors(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        # give budget impact editors view on item
        item.__ac_local_roles__['{0}_{1}'.format(cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)] = 'Reader'

        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_budgetimpacteditors', ))
        update_annexes(advice)

        self.changeUser('budgetimpacteditor')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForAdvisers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_advices', ))
        update_annexes(advice)

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForCopyGroups(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((item_initial_state, ))
        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_copy_groups', ))
        item.setCopyGroups(('vendors_reviewers', ))
        item.updateLocalRoles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForGroupInCharge(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        proposingGroup = item.getProposingGroup(theObject=True)
        cfg.setItemGroupInChargeStates(item_initial_state)

        # does not fail in no group in charge
        self.assertFalse(proposingGroup.getGroupInChargeAt())
        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_groupincharge', ))
        update_annexes(item)
        proposingGroup.setGroupInCharge(({'group_id': 'vendors', 'date_to': ''},))
        item.updateLocalRoles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setItemPowerObserversStates((item_initial_state, ))
        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        item.updateLocalRoles()

        self.changeUser('powerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForRestrictedPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setItemRestrictedPowerObserversStates((item_initial_state, ))
        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        item.updateLocalRoles()

        self.changeUser('restrictedpowerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForProposingGroupSuffixes(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        # validate the item so it is visible by every roles of the proposing group
        self.validateItem(item)
        self.assertEqual(item.queryState(), 'validated')

        proposingGroupSuffixes = [k for k in cfg.listItemAnnexConfidentialVisibleFor()
                                  if k.startswith(PROPOSINGGROUPPREFIX)]
        for proposingGroupSuffix in proposingGroupSuffixes:
            cfg.setAdviceAnnexConfidentialVisibleFor((proposingGroupSuffix, ))
            update_annexes(advice)
            # get a user from the right 'developers' subgroup
            username = getattr(import_data.developers,
                               proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, ''))[0].id
            self.changeUser(username)
            if not self.hasPermission(View, advice):
                pm_logger.info("Could not test if '%s' can access confidential "
                               "annexes because he may not see the item !" % self.member.getId())
                continue
            self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                      annexes_table, categorized_child)

    def _setupConfidentialityOnMeetingAnnexes(self):
        """ """
        cfg = self.meetingConfig
        cfgMeetingWF = self.wfTool.getWorkflowsFor(cfg.getMeetingTypeName())[0]
        meeting_initial_state = self.wfTool[cfgMeetingWF.getId()].initial_state

        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/10/10'))
        annex_config = get_config_root(meeting)
        annex_group = get_group(annex_config, meeting)
        annex_group.confidentiality_activated = True

        annexes_table = meeting.restrictedTraverse('@@iconifiedcategory')
        categorized_child = meeting.restrictedTraverse('@@categorized-childs')

        annexNotConfidential = self.addAnnex(meeting, annexTitle='Annex not confidential')
        annexConfidential = self.addAnnex(meeting, annexTitle='Annex confidential')
        annexConfidential.confidential = True
        notify(ObjectModifiedEvent(annexConfidential))
        return meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential

    def test_pm_MeetingGetCategorizedElementsWithConfidentialityForPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnMeetingAnnexes()

        cfg.setMeetingPowerObserversStates((meeting_initial_state, ))
        cfg.setMeetingAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        meeting.updateLocalRoles()

        self.changeUser('powerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_MeetingGetCategorizedElementsWithConfidentialityForRestrictedPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnMeetingAnnexes()

        cfg.setMeetingRestrictedPowerObserversStates((meeting_initial_state, ))
        cfg.setMeetingAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        meeting.updateLocalRoles()

        self.changeUser('restrictedpowerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_MeetingGetCategorizedElementsWithConfidentialityForProposingGroupProfiles(self):
        ''' '''
        cfg = self.meetingConfig
        meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnMeetingAnnexes()

        # freeze the meeting so it is visible by every profiles
        self.freezeMeeting(meeting)
        self.assertEqual(meeting.queryState(), 'frozen')

        profileSuffixes = [k for k in cfg.listMeetingAnnexConfidentialVisibleFor()
                           if k.startswith(SUFFIXPROFILEPREFIX)]
        for profileSuffix in profileSuffixes:
            # every users of a Plone subgroup profileSuffix will have access
            for groupConfig in (import_data.developers, import_data.vendors):
                cfg.setMeetingAnnexConfidentialVisibleFor((profileSuffix, ))
                update_annexes(meeting)
                # get a user from the right 'developers' subgroup
                users = getattr(groupConfig,
                                profileSuffix.replace(SUFFIXPROFILEPREFIX, ''))
                if not users:
                    pm_logger.info("Could not test if profile '%s' can access confidential "
                                   "annexes for group '%s' because no users is defined in this profile !"
                                   % (profileSuffix.replace(SUFFIXPROFILEPREFIX, ''), groupConfig.id))
                    continue
                username = users[0].id
                self.changeUser(username)
                if not self.hasPermission(View, meeting):
                    pm_logger.info("Could not test if '%s' can access confidential "
                                   "annexes because he may not see the item !" % self.member.getId())
                    continue
                self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                          annexes_table, categorized_child)

    def test_pm_AnnexesTitleFoundInItemSearchableText(self):
        '''MeetingFiles title is indexed in the item SearchableText.'''
        ANNEX_TITLE = "SpecialAnnexTitle"
        ITEM_TITLE = "SpecialItemTitle"
        ITEM_DESCRIPTION = "Item description"
        ITEM_DECISION = "Item decision"
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title=ITEM_TITLE)
        item.setDescription(ITEM_DESCRIPTION)
        item.setDecision(ITEM_DECISION)
        item.reindexObject(idxs=['SearchableText', ])
        catalog = self.portal.portal_catalog
        index = catalog.Indexes['SearchableText']
        self.assertTrue(len(catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertFalse(catalog(SearchableText=ANNEX_TITLE))
        self.assertEquals(SearchableText(item)(),
                          'SpecialItemTitle  <p>Item description</p>  <p>Item decision</p> ')
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p'])

        # add an annex and test that the annex title is found in the item's SearchableText
        annex = self.addAnnex(item, annexTitle=ANNEX_TITLE)
        # now querying for ANNEX_TITLE will return the relevant item
        self.assertTrue(len(catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ANNEX_TITLE)) == 2)
        self.assertEquals(SearchableText(item)(),
                          'SpecialItemTitle  <p>Item description</p>  <p>Item decision</p>  SpecialAnnexTitle ')
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p', 'specialannextitle'])
        # works also when clear and rebuild catalog
        self.portal.portal_catalog.clearFindAndRebuild()
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p', 'specialannextitle'])
        # if we remove the annex, the item is not found anymore when querying
        # on removed annex's title
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertTrue(catalog(SearchableText=ITEM_TITLE))
        self.assertFalse(catalog(SearchableText=ANNEX_TITLE))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAnnexes, prefix='test_pm_'))
    return suite
