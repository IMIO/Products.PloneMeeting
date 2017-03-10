# -*- coding: utf-8 -*-
#
# File: testWFAdaptations.py
#
# Copyright (c) 2017 by Imio.be
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

from DateTime.DateTime import DateTime

from zope.i18n import translate

from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer

from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.model.adaptations import performWorkflowAdaptations
from Products.PloneMeeting.config import HIDE_DECISION_UNDER_WRITING_MSG
from Products.PloneMeeting.config import WriteDecision
from Products.PloneMeeting.config import WriteItemMeetingManagerFields

from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE
from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_VALIDATING_STATES
from Products.PloneMeeting.model.adaptations import WF_NOT_CREATOR_EDITS_UNLESS_CLOSED
from Products.PloneMeeting.model.adaptations import getAllPossibleReturnedState


class testWFAdaptations(PloneMeetingTestCase):
    '''Tests the different existing wfAdaptations.  Also made to be back tested by extension profiles...
       Each test call submethods that check the behaviour while each wfAdaptation is active or inactive.
       This way, an external profile will just override the called submethods if necessary.
       This way too, we will be able to check multiple activated wfAdaptations.'''

    def test_pm_WFA_availableWFAdaptations(self):
        '''Test what are the available wfAdaptations.
           This way, if we add a wfAdaptations, the test will 'break' until it is adapted...'''
        self.assertEquals(sorted(self.meetingConfig.listWorkflowAdaptations().keys()),
                          ['archiving',
                           'creator_edits_unless_closed',
                           'creator_initiated_decisions',
                           'everyone_reads_all',
                           'hide_decisions_when_under_writing',
                           'items_come_validated',
                           'mark_not_applicable',
                           'no_global_observation',
                           'no_proposal',
                           'no_publication',
                           'only_creator_may_delete',
                           'postpone_next_meeting',
                           'pre_validation',
                           'pre_validation_keep_reviewer_permissions',
                           'removed',
                           'return_to_proposing_group',
                           'return_to_proposing_group_with_all_validations',
                           'return_to_proposing_group_with_last_validation',
                           'reviewers_take_back_validated_item',
                           'waiting_advices'])

    def test_pm_WFA_appliedOnMeetingConfigEdit(self):
        """WFAdpatations are applied when the MeetingConfig is edited."""
        cfg = self.meetingConfig
        # ease override by subproducts
        if not 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('siteadmin')
        self.assertFalse('return_to_proposing_group' in cfg.getWorkflowAdaptations())
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertFalse('returned_to_proposing_group' in itemWF.states)
        # activate
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in itemWF.states)

    def test_pm_WFA_mayBeRemovedOnMeetingConfigEdit(self):
        """If a WFAdaptation is unselected in a MeetingConfig, the workflow
           will not integrate it anymore.  Try with 'return_to_proposing_group'."""
        cfg = self.meetingConfig
        # ease override by subproducts
        if not 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('siteadmin')
        self.assertFalse('return_to_proposing_group' in cfg.getWorkflowAdaptations())
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertFalse('returned_to_proposing_group' in itemWF.states)
        # activate
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in itemWF.states)
        # deactivate
        cfg.setWorkflowAdaptations(())
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertFalse('returned_to_proposing_group' in itemWF.states)

    def test_pm_WFA_mayBeAppliedAsMeetingManager(self):
        """When a MeetingManager edit the MeetingConfig, WFAdaptations are applied when the
           MeetingConfig is saved."""
        cfg = self.meetingConfig
        # ease override by subproducts
        if not 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # activate
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in itemWF.states)

    def test_pm_WFA_sameWorkflowForSeveralMeetingConfigs(self):
        """As the real WF used for item/meeting of a MeetingConfig are duplicated ones,
           the original workflow may be used for several MeetingConfigs.  Use same WF for cfg and cfg2
           and activate a WFAdaptation for cfg, check that it does not change cfg2."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # use same WF
        cfg2.setItemWorkflow(cfg.getItemWorkflow())
        cfg2.setMeetingWorkflow(cfg.getMeetingWorkflow())
        cfg2.at_post_edit_script()
        self.assertEquals(cfg.getItemWorkflow(), cfg2.getItemWorkflow())
        self.assertEquals(cfg.getMeetingWorkflow(), cfg2.getMeetingWorkflow())
        # apply the 'return_to_proposing_group' WFAdaptation for cfg
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        cfg.at_post_edit_script()
        originalWF = self.wfTool.get(cfg.getItemWorkflow())
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        cfg2ItemWF = self.wfTool.getWorkflowsFor(cfg2.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in cfgItemWF.states)
        self.assertFalse('returned_to_proposing_group' in originalWF.states)
        self.assertFalse('returned_to_proposing_group' in cfg2ItemWF.states)
        # test again if saving cfg2
        cfg2.at_post_edit_script()
        originalWF = self.wfTool.get(cfg.getItemWorkflow())
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        cfg2ItemWF = self.wfTool.getWorkflowsFor(cfg2.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in cfgItemWF.states)
        self.assertFalse('returned_to_proposing_group' in cfg2ItemWF.states)
        self.assertFalse('returned_to_proposing_group' in originalWF.states)

    def test_pm_Validate_workflowAdaptations_conflicts(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage conflicts
           between wfAdaptations that may not be selected together."""
        wa_conflicts = translate('wa_conflicts', domain='PloneMeeting', context=self.request)
        cfg = self.meetingConfig

        # 'items_come_validated' alone is ok
        self.failIf(cfg.validate_workflowAdaptations(('items_come_validated', )))
        # conflicts with some
        for otherWFA in ('creator_initiated_decisions',
                         'pre_validation',
                         'pre_validation_keep_reviewer_permissions',
                         'reviewers_take_back_validated_item'):
            self.assertEquals(
                cfg.validate_workflowAdaptations(('items_come_validated', otherWFA)),
                wa_conflicts)

        # 'archiving' must be used alone
        self.failIf(cfg.validate_workflowAdaptations(('archiving', )))
        # conflicts with any other
        self.assertEquals(
            cfg.validate_workflowAdaptations(('archiving', 'any_other')),
            wa_conflicts)

        # 'no_proposal' alone is ok
        self.failIf(cfg.validate_workflowAdaptations(('no_proposal', )))
        # conflicts with some
        for otherWFA in ('pre_validation',
                         'pre_validation_keep_reviewer_permissions'):
            self.assertEquals(
                cfg.validate_workflowAdaptations(('no_proposal', otherWFA)),
                wa_conflicts)

        # 'pre_validation' alone is ok
        self.failIf(cfg.validate_workflowAdaptations(('pre_validation', )))
        # conflicts with 'pre_validation_keep_reviewer_permissions')
        self.assertEquals(
            cfg.validate_workflowAdaptations(('no_proposal', 'pre_validation_keep_reviewer_permissions')),
            wa_conflicts)

        # return_to_proposing_group... alone is ok
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group',)))
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        # Only one return_to_proposing_group can be selectable
        self.assertEquals(
            cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',
                                              'return_to_proposing_group')), wa_conflicts)
        self.assertEquals(
            cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',
                                              'return_to_proposing_group_with_all_validations')), wa_conflicts)
        self.assertEquals(
            cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',
                                              'return_to_proposing_group')), wa_conflicts)

    def test_pm_Validate_workflowAdaptations_added_no_publication(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage addition
           of wfAdaptations 'no_publication' that is not possible if some meeting
           or items are 'published'."""
        # ease override by subproducts
        if not 'no_publication' in self.meetingConfig.listWorkflowAdaptations():
            return

        no_publication_added_error = translate('wa_added_no_publication_error',
                                               domain='PloneMeeting',
                                               context=self.request)
        cfg = self.meetingConfig
        # make sure we do not have recurring items
        self.changeUser('pmManager')
        # create a meeting with an item and publish it
        meeting = self.create('Meeting', date='2016/01/15')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.publishMeeting(meeting)
        self.assertEquals(meeting.queryState(), 'published')
        self.assertEquals(item.queryState(), 'itempublished')
        self.assertEquals(
            cfg.validate_workflowAdaptations(('no_publication', )),
            no_publication_added_error)

        # it can not be selected because item or meeting is 'published'
        # delete meeting and create an item at set it in state 'itempublished'
        self.deleteAsManager(meeting.UID())  # this will delete every linked item

        newItem = self.create('MeetingItem')
        itemWF = self.wfTool.getWorkflowsFor(newItem)[0]
        self.wfTool.setStatusOf(itemWF.getId(),
                                newItem,
                                {'action': None,
                                 'review_state': 'itempublished',
                                 'actor': self.member.getId(),
                                 'comments': '',
                                 'time': DateTime()})
        newItem.reindexObject()
        self.assertEquals(newItem.queryState(),
                          'itempublished')
        self.assertEquals(
            cfg.validate_workflowAdaptations(('no_publication', )),
            no_publication_added_error)
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        self.failIf(cfg.validate_workflowAdaptations(('no_publication', )))

    def test_pm_Validate_workflowAdaptations_added_no_proposal(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage addition
           of wfAdaptations 'no_proposal' that is not possible if some items are 'proposed'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'no_proposal' in cfg.listWorkflowAdaptations():
            return

        no_proposal_added_error = translate('wa_added_no_proposal_error',
                                            domain='PloneMeeting',
                                            context=self.request)
        self.changeUser('pmManager')
        # create an item and propose it
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertEquals(
            cfg.validate_workflowAdaptations(('no_proposal', )),
            no_proposal_added_error)

        # it can not be selected because item is 'proposed'
        self.validateItem(item)
        self.failIf(cfg.validate_workflowAdaptations(('no_proposal', )))

    def test_pm_Validate_workflowAdaptations_added_items_come_validated(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage addition
           of wfAdaptations 'items_come_validated' that is not possible if some items are
           'itemcreated', 'prevalidated' or 'proposed'.
           Selection of 'items_come_validated' and 'pre_validation' is not possible and
           will raise a conflict, we do not test it here."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'items_come_validated' in cfg.listWorkflowAdaptations():
            return

        items_come_validated_added_error = translate('wa_added_items_come_validated_error',
                                                     domain='PloneMeeting',
                                                     context=self.request)
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem')
        self.assertEquals(item.queryState(), 'itemcreated')
        self.assertEquals(
            cfg.validate_workflowAdaptations(('items_come_validated', )),
            items_come_validated_added_error)
        self.proposeItem(item)
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertEquals(
            cfg.validate_workflowAdaptations(('items_come_validated', )),
            items_come_validated_added_error)

        # make wfAdaptation selectable
        self.validateItem(item)
        self.failIf(cfg.validate_workflowAdaptations(('items_come_validated', )))

    def test_pm_Validate_workflowAdaptations_removed_archiving(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'archiving' that is not possible."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'archiving' in cfg.listWorkflowAdaptations():
            return

        archiving_removed_error = translate('wa_removed_archiving_error',
                                            domain='PloneMeeting',
                                            context=self.request)
        cfg.setWorkflowAdaptations(('archiving', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self.failIf(cfg.validate_workflowAdaptations(('archiving', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            archiving_removed_error)

    def test_pm_Validate_workflowAdaptations_removed_pre_validation(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'pre_validation' that is not possible if some items are 'pre_validated'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'pre_validation' in cfg.listWorkflowAdaptations():
            return

        pre_validation_removed_error = translate('wa_removed_pre_validation_error',
                                                 domain='PloneMeeting',
                                                 context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('pre_validation', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.assertEqual(item.queryState(), 'prevalidated')
        self.failIf(cfg.validate_workflowAdaptations(('pre_validation', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            pre_validation_removed_error)

        # make wfAdaptation selectable
        self.validateItem(item)
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_postpone_next_meeting(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'postpone_next_meeting' that is not possible if
           some items are 'postponed_next_meeting'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'postpone_next_meeting' in cfg.listWorkflowAdaptations():
            return

        postpone_removed_error = translate('wa_removed_postpone_next_meeting_error',
                                           domain='PloneMeeting',
                                           context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('postpone_next_meeting', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        self.assertEqual(item.queryState(), 'postponed_next_meeting')
        self.failIf(cfg.validate_workflowAdaptations(('postpone_next_meeting', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            postpone_removed_error)

        # make wfAdaptation selectable
        self.do(item, 'backToItemFrozen')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_mark_not_applicable(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'mark_not_applicable' that is not possible if
           some items are 'marked_not_applicable'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'mark_not_applicable' in cfg.listWorkflowAdaptations():
            return

        mark_not_applicable_removed_error = translate('wa_removed_mark_not_applicable_error',
                                                      domain='PloneMeeting',
                                                      context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('mark_not_applicable', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'mark_not_applicable')
        self.assertEqual(item.queryState(), 'marked_not_applicable')
        self.failIf(cfg.validate_workflowAdaptations(('mark_not_applicable', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            mark_not_applicable_removed_error)

        # make wfAdaptation selectable
        self.do(item, 'backToItemFrozen')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_removed(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'removed' that is not possible if
           some items are 'removed'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'removed' in cfg.listWorkflowAdaptations():
            return

        removed_removed_error = translate('wa_removed_removed_error',
                                          domain='PloneMeeting',
                                          context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('removed', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'remove')
        self.assertEqual(item.queryState(), 'removed')
        self.failIf(cfg.validate_workflowAdaptations(('removed', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            removed_removed_error)

        # make wfAdaptation selectable
        self.do(item, 'backToItemFrozen')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_waiting_advices(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'waiting_advices' that is not possible if some items are
           'waiting_advices'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'waiting_advices' in cfg.listWorkflowAdaptations():
            return

        waiting_advices_proposed_state = '{0}_waiting_advices'.format(self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.tool.vendors.setItemAdviceStates(
            ("{0}__state__{1}".format(cfg.getId(), waiting_advices_proposed_state),))

        waiting_advices_removed_error = translate('wa_removed_waiting_advices_error',
                                                  domain='PloneMeeting',
                                                  context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('waiting_advices', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        self.proposeItem(item)
        proposedState = item.queryState()
        self._setItemToWaitingAdvices(item,
                                      'wait_advices_from_{0}'.format(proposedState))
        self.assertEqual(item.queryState(),
                         '{0}_waiting_advices'.format(proposedState))
        self.failIf(cfg.validate_workflowAdaptations(('waiting_advices', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            waiting_advices_removed_error)

        # make wfAdaptation selectable
        self.changeUser(self._userAbleToBackFromWaitingAdvices(item.queryState()))
        self.do(item, 'backTo_{0}_from_waiting_advices'.format(proposedState))
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_return_to_proposing_group(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'return_to_proposing_group' that is not possible if
           some items are 'returned_to_proposing_group'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            return

        return_to_proposing_group_removed_error = translate('wa_removed_return_to_proposing_group_error',
                                                            domain='PloneMeeting',
                                                            context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('return_to_proposing_group', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date='2016/01/15')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        self.assertEquals(item.queryState(), 'returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group', )))
        if 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        if 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            return_to_proposing_group_removed_error)

        # make wfAdaptation unselectable
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_return_to_proposing_group_with_last_validation(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'return_to_proposing_group with last validation' that is not possible if
           some items are 'returned_to_proposing_group xxx'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            return

        return_to_proposing_group_removed_error = translate('wa_removed_return_to_proposing_group_with_last_validation_error',
                                                            domain='PloneMeeting',
                                                            context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('return_to_proposing_group_with_last_validation', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date='2016/01/15')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        self.assertEquals(item.queryState(), 'returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group', )))
        if 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        self.assertEquals(item.queryState(), 'returned_to_proposing_group_proposed')
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            return_to_proposing_group_removed_error)
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.assertEquals(
                cfg.validate_workflowAdaptations(('return_to_proposing_group', )),
                return_to_proposing_group_removed_error)
        if 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        # make wfAdaptation unselectable
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_return_to_proposing_group_with_all_validations(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'return_to_proposing_group with all validations' that is not possible if
           some items are 'returned_to_proposing_group xxx'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            return

        return_to_proposing_group_removed_error = translate('wa_removed_return_to_proposing_group_with_all_validations_error',
                                                            domain='PloneMeeting',
                                                            context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('return_to_proposing_group_with_all_validations', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date='2016/01/15')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        self.assertEquals(item.queryState(), 'returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group', )))

        if 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        self.assertEquals(item.queryState(), 'returned_to_proposing_group_proposed')
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            return_to_proposing_group_removed_error)
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.assertEquals(
                cfg.validate_workflowAdaptations(('return_to_proposing_group', )),
                return_to_proposing_group_removed_error)
        if 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            self.assertEquals(
                cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)),
                return_to_proposing_group_removed_error)
        # make wfAdaptation unselectable
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_hide_decisions_when_under_writing(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'hide_decisions_when_under_writing' that is not possible if
           some meetings are 'decisions_published'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'hide_decisions_when_under_writing' in cfg.listWorkflowAdaptations():
            return

        hide_decisions_when_under_writing_removed_error = \
            translate('wa_removed_hide_decisions_when_under_writing_error',
                      domain='PloneMeeting',
                      context=self.request)
        self.changeUser('pmManager')
        cfg.setWorkflowAdaptations(('hide_decisions_when_under_writing', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        meeting = self.create('Meeting', date='2016/01/15')
        self.decideMeeting(meeting)
        self.do(meeting, 'publish_decisions')
        self.failIf(cfg.validate_workflowAdaptations(('hide_decisions_when_under_writing', )))
        self.assertEquals(
            cfg.validate_workflowAdaptations(()),
            hide_decisions_when_under_writing_removed_error)

        # make wfAdaptation selectable
        self.closeMeeting(meeting)
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_WFA_no_publication(self):
        '''Test the workflowAdaptation 'no_publication'.
           This test check the removal of the 'published' state in the meeting/item WF.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'no_publication' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._no_publication_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('no_publication')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._no_publication_active()

    def _no_publication_inactive(self):
        '''Tests while 'no_publication' wfAdaptation is inactive.'''
        meeting = self._createMeetingWithItems()
        item = meeting.getItems()[0]
        self.publishMeeting(meeting)
        self.assertEqual(item.queryState(), 'itempublished')

    def _no_publication_active(self):
        '''Tests while 'no_publication' wfAdaptation is active.'''
        m1 = self._createMeetingWithItems()
        self.failIf('publish' in self.transitions(m1))
        for item in m1.getItems():
            item.setDecision('<p>My decision<p>')
        for tr in self._getTransitionsToCloseAMeeting():
            if tr in self.transitions(m1):
                lastTriggeredTransition = tr
                self.do(m1, tr)
                self.failIf('publish' in self.transitions(m1))
        # check that we are able to reach the end of the wf process
        self.assertEquals(lastTriggeredTransition, self._getTransitionsToCloseAMeeting()[-1])

    def test_pm_WFA_no_proposal(self):
        '''Test the workflowAdaptation 'no_proposal'.
           Check the removal of state 'proposed' in the item WF.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'no_proposal' in self.meetingConfig.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._no_proposal_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('no_proposal')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._no_proposal_active()

    def _no_proposal_inactive(self):
        '''Tests while 'no_proposal' wfAdaptation is inactive.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.failUnless('propose' in self.transitions(i1))
        self.do(i1, 'propose')
        self.do(i1, 'validate')

    def _no_proposal_active(self):
        '''Tests while 'no_proposal' wfAdaptation is active.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.failIf('propose' in self.transitions(i1))
        self.do(i1, 'validate')

    def test_pm_WFA_pre_validation(self):
        '''Test the workflowAdaptation 'pre_validation'.
           Check the addition of a 'prevalidated' state in the item WF.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'pre_validation' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._pre_validation_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('pre_validation')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        # define pmManager as a prereviewer
        self._turnUserIntoPrereviewer(self.member)
        self._pre_validation_active(self.member.getId())

    def _pre_validation_inactive(self):
        '''Tests while 'pre_validation' wfAdaptation is inactive.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failIf('prevalidate' in self.transitions(i1))
        self.do(i1, 'validate')

    def _pre_validation_active(self, username):
        '''Tests while 'pre_validation' wfAdaptation is active.'''
        # XXX force 'MeetingManager' to login again either
        # he is not considered in the _prereviewers group by the method
        # member.getGroups()
        self.changeUser('pmManager')
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failUnless('prevalidate' in self.transitions(i1))
        self.do(i1, 'prevalidate')
        self.do(i1, 'validate')

    def test_pm_WFA_pre_validation_keep_reviewer_permissions(self):
        '''Test the workflowAdaptation 'pre_validation_keep_reviewer_permissions'.
           Check the addition of a 'prevalidated' state in the item WF, moreover
           the 'MeetingReviewer' will also be able to validate items proposed
           to the prereviewer.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'pre_validation_keep_reviewer_permissions' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._pre_validation_keep_reviewer_permissions_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('pre_validation_keep_reviewer_permissions')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        # define pmManager as a prereviewer
        self._turnUserIntoPrereviewer(self.member)
        self._pre_validation_keep_reviewer_permissions_active(self.member.getId())

    def _pre_validation_keep_reviewer_permissions_inactive(self):
        '''Tests while 'pre_validation' wfAdaptation is inactive.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failIf('prevalidate' in self.transitions(i1))
        self.do(i1, 'validate')

    def _pre_validation_keep_reviewer_permissions_active(self, username):
        '''Tests while 'pre_validation_keep_reviewer_permissions' wfAdaptation is active.'''
        self.changeUser('pmManager')
        i1 = self.create('MeetingItem')
        self.do(i1, 'propose')
        # a 'pmReviewerLevel1' may 'propose' the item but a 'pmReviewerLevel2' too
        # even if 'pmReviewerLevel2' is not in the _prereviewers group
        self.changeUser('pmReviewerLevel1')
        self.failUnless('prevalidate' in self.transitions(i1))
        self.assertTrue('developers_prereviewers' in self.member.getGroups())
        self.changeUser('pmReviewerLevel2')
        self.failUnless('prevalidate' in self.transitions(i1))
        self.assertTrue(not 'developers_prereviewers' in self.member.getGroups())
        self.do(i1, 'prevalidate')
        self.do(i1, 'validate')

    def test_pm_WFA_creator_initiated_decisions(self):
        '''Test the workflowAdaptation 'creator_initiated_decisions'.
           Check that the creator can edit the decision field while activated.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'creator_initiated_decisions' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._creator_initiated_decisions_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('creator_initiated_decisions')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._creator_initiated_decisions_active()

    def _creator_initiated_decisions_inactive(self):
        '''Tests while 'creator_initiated_decisions' wfAdaptation is inactive.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        self.failIf(self.hasPermission(WriteDecision, i1))

    def _creator_initiated_decisions_active(self):
        '''Tests while 'creator_initiated_decisions' wfAdaptation is active.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        self.failUnless(self.hasPermission(WriteDecision, i1))

    def test_pm_WFA_items_come_validated(self):
        '''Test the workflowAdaptation 'items_come_validated'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'items_come_validated' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._items_come_validated_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('items_come_validated')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._items_come_validated_active()

    def _items_come_validated_inactive(self):
        '''Tests while 'items_come_validated' wfAdaptation is inactive.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        self.assertEquals(self.transitions(i1), ['propose', ])

    def _items_come_validated_active(self):
        '''Tests while 'items_come_validated' wfAdaptation is active.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'validated')
        self.assertEquals(self.transitions(i1), [])

    def test_pm_WFA_archiving(self):
        '''Test the workflowAdaptation 'archiving'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'archiving' in cfg.listWorkflowAdaptations():
            return
        # check while the wfAdaptation is not activated
        self._archiving_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations('archiving')
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._archiving_active()

    def _archiving_inactive(self):
        '''Tests while 'archiving' wfAdaptation is inactive.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.transitions(i1))

    def _archiving_active(self):
        '''Tests while 'archiving' wfAdaptation is active.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        self.assertEquals(i1.queryState(), 'itemarchived')
        self.failIf(self.transitions(i1))
        # even for the admin (Manager)
        self.changeUser('admin')
        self.failIf(self.transitions(i1))

    def test_pm_WFA_only_creator_may_delete(self):
        '''Test the workflowAdaptation 'archiving'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'only_creator_may_delete' in cfg.listWorkflowAdaptations():
            return
        # check while the wfAdaptation is not activated
        self._only_creator_may_delete_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('only_creator_may_delete')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        self._only_creator_may_delete_active()

    def _only_creator_may_delete_inactive(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is inactive.
           Other roles than 'MeetingMember' have the 'Delete objects' permission in different states.'''
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        self.assertEquals(item.queryState(), 'itemcreated')
        # we have transitions
        self.failUnless(self.hasPermission(DeleteObjects, item))
        self.proposeItem(item)
        self.failIf(self.hasPermission(DeleteObjects, item))
        self.changeUser('pmReviewer2')
        # the Reviewer can delete
        self.failUnless(self.hasPermission(DeleteObjects, item))
        self.validateItem(item)
        self.failIf(self.hasPermission(DeleteObjects, item))
        self.changeUser('pmManager')
        # the MeetingManager can delete
        self.failUnless(self.hasPermission(DeleteObjects, item))
        # God can delete too...
        self.changeUser('admin')
        self.failUnless(self.hasPermission(DeleteObjects, item))

    def _only_creator_may_delete_active(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is active.
           Only the 'MeetingMember' and the 'Manager' have the 'Delete objects' permission.'''
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        # now check the item workflow states regarding the 'Delete objects' permission
        wf = self.wfTool.getWorkflowsFor(item)[0]
        # the only state in wich the creator (MeetingMember) can delete
        # the item is when it is 'itemcreated'
        for state in wf.states.values():
            if state.id == 'itemcreated':
                self.assertEquals(state.permission_roles[DeleteObjects], ('MeetingMember', 'Manager'))
            else:
                self.assertEquals(state.permission_roles[DeleteObjects], ('Manager', ))

    def test_pm_WFA_no_global_observation(self):
        '''Test the workflowAdaptation 'no_global_observation'.'''
        # ease override by subproducts
        if not 'no_global_observation' in self.meetingConfig.listWorkflowAdaptations():
            return
        # check while the wfAdaptation is not activated
        self._no_global_observation_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('no_global_observation')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        self._no_global_observation_active()

    def _no_global_observation_inactive(self):
        '''Tests while 'no_global_observation' wfAdaptation is inactive.'''
        # when the item is 'itempublished', everybody (having MeetingObserverGlobal role) can see the items
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in self.meetingConfig.getTransitionsForPresentingAnItem():
            self.changeUser('pmManager')
            try:
                self.do(i1, tr)
            except WorkflowException:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission(View, i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is visible by everybody
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            self.changeUser('pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            if isPublished:
                self.changeUser('pmCreator2')
                self.failUnless(self.hasPermission(View, i1))
            else:
                self.changeUser('pmCreator2')
                self.failIf(self.hasPermission(View, i1))
        # check that the meeting have been published
        self.failUnless(isPublished)

    def _no_global_observation_active(self):
        '''Tests while 'no_global_observation' wfAdaptation is active.'''
        # when the item is 'itempublished', it is no more viewable by everybody
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in self.meetingConfig.getTransitionsForPresentingAnItem():
            self.changeUser('pmManager')
            try:
                self.do(i1, tr)
            except WorkflowException:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission(View, i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is NOT visible because of the wfAdaptation
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            self.changeUser('pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            # no matter the element is published or not
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission(View, i1))
        #check that the meeting have been published
        self.failUnless(isPublished)
        # check every decided states of the item
        # set the meeting back to decided
        self.changeUser('admin')
        while not m1.queryState() == 'decided':
            self.do(m1, [tr for tr in self.transitions(m1) if tr.startswith('back')][0])
        # now the meeting is 'decided', put i1 backToFrozen and test every available decided state
        while not i1.queryState() in ['itemfrozen', 'itempublished', ]:
            self.do(i1, [tr for tr in self.transitions(i1) if tr.startswith('back')][0])
        # now check every item decision
        self.changeUser('pmManager')
        availableDecisionTransitions = [tr for tr in self.transitions(i1) if not tr.startswith('back')]
        for availableDecisionTransition in availableDecisionTransitions:
            self.do(i1, availableDecisionTransition)
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission(View, i1))
            self.changeUser('pmManager')
            # compute backTransition
            backTransition = [tr for tr in self.transitions(i1) if tr.startswith('back')][0]
            self.do(i1, backTransition)

    def test_pm_WFA_everyone_reads_all(self):
        '''Test the workflowAdaptation 'everyone_reads_all'.'''
        # ease override by subproducts
        if not 'everyone_reads_all' in self.meetingConfig.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._everyone_reads_all_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('everyone_reads_all')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        self._everyone_reads_all_active()

    def _everyone_reads_all_inactive(self):
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in self.meetingConfig.getTransitionsForPresentingAnItem():
            self.changeUser('pmManager')
            try:
                self.do(i1, tr)
            except WorkflowException:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            self.changeUser('pmCreator2')
            self.failIf(self.hasPermission(View, i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is visible by everybody
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            self.changeUser('pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            if isPublished:
                self.changeUser('pmCreator2')
                self.failUnless(self.hasPermission(View, i1))
            else:
                self.changeUser('pmCreator2')
                self.failIf(self.hasPermission(View, i1))
        #check that the meeting have been published
        self.failUnless(isPublished)

    def _everyone_reads_all_active(self):
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        # if activated, everyone can even see everything before
        '''Tests while 'everyone_reads_all' wfAdaptation is inactive.'''
        # when the meeting/item is 'published' and in following states,
        # everybody (having MeetingObserverGlobal role) can see the items
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in self.meetingConfig.getTransitionsForPresentingAnItem():
            self.changeUser('pmManager')
            try:
                self.do(i1, tr)
            except WorkflowException:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            self.changeUser('pmCreator2')
            self.failUnless(self.hasPermission(View, i1))
        # now here i1 is "presented"
        # once meeting/items are "published", it is visible by everybody
        isPublished = False
        for tr in self._getTransitionsToCloseAMeeting():
            self.changeUser('pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            self.changeUser('pmCreator1')
            self.failUnless(self.hasPermission(View, i1))
            if not isPublished and m1.queryState() == 'published':
                isPublished = True
            self.changeUser('pmCreator2')
            self.failUnless(self.hasPermission(View, i1))
        #check that the meeting have been published
        self.failUnless(isPublished)

    def test_pm_WFA_creator_edits_unless_closed(self):
        '''Test the workflowAdaptation 'creator_edits_unless_closed'.'''
        # ease override by subproducts
        if not 'creator_edits_unless_closed' in self.meetingConfig.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._creator_edits_unless_closed_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('creator_edits_unless_closed')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        self._creator_edits_unless_closed_active()

    def _creator_edits_unless_closed_inactive(self):
        '''Tests while 'creator_edits_unless_closed' wfAdaptation is inactive.'''
        # by default, the item creator can just edit a created item, no more after
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision('<p>My decision</p>')
        self.failUnless(self.hasPermission(ModifyPortalContent, i1))
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in self.meetingConfig.getTransitionsForPresentingAnItem():
            self.changeUser('pmManager')
            try:
                self.do(i1, tr)
            except WorkflowException:
                continue
            self.changeUser('pmCreator1')
            # the creator can no more modify the item
            self.failIf(self.hasPermission(ModifyPortalContent, i1))
        for tr in self._getTransitionsToCloseAMeeting():
            self.changeUser('pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            self.changeUser('pmCreator1')
            # the creator can no more modify the item
            self.failIf(self.hasPermission(ModifyPortalContent, i1))

    def _creator_edits_unless_closed_active(self):
        '''Tests while 'creator_edits_unless_closed' wfAdaptation is active.'''
        self.changeUser('pmCreator1')
        i1 = self.create('MeetingItem')
        i1.setDecision("<p>My decision</p>")
        self.failUnless(self.hasPermission(ModifyPortalContent, i1))
        self.changeUser('pmManager')
        m1 = self.create('Meeting', date=DateTime())
        for tr in self.meetingConfig.getTransitionsForPresentingAnItem():
            self.changeUser('pmManager')
            try:
                self.do(i1, tr)
            except WorkflowException:
                continue
            self.changeUser('pmCreator1')
            # the creator can still modify the item if certain states
            # by default every state before "present"
            if not i1.queryState() in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                self.failUnless(self.hasPermission(ModifyPortalContent, i1))
            else:
                self.failIf(self.hasPermission(ModifyPortalContent, i1))
        for tr in self._getTransitionsToCloseAMeeting():
            self.changeUser('pmManager')
            if tr in self.transitions(m1):
                self.do(m1, tr)
            else:
                continue
            self.changeUser('pmCreator1')
            # the creator can still modify the item if certain states
            if not i1.queryState() in WF_NOT_CREATOR_EDITS_UNLESS_CLOSED:
                self.failUnless(self.hasPermission(ModifyPortalContent, i1))
            else:
                self.failIf(self.hasPermission(ModifyPortalContent, i1))

    def test_pm_WFA_return_to_proposing_group(self):
        '''Test the workflowAdaptation 'return_to_proposing_group'.'''
        # ease override by subproducts
        if not 'return_to_proposing_group' in self.meetingConfig.listWorkflowAdaptations():
            return
        # check while the wfAdaptation is not activated
        self._return_to_proposing_group_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('return_to_proposing_group')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        # test what should happen to the wf (added states and transitions)
        self._return_to_proposing_group_active()
        # test the functionnality of returning an item to the proposing group
        self._return_to_proposing_group_active_wf_functionality()

    def _return_to_proposing_group_inactive(self):
        '''Tests while 'return_to_proposing_group' wfAdaptation is inactive.'''
        # make sure the 'return_to_proposing_group' state does not exist in the item WF
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.failIf('returned_to_proposing_group' in itemWF.states)

    def _return_to_proposing_group_active(self):
        '''Tests while 'return_to_proposing_group' wfAdaptation is active.'''
        # we subdvise this test in 3, testing every constants, this way,
        # a subplugin can call these test separately
        # RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
        self._return_to_proposing_group_active_from_item_states()
        # RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE
        self._return_to_proposing_group_active_state_to_clone()
        # RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
        self._return_to_proposing_group_active_custom_permissions()

    def _return_to_proposing_group_active_from_item_states(self):
        '''Helper method to test 'return_to_proposing_group' wfAdaptation regarding the
           RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES defined value.'''
        # make sure the 'return_to_proposing_group' state does not exist in the item WF
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.failUnless('returned_to_proposing_group' in itemWF.states)
        # check from witch state we can go to 'returned_to_proposing_group', it corresponds
        # to model.adaptations.RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
        from_states = set()
        for state in itemWF.states.values():
            if 'return_to_proposing_group' in state.transitions:
                from_states.add(state.id)
        # at least every states in from_states were defined in RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
        self.failIf(from_states.difference(set(RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES)))

    def _return_to_proposing_group_active_state_to_clone(self):
        '''Helper method to test 'return_to_proposing_group' wfAdaptation regarding the
           RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE defined value.'''
        # make sure permissions of the new state correspond to permissions of the state
        # defined in the model.adaptations.RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE item state name
        # just take care that for new state, MeetingManager have been added to every permissions
        # this has only sense if using it, aka no RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
        # this could be the case if a subproduct (MeetingXXX) calls this test...
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        cfgItemWFId = self.meetingConfig.getItemWorkflow()
        state_to_clone_id = RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE.get(cfgItemWFId).split('.')[1]
        cloned_state_permissions = itemWF.states[state_to_clone_id].permission_roles
        new_state_permissions = itemWF.states['returned_to_proposing_group'].permission_roles
        for permission in cloned_state_permissions:
            cloned_state_permission_with_meetingmanager = []
            acquired = isinstance(cloned_state_permissions[permission], list) and True or False
            if not 'MeetingManager' in cloned_state_permissions[permission]:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
                cloned_state_permission_with_meetingmanager.append('MeetingManager')
            else:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
            # 'Delete objects' is only given to ['Manager', ]
            if permission == DeleteObjects:
                cloned_state_permission_with_meetingmanager = ['Manager', ]

            if not acquired:
                cloned_state_permission_with_meetingmanager = tuple(cloned_state_permission_with_meetingmanager)

            self.assertEquals(cloned_state_permission_with_meetingmanager,
                              new_state_permissions[permission])
            # Permission acquisition is also cloned
            self.assertEquals(
                itemWF.states[state_to_clone_id].getPermissionInfo(permission)['acquired'],
                itemWF.states['returned_to_proposing_group'].getPermissionInfo(permission)['acquired'])

    def _return_to_proposing_group_active_custom_permissions(self):
        '''Helper method to test 'return_to_proposing_group' wfAdaptation regarding the
           RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS defined value.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        cfgItemWFId = cfg.getItemWorkflow()
        # now test the RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS, if some custom permissions are defined,
        # it will override the permissions coming from the state to clone permissions
        from Products.PloneMeeting.model import adaptations
        # first time the wfAdaptation was applied without a defined RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
        self.assertEquals(adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS, {})
        # we will change the WriteItemMeetingManagerFields but for now, it is the same permissions than
        # in the permissions cloned from the defined state to clone
        CUSTOM_PERMISSION = WriteItemMeetingManagerFields
        cfgItemWFId = cfg.getItemWorkflow()
        state_to_clone_id = RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE.get(cfgItemWFId).split('.')[1]
        if not 'MeetingManager' in \
           itemWF.states[state_to_clone_id].permission_roles[CUSTOM_PERMISSION]:
            if isinstance(itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION], tuple):
                tmp_list = list(itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION])
                tmp_list.remove('MeetingManager')
                itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION] = tuple(tmp_list)
            else:
                itemWF.states['returned_to_proposing_group'].\
                    permission_roles[CUSTOM_PERMISSION].remove('MeetingManager')
        self.assertEquals(
            itemWF.states[state_to_clone_id].permission_roles[CUSTOM_PERMISSION],
            itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION])
        # we will add the 'MeetingMember' role, make sure it is not already there...
        if 'MeetingMember' in \
           itemWF.states[state_to_clone_id].permission_roles[CUSTOM_PERMISSION]:
            tmp_list = list(itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION])
            tmp_list.remove('MeetingMember')
            itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION] = tuple(tmp_list)
        self.failIf('MeetingMember' in itemWF.states['returned_to_proposing_group'].permission_roles[CUSTOM_PERMISSION])
        # we define the custom permissions and we run the wfAdaptation again...
        adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS[cfgItemWFId] = \
            {WriteItemMeetingManagerFields:
             ('Manager', 'MeetingManager', 'MeetingMember', )}
        # reapply wfAdaptation 'return_to_proposing_group'
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        # now our custom permission must be taken into account but other permissions should be the same than
        # the ones defined in the state to clone permissions of
        cloned_state_permissions = itemWF.states[state_to_clone_id].permission_roles
        new_state_permissions = itemWF.states['returned_to_proposing_group'].permission_roles
        for permission in cloned_state_permissions:
            cloned_state_permission_with_meetingmanager = []
            acquired = isinstance(cloned_state_permissions[permission], list) and True or False
            if not 'MeetingManager' in cloned_state_permissions[permission]:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
                cloned_state_permission_with_meetingmanager.append('MeetingManager')
            else:
                cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
            # here check if we are treating our custom permission
            if permission == CUSTOM_PERMISSION:
                cloned_state_permission_with_meetingmanager = \
                    adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS[cfgItemWFId][CUSTOM_PERMISSION]
            # 'Delete objects' is only given to ['Manager', 'MeetingManager']
            # if it was not defined in RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
            if permission == DeleteObjects:
                cloned_state_permission_with_meetingmanager = ['Manager', ]
            if not acquired:
                cloned_state_permission_with_meetingmanager = tuple(cloned_state_permission_with_meetingmanager)
            self.assertEquals(cloned_state_permission_with_meetingmanager,
                              new_state_permissions[permission])
        # if 'Delete objects' was defined in RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS
        # the defined permissions are kept.  For example, give 'Delete objects' to 'Manager' and 'MeetingManager'
        adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS[cfgItemWFId][DeleteObjects] = \
            ('Manager', 'MeetingManager')
        # reapply wfAdaptation 'return_to_proposing_group'
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        new_state_permissions = itemWF.states['returned_to_proposing_group'].permission_roles
        self.assertEquals(('Manager', 'MeetingManager', ),
                          new_state_permissions[DeleteObjects])
        adaptations.RETURN_TO_PROPOSING_GROUP_CUSTOM_PERMISSIONS = {}
        # reapply wfAdaptation 'return_to_proposing_group'
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        new_state_permissions = itemWF.states['returned_to_proposing_group'].permission_roles
        self.assertEquals(('Manager',), new_state_permissions[DeleteObjects])

    def _return_to_proposing_group_active_wf_functionality(self):
        '''Tests the workflow functionality of using the 'return_to_proposing_group' wfAdaptation.'''
        # while it is active, the creators of the item can edit the item as well as the MeetingManagers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        # create a Meeting and add the item to it
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        self.presentItem(item)
        # now that it is presented, the pmCreator1/pmReviewer1 can not edit it anymore
        for userId in ('pmCreator1', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.hasPermission(ModifyPortalContent, item))
        # the item can be send back to the proposing group by the MeetingManagers only
        for userId in ('pmCreator1', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.wfTool.getTransitionsFor(item))
        self.changeUser('pmManager')
        self.failUnless('return_to_proposing_group' in [tr['name'] for tr in self.wfTool.getTransitionsFor(item)])
        # send the item back to the proposing group so the proposing group as an edit access to it
        self.do(item, 'return_to_proposing_group')
        self.changeUser('pmCreator1')
        self.failUnless(self.hasPermission(ModifyPortalContent, item))
        # the item creator may not be able to delete the item
        self.failIf(self.hasPermission(DeleteObjects, item))
        # MeetingManagers can still edit it also
        self.changeUser('pmManager')
        self.failUnless(self.hasPermission(ModifyPortalContent, item))
        # the creator can send the item back to the meeting managers, as the meeting managers
        for userId in ('pmCreator1', 'pmManager'):
            self.changeUser(userId)
            self.failUnless('backTo_presented_from_returned_to_proposing_group' in
                            [tr['name'] for tr in self.wfTool.getTransitionsFor(item)])
        # when the creator send the item back to the meeting, it is in the right state depending
        # on the meeting state.  Here, when meeting is 'created', the item is back to 'presented'
        self.do(item, 'backTo_presented_from_returned_to_proposing_group')
        self.assertEquals(item.queryState(), 'presented')
        # send the item back to proposing group, freeze the meeting then send the item back to the meeting
        # the item should be now in the item state corresponding to the meeting frozen state, so 'itemfrozen'
        self.do(item, 'return_to_proposing_group')
        self.freezeMeeting(meeting)
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.assertEquals(item.queryState(), 'itemfrozen')

    def test_pm_WFA_return_to_proposing_group_with_last_validation(self):
        '''Test the workflowAdaptation 'return_to_proposing_group_with_last_validation'.'''
        # ease override by subproducts
        if not 'return_to_proposing_group_with_last_validation' in self.meetingConfig.listWorkflowAdaptations():
            return
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('return_to_proposing_group_with_last_validation')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        # test what should happen to the wf (added states and transitions)
        self._return_to_proposing_group_with_validation_active()
        # test the functionnality of returning an item to the proposing group
        self._return_to_proposing_group_with_validation_active_wf_functionality()

    def _return_to_proposing_group_with_validation_active(self):
        '''Tests while 'return_to_proposing_group' wfAdaptation is active.'''
        # we subdvise this test in 3, testing every constants, this way,
        # a subplugin can call these test separately
        # RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
        #  ... we use the same test than original return to proposing group
        self._return_to_proposing_group_active_from_item_states()
        # RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE ORIGINAL and WITH VALIDATION
        self._return_to_proposing_group_with_validation_active_state_to_clone()

    def _return_to_proposing_group_with_validation_active_state_to_clone(self):
        '''Helper method to test 'return_to_proposing_group' wfAdaptation regarding the
           RETURN_TO_PROPOSING_GROUP_VALIDATING_STATES defined value.'''
        # make sure permissions of the new state correspond to permissions of the state
        # defined in the model.adaptations.RETURN_TO_PROPOSING_GROUP_WITH_LAST_VALIDATION_STATE_TO_CLONE item state name
        # just take care that for new state, MeetingManager have been added to every permissions
        # this has only sense if using it, aka no RETURN_TO_PROPOSING_GROUP_WITH_LAST_VALIDATION_CUSTOM_PERMISSIONS
        # this could be the case if a subproduct (MeetingXXX) calls this test...
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        cfgItemWFId = self.meetingConfig.getItemWorkflow()

        state_to_clone_ids = (RETURN_TO_PROPOSING_GROUP_STATE_TO_CLONE.get(cfgItemWFId).split('.')[1], ) + \
                              RETURN_TO_PROPOSING_GROUP_VALIDATING_STATES
        for state_to_clone_id in state_to_clone_ids:
            cloned_state_permissions = itemWF.states[state_to_clone_id].permission_roles
            returned_state = 'returned_to_proposing_group'
            if state_to_clone_id != 'itemcreated':
                returned_state += '_{0}'.format(state_to_clone_id)
            new_state_permissions = itemWF.states[returned_state].permission_roles
            for permission in cloned_state_permissions:
                cloned_state_permission_with_meetingmanager = []
                acquired = isinstance(cloned_state_permissions[permission], list) and True or False
                if not 'MeetingManager' in cloned_state_permissions[permission]:
                    cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])
                    cloned_state_permission_with_meetingmanager.append('MeetingManager')
                else:
                    cloned_state_permission_with_meetingmanager = list(cloned_state_permissions[permission])

                # 'Delete objects' is only given to ['Manager', ]
                if permission == DeleteObjects:
                    cloned_state_permission_with_meetingmanager = ['Manager', ]
                if not acquired:
                    cloned_state_permission_with_meetingmanager = tuple(cloned_state_permission_with_meetingmanager)
                if cloned_state_permission_with_meetingmanager != new_state_permissions[permission]:
                    import ipdb; ipdb.set_trace()
                self.assertEquals(cloned_state_permission_with_meetingmanager,
                                  new_state_permissions[permission])
                # Permission acquisition is also cloned
                self.assertEquals(
                    itemWF.states[state_to_clone_id].getPermissionInfo(permission)['acquired'],
                    itemWF.states[returned_state].getPermissionInfo(permission)['acquired'])

    def _return_to_proposing_group_with_validation_active_wf_functionality(self):
        '''Tests the workflow functionality of using the 'return_to_proposing_group_with_last_validation' wfAdaptation.'''
        # while it is active, the creators of the item can edit the item as well as the MeetingManagers
        # after, he must be send to reviewer the item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        # create a Meeting and add the item to it
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime())
        self.presentItem(item)
        # now that it is presented, the pmCreator1/pmReviewer1 can not edit it anymore
        for userId in ('pmCreator1', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.hasPermission(ModifyPortalContent, item))
        # the item can be send back to the proposing group by the MeetingManagers only
        for userId in ('pmCreator1', 'pmReviewer1'):
            self.changeUser(userId)
            self.failIf(self.wfTool.getTransitionsFor(item))
        self.changeUser('pmManager')
        self.failUnless('return_to_proposing_group' in [tr['name'] for tr in self.wfTool.getTransitionsFor(item)])
        # send the item back to the proposing group so the proposing group as an edit access to it
        self.do(item, 'return_to_proposing_group')
        self.changeUser('pmCreator1')
        self.failUnless(self.hasPermission(ModifyPortalContent, item))
        # the item creator may not be able to delete the item
        self.failIf(self.hasPermission(DeleteObjects, item))
        # MeetingManagers can still edit it also
        self.changeUser('pmManager')
        self.failUnless(self.hasPermission(ModifyPortalContent, item))
        # Now send item to the reviewer
        self.changeUser('pmCreator1')
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        # he item creator may not be able to modify the item
        self.failIf(self.hasPermission(ModifyPortalContent, item))
        # MeetingManagers can still edit it also
        self.changeUser('pmManager')
        self.failUnless(self.hasPermission(ModifyPortalContent, item))
        # the reviewer can send the item back to the meeting managers, as the meeting managers
        self.changeUser('pmReviewer1')
        for userId in ('pmReviewer1', 'pmManager'):
            self.changeUser(userId)
            self.failUnless('backTo_presented_from_returned_to_proposing_group' in
                            [tr['name'] for tr in self.wfTool.getTransitionsFor(item)])
        # when the creator send the item back to the meeting, it is in the right state depending
        # on the meeting state.  Here, when meeting is 'created', the item is back to 'presented'
        self.do(item, 'backTo_presented_from_returned_to_proposing_group')
        self.assertEquals(item.queryState(), 'presented')
        # send the item back to proposing group, freeze the meeting then send the item back to the meeting
        # the item should be now in the item state corresponding to the meeting frozen state, so 'itemfrozen'
        self.do(item, 'return_to_proposing_group')
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        self.freezeMeeting(meeting)
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.assertEquals(item.queryState(), 'itemfrozen')

    def test_pm_WFA_return_to_proposing_group_with_all_validations(self):
        '''Test the workflowAdaptation 'return_to_proposing_group_with_all_validations'.'''
        # ease override by subproducts
        if not 'return_to_proposing_group_with_all_validations' in self.meetingConfig.listWorkflowAdaptations():
            return
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('return_to_proposing_group_with_all_validations')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        # test what should happen to the wf (added states and transitions)
        # We can using the same test than last Validation in standard wf (created --> proposed)
        self._return_to_proposing_group_with_validation_active()
        # We can also using the same test than last Validation
        self._return_to_proposing_group_with_validation_active_wf_functionality()

    def test_pm_WFA_hide_decisions_when_under_writing(self):
        '''Test the workflowAdaptation 'hide_decisions_when_under_writing'.
           If meeting is in 'decided' state, only the MeetingManagers can
           view the real decision. The other people view a standard
           message taken from the MeetingConfig.'''
        # ease override by subproducts
        if not 'hide_decisions_when_under_writing' in self.meetingConfig.listWorkflowAdaptations():
            return
        self.changeUser('admin')
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._hide_decisions_when_under_writing_inactive()
        # activate the wfAdaptation and check
        self.meetingConfig.setWorkflowAdaptations('hide_decisions_when_under_writing')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        self._hide_decisions_when_under_writing_active()
        # test also for the meetingConfig2 if it uses a different workflow
        if self.meetingConfig.getMeetingWorkflow() == self.meetingConfig2.getMeetingWorkflow():
            return
        self.meetingConfig = self.meetingConfig2
        self._hide_decisions_when_under_writing_inactive()
        self.meetingConfig.setWorkflowAdaptations('hide_decisions_when_under_writing')
        performWorkflowAdaptations(self.meetingConfig, logger=pm_logger)
        # check while the wfAdaptation is not activated
        self._hide_decisions_when_under_writing_active()

    def _hide_decisions_when_under_writing_inactive(self):
        '''Tests while 'hide_decisions_when_under_writing' wfAdaptation is inactive.
           In this case, the decision is always accessible by the creator no matter it is
           adapted by any MeetingManagers.  There is NO extra 'decisions_published' state moreover.'''
        meetingWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getMeetingTypeName())[0]
        self.failIf('decisions_published' in meetingWF.states)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2013/01/01 12:00'))
        item = self.create('MeetingItem')
        item.setMotivation('<p>testing motivation field</p>')
        item.setDecision('<p>testing decision field</p>')
        self.presentItem(item)
        self.changeUser('pmCreator1')
        # relevant users can see the decision
        self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        self.changeUser('pmManager')
        self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        self.freezeMeeting(meeting)
        self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        # maybe we have a 'publish' transition
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
            self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
            self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        self.decideMeeting(meeting)
        # set a decision...
        item.setMotivation('<p>Motivation adapted by pmManager</p>')
        item.setDecision('<p>Decision adapted by pmManager</p>')
        item.reindexObject()
        # it is immediatelly viewable by the item's creator as
        # the 'hide_decisions_when_under_writing' wfAdaptation is not enabled
        self.changeUser('pmCreator1')
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        self.changeUser('pmManager')
        self.closeMeeting(meeting)
        self.assertEquals(meeting.queryState(), 'closed')
        self.changeUser('pmCreator1')
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')

    def _hide_decisions_when_under_writing_active(self):
        '''Tests while 'hide_decisions_when_under_writing' wfAdaptation is active.'''
        meetingWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getMeetingTypeName())[0]
        self.failUnless('decisions_published' in meetingWF.states)
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2013/01/01 12:00'))
        item = self.create('MeetingItem')
        item.setMotivation('<p>testing motivation field</p>')
        item.setDecision('<p>testing decision field</p>')
        self.presentItem(item)
        self.changeUser('pmCreator1')
        # relevant users can see the decision
        self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        self.changeUser('pmManager')
        self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        self.freezeMeeting(meeting)
        self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        # maybe we have a 'publish' transition
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
            self.assertEquals(item.getMotivation(), '<p>testing motivation field</p>')
            self.assertEquals(item.getDecision(), '<p>testing decision field</p>')
        self.decideMeeting(meeting)
        # set a decision...
        item.setMotivation('<p>Motivation adapted by pmManager</p>')
        item.setDecision('<p>Decision adapted by pmManager</p>')
        item.reindexObject()
        self.changeUser('pmCreator1')
        self.assertEquals(meeting.queryState(), 'decided')
        self.assertEquals(item.getMotivation(),
                          HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEquals(item.getDecision(),
                          HIDE_DECISION_UNDER_WRITING_MSG)

        # special test, remove an annex, it is done as 'all_powerful_Oz' user
        # and broke when checking has_permission in MeetingItem._mayNotViewDecisionMsg
        self.changeUser('siteadmin')
        annex = self.addAnnex(item)
        self.deleteAsManager(annex.UID())

        # MeetingManagers see it correctly
        self.changeUser('pmManager')
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        # a 'publish_decisions' transition is added after 'decide'
        self.do(meeting, 'publish_decisions')
        self.assertEquals(meeting.queryState(), 'decisions_published')
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        # now that the meeting is in the 'decisions_published' state, decision is viewable to item's creator
        self.changeUser('pmCreator1')
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        # items are automatically set to a final specific state when decisions are published
        self.assertEquals(item.queryState(),
                          self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['publish_decisions'])
        self.changeUser('pmManager')
        # every items of the meeting are in the same final specific state
        for itemInMeeting in meeting.getItems():
            self.assertEquals(itemInMeeting.queryState(),
                              self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['publish_decisions'])
        self.do(meeting, 'close')
        self.changeUser('pmCreator1')
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')

        # moreover when the 'decisions_published' is activated,
        # 'decisions' searches take this new state into account
        for collection in self.meetingConfig.searches.searches_decisions.objectValues('DashboardCollection'):
            for criterion in collection.query:
                if criterion['i'] == 'review_state':
                    self.assertTrue('decisions_published' in criterion['v'])

    def test_pm_WFA_return_to_proposing_group_with_hide_decisions_when_under_writing(self):
        """Test when both 'return_to_proposing_group' and 'hide_decisions_when_under_writing' WFAdaptations
           are enabled, in this case, when the meeting is decided and decisions are hidden, nevertheless, when
           returned to the proposing group, the decision is visible to the users able to edit the item."""
        # ease override by subproducts
        if not 'return_to_proposing_group' in self.meetingConfig.listWorkflowAdaptations() or \
           not 'hide_decisions_when_under_writing' in self.meetingConfig.listWorkflowAdaptations():
            return
        self.changeUser('admin')
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        cfg.setWorkflowAdaptations(
            ('hide_decisions_when_under_writing', 'return_to_proposing_group'))
        performWorkflowAdaptations(cfg, logger=pm_logger)

        # if one of the user of the proposingGroup may edit the decision, then
        # every members of the proposingGroup may see the decision, this way, if MeetingMember
        # may edit the decision, then a MeetingObserverLocal may see it also evern if he may not edit it
        meeting = self.create('Meeting', date=DateTime('2016/01/01 12:00'))
        item = self.create('MeetingItem')
        item.setMotivation('<p>Motivation field</p>')
        item.setDecision('<p>Decision field</p>')
        self.presentItem(item)
        # maybe we have a 'publish' transition
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
        self.decideMeeting(meeting)

        # set another decision...
        item.setMotivation('<p>Motivation adapted by pmManager</p>')
        item.setDecision('<p>Decision adapted by pmManager</p>')
        item.reindexObject()

        # not viewable for now
        self.changeUser('pmCreator1')
        self.assertEquals(meeting.queryState(), 'decided')
        self.assertEquals(item.getMotivation(),
                          HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEquals(item.getDecision(),
                          HIDE_DECISION_UNDER_WRITING_MSG)

        # return the item to the proposingGroup
        self.changeUser('pmManager')
        self.do(item, 'return_to_proposing_group')
        # now the decision is viewable by the 'pmCreator1' as he may edit it
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertEquals(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEquals(item.getDecision(), '<p>Decision adapted by pmManager</p>')

        # but another user that may see the item but not edit it may not see the decision
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((item.queryState(), ))
        item.setCopyGroups(('vendors_reviewers', ))
        item.updateLocalRoles()
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertEquals(item.getMotivation(), HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEquals(item.getDecision(), HIDE_DECISION_UNDER_WRITING_MSG)

    def test_pm_WFA_waiting_advices(self):
        '''Test the workflowAdaptation 'waiting_advices'.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not 'waiting_advices' in cfg.listWorkflowAdaptations():
            return

        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        originalWFA = cfg.getWorkflowAdaptations()
        cfg.setWorkflowAdaptations(())
        cfg.at_post_edit_script()
        self._waiting_advices_inactive()

        # activate the wfAdaptation and check
        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': (self.WF_STATE_NAME_MAPPINGS['proposed_first_level'], ),
             'back_states': (self.WF_STATE_NAME_MAPPINGS['proposed_first_level'], ),
             'perm_cloned_states': (self.WF_STATE_NAME_MAPPINGS['proposed_first_level'], ),
             'remove_modify_access': True},)
        cfg.setWorkflowAdaptations(originalWFA + ('waiting_advices',))
        cfg.at_post_edit_script()
        self._waiting_advices_active()

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def _waiting_advices_inactive(self):
        '''Tests while 'waiting_advices' wfAdaptation is inactive.'''
        # make sure the 'waiting_advices' state does not exist in the item WF
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.failIf('waiting_advices' in str(itemWF.states.keys()))

    def _waiting_advices_active(self):
        '''Tests while 'waiting_advices' wfAdaptation is active.'''
        cfg = self.meetingConfig
        # by default it is linked to the 'proposed' state
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        waiting_state_name = '{0}_waiting_advices'.format(self.WF_STATE_NAME_MAPPINGS['proposed_first_level'])
        waiting_transition_name = 'wait_advices_from_{0}'.format(self.WF_STATE_NAME_MAPPINGS['proposed_first_level'])
        self.assertTrue(waiting_state_name in itemWF.states)

        # right, create an item and set it to 'waiting_advices'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item, first_level=True)
        # 'pmCreator1' is not able to set item to 'waiting_advices'
        self.assertFalse(self.transitions(item))
        # 'pmReviewer1' may do it but by default is not able to edit it
        self.changeUser('pmReviewer1')
        # no advice asked so a No() instance is returned for now
        self.assertFalse(waiting_transition_name in self.transitions(item))
        advice_required_to_ask_advices = translate('advice_required_to_ask_advices',
                                                   domain='PloneMeeting',
                                                   context=self.request)
        methodName = 'mayWait_advices_from_{0}'.format(self.WF_STATE_NAME_MAPPINGS['proposed_first_level'])
        self.assertEqual(translate(getattr(item.wfConditions(), methodName)().msg,
                                   context=self.request),
                         advice_required_to_ask_advices)
        # ask an advice so transition is available
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # still not available because no advice may be asked in state waiting_state_name
        self.assertFalse(waiting_state_name in self.tool.vendors.getItemAdviceStates())
        self.assertFalse(waiting_transition_name in self.transitions(item))

        # do things work
        self.tool.vendors.setItemAdviceStates(("{0}__state__{1}".format(cfg.getId(), waiting_state_name), ))
        self.assertTrue(waiting_transition_name in self.transitions(item))
        self._setItemToWaitingAdvices(item, waiting_transition_name)
        self.assertEqual(item.queryState(), waiting_state_name)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))

        # pmCreator1 may view but not edit
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertFalse(self.transitions(item))

        # right come back to 'proposed'
        self.changeUser('pmReviewer1')
        self.do(item, 'backTo_%s_from_waiting_advices' % self.WF_STATE_NAME_MAPPINGS['proposed_first_level'])
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['proposed_first_level'])

    def test_pm_WFA_waiting_advices_with_prevalidation(self):
        '''It can also work from several states, if pre_validation is enabled
           it is possible to go from 'proposed' and 'prevalidated' to 'waiting_advices'
           and to go back to both states.'''
        cfg = self.meetingConfig
        if not 'pre_validation' in cfg.listWorkflowAdaptations() or \
           not 'waiting_advices' in cfg.listWorkflowAdaptations():
            return

        wfAdaptations = list(cfg.getWorkflowAdaptations())
        if not 'pre_validation' in wfAdaptations:
            wfAdaptations.append('pre_validation')
        if not 'waiting_advices' in wfAdaptations:
            wfAdaptations.append('waiting_advices')
        cfg.setWorkflowAdaptations(tuple(wfAdaptations))
        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': (self.WF_STATE_NAME_MAPPINGS['proposed_first_level'],
                             'prevalidated', ),
             'back_states': (self.WF_STATE_NAME_MAPPINGS['proposed_first_level'],
                             'prevalidated', ),
             'perm_cloned_states': (self.WF_STATE_NAME_MAPPINGS['proposed_first_level'],
                                    'prevalidated', ),
             'remove_modify_access': True},)
        cfg.at_post_edit_script()
        waiting_advices_state = '{0}__or__prevalidated_waiting_advices'.format(
            self.WF_STATE_NAME_MAPPINGS['proposed_first_level'])
        self.tool.vendors.setItemAdviceStates(("{0}__state__{1}".format(cfg.getId(), waiting_advices_state), ))

        # by default it is linked to the 'proposed' state
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue(waiting_advices_state in itemWF.states)

        # suffixed transitions are not added
        self.assertFalse('%s_waiting_advices' % self.WF_STATE_NAME_MAPPINGS['proposed_first_level']
                         in itemWF.states)
        self.assertFalse('prevalidated_waiting_advices' in itemWF.states)
        # transitions are created
        wait_advices_from_proposed_transition = 'wait_advices_from_%s' % \
            self.WF_STATE_NAME_MAPPINGS['proposed_first_level']
        self.assertTrue(wait_advices_from_proposed_transition in itemWF.transitions)
        self.assertTrue('wait_advices_from_prevalidated' in itemWF.transitions)
        # back transitions are created
        self.assertTrue('backTo_%s_from_waiting_advices' % self.WF_STATE_NAME_MAPPINGS['proposed_first_level']
                        in itemWF.transitions)
        self.assertTrue('backTo_prevalidated_from_waiting_advices' in itemWF.transitions)

        # right, create an item and set it to 'proposed__or__prevalidated_waiting_advices'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        self._afterItemCreatedWaitingAdviceWithPrevalidation(item)
        self.proposeItem(item, first_level=True)
        # 'pmCreator1' is not able to set item to 'waiting_advices'
        self.assertFalse(self.transitions(item))
        # 'pmReviewerLevel1' may do it, it is a prereviewer
        self.changeUser('pmReviewerLevel1')
        self.assertTrue(wait_advices_from_proposed_transition in self.transitions(item))
        # trigger from 'prevalidated'
        self.do(item, 'prevalidate')
        self.assertEquals(item.queryState(), 'prevalidated')
        self.assertFalse(self.transitions(item))
        self.changeUser('pmReviewerLevel2')
        self.do(item, 'wait_advices_from_prevalidated')
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))

        # pmCreator1 may view but not edit
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertFalse(self.transitions(item))

        # right test the back transitions, first come back to 'prevalidated', then to 'proposed'
        self.changeUser('pmManager')
        self.do(item, 'backTo_prevalidated_from_waiting_advices')
        self.assertEquals(item.queryState(), 'prevalidated')
        self.do(item, 'wait_advices_from_prevalidated')
        self.do(item, 'backTo_prevalidated_from_waiting_advices')
        self.assertEquals(item.queryState(), 'prevalidated')

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def test_pm_WFA_waiting_advices_several_states(self):
        '''Test the workflowAdaptation 'waiting_advices'.
           By default WAITING_ADVICES_FROM_STATES is going from proposed/prevaliated
           to one single state then back.  But we can go to several states, here got to 2 different
           states from 'itemcreated' and 'proposed.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not 'waiting_advices' in cfg.listWorkflowAdaptations():
            return

        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': ('itemcreated', ),
             'back_states': ('itemcreated', ),
             'perm_cloned_states': ('itemcreated', ),
             'remove_modify_access': True},
            {'from_states': (self.WF_STATE_NAME_MAPPINGS['proposed'], ),
             'back_states': (self.WF_STATE_NAME_MAPPINGS['proposed'], ),
             'perm_cloned_states': (self.WF_STATE_NAME_MAPPINGS['proposed'], ),
             'remove_modify_access': True},)
        cfg.setWorkflowAdaptations(cfg.getWorkflowAdaptations() + ('waiting_advices', ))
        cfg.at_post_edit_script()
        waiting_advices_itemcreated_state = 'itemcreated_waiting_advices'
        waiting_advices_proposed_state = '{0}_waiting_advices'.format(self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.tool.vendors.setItemAdviceStates(
            ("{0}__state__{1}".format(cfg.getId(), waiting_advices_itemcreated_state),
             "{0}__state__{1}".format(cfg.getId(), waiting_advices_proposed_state),))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # from 'itemcreated'
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEquals(item.queryState(), 'itemcreated_waiting_advices')
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.do(item, 'backTo_itemcreated_from_waiting_advices')
        self.assertEquals(item.queryState(), 'itemcreated')

        # from proposed
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self._setItemToWaitingAdvices(item,
                                      'wait_advices_from_%s' % self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertEquals(item.queryState(), '%s_waiting_advices' % self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        # 'pmCreator1' may view, not edit
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertFalse(self.transitions(item))
        self.changeUser(self._userAbleToBackFromWaitingAdvices(item.queryState()))
        self.do(item, 'backTo_%s_from_waiting_advices' % self.WF_STATE_NAME_MAPPINGS['proposed'])
        self.assertEquals(item.queryState(), self.WF_STATE_NAME_MAPPINGS['proposed'])

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def test_pm_WFA_waiting_advices_may_edit(self):
        '''Test the workflowAdaptation 'waiting_advices'.
           This time we set 'remove_modify_access' to False so Modify access
           is kept on the item set to 'waiting_advices'.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not 'waiting_advices' in cfg.listWorkflowAdaptations():
            return

        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': ('itemcreated', ),
             'back_states': ('itemcreated', ),
             'perm_cloned_states': ('itemcreated', ),
             'remove_modify_access': False},)
        cfg.setWorkflowAdaptations('waiting_advices')
        cfg.at_post_edit_script()
        self.tool.vendors.setItemAdviceStates(("{0}__state__{1}".format(cfg.getId(),
                                                                        'itemcreated_waiting_advices'), ))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers(('vendors', ))
        item.at_post_edit_script()
        # from 'itemcreated'
        self._setItemToWaitingAdvices(item, 'wait_advices_from_itemcreated')
        self.assertEquals(item.queryState(), 'itemcreated_waiting_advices')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(DeleteObjects, item))
        self.changeUser(self._userAbleToBackFromWaitingAdvices(item.queryState()))
        self.do(item, 'backTo_itemcreated_from_waiting_advices')
        self.assertEquals(item.queryState(), 'itemcreated')

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def _setItemToWaitingAdvices(self, item, transition):
        """Done to be overrided, sometimes it is necessary to do something more to be able
           to set item to 'waiting_advices'."""
        self.do(item, transition)

    def _userAbleToBackFromWaitingAdvices(self, currentState):
        """Return username able to back from waiting advices."""
        if currentState == 'itemcreated_waiting_advices':
            return 'pmCreator1'
        else:
            return 'pmReviewer1'

    def _afterItemCreatedWaitingAdviceWithPrevalidation(self, item):
        """Made to be overrided..."""
        return

    def test_pm_WFA_postpone_next_meeting(self):
        '''Test the workflowAdaptation 'postpone_next_meeting'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'postpone_next_meeting' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._postpone_next_meeting_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations(('postpone_next_meeting', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._postpone_next_meeting_active()

    def _postpone_next_meeting_inactive(self):
        '''Tests while 'postpone_next_meeting' wfAdaptation is inactive.'''
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertFalse('postpone_next_meeting' in itemWF.transitions)
        self.assertFalse('postponed_next_meeting' in itemWF.states)

    def _postpone_next_meeting_active(self):
        '''Tests while 'postpone_next_meeting' wfAdaptation is active.'''
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertTrue('postpone_next_meeting' in itemWF.transitions)
        self.assertTrue('postponed_next_meeting' in itemWF.states)
        # test it
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        self.assertEqual(item.queryState(), 'postponed_next_meeting')
        # back transition
        self.do(item, 'backToItemFrozen')

    def test_pm_WFA_postpone_next_meeting_back_transition(self):
        '''The back transition may vary if using additional WFAdaptations,
           item may back to 'itempublished', 'itemfrozen', ...'''
        cfg = self.meetingConfig
        if not 'postpone_next_meeting' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')

        # test with only 'postpone_next_meeting' then when using 'no_publication'
        for wfAdaptations in [('postpone_next_meeting', ),
                              ('no_publication', 'postpone_next_meeting')]:
            # activate the wfAdaptations and check
            cfg.setWorkflowAdaptations(wfAdaptations)
            cfg.at_post_edit_script()

            itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
            self.assertEquals(itemWF.states['postponed_next_meeting'].transitions,
                              itemWF.states['delayed'].transitions)
            # transition 'postpone_next_meeting' get out from same state as 'delay'
            for state in itemWF.states.values():
                if 'delay' in state.transitions:
                    self.assertTrue('postpone_next_meeting' in state.transitions)
                else:
                    self.assertFalse('postpone_next_meeting' in state.transitions)

    def test_pm_WFA_postpone_next_meeting_duplicated_and_validated_advices_inherited(self):
        '''When an item is set to 'postponed_next_meeting', it is automatically duplicated
           and the duplicated item is automatically validated.
           Moreover, advices on the duplicated item are inherited from original item.'''
        cfg = self.meetingConfig
        if not 'postpone_next_meeting' in cfg.listWorkflowAdaptations():
            return

        self.changeUser('admin')
        self.create('MeetingGroup', id='group1',  title='NewGroup1', acronym='N.G.1')
        self.create('MeetingGroup', id='group2',  title='NewGroup2', acronym='N.G.2')
        self.create('MeetingGroup', id='poweradvisers',  title='Power advisers', acronym='PA')
        cfg.setSelectableAdvisers(('vendors', 'group1', 'group2', 'poweradvisers'))
        self.portal.portal_groups.addPrincipalToGroup('pmAdviser1', 'poweradvisers_advisers')
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'group': 'group2',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setPowerAdvisersGroups(('poweradvisers', ))
        cfg.setItemPowerObserversStates(('itemcreated', ))
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))
        originalWFAdaptations = cfg.getWorkflowAdaptations()
        if not 'postpone_next_meeting' in originalWFAdaptations:
            cfg.setWorkflowAdaptations(originalWFAdaptations + ('postpone_next_meeting', ))
        cfg.at_post_edit_script()

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        item.setOptionalAdvisers(('vendors', 'developers__rowid__unique_id_123',
                                  'group2__rowid__unique_id_456', 'group1'))
        item.at_post_edit_script()
        # give advices
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'developers',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': 'poweradvisers',
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})

        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        # duplicated and duplicated item is validated
        clonedItem = item.getBRefs('ItemPredecessor')[0]
        self.assertEqual(clonedItem.getPredecessor(), item)
        self.assertEqual(clonedItem.queryState(), 'validated')
        # optional and automatic given advices were inherited
        self.assertTrue(clonedItem.adviceIsInherited('vendors'))
        self.assertTrue(clonedItem.adviceIsInherited('developers'))
        # optional and automatic advices that were not given are inherited
        # as well as the power adviser advice
        self.assertTrue(clonedItem.adviceIsInherited('group1'))
        self.assertTrue(clonedItem.adviceIsInherited('group2'))
        self.assertTrue(clonedItem.adviceIsInherited('poweradvisers'))

    def test_pm_WFA_postpone_next_meeting_advices_inherited(self):
        '''When an item is set to 'postponed_next_meeting', cloned item inherits from every advices.'''
        cfg = self.meetingConfig
        if not 'postpone_next_meeting' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        originalWFAdaptations = cfg.getWorkflowAdaptations()
        if not 'postpone_next_meeting' in originalWFAdaptations:
            cfg.setWorkflowAdaptations(originalWFAdaptations + ('postpone_next_meeting', ))
        cfg.at_post_edit_script()

        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        # duplicated and duplicated item is validated
        clonedItem = item.getBRefs('ItemPredecessor')[0]
        self.assertEqual(clonedItem.getPredecessor(), item)
        self.assertEqual(clonedItem.queryState(), 'validated')

    def test_pm_WFA_mark_not_applicable(self):
        '''Test the workflowAdaptation 'mark_not_applicable'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'mark_not_applicable' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._mark_not_applicable_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations(('mark_not_applicable', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._mark_not_applicable_active()

    def _mark_not_applicable_inactive(self):
        '''Tests while 'mark_not_applicable' wfAdaptation is inactive.'''
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertFalse('mark_not_applicable' in itemWF.transitions)
        self.assertFalse('marked_not_applicable' in itemWF.states)

    def _mark_not_applicable_active(self):
        '''Tests while 'mark_not_applicable' wfAdaptation is active.'''
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertTrue('mark_not_applicable' in itemWF.transitions)
        self.assertTrue('marked_not_applicable' in itemWF.states)
        # test it
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'mark_not_applicable')
        self.assertEqual(item.queryState(), 'marked_not_applicable')
        # back transition
        self.do(item, 'backToItemFrozen')

    def test_pm_WFA_removed(self):
        '''Test the workflowAdaptation 'removed'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'removed' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._removed_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations(('removed', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._removed_active()

    def _removed_inactive(self):
        '''Tests while 'removed' wfAdaptation is inactive.'''
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertFalse('remove' in itemWF.transitions)
        self.assertFalse('removed' in itemWF.states)

    def _removed_active(self):
        '''Tests while 'mark_not_applicable' wfAdaptation is active.'''
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertTrue('remove' in itemWF.transitions)
        self.assertTrue('removed' in itemWF.states)
        # test it
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'remove')
        self.assertEqual(item.queryState(), 'removed')
        # back transition
        self.do(item, 'backToItemFrozen')

    def test_pm_WFA_reviewers_take_back_validated_item(self):
        '''Test the workflowAdaptation 'reviewers_take_back_validated_item'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not 'reviewers_take_back_validated_item' in cfg.listWorkflowAdaptations():
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._reviewers_take_back_validated_item_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations(('reviewers_take_back_validated_item', ))
        performWorkflowAdaptations(cfg, logger=pm_logger)
        self._reviewers_take_back_validated_item_active()

    def _reviewers_take_back_validated_item_inactive(self):
        '''Tests while 'reviewers_take_back_validated_item' wfAdaptation is inactive.'''
        # validate an item, the MeetingReviewer is unable to take it back
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.do(item, 'validate')
        self.assertEqual(self.transitions(item), [])

    def _reviewers_take_back_validated_item_active(self):
        '''Tests while 'reviewers_take_back_validated_item' wfAdaptation is active.'''
        # first create a meeting, we will check the MeetingReviewer may not present the item
        self.changeUser('pmManager')
        self.create('Meeting', date=DateTime()+1)
        # validate an item, the MeetingReviewer will be able to take it back
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.do(item, 'validate')
        # make test defensive if used by subproducts, we have a 'backXXX' transition
        self.assertTrue([tr for tr in self.transitions(item) if tr.startswith('back')])
        # but he will not be able to present it
        self.assertFalse('present' in self.transitions(item))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWFAdaptations, prefix='test_pm_'))
    return suite
