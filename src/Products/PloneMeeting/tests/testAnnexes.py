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

from time import sleep
from AccessControl import Unauthorized
from DateTime import DateTime
from zope.annotation import IAnnotations
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from collective.documentviewer.config import CONVERTABLE_TYPES
from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.interfaces import IIconifiedPreview
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_group
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.helpers.cache import cleanRamCacheFor
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.indexes import SearchableText
from Products.PloneMeeting.profiles.testing import import_data
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
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
        categorized_child = item.restrictedTraverse('@@categorized-childs-infos')
        annex_category = cfg.annexes_types.item_annexes.get('financial-analysis')
        categorized_child.category_uid = annex_category.UID()

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
        update_all_categorized_elements(item)

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
        update_all_categorized_elements(item)
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
            update_all_categorized_elements(item)
            # get a user from the right 'developers' subgroup
            group_suffix = proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, '')
            users = getattr(import_data.developers, group_suffix)
            if not users:
                pm_logger.info("Could not test if developers.'%s' can access confidential "
                               "annexes because there are no user in the group !" % group_suffix)
                continue
            username = users[0].id
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
        update_all_categorized_elements(obj)
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
        cleanRamCacheFor('Products.PloneMeeting.adapters._user_groups')
        self.assertEqual(set([elt['UID'] for elt in get_categorized_elements(obj)]),
                         set((annexNotConfidential.UID(),
                              annexConfidential.UID())))
        self.assertTrue('Annex not confidential' in annexes_table())
        self.assertTrue('Annex confidential' in annexes_table())
        categorized_child.update()
        result = categorized_child.index()
        self.assertTrue('Annex not confidential' in result)
        self.assertTrue('Annex confidential' in result)

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
        categorized_child.update()
        result = categorized_child.index()
        self.assertTrue('Annex not confidential' in result)
        self.assertFalse('Annex confidential' in result)

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
        annex_category = cfg.annexes_types.advice_annexes.get('advice-annex')
        categorized_child = advice.restrictedTraverse('@@categorized-childs-infos')
        categorized_child.category_uid = annex_category.UID()

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
        update_all_categorized_elements(advice)

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
        update_all_categorized_elements(advice)

        self.changeUser('budgetimpacteditor')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForAdvisers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_advices', ))
        update_all_categorized_elements(advice)

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
        update_all_categorized_elements(item)
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
            update_all_categorized_elements(advice)
            # get a user from the right 'developers' subgroup
            group_suffix = proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, '')
            users = getattr(import_data.developers, group_suffix)
            if not users:
                pm_logger.info("Could not test if developers.'%s' can access confidential "
                               "annexes because there are no user in the group !" % group_suffix)
                continue
            username = users[0].id
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
        categorized_child = meeting.restrictedTraverse('@@categorized-childs-infos')
        annex_category = cfg.annexes_types.meeting_annexes.get('meeting-annex')
        categorized_child.category_uid = annex_category.UID()

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
                update_all_categorized_elements(meeting)
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
        ITEM_DESCRIPTION = "Item description text"
        ITEM_DECISION = "Item decision text"
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
        self.assertEquals(
            SearchableText(item)(),
            '{0}  <p>{1}</p>  <p>{2}</p> '.format(
                ITEM_TITLE, ITEM_DESCRIPTION, ITEM_DECISION)
        )
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          [ITEM_TITLE.lower(), 'p', 'item', 'description', 'text', 'p',
                           'p', 'item', 'decision', 'text', 'p'])

        # add an annex and test that the annex title is found in the item's SearchableText
        annex = self.addAnnex(item, annexTitle=ANNEX_TITLE)
        # now querying for ANNEX_TITLE will return the relevant item
        self.assertTrue(len(catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ANNEX_TITLE)) == 2)
        self.assertEquals(
            SearchableText(item)(),
            '{0}  <p>{1}</p>  <p>{2}</p>  {3} '.format(
                ITEM_TITLE, ITEM_DESCRIPTION, ITEM_DECISION, ANNEX_TITLE))
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          [ITEM_TITLE.lower(), 'p', 'item', 'description', 'text', 'p',
                           'p', 'item', 'decision', 'text', 'p', ANNEX_TITLE.lower()])
        # works also when clear and rebuild catalog
        self.portal.portal_catalog.clearFindAndRebuild()
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          [ITEM_TITLE.lower(), 'p', 'item', 'description', 'text', 'p',
                           'p', 'item', 'decision', 'text', 'p', ANNEX_TITLE.lower()])
        # if we remove the annex, the item is not found anymore when querying
        # on removed annex's title
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertTrue(catalog(SearchableText=ITEM_TITLE))
        self.assertFalse(catalog(SearchableText=ANNEX_TITLE))

    def test_pm_AnnexesConvertedIfAutoConvertIsEnabled(self):
        """If collective.documentviewer 'auto_convert' is enabled,
           the annexes and decision annexes are converted."""
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_convert = True
        gsettings.auto_layout_file_types = CONVERTABLE_TYPES.keys()

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        annex = self.addAnnex(item)
        # annex has been converted no matter 'to_print' value
        self.assertFalse(annex.to_print)
        self.assertTrue(IIconifiedPreview(annex).converted)

        # annex is not converted if auto_convert is disabled
        gsettings.auto_convert = False
        not_converted_annex = self.addAnnex(item)
        self.assertFalse(not_converted_annex.to_print)
        self.assertFalse(IIconifiedPreview(not_converted_annex).converted)

    def test_pm_AnnexesConvertedDependingOnAnnexToPrintMode(self):
        """If collective.documentviewer 'auto_convert' is disabled,
           annexes set 'to_print' is only converted if
           MeetingConfig.annexToPrintMode is 'enabled_for_printing'."""
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_convert = False
        gsettings.auto_layout_file_types = CONVERTABLE_TYPES.keys()
        cfg = self.meetingConfig
        cfg.setAnnexToPrintMode('enabled_for_info')

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        not_converted_annex = self.addAnnex(item)
        # annex 'to_print' was set to False because 'to_be_printed_activated'
        # is not enabled on the category group
        category = get_category_object(not_converted_annex, not_converted_annex.content_category)
        category_group = category.get_category_group()
        self.assertFalse(category_group.to_be_printed_activated)
        self.assertFalse(not_converted_annex.to_print)
        self.assertFalse(IIconifiedPreview(not_converted_annex).converted)

        # no matter 'to_be_printed_activated' is enabled
        # if MeetingConfig.annexToPrintMode is not 'enabled_for_printing'
        # the annex is not converted
        category_group.to_be_printed_activated = True
        not_converted_annex2 = self.addAnnex(item)
        self.assertFalse(not_converted_annex2.to_print)
        self.assertFalse(IIconifiedPreview(not_converted_annex2).converted)

        # annex is converted if 'to_be_printed_activated' enabled and
        # MeetingConfig.annexToPrintMode is 'enabled_for_printing'
        cfg.setAnnexToPrintMode('enabled_for_printing')
        converted_annex = self.addAnnex(item)
        self.assertFalse(converted_annex.to_print)
        self.assertFalse(IIconifiedPreview(converted_annex).converted)
        converted_annex.to_print = True
        notify(ObjectModifiedEvent(converted_annex))
        self.assertTrue(converted_annex.to_print)
        self.assertTrue(IIconifiedPreview(converted_annex).converted)

        # if an annex is not 'to_print', it is not converted
        converted_annex2 = self.addAnnex(item)
        converted_annex2.to_print = False
        notify(ObjectModifiedEvent(converted_annex2))
        self.assertFalse(converted_annex2.to_print)
        self.assertFalse(IIconifiedPreview(converted_annex2).converted)

    def test_pm_AnnexOnlyConvertedAgainWhenNecessary(self):
        """When conversion is enabled, either by 'auto_convert' or
           when MeetingConfig.annexToPrintMode is 'enabled_for_printing',
           if an annex is updated, it will be converted again onModified."""
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_convert = True
        gsettings.auto_layout_file_types = CONVERTABLE_TYPES.keys()
        default_category = get_category_object(
            self.meetingConfig,
            'annexes_types_-_item_annexes_-_financial-analysis')
        default_category_group = default_category.get_category_group()
        default_category_group.to_be_printed_activated = True

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        annex = self.addAnnex(item)
        # has been converted
        self.assertTrue(IIconifiedPreview(annex).converted)
        ann = IAnnotations(annex)['collective.documentviewer']
        initial_conversion_date = ann['last_updated']

        # now play with 'to_print', it will not be converted again
        sleep(2)
        annex.to_print = False
        notify(ObjectModifiedEvent(annex))
        self.assertEqual(initial_conversion_date,
                         IAnnotations(annex)['collective.documentviewer']['last_updated'])
        annex.to_print = True
        notify(ObjectModifiedEvent(annex))
        self.assertEqual(initial_conversion_date,
                         IAnnotations(annex)['collective.documentviewer']['last_updated'])

        # if contents really changed, not only the ModificationDate then it is converted again
        modified = annex.modified()
        annex.notifyModified()
        self.assertNotEqual(modified, annex.modified())
        notify(ObjectModifiedEvent(annex))
        # still not converted again as file content did not changed
        self.assertEqual(initial_conversion_date,
                         IAnnotations(annex)['collective.documentviewer']['last_updated'])
        # if file content changed, then annex is converted again
        self.annexFile = u'file_correct2.pdf'
        annex.file = self._annex_file_content()
        notify(ObjectModifiedEvent(annex))
        self.assertNotEqual(initial_conversion_date,
                            IAnnotations(annex)['collective.documentviewer']['last_updated'])

        # works also if auto_convert not enabled but
        # MeetingConfig.annexToPrintMode is 'enabled_for_printing'
        gsettings.auto_convert = False
        self.meetingConfig.setAnnexToPrintMode('enabled_for_printing')
        sleep(2)
        self.annexFile = u'file_correct.pdf'
        annex.file = self._annex_file_content()
        notify(ObjectModifiedEvent(annex))
        self.assertNotEqual(initial_conversion_date,
                            IAnnotations(annex)['collective.documentviewer']['last_updated'])

    def test_pm_ChangeAnnexPosition(self):
        """Annexes are orderable by the user able to add annexes."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)
        annex3 = self.addAnnex(item)
        self.assertEqual(item.objectValues(), [annex1, annex2, annex3])
        item.folder_position_typeaware(position='down', id=annex1.getId())
        self.assertEqual(item.objectValues(), [annex2, annex1, annex3])
        # member of the same group are able to change annexes position
        self.assertTrue('developers_creators' in self.member.getGroups())
        self.changeUser('pmCreator1b')
        self.assertTrue('developers_creators' in self.member.getGroups())
        item.folder_position_typeaware(position='down', id=annex1.getId())
        self.assertEqual(item.objectValues(), [annex2, annex3, annex1])
        # only members able to add annexes are able to change position
        self.validateItem(item)
        self.assertEqual(item.queryState(), 'validated')
        self.changeUser('pmObserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertRaises(Unauthorized, item.folder_position_typeaware, position='up', id=annex1.getId())

    def test_pm_AnnexesCreationDateKeptWhenItemDuplicated(self):
        """When an item is duplicated, if annexes are kept,
           the annexes creation date is also kept."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)
        clonedItem = item.clone()
        self.assertEqual(annex1.created(), clonedItem.objectValues()[0].created())
        self.assertEqual(annex2.created(), clonedItem.objectValues()[1].created())

    def test_pm_DecisionAnnexesDeletableByOwner(self):
        """annexDecision may be deleted by the Owner, aka the user that added the annex."""
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.validateItem(item)
        # when an item is 'accepted', the MeetingMember may add annexDecision
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/11/11'))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        self.assertEqual(item.queryState(), 'accepted')
        self.changeUser('pmCreator1')
        decisionAnnex1 = self.addAnnex(item, relatedTo='item_decision')
        self.assertTrue(decisionAnnex1 in item.objectValues())
        # doable if cfg.ownerMayDeleteAnnexDecision is True
        self.assertFalse(cfg.getOwnerMayDeleteAnnexDecision())
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@delete_givenuid'), decisionAnnex1.UID())
        cfg.setOwnerMayDeleteAnnexDecision(True)
        item.restrictedTraverse('@@delete_givenuid')(decisionAnnex1.UID())
        self.assertFalse(decisionAnnex1 in item.objectValues())
        # add an annex and another user having same groups for item can not remove it
        decisionAnnex2 = self.addAnnex(item, relatedTo='item_decision')
        self.changeUser('pmCreator1b')
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@delete_givenuid'), decisionAnnex2.UID())

    def test_pm_ItemAnnexFormVocabularies(self):
        """The vocabularies used for MeetingItem is different if used for annex or annexDecision."""
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # set item in a state where both annex and annexDecision are addable
        self.validateItem(item)

        # check with form, context is the MeetingItem
        form_annex = item.restrictedTraverse('++add++annex')
        self.request['PUBLISHED'] = form_annex
        form_annex_instance = form_annex.form_instance
        form_annex_instance.update()
        form_annex_widget = form_annex_instance.widgets['IIconifiedCategorization.content_category']
        form_annex_widget_terms = form_annex_widget.terms.terms.by_token.keys()
        self.assertEqual(
            form_annex_widget_terms,
            ['annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex',
             'annexes_types_-_item_annexes_-_overhead-analysis',
             'annexes_types_-_item_annexes_-_financial-analysis_-_financial-analysis-sub-annex',
             'annexes_types_-_item_annexes_-_financial-analysis',
             'annexes_types_-_item_annexes_-_item-annex',
             'annexes_types_-_item_annexes_-_budget-analysis',
             'annexes_types_-_item_annexes_-_overhead-analysis_-_overhead-analysis-sub-annex'])

        # now for decisionAnnex
        # check with form, context is the MeetingItem
        form_annexDecision = item.restrictedTraverse('++add++annexDecision')
        self.request['PUBLISHED'] = form_annexDecision
        form_annexDecision_instance = form_annexDecision.form_instance
        form_annexDecision_instance.update()
        form_annexDecision_widget = form_annexDecision_instance.widgets['IIconifiedCategorization.content_category']
        form_annexDecision_widget_terms = form_annexDecision_widget.terms.terms.by_token.keys()
        self.assertEqual(
            form_annexDecision_widget_terms,
            ['annexes_types_-_item_decision_annexes_-_decision-annex'])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAnnexes, prefix='test_pm_'))
    return suite
