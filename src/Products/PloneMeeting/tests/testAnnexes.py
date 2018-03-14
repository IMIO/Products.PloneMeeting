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
from zope.component import queryUtility
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from collective.documentviewer.config import CONVERTABLE_TYPES
from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.event import IconifiedPrintChangedEvent
from collective.iconifiedcategory.interfaces import IIconifiedPreview
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_group
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.actionspanel.interfaces import IContentDeletable
from imio.annex.columns import ActionsColumn
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.indexes import SearchableText
from Products.PloneMeeting.MeetingConfig import PROPOSINGGROUPPREFIX
from Products.PloneMeeting.MeetingConfig import SUFFIXPROFILEPREFIX
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


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
        self.assertFalse(proposingGroup.getGroupsInCharge())
        cfg.setItemAnnexConfidentialVisibleFor(('reader_groupincharge', ))
        update_all_categorized_elements(item)
        proposingGroup.setGroupsInCharge(('vendors', ))
        item.setProposingGroupWithGroupInCharge(
            '{0}__groupincharge__{1}'.format(
                item.getProposingGroup(), 'vendors'))
        item.updateLocalRoles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def _get_meeting_managers_for(self, cfg):
        meeting_managers_group_id = '{0}_{1}'.format(cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
        meeting_managers_group = api.group.get(meeting_managers_group_id)
        meeting_manager_ids = meeting_managers_group.getMemberIds()
        return meeting_manager_ids

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
            # get a user from the right 'developers' subgroup but make sure it is not a MeetingManager
            group_suffix = proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, '')
            developers_suffixed_group = self.tool.developers.getPloneGroups(suffixes=[group_suffix])[0]
            userIds = [userId for userId in developers_suffixed_group.getMemberIds()
                       if userId not in self._get_meeting_managers_for(cfg)]
            if not userIds:
                pm_logger.info("Could not test if developers.'%s' can access confidential "
                               "annexes because there are no user in the group !" % group_suffix)
                continue
            self.changeUser(userIds[0])
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
        # is viewable for Manager and MeetingManager
        current_user_id = self.member.getId()
        self.changeUser('siteadmin')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        self.changeUser('pmManager')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        self.changeUser(current_user_id)

        # disable access to condifential elements to every profiles
        cfg.setItemAnnexConfidentialVisibleFor(())
        cfg.setAdviceAnnexConfidentialVisibleFor(())
        cfg.setMeetingAnnexConfidentialVisibleFor(())
        update_all_categorized_elements(obj)
        self._checkMayNotAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                   annexes_table, categorized_child)
        # is viewable for Manager and MeetingManager
        self.changeUser('siteadmin')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        self.changeUser('pmManager')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
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
        self.assertFalse(proposingGroup.getGroupsInCharge())
        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_groupincharge', ))
        update_all_categorized_elements(item)
        proposingGroup.setGroupsInCharge(('vendors', ))
        item.setProposingGroupWithGroupInCharge(
            '{0}__groupincharge__{1}'.format(
                item.getProposingGroup(), 'vendors'))
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
            # get a user from the right 'developers' subgroup but make sure it is not a MeetingManager
            group_suffix = proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, '')
            developers_suffixed_group = self.tool.developers.getPloneGroups(suffixes=[group_suffix])[0]
            userIds = [userId for userId in developers_suffixed_group.getMemberIds()
                       if userId not in self._get_meeting_managers_for(cfg)]
            if not userIds:
                pm_logger.info("Could not test if developers.'%s' can access confidential "
                               "annexes because there are no user in the group !" % group_suffix)
                continue
            self.changeUser(userIds[0])
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
            for mGroup in (self.tool.developers, self.tool.vendors):
                cfg.setMeetingAnnexConfidentialVisibleFor((profileSuffix, ))
                update_all_categorized_elements(meeting)
                group_suffix = profileSuffix.replace(SUFFIXPROFILEPREFIX, '')
                # get a user from the right 'developers/vendors' subgroup
                suffixed_group = mGroup.getPloneGroups(suffixes=[group_suffix])[0]
                userIds = [userId for userId in suffixed_group.getMemberIds()
                           if userId not in self._get_meeting_managers_for(cfg)]
                if not userIds:
                    pm_logger.info("Could not test if profile '%s' can access confidential "
                                   "annexes for group '%s' because no users is defined in this profile !"
                                   % (group_suffix, mGroup.getId()))
                    continue
                self.changeUser(userIds[0])
                if not self.hasPermission(View, meeting):
                    pm_logger.info("Could not test if '%s' can access confidential "
                                   "annexes because he may not see the item !" % self.member.getId())
                    continue
                self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                          annexes_table, categorized_child)

    def test_pm_SwitchingConfidentialityUsingActionView(self):
        """Test that enabling/disabling/enabling
           confidentiality on an annex works correctly."""
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        cfg.setItemPowerObserversStates((item_initial_state, ))
        # confidential annexes are visible by proposing group creators
        cfg.setItemAnnexConfidentialVisibleFor(('suffix_proposing_group_creators', ))

        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        view = annexConfidential.restrictedTraverse('@@iconified-confidential')
        view.attribute_mapping = {'confidential': 'confidential'}

        # confidential for now
        self.changeUser('powerobserver1')
        self.assertFalse(annexConfidential.UID() in get_categorized_elements(item))
        self.assertEqual(annexConfidential.__ac_local_roles__,
                         {'pmCreator1': ['Owner'], 'developers_creators': ['AnnexReader']})
        # remove confidentiality, only MeetingManagers may change confidentiality
        self.changeUser('pmManager')
        self.request.set('confidential', False)
        view()
        self.changeUser('powerobserver1')
        self.assertTrue(annexConfidential.UID() in
                        [elt['UID'] for elt in get_categorized_elements(item)])
        self.assertEqual(annexConfidential.__ac_local_roles__,
                         {'pmCreator1': ['Owner']})
        # confidential again
        self.changeUser('pmManager')
        self.request.set('confidential', True)
        view()
        self.changeUser('powerobserver1')
        self.assertFalse(annexConfidential.UID() in
                         [elt['UID'] for elt in get_categorized_elements(item)])
        self.assertEqual(annexConfidential.__ac_local_roles__,
                         {'pmCreator1': ['Owner'], 'developers_creators': ['AnnexReader']})

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
        notify(IconifiedPrintChangedEvent(converted_annex,
                                          old_values={'to_print': False},
                                          new_values={'to_print': True}))
        self.assertTrue(converted_annex.to_print)
        self.assertTrue(IIconifiedPreview(converted_annex).converted)

        # if an annex is not 'to_print', it is not converted
        converted_annex2 = self.addAnnex(item)
        converted_annex2.to_print = False
        notify(IconifiedPrintChangedEvent(converted_annex2,
                                          old_values={'to_print': True},
                                          new_values={'to_print': False}))
        self.assertFalse(converted_annex2.to_print)
        self.assertFalse(IIconifiedPreview(converted_annex2).converted)

    def test_pm_AnnexOnlyConvertedAgainWhenNecessary(self):
        """When conversion is enabled, either by 'auto_convert' or
           when MeetingConfig.annexToPrintMode is 'enabled_for_printing',
           if an annex is updated, it will be converted again onModified."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_convert = True
        gsettings.auto_layout_file_types = CONVERTABLE_TYPES.keys()
        default_category = get_category_object(
            self.meetingConfig,
            '{0}-annexes_types_-_item_annexes_-_financial-analysis'.format(cfgId))
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
        self.assertFalse(self.hasPermission(AddAnnex, item))
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

    def test_pm_AnnexesDeletableByItemEditor(self):
        """annex/annexDecision may be deleted if user may edit the item."""
        cfg = self.meetingConfig
        # use the 'only_creator_may_delete' WF adaptation if available
        # in this case, it will ensure that when validated, the item may not be
        # deleted but annexes may be deleted by item editor
        if 'only_creator_may_delete' in cfg.listWorkflowAdaptations():
            cfg.setWorkflowAdaptations('only_creator_may_delete')
            cfg.at_post_edit_script()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        annex1 = self.addAnnex(item)
        annexDecision1 = self.addAnnex(item, relatedTo='item_decision')
        annex2 = self.addAnnex(item)
        annexDecision2 = self.addAnnex(item, relatedTo='item_decision')
        annex3 = self.addAnnex(item)
        annexDecision3 = self.addAnnex(item, relatedTo='item_decision')
        # delete annex as item creator
        self.assertTrue(IContentDeletable(annex1).mayDelete())
        self.assertTrue(IContentDeletable(annexDecision1).mayDelete())
        self.assertTrue(IContentDeletable(annex2).mayDelete())
        self.assertTrue(IContentDeletable(annexDecision2).mayDelete())
        self.assertTrue(IContentDeletable(annex3).mayDelete())
        self.assertTrue(IContentDeletable(annexDecision3).mayDelete())
        item.restrictedTraverse('@@delete_givenuid')(annex1.UID())
        item.restrictedTraverse('@@delete_givenuid')(annexDecision1.UID())

        self.proposeItem(item)
        # creator no more able to delete annex
        self.assertFalse(IContentDeletable(annex2).mayDelete())
        self.assertFalse(IContentDeletable(annexDecision2).mayDelete())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annex2.UID())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annexDecision2.UID())
        self.changeUser('pmReviewer1')
        if 'only_creator_may_delete' in cfg.listWorkflowAdaptations():
            self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertTrue(IContentDeletable(annex2).mayDelete())
        item.restrictedTraverse('@@delete_givenuid')(annex2.UID())
        item.restrictedTraverse('@@delete_givenuid')(annexDecision2.UID())

        self.validateItem(item)
        # reviewer no more able to delete annex
        self.assertFalse(IContentDeletable(annex3).mayDelete())
        self.assertFalse(IContentDeletable(annexDecision3).mayDelete())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annex3.UID())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annexDecision3.UID())
        self.changeUser('pmManager')
        if 'only_creator_may_delete' in cfg.listWorkflowAdaptations():
            self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertTrue(IContentDeletable(annex3).mayDelete())
        item.restrictedTraverse('@@delete_givenuid')(annex3.UID())
        item.restrictedTraverse('@@delete_givenuid')(annexDecision3.UID())

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
        cfg = self.meetingConfig
        cfgId = cfg.getId()
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
        form_annex_widget_terms = [term.token for term in form_annex_widget.terms]
        self.assertEqual(
            form_annex_widget_terms,
            ['{0}-annexes_types_-_item_annexes_-_financial-analysis'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_financial-analysis_-_financial-analysis-sub-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_budget-analysis'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_overhead-analysis'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_overhead-analysis_-_overhead-analysis-sub-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_item-annex'.format(cfgId)])

        # now for decisionAnnex
        # check with form, context is the MeetingItem
        form_annexDecision = item.restrictedTraverse('++add++annexDecision')
        self.request['PUBLISHED'] = form_annexDecision
        form_annexDecision_instance = form_annexDecision.form_instance
        form_annexDecision_instance.update()
        form_annexDecision_widget = form_annexDecision_instance.widgets['IIconifiedCategorization.content_category']
        form_annexDecision_widget_terms = [term.token for term in form_annexDecision_widget.terms]
        self.assertEqual(
            form_annexDecision_widget_terms,
            ['{0}-annexes_types_-_item_decision_annexes_-_decision-annex'.format(cfgId)])

    def test_pm_MeetingAnnexFormVocabularies(self):
        """This is essentially done to make sure ++add++annex works
           correctly when adding an annex on a meeting."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())

        # check with form, context is the MeetingItem
        form_annex = meeting.restrictedTraverse('++add++annex')
        form_annex_instance = form_annex.form_instance
        form_annex_instance.update()
        form_annex_widget = form_annex_instance.widgets['IIconifiedCategorization.content_category']
        form_annex_widget_terms = [term.token for term in form_annex_widget.terms]
        self.assertEqual(
            form_annex_widget_terms,
            ['{0}-annexes_types_-_meeting_annexes_-_meeting-annex'.format(cfgId)])

    def test_pm_AdviceAnnexFormVocabularies(self):
        """This is essentially done to make sure ++add++annex works
           correctly when adding an annex on an advice."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        item, advice = self._setupItemWithAdvice()

        # check with form, context is the advice
        form_annex = advice.restrictedTraverse('++add++annex')
        form_annex_instance = form_annex.form_instance
        form_annex_instance.update()
        form_annex_widget = form_annex_instance.widgets['IIconifiedCategorization.content_category']
        form_annex_widget_terms = [term.token for term in form_annex_widget.terms]
        self.assertEqual(
            form_annex_widget_terms,
            ['{0}-annexes_types_-_advice_annexes_-_advice-annex'.format(cfgId),
             '{0}-annexes_types_-_advice_annexes_-_advice-legal-analysis'.format(cfgId)])

    def test_pm_UpdateCategorizedElements(self):
        """The actions "update_categorized_elements" from collective.iconifiedcategory
           will update annex confidentiality accesses."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        cfg.setItemPowerObserversStates(('itemcreated', ))

        # only available to 'Managers'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized,
                          cfg.annexes_types.item_annexes.restrictedTraverse,
                          '@@update-categorized-elements')

        # create item with annex
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_config = get_config_root(annex)
        annex_group = get_group(annex_config, annex)
        # enable confidentiality
        annex_group.confidentiality_activated = True
        annex.confidential = True
        notify(ObjectModifiedEvent(annex))
        category = get_category_object(annex, annex.content_category)
        currentIndexedCategoryTitle = category.Title()
        self.assertEqual(item.categorized_elements[annex.UID()]['category_title'],
                         currentIndexedCategoryTitle)
        # restrictedpowerobservers have access to annex, not powerobservers
        rpoId = '{0}_restrictedpowerobservers'.format(cfgId)
        poId = '{0}_powerobservers'.format(cfgId)
        self.assertEqual(
            annex.__ac_local_roles__[rpoId], ['AnnexReader'])
        self.assertFalse(poId in annex.__ac_local_roles__)

        # change configuration : category title and MeetingConfig.itemAnnexConfidentialVisibleFor
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        NEW_CATEGORY_TITLE = 'New category title'
        category.title = NEW_CATEGORY_TITLE
        self.assertNotEqual(currentIndexedCategoryTitle, NEW_CATEGORY_TITLE)
        # categorized_elements was not updated
        self.assertNotEqual(item.categorized_elements[annex.UID()]['category_title'],
                            NEW_CATEGORY_TITLE)

        # call @@update-categorized-elements then check again
        self.changeUser('siteadmin')
        view = cfg.annexes_types.item_annexes.restrictedTraverse('@@update-categorized-elements')
        view()
        self.assertEqual(item.categorized_elements[annex.UID()]['category_title'],
                         NEW_CATEGORY_TITLE)
        # accesses were also updated : powerobservers have access to annex, not restrictedpowerobservers
        self.assertEqual(
            annex.__ac_local_roles__[poId], ['AnnexReader'])
        self.assertFalse(rpoId in annex.__ac_local_roles__)

    def test_pm_CategorizedAnnexesShowMethods(self):
        """Test the @@categorized-annexes view."""
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('@@categorized-annexes')
        # both annex and annexDecision are displayed and addable
        self.assertTrue(view.showAddAnnex())
        self.assertTrue(view.showAddAnnexDecision())
        self.assertTrue(view.showDecisionAnnexesSection())
        # add an annex and an annexDecision
        self.addAnnex(item)
        annexDecision = self.addAnnex(item, relatedTo='item_decision')
        self.assertTrue(view.showAddAnnex())
        self.assertTrue(view.showAddAnnexDecision())
        self.assertTrue(view.showAnnexesSection())
        self.assertTrue(view.showDecisionAnnexesSection())
        # propose item, annex sections are still shown but not addable
        self.proposeItem(item)
        self.assertFalse(view.showAddAnnex())
        self.assertFalse(view.showAddAnnexDecision())
        self.assertTrue(view.showAnnexesSection())
        self.assertTrue(view.showDecisionAnnexesSection())

        # annexDecision section is shown if annexDecision are stored or if
        # annexDecision annex types are available (active), disable the annexDecision annex types
        for annex_type in cfg.annexes_types.item_decision_annexes.objectValues():
            annex_type.enabled = False
            annex_type.reindexObject(idxs=['enabled'])
        # view._annexDecisionCategories is memoized
        view = item.restrictedTraverse('@@categorized-annexes')
        # showDecisionAnnexesSection still True because annexDecision exists
        self.assertTrue(view.showDecisionAnnexesSection())
        self.deleteAsManager(annexDecision.UID())
        # view._annexDecisionCategories is memoized
        view = item.restrictedTraverse('@@categorized-annexes')
        self.assertFalse(view.showDecisionAnnexesSection())

    def test_pm_Other_mc_correspondences_vocabulary(self):
        """ """
        cfg = self.meetingConfig
        annex_type = cfg.annexes_types.item_annexes.get(self.annexFileType)
        # get vocabulary name
        type_info = self.portal.portal_types.get(annex_type.portal_type)
        vocab_name = type_info.lookupSchema()['other_mc_correspondences'].value_type.vocabularyName
        vocab = queryUtility(IVocabularyFactory, vocab_name)
        # build expected result depending on existing MC
        expected = []
        for mc in self.tool.objectValues('MeetingConfig'):
            if cfg == mc:
                continue
            mc_title = mc.Title()
            values = [
                u'{0} \u2192 Item annexes \u2192 Financial analysis'.format(mc_title),
                u'{0} \u2192 Item annexes \u2192 Financial analysis '
                u'\u2192 Financial analysis sub annex'.format(mc_title),
                u'{0} \u2192 Item annexes \u2192 Legal analysis'.format(mc_title),
                u'{0} \u2192 Item annexes \u2192 Budget analysis'.format(mc_title),
                u'{0} \u2192 Item annexes \u2192 Budget analysis '
                u'\u2192 Budget analysis sub annex'.format(mc_title),
                u'{0} \u2192 Item annexes \u2192 Other annex(es)'.format(mc_title),
                u'{0} \u2192 Item decision annexes \u2192 Decision annex(es)'.format(mc_title)]
            expected.extend(values)
        self.assertEqual([term.title for term in vocab(annex_type)._terms], expected)

    def test_pm_annex_type_only_for_meeting_managers(self):
        """An ItemAnnexContentCategory may be defined only selectable by MeetingManagers."""
        cfg = self.meetingConfig
        vocab = queryUtility(IVocabularyFactory, 'collective.iconifiedcategory.categories')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)

        # we will make 'only_for_meeting_managers' the 'overhead-analysis' category
        # and the 'budget-analysis_-_budget-analysis-sub-annex' subcategory
        overhead_analysis = cfg.annexes_types.item_annexes.get('overhead-analysis')
        overhead_analysis_category_id = calculate_category_id(overhead_analysis)
        budget_analysis_subannex = cfg.annexes_types.item_annexes.get(
            'budget-analysis').get('budget-analysis-sub-annex')
        budget_analysis_subannex_category_id = calculate_category_id(budget_analysis_subannex)

        term_tokens = [term.token for term in vocab(annex)._terms]
        self.assertTrue(overhead_analysis_category_id in term_tokens)
        self.assertTrue(budget_analysis_subannex_category_id in term_tokens)

        # hide the 2 categories
        overhead_analysis.only_for_meeting_managers = True
        budget_analysis_subannex.only_for_meeting_managers = True

        # no more in vocabulary for 'pmCreator1'
        term_tokens = [term.token for term in vocab(annex)._terms]
        self.assertFalse(overhead_analysis_category_id in term_tokens)
        self.assertFalse(budget_analysis_subannex_category_id in term_tokens)

        # in vocabulary for a MeetingManager
        self.changeUser('pmManager')
        term_tokens = [term.token for term in vocab(annex)._terms]
        self.assertTrue(overhead_analysis_category_id in term_tokens)
        self.assertTrue(budget_analysis_subannex_category_id in term_tokens)

    def test_pm_actions_panel_history_only_for_managers(self):
        """The 'history' icon in the actions panel is only shown to real Managers."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_brain = self.portal.portal_catalog(UID=annex.UID())[0]
        column = ActionsColumn(self.portal, self.request, self)
        self.assertFalse('@@historyview' in column.renderCell(annex_brain))
        self.changeUser('pmManager')
        self.assertFalse('@@historyview' in column.renderCell(annex_brain))
        self.changeUser('admin')
        self.assertTrue('@@historyview' in column.renderCell(annex_brain))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAnnexes, prefix='test_pm_'))
    return suite
