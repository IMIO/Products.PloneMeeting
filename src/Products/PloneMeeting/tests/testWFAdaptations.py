# -*- coding: utf-8 -*-
#
# File: testWFAdaptations.py
#
# GNU General Public License (GPL)
#

from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.contact.plonegroup.utils import select_org_for_function
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.config import HIDE_DECISION_UNDER_WRITING_MSG
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.model.adaptations import RETURN_TO_PROPOSING_GROUP_FROM_ITEM_STATES
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from zope.event import notify
from zope.i18n import translate
from zope.lifecycleevent import ObjectModifiedEvent


class testWFAdaptations(PloneMeetingTestCase):
    '''Tests the different existing wfAdaptations.  Also made to be back tested by extension profiles...
       Each test call submethods that check the behaviour while each wfAdaptation is active or inactive.
       This way, an external profile will just override the called submethods if necessary.
       This way too, we will be able to check multiple activated wfAdaptations.'''

    def _check_wfa_available(self, wfas):
        available = True
        available_wfas = self.meetingConfig.listWorkflowAdaptations()
        for wfa in wfas:
            if wfa not in available_wfas:
                available = False
                pm_logger.info('Bypassing {0} because WFAdaptation {1} is not available!'.format(
                    self._testMethodName, wfa))
                break
        return available

    def test_pm_WFA_availableWFAdaptations(self):
        '''Test what are the available wfAdaptations.
           This way, if we add a wfAdaptations, the test will 'break' until it is adapted...'''
        self.assertEqual(sorted(self.meetingConfig.listWorkflowAdaptations().keys()),
                         ['accepted_but_modified',
                          'accepted_out_of_meeting',
                          'accepted_out_of_meeting_and_duplicated',
                          'accepted_out_of_meeting_emergency',
                          'accepted_out_of_meeting_emergency_and_duplicated',
                          'decide_item_when_back_to_meeting_from_returned_to_proposing_group',
                          'delayed',
                          'hide_decisions_when_under_writing',
                          'mark_not_applicable',
                          'meetingmanager_correct_closed_meeting',
                          'no_publication',
                          'only_creator_may_delete',
                          'postpone_next_meeting',
                          'pre_accepted',
                          'presented_item_back_to_itemcreated',
                          'presented_item_back_to_proposed',
                          'refused',
                          'removed',
                          'removed_and_duplicated',
                          'return_to_proposing_group',
                          'return_to_proposing_group_with_all_validations',
                          'return_to_proposing_group_with_last_validation',
                          'reviewers_take_back_validated_item',
                          'waiting_advices',
                          'waiting_advices_adviser_may_validate',
                          'waiting_advices_adviser_send_back',
                          'waiting_advices_from_before_last_val_level',
                          'waiting_advices_from_every_val_levels',
                          'waiting_advices_from_last_val_level',
                          'waiting_advices_given_advices_required_to_validate',
                          'waiting_advices_proposing_group_send_back'])

    def test_pm_WFA_appliedOnMeetingConfigEdit(self):
        """WFAdpatations are applied when the MeetingConfig is edited."""
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group']):
            return
        self.changeUser('siteadmin')
        self.assertFalse('return_to_proposing_group' in cfg.getWorkflowAdaptations())
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertFalse('returned_to_proposing_group' in itemWF.states)
        # activate
        self._activate_wfas(('return_to_proposing_group', ))
        cfg.at_post_edit_script()
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in itemWF.states)

    def test_pm_WFA_mayBeRemovedOnMeetingConfigEdit(self):
        """If a WFAdaptation is unselected in a MeetingConfig, the workflow
           will not integrate it anymore.  Try with 'return_to_proposing_group'."""
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group']):
            return
        self.changeUser('siteadmin')
        self.assertFalse('return_to_proposing_group' in cfg.getWorkflowAdaptations())
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertFalse('returned_to_proposing_group' in itemWF.states)
        # activate
        self._activate_wfas(('return_to_proposing_group', ))
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in itemWF.states)
        # deactivate
        self._activate_wfas(())
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertFalse('returned_to_proposing_group' in itemWF.states)

    def test_pm_WFA_mayBeAppliedAsMeetingManager(self):
        """When a MeetingManager edit the MeetingConfig, WFAdaptations are applied when the
           MeetingConfig is saved."""
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group']):
            return
        self.changeUser('pmManager')
        # activate
        self._activate_wfas(('return_to_proposing_group', ))
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue('returned_to_proposing_group' in itemWF.states)

    def test_pm_WFA_sameWorkflowForSeveralMeetingConfigs(self):
        """As the real WF used for item/meeting of a MeetingConfig are duplicated ones,
           the original workflow may be used for several MeetingConfigs.  Use same WF for cfg and cfg2
           and activate a WFAdaptation for cfg, check that it does not change cfg2."""
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group']):
            return
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        # use same WF
        cfg2.setItemWorkflow(cfg.getItemWorkflow())
        cfg2.setMeetingWorkflow(cfg.getMeetingWorkflow())
        cfg2.at_post_edit_script()
        self.assertEqual(cfg.getItemWorkflow(), cfg2.getItemWorkflow())
        self.assertEqual(cfg.getMeetingWorkflow(), cfg2.getMeetingWorkflow())
        # apply the 'return_to_proposing_group' WFAdaptation for cfg
        # activate
        self._activate_wfas(('return_to_proposing_group', ))
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

        # return_to_proposing_group_... alone is ok
        self.failIf(cfg.validate_workflowAdaptations(
            ('return_to_proposing_group',)))
        self.failIf(cfg.validate_workflowAdaptations(
            ('return_to_proposing_group_with_last_validation',)))
        self.failIf(cfg.validate_workflowAdaptations(
            ('return_to_proposing_group_with_all_validations',)))
        # Only one return_to_proposing_group can be selectable
        self.assertEqual(
            cfg.validate_workflowAdaptations(
                ('return_to_proposing_group_with_last_validation',
                 'return_to_proposing_group')),
            wa_conflicts)
        self.assertEqual(
            cfg.validate_workflowAdaptations(
                ('return_to_proposing_group_with_last_validation',
                 'return_to_proposing_group_with_all_validations')),
            wa_conflicts)
        self.assertEqual(
            cfg.validate_workflowAdaptations(
                ('return_to_proposing_group_with_all_validations',
                 'return_to_proposing_group')),
            wa_conflicts)

        # removed and removed_and_duplicated may not be used together
        self.failIf(cfg.validate_workflowAdaptations(('removed',)))
        self.failIf(cfg.validate_workflowAdaptations(('removed_and_duplicated',)))
        self.assertEqual(
            cfg.validate_workflowAdaptations(('removed',
                                              'removed_and_duplicated')), wa_conflicts)

        # accepted_out_of_meeting and accepted_out_of_meeting_and_duplicated
        # may not be used together
        self.failIf(cfg.validate_workflowAdaptations(
            ('accepted_out_of_meeting',)))
        self.failIf(cfg.validate_workflowAdaptations(
            ('accepted_out_of_meeting_and_duplicated',)))
        self.assertEqual(
            cfg.validate_workflowAdaptations(
                ('accepted_out_of_meeting',
                 'accepted_out_of_meeting_and_duplicated')), wa_conflicts)

        # accepted_out_of_meeting_emergency and
        # accepted_out_of_meeting_emergency_and_duplicated may not be used together
        self.failIf(cfg.validate_workflowAdaptations(
            ('accepted_out_of_meeting_emergency',)))
        self.failIf(cfg.validate_workflowAdaptations(
            ('accepted_out_of_meeting_emergency_and_duplicated',)))
        self.assertEqual(
            cfg.validate_workflowAdaptations(
                ('accepted_out_of_meeting_emergency',
                 'accepted_out_of_meeting_emergency_and_duplicated')),
            wa_conflicts)

    def test_pm_Validate_workflowAdaptations_item_validation_levels_dependency(self):
        """Test MeetingConfig.validate_workflowAdaptations where some wfAdaptations
           depend on MeetingConfig.itemWFValidationLevels (that must be activated)."""
        wa_dependency = translate('wa_item_validation_levels_dependency',
                                  domain='PloneMeeting',
                                  context=self.request)
        cfg = self.meetingConfig
        self.assertEqual(cfg.getItemWFValidationLevels(data='state', only_enabled=True),
                         ['itemcreated', 'proposed'])
        self.failIf(cfg.validate_workflowAdaptations(('reviewers_take_back_validated_item', )))
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation', )))
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations', )))
        self.failIf(cfg.validate_workflowAdaptations(('presented_item_back_to_itemcreated', )))

        # disable every item validation levels
        self._disableItemValidationLevel(cfg)
        self.assertEqual(
            cfg.validate_workflowAdaptations(('reviewers_take_back_validated_item', )),
            wa_dependency)
        self.assertEqual(
            cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation', )),
            wa_dependency)
        self.assertEqual(
            cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations', )),
            wa_dependency)
        self.assertEqual(
            cfg.validate_workflowAdaptations(('presented_item_back_to_itemcreated', )),
            wa_dependency)

    def test_pm_Validate_workflowAdaptations_presented_item_back_to_validation_state(self):
        """If a WFA 'presented_item_back_to_XXX' is selected,
           then MeetingConfig.itemWFValidationLevels must provides some states,
           moreover it checks too if a validation level is available,
           this could not be the case when set using import_data or
           if validation_level was just disabled."""
        wa_error = translate(
            'wa_presented_back_to_wrong_itemWFValidationLevels',
            domain='PloneMeeting', context=self.request)
        cfg = self.meetingConfig

        # itemcreated and proposed are enabled
        self.assertEqual(cfg.getItemWFValidationLevels(data='state', only_enabled=True),
                         ['itemcreated', 'proposed'])
        self.failIf(cfg.validate_workflowAdaptations(('presented_item_back_to_itemcreated', )))
        self.failIf(cfg.validate_workflowAdaptations(('presented_item_back_to_proposed', )))
        # unknown (unselected) item validation level
        self.assertEqual(
            cfg.validate_workflowAdaptations(('presented_item_back_to_unknown', )),
            wa_error)

    def test_pm_Validate_workflowAdaptations_added_no_publication(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage addition
           of wfAdaptations 'no_publication' that is not possible if some meeting
           or items are 'published'."""
        # ease override by subproducts
        if not self._check_wfa_available(['no_publication']):
            return

        # make sure no wfas activated
        self._activate_wfas([])

        no_publication_added_error = translate('wa_added_no_publication_error',
                                               domain='PloneMeeting',
                                               context=self.request)
        cfg = self.meetingConfig
        # make sure we do not have recurring items
        self.changeUser('pmManager')
        # create a meeting with an item and publish it
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.publishMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'published')
        self.assertEqual(item.query_state(), 'itempublished')
        self.assertEqual(
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
        self.assertEqual(newItem.query_state(),
                         'itempublished')
        self.assertEqual(
            cfg.validate_workflowAdaptations(('no_publication', )),
            no_publication_added_error)
        self.portal.restrictedTraverse('@@delete_givenuid')(newItem.UID())
        self.failIf(cfg.validate_workflowAdaptations(('no_publication', )))

    def test_pm_Validate_workflowAdaptations_removed_postpone_next_meeting(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'postpone_next_meeting' that is not possible if
           some items are 'postponed_next_meeting'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['postpone_next_meeting']):
            return

        postpone_removed_error = translate('wa_removed_postpone_next_meeting_error',
                                           domain='PloneMeeting',
                                           context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas(('postpone_next_meeting', ))

        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        self.assertEqual(item.query_state(), 'postponed_next_meeting')
        self.failIf(cfg.validate_workflowAdaptations(('postpone_next_meeting', )))
        self.assertEqual(
            cfg.validate_workflowAdaptations(()),
            postpone_removed_error)

        # make wfAdaptation selectable
        self.do(item, 'backToItemPublished')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def _validate_item_decision_state_removed(self, wf_adaptation_name, item_state, item_transition):
        """Helper method checking that removing an item decision state is not
           possible if some items still in this state."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if wf_adaptation_name not in cfg.listWorkflowAdaptations():
            return

        msg_removed_error = translate(
            'wa_removed_{0}_error'.format(wf_adaptation_name),
            domain='PloneMeeting',
            context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas((wf_adaptation_name, ))

        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, item_transition)
        self.assertEqual(item.query_state(), item_state)
        self.failIf(cfg.validate_workflowAdaptations((wf_adaptation_name, )))
        self.assertEqual(
            cfg.validate_workflowAdaptations(()),
            msg_removed_error)

        # make wfAdaptation selectable
        self.do(item, 'backToItemPublished')
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_mark_not_applicable(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'mark_not_applicable' that is not possible if
           some items are 'marked_not_applicable'."""

        self._validate_item_decision_state_removed(
            wf_adaptation_name='mark_not_applicable',
            item_state='marked_not_applicable',
            item_transition='mark_not_applicable')

    def test_pm_Validate_workflowAdaptations_removed_removed(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'removed' or 'removed_and_duplicated' that is not possible if
           some items are 'removed'."""

        # refused is a default WFAdaptation, do not _performWorkflowAdaptations again
        self._validate_item_decision_state_removed(
            wf_adaptation_name='removed',
            item_state='removed',
            item_transition='remove')

        cfg = self.meetingConfig
        if 'removed_and_duplicated' in cfg.listWorkflowAdaptations():
            # possible to switch from one to the other
            self.failIf(cfg.validate_workflowAdaptations(('removed_and_duplicated', )))
            cfg.setWorkflowAdaptations(('removed_and_duplicated', ))
            self.failIf(cfg.validate_workflowAdaptations(('removed', )))

    def test_pm_Validate_workflowAdaptations_removed_refused(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'refuse' that is not possible if
           some items are 'refused'."""

        self._validate_item_decision_state_removed(
            wf_adaptation_name='refused',
            item_state='refused',
            item_transition='refuse')

    def test_pm_Validate_workflowAdaptations_removed_accepted_out_of_meeting(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'accepted_out_of_meeting' or 'accepted_out_of_meeting_emergency'
           that is not possible if some items are 'accepted_out_of_meeting' or
           'accepted_out_of_meeting_emergency'."""

        def _check(wfa_name, transition, back_transition, error_msg_id):
            """ """
            msg_removed_error = translate(
                error_msg_id,
                domain='PloneMeeting',
                context=self.request)
            self.changeUser('pmManager')
            self._activate_wfas((wfa_name, ))

            item = self.create('MeetingItem')
            self.validateItem(item)
            self.failIf(cfg.validate_workflowAdaptations((wfa_name, )))
            # do transition available
            if wfa_name.startswith('accepted_out_of_meeting_emergency'):
                item.setEmergency('emergency_accepted')
            else:
                # accepted_out_of_meeting/accepted_out_of_meeting_and_duplicated
                item.setIsAcceptableOutOfMeeting(True)
            self.do(item, transition)
            self.assertEqual(
                cfg.validate_workflowAdaptations(()),
                msg_removed_error)

            self.do(item, back_transition)
            self.failIf(cfg.validate_workflowAdaptations(()))

        # ease override by subproducts
        cfg = self.meetingConfig
        if 'accepted_out_of_meeting' in cfg.listWorkflowAdaptations():
            _check(wfa_name='accepted_out_of_meeting',
                   transition='accept_out_of_meeting',
                   back_transition='backToValidatedFromAcceptedOutOfMeeting',
                   error_msg_id='wa_removed_accepted_out_of_meeting_error')
        if 'accepted_out_of_meeting_and_duplicated' in cfg.listWorkflowAdaptations():
            _check(wfa_name='accepted_out_of_meeting_and_duplicated',
                   transition='accept_out_of_meeting',
                   back_transition='backToValidatedFromAcceptedOutOfMeeting',
                   error_msg_id='wa_removed_accepted_out_of_meeting_error')
        if 'accepted_out_of_meeting_emergency' in cfg.listWorkflowAdaptations():
            _check(wfa_name='accepted_out_of_meeting_emergency',
                   transition='accept_out_of_meeting_emergency',
                   back_transition='backToValidatedFromAcceptedOutOfMeetingEmergency',
                   error_msg_id='wa_removed_accepted_out_of_meeting_emergency_error')
        if 'accepted_out_of_meeting_emergency_and_duplicated' in cfg.listWorkflowAdaptations():
            _check(wfa_name='accepted_out_of_meeting_emergency_and_duplicated',
                   transition='accept_out_of_meeting_emergency',
                   back_transition='backToValidatedFromAcceptedOutOfMeetingEmergency',
                   error_msg_id='wa_removed_accepted_out_of_meeting_emergency_error')

    def test_pm_Validate_workflowAdaptations_removed_waiting_advices(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'waiting_advices' that is not possible if some items are
           'waiting_advices'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['waiting_advices']):
            return

        waiting_advices_proposed_state = '{0}_waiting_advices'.format(
            self._stateMappingFor('proposed'))
        self.vendors.item_advice_states = ("{0}__state__{1}".format(
            cfg.getId(), waiting_advices_proposed_state),)
        # clean MeetingConfig.getItemAdviceStatesForOrg
        notify(ObjectModifiedEvent(self.vendors))

        waiting_advices_removed_error = translate('wa_removed_waiting_advices_error',
                                                  domain='PloneMeeting',
                                                  context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas(('waiting_advices', 'waiting_advices_proposing_group_send_back'))

        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        self.proposeItem(item)
        proposedState = item.query_state()
        self._setItemToWaitingAdvices(item,
                                      'wait_advices_from_{0}'.format(proposedState))
        self.assertEqual(item.query_state(),
                         '{0}_waiting_advices'.format(proposedState))
        self.failIf(cfg.validate_workflowAdaptations(
            ('waiting_advices', 'waiting_advices_proposing_group_send_back')))
        self.assertEqual(
            cfg.validate_workflowAdaptations(()),
            waiting_advices_removed_error)

        # make wfAdaptation selectable
        self.changeUser(self._userAbleToBackFromWaitingAdvices(item.query_state()))
        self.do(item, 'backTo_{0}_from_waiting_advices'.format(proposedState))
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_Validate_workflowAdaptations_removed_return_to_proposing_group(self):
        """Test MeetingConfig.validate_workflowAdaptations that manage removal
           of wfAdaptations 'return_to_proposing_group' that is not possible if
           some items are 'returned_to_proposing_group'."""
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['return_to_proposing_group']):
            return

        return_to_proposing_group_removed_error = translate('wa_removed_return_to_proposing_group_error',
                                                            domain='PloneMeeting',
                                                            context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas(('return_to_proposing_group', ))

        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        self.assertEqual(item.query_state(), 'returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group', )))
        if 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        if 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        self.assertEqual(
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
        if not self._check_wfa_available(['return_to_proposing_group_with_last_validation']):
            return

        return_to_proposing_group_removed_error = translate(
            'wa_removed_return_to_proposing_group_with_last_validation_error',
            domain='PloneMeeting',
            context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas(('return_to_proposing_group_with_last_validation', ))

        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        self.assertEqual(item.query_state(), 'returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group', )))
        if 'return_to_proposing_group_with_all_validations' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        self.assertEqual(item.query_state(), 'returned_to_proposing_group_proposed')
        self.assertEqual(
            cfg.validate_workflowAdaptations(()),
            return_to_proposing_group_removed_error)
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.assertEqual(
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
        if not self._check_wfa_available(['return_to_proposing_group_with_all_validations']):
            return

        return_to_proposing_group_removed_error = translate(
            'wa_removed_return_to_proposing_group_with_all_validations_error',
            domain='PloneMeeting',
            context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas(('return_to_proposing_group_with_all_validations', ))

        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.do(item, 'return_to_proposing_group')
        self.assertEqual(item.query_state(), 'returned_to_proposing_group')
        self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_all_validations',)))
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group', )))

        if 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            self.failIf(cfg.validate_workflowAdaptations(('return_to_proposing_group_with_last_validation',)))
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        self.assertEqual(item.query_state(), 'returned_to_proposing_group_proposed')
        self.assertEqual(
            cfg.validate_workflowAdaptations(()),
            return_to_proposing_group_removed_error)
        if 'return_to_proposing_group' in cfg.listWorkflowAdaptations():
            self.assertEqual(
                cfg.validate_workflowAdaptations(('return_to_proposing_group', )),
                return_to_proposing_group_removed_error)
        if 'return_to_proposing_group_with_last_validation' in cfg.listWorkflowAdaptations():
            self.assertEqual(
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
        if not self._check_wfa_available(['hide_decisions_when_under_writing']):
            return

        hide_decisions_when_under_writing_removed_error = \
            translate('wa_removed_hide_decisions_when_under_writing_error',
                      domain='PloneMeeting',
                      context=self.request)
        self.changeUser('pmManager')
        self._activate_wfas(('hide_decisions_when_under_writing', ))

        meeting = self.create('Meeting')
        self.decideMeeting(meeting)
        self.do(meeting, 'publish_decisions')
        self.failIf(cfg.validate_workflowAdaptations(('hide_decisions_when_under_writing', )))
        self.assertEqual(
            cfg.validate_workflowAdaptations(()),
            hide_decisions_when_under_writing_removed_error)

        # make wfAdaptation selectable
        self.closeMeeting(meeting)
        self.failIf(cfg.validate_workflowAdaptations(()))

    def test_pm_WFA_no_publication(self):
        '''Test the workflowAdaptation 'no_publication'.
           This test check the removal of the 'published' state in the meeting/item WF.'''
        # ease override by subproducts
        if not self._check_wfa_available(['no_publication']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._activate_wfas([])
        self._no_publication_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('no_publication', ))
        self._no_publication_active()

    def _no_publication_inactive(self):
        '''Tests while 'no_publication' wfAdaptation is inactive.'''
        meeting = self._createMeetingWithItems()
        item = meeting.get_items()[0]
        self.publishMeeting(meeting)
        self.assertEqual(item.query_state(), 'itempublished')
        # item decided states point back to itempublished
        cfg = self.meetingConfig
        itemWF = cfg.getItemWorkflow(True)
        for state in itemWF.states.values():
            if state in self.meetingConfig.getItemDecidedStates():
                self.assertTrue('backToItemPublished' in state.transitions)

    def _no_publication_active(self):
        '''Tests while 'no_publication' wfAdaptation is active.'''
        m1 = self._createMeetingWithItems()
        self.failIf('publish' in self.transitions(m1))
        for item in m1.get_items():
            item.setDecision('<p>My decision<p>')
        for tr in self._getTransitionsToCloseAMeeting():
            if tr in self.transitions(m1):
                lastTriggeredTransition = tr
                self.do(m1, tr)
                self.failIf('publish' in self.transitions(m1))
                self.failIf('backToPublished' in self.transitions(m1))
        # check that we are able to reach the end of the wf process
        self.assertEqual(lastTriggeredTransition, self._getTransitionsToCloseAMeeting()[-1])
        # check that every item decided states now point back to itemfrozen
        # item decided states point back to itempublished
        cfg = self.meetingConfig
        itemWF = cfg.getItemWorkflow(True)
        for state in itemWF.states.values():
            if state in self.meetingConfig.getItemDecidedStates():
                self.assertTrue('backToItemFrozen' in state.transitions)
        # meeting transitions, check the freeze/backToFrozen transitions
        meetingWF = cfg.getMeetingWorkflow(True)
        self.assertEqual(meetingWF.transitions['freeze'].new_state_id, 'frozen')
        self.assertEqual(meetingWF.transitions['freeze'].guard.expr.text,
                         'python:here.wfConditions().mayFreeze()')
        self.assertEqual(meetingWF.transitions['backToFrozen'].new_state_id, 'frozen')
        self.assertEqual(meetingWF.transitions['backToFrozen'].guard.expr.text,
                         "python:here.wfConditions().mayCorrect('frozen')")

    def test_pm_WFA_no_publication_and_pre_accepted(self):
        '''Test the workflowAdaptation 'no_publication/pre_accepted' togheter.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['no_publication', 'pre_accepted']):
            return
        self.changeUser('pmManager')
        self._activate_wfas(('pre_accepted', 'no_publication', ))
        cfg = self.meetingConfig
        itemWF = cfg.getItemWorkflow(True)
        self.assertTrue('accept' in itemWF.states['pre_accepted'].transitions)
        self.assertTrue('backToItemFrozen' in itemWF.states['pre_accepted'].transitions)

    def test_pm_WFA_pre_validation(self):
        '''Test when using prevalidation.
           Check the addition of a 'prevalidated' state in the item WF.'''
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._pre_validation_inactive()
        # activate the wfAdaptation and check
        self._enablePrevalidation(self.meetingConfig)
        # define pmManager as a prereviewer
        self._turnUserIntoPrereviewer(self.member)
        self._pre_validation_active(self.member.getId())

    def _pre_validation_inactive(self):
        '''Test when prevalidation is inactive.'''
        i1 = self.create('MeetingItem')
        # by default a 'propose' transition exists
        self.do(i1, 'propose')
        self.failIf('prevalidate' in self.transitions(i1))
        self.do(i1, 'validate')

    def _pre_validation_active(self, username):
        '''Test when prevalidation is active.'''
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

    def test_pm_WFA_only_creator_may_delete(self):
        '''Test the workflowAdaptation 'only_creator_may_delete'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['only_creator_may_delete']):
            return
        # check while the wfAdaptation is not activated
        self._only_creator_may_delete_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('only_creator_may_delete', ))
        self._only_creator_may_delete_active()

    def _only_creator_may_delete_inactive(self):
        '''Tests while 'only_creator_may_delete' wfAdaptation is inactive.
           Other roles than 'MeetingMember' have the 'Delete objects' permission in different states.'''
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        self.assertEqual(item.query_state(), 'itemcreated')
        # creator can delete
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
        self.assertEqual(item.query_state(), 'itemcreated')
        # creator can delete
        self.failUnless(self.hasPermission(DeleteObjects, item))
        self.proposeItem(item)
        self.failIf(self.hasPermission(DeleteObjects, item))
        self.changeUser('pmReviewer2')
        # the Reviewer can NOT delete
        self.failIf(self.hasPermission(DeleteObjects, item))
        self.validateItem(item)
        self.failIf(self.hasPermission(DeleteObjects, item))
        self.changeUser('pmManager')
        # the MeetingManager can NOT delete
        self.failIf(self.hasPermission(DeleteObjects, item))
        # God can delete too...
        self.changeUser('admin')
        self.failUnless(self.hasPermission(DeleteObjects, item))

    def test_pm_WFA_return_to_proposing_group(self):
        '''Test the workflowAdaptation 'return_to_proposing_group'.'''
        for cfg in (self.meetingConfig, self.meetingConfig2):
            self.setMeetingConfig(cfg.getId())
            # ease override by subproducts
            if not self._check_wfa_available(['return_to_proposing_group']):
                return
            # check while the wfAdaptation is not activated
            self._return_to_proposing_group_inactive()
            # activate the wfAdaptation and check
            self._activate_wfas(('return_to_proposing_group', ))
            # test what should happen to the wf (added states and transitions)
            self._return_to_proposing_group_active()
            # test the functionnality of returning an item to the proposing group
            self._return_to_proposing_group_active_wf_functionality()
            # disable WFA so test with cfg2 while inactive works
            self._activate_wfas(())

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
        meeting = self.create('Meeting')
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
        self.assertEqual(item.query_state(), 'presented')
        # send the item back to proposing group, freeze the meeting then send the item back to the meeting
        # the item should be now in the item state corresponding to the meeting frozen state, so 'itemfrozen'
        self.do(item, 'return_to_proposing_group')
        self.freezeMeeting(meeting)
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.assertEqual(item.query_state(), 'itemfrozen')

    def test_pm_WFA_return_to_proposing_group_with_last_validation(self):
        '''Test the workflowAdaptation 'return_to_proposing_group_with_last_validation'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group_with_last_validation']):
            return
        # activate the wfAdaptation and check
        self._activate_wfas(('return_to_proposing_group_with_last_validation', ))
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

    def _return_to_proposing_group_with_validation_active_wf_functionality(self):
        '''Tests the workflow functionality of using the
           'return_to_proposing_group_with_last_validation' wfAdaptation.'''
        # while it is active, the creators of the item can edit the item as well as the MeetingManagers
        # after, he must be send to reviewer the item
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.validateItem(item)
        # create a Meeting and add the item to it
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
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
        self.assertEqual(item.query_state(), 'presented')
        # send the item back to proposing group, freeze the meeting then send the item back to the meeting
        # the item should be now in the item state corresponding to the meeting frozen state, so 'itemfrozen'
        self.do(item, 'return_to_proposing_group')
        self.do(item, 'goTo_returned_to_proposing_group_proposed')
        self.freezeMeeting(meeting)
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')
        self.assertEqual(item.query_state(), 'itemfrozen')

    def test_pm_WFA_return_to_proposing_group_with_all_validations(self):
        '''Test the workflowAdaptation 'return_to_proposing_group_with_all_validations'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group_with_all_validations']):
            return
        # activate the wfAdaptation and check
        self._activate_wfas(('return_to_proposing_group_with_all_validations', ))
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
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['hide_decisions_when_under_writing']):
            return
        self.changeUser('admin')
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._hide_decisions_when_under_writing_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('hide_decisions_when_under_writing', ))
        self._hide_decisions_when_under_writing_active()
        # test also for the meetingConfig2 if it uses a different workflow
        if cfg.getMeetingWorkflow() == self.meetingConfig2.getMeetingWorkflow():
            return
        self.meetingConfig = self.meetingConfig2
        self._hide_decisions_when_under_writing_inactive()
        self._activate_wfas(('hide_decisions_when_under_writing', ))
        # check while the wfAdaptation is not activated
        self._hide_decisions_when_under_writing_active()

    def _hide_decisions_when_under_writing_inactive(self):
        '''Tests while 'hide_decisions_when_under_writing' wfAdaptation is inactive.
           In this case, the decision is always accessible by the creator no matter it is
           adapted by any MeetingManagers.  There is NO extra 'decisions_published' state moreover.'''
        meetingWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getMeetingTypeName())[0]
        self.failIf('decisions_published' in meetingWF.states)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setMotivation('<p>testing motivation field</p>')
        item.setDecision('<p>testing decision field</p>')
        self.presentItem(item)
        self.changeUser('pmCreator1')
        # relevant users can see the decision
        self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        self.changeUser('pmManager')
        self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        self.freezeMeeting(meeting)
        self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        # maybe we have a 'publish' transition
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
            self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
            self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        self.decideMeeting(meeting)
        # set a decision...
        item.setMotivation('<p>Motivation adapted by pmManager</p>')
        item.setDecision('<p>Decision adapted by pmManager</p>')
        item.reindexObject()
        # it is immediatelly viewable by the item's creator as
        # the 'hide_decisions_when_under_writing' wfAdaptation is not enabled
        self.changeUser('pmCreator1')
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        self.changeUser('pmManager')
        self.closeMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'closed')
        self.changeUser('pmCreator1')
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')

    def _hide_decisions_when_under_writing_active(self):
        '''Tests while 'hide_decisions_when_under_writing' wfAdaptation is active.'''
        meetingWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getMeetingTypeName())[0]
        self.failUnless('decisions_published' in meetingWF.states)
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setMotivation('<p>testing motivation field</p>')
        item.setDecision('<p>testing decision field</p>')
        self.presentItem(item)
        self.changeUser('pmCreator1')
        # relevant users can see the decision
        self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        self.changeUser('pmManager')
        self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        self.freezeMeeting(meeting)
        self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
        self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        # maybe we have a 'publish' transition
        if 'publish' in self.transitions(meeting):
            self.do(meeting, 'publish')
            self.assertEqual(item.getMotivation(), '<p>testing motivation field</p>')
            self.assertEqual(item.getDecision(), '<p>testing decision field</p>')
        self.decideMeeting(meeting)
        # set a decision...
        item.setMotivation('<p>Motivation adapted by pmManager</p>')
        item.setDecision('<p>Decision adapted by pmManager</p>')
        # getDecision must return 'utf-8' encoded string, make sure it is
        item.reindexObject()
        self.assertTrue(isinstance(item.getDecision(), basestring))
        self.assertFalse(isinstance(item.getDecision(), unicode))
        self.changeUser('pmCreator1')
        self.assertEqual(meeting.query_state(), 'decided')
        self.assertEqual(item.getMotivation(),
                         HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEqual(item.getDecision(),
                         HIDE_DECISION_UNDER_WRITING_MSG)
        # getDecision must return 'utf-8' encoded string, make sure it is
        self.assertTrue(isinstance(item.getDecision(), basestring))
        self.assertFalse(isinstance(item.getDecision(), unicode))

        # special test, remove an annex, it is done as 'all_powerful_Oz' user
        # and broke when checking has_permission in MeetingItem._mayNotViewDecisionMsg
        self.changeUser('siteadmin')
        annex = self.addAnnex(item)
        self.deleteAsManager(annex.UID())

        # MeetingManagers see it correctly
        self.changeUser('pmManager')
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        # make sure decision is visible or not when item is decided and so no more editable by anyone
        self.do(item, 'accept')
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertEqual(item.getMotivation(),
                         HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEqual(item.getDecision(),
                         HIDE_DECISION_UNDER_WRITING_MSG)
        # a 'publish_decisions' transition is added after 'decide'
        self.changeUser('pmManager')
        self.do(meeting, 'publish_decisions')
        self.assertEqual(meeting.query_state(), 'decisions_published')
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        # now that the meeting is in the 'decisions_published' state, decision is viewable to item's creator
        self.changeUser('pmCreator1')
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')
        # items are automatically set to a final specific state when decisions are published
        self.assertEqual(item.query_state(),
                         self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['publish_decisions'])
        self.changeUser('pmManager')
        # every items of the meeting are in the same final specific state
        for itemInMeeting in meeting.get_items():
            self.assertEqual(itemInMeeting.query_state(),
                             self.ITEM_WF_STATE_AFTER_MEETING_TRANSITION['publish_decisions'])
        self.do(meeting, 'close')
        self.changeUser('pmCreator1')
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')

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
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['return_to_proposing_group',
                                          'hide_decisions_when_under_writing']):
            return
        self.changeUser('admin')
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        self._activate_wfas(('hide_decisions_when_under_writing',
                             'return_to_proposing_group', ))

        # if one of the user of the proposingGroup may edit the decision, then
        # every members of the proposingGroup may see the decision, this way, if MeetingMember
        # may edit the decision, then a MeetingObserverLocal may see it also evern if he may not edit it
        meeting = self.create('Meeting')
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
        self.assertEqual(meeting.query_state(), 'decided')
        self.assertEqual(item.getMotivation(),
                         HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEqual(item.getDecision(),
                         HIDE_DECISION_UNDER_WRITING_MSG)

        # return the item to the proposingGroup
        self.changeUser('pmManager')
        self.do(item, 'return_to_proposing_group')
        # now the decision is viewable by the 'pmCreator1' as he may edit it
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertEqual(item.getMotivation(), '<p>Motivation adapted by pmManager</p>')
        self.assertEqual(item.getDecision(), '<p>Decision adapted by pmManager</p>')

        # but another user that may see the item but not edit it may not see the decision
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates((item.query_state(), ))
        item.setCopyGroups((self.vendors_reviewers, ))
        item.update_local_roles()
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertEqual(item.getMotivation(), HIDE_DECISION_UNDER_WRITING_MSG)
        self.assertEqual(item.getDecision(), HIDE_DECISION_UNDER_WRITING_MSG)

    def test_pm_WFA_decide_item_when_back_to_meeting_from_returned_to_proposing_group(self):
        cfg = self.meetingConfig
        if not self._check_wfa_available(
                ['decide_item_when_back_to_meeting_from_returned_to_proposing_group']):
            return

        self.changeUser('admin')
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        self._activate_wfas(
            ('accepted_but_modified',
             'return_to_proposing_group',
             'decide_item_when_back_to_meeting_from_returned_to_proposing_group', ))

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision adapted by pmManager</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)

        self.do(item, 'return_to_proposing_group')

        self.changeUser('pmCreator1')
        self.do(item, 'backTo_itemfrozen_from_returned_to_proposing_group')

        # Ensure the item is not simply frozen at this point
        # and ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION was applied automatically
        from Products.PloneMeeting.config import ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION
        wfTool = api.portal.get_tool('portal_workflow')
        itemWorkflow = wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertTrue(ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION in itemWorkflow.transitions,
                        "%s not in item workflow" % ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION)
        transition = itemWorkflow.transitions[ITEM_TRANSITION_WHEN_RETURNED_FROM_PROPOSING_GROUP_AFTER_CORRECTION]
        self.assertEqual(transition.new_state_id, item.query_state())

    def test_pm_WFA_waiting_advices(self):
        '''Test the workflowAdaptation 'waiting_advices'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices']):
            return

        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._activate_wfas(())
        self._waiting_advices_inactive()

        # activate the wfAdaptation and check
        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': (self._stateMappingFor('proposed_first_level'), ),
             'back_states': (self._stateMappingFor('proposed_first_level'), ),
             'perm_cloned_states': (self._stateMappingFor('proposed_first_level'), ),
             'remove_modify_access': True,
             'use_custom_icon': False,
             'use_custom_back_transition_title_for': (),
             'use_custom_state_title': True, },)
        self._activate_wfas(
            ('waiting_advices', 'waiting_advices_proposing_group_send_back'),
            keep_existing=True)
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
        waiting_state_name = '{0}_waiting_advices'.format(self._stateMappingFor('proposed_first_level'))
        waiting_transition_name = 'wait_advices_from_{0}'.format(self._stateMappingFor('proposed_first_level'))
        self.assertTrue(waiting_state_name in itemWF.states)

        # the budget impact editors functionnality still works even if 'remove_modify_access': True
        cfg.setItemBudgetInfosStates((waiting_state_name, ))

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
        proposed_state = self._stateMappingFor('proposed_first_level')
        self.assertEqual(translate(item.wfConditions().mayWait_advices_from(proposed_state).msg,
                                   context=self.request),
                         advice_required_to_ask_advices)
        # ask an advice so transition is available
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        # still not available because no advice may be asked in state waiting_state_name
        self.assertFalse(waiting_state_name in self.vendors.item_advice_states)
        self.assertFalse(waiting_transition_name in self.transitions(item))

        # do things work
        self.vendors.item_advice_states = ("{0}__state__{1}".format(
            cfg.getId(), waiting_state_name), )
        # clean MeetingConfig.getItemAdviceStatesForOrg
        notify(ObjectModifiedEvent(self.vendors))

        self.assertTrue(waiting_transition_name in self.transitions(item))
        self._setItemToWaitingAdvices(item, waiting_transition_name)
        self.assertEqual(item.query_state(), waiting_state_name)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))

        # pmCreator1 may view but not edit
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertFalse(self.transitions(item))

        # budget impact editors access are correct even when 'remove_modify_access': True
        self.changeUser('budgetimpacteditor')
        self.assertTrue(self.hasPermission(WriteBudgetInfos, item))

        # right come back to 'proposed'
        self.changeUser('pmReviewer1')
        self.do(item, 'backTo_%s_from_waiting_advices' % self._stateMappingFor('proposed_first_level'))
        self.assertEqual(item.query_state(), self._stateMappingFor('proposed_first_level'))

    def test_pm_WFA_waiting_advices_with_prevalidation(self):
        '''It can also work from several states, if pre_validation is enabled
           it is possible to go from 'proposed' and 'prevalidated' to 'waiting_advices'
           and to go back to both states.'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_proposing_group_send_back']):
            return

        self._enablePrevalidation(cfg)
        self._activate_wfas(
            ['waiting_advices', 'waiting_advices_proposing_group_send_back'],
            keep_existing=True)
        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': (self._stateMappingFor('proposed_first_level'),
                             'prevalidated', ),
             'back_states': (self._stateMappingFor('proposed_first_level'),
                             'prevalidated', ), }, )
        waiting_advices_state = '{0}__or__prevalidated_waiting_advices'.format(
            self._stateMappingFor('proposed_first_level'))
        self.vendors.item_advice_states = ("{0}__state__{1}".format(cfg.getId(), waiting_advices_state), )
        # clean MeetingConfig.getItemAdviceStatesForOrg
        notify(ObjectModifiedEvent(self.vendors))

        # by default it is linked to the 'proposed' state
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        self.assertTrue(waiting_advices_state in itemWF.states)

        # suffixed transitions are not added
        self.assertFalse('%s_waiting_advices' % self._stateMappingFor('proposed_first_level')
                         in itemWF.states)
        self.assertFalse('prevalidated_waiting_advices' in itemWF.states)
        # transitions are created
        wait_advices_from_proposed_transition = 'wait_advices_from_%s' % \
            self._stateMappingFor('proposed_first_level')
        self.assertTrue(wait_advices_from_proposed_transition in itemWF.transitions)
        self.assertTrue('wait_advices_from_prevalidated' in itemWF.transitions)
        # back transitions are created
        self.assertTrue('backTo_%s_from_waiting_advices' % self._stateMappingFor('proposed_first_level')
                        in itemWF.transitions)
        self.assertTrue('backTo_prevalidated_from_waiting_advices' in itemWF.transitions)

        # right, create an item and set it to 'proposed__or__prevalidated_waiting_advices'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        self._afterItemCreatedWaitingAdviceWithPrevalidation(item)
        self.proposeItem(item, first_level=True)
        # 'pmCreator1' is not able to set item to 'waiting_advices'
        self.assertFalse(self.transitions(item))
        # 'pmReviewerLevel1' may do it, it is a prereviewer
        self.changeUser('pmReviewerLevel1')
        self.assertTrue(wait_advices_from_proposed_transition in self.transitions(item))
        # trigger from 'prevalidated'
        self.do(item, 'prevalidate')
        self.assertEqual(item.query_state(), 'prevalidated')
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
        self.assertEqual(item.query_state(), 'prevalidated')
        self.do(item, 'wait_advices_from_prevalidated')
        self.do(item, 'backTo_prevalidated_from_waiting_advices')
        self.assertEqual(item.query_state(), 'prevalidated')

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def test_pm_WFA_waiting_advices_several_states(self):
        '''Test the workflowAdaptation 'waiting_advices'.
           By default WAITING_ADVICES_FROM_STATES is going from proposed/prevaliated
           to one single state then back.  But we can go to several states, here got to 2 different
           states from 'itemcreated' and 'proposed.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices']):
            return

        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = (
            {'from_states': ('itemcreated', ),
             'back_states': ('itemcreated', ),
             'perm_cloned_states': ('itemcreated', ),
             'remove_modify_access': True,
             'use_custom_icon': False,
             'use_custom_back_transition_title_for': (),
             'use_custom_state_title': True, },
            {'from_states': (self._stateMappingFor('proposed'), ),
             'back_states': (self._stateMappingFor('proposed'), ),
             'perm_cloned_states': (self._stateMappingFor('proposed'), ),
             'remove_modify_access': True,
             'use_custom_icon': False,
             'use_custom_back_transition_title_for': (),
             'use_custom_state_title': True, },)
        self._activate_wfas(
            ('waiting_advices', 'waiting_advices_proposing_group_send_back'), keep_existing=True)
        waiting_advices_itemcreated_state = 'itemcreated_waiting_advices'
        waiting_advices_proposed_state = '{0}_waiting_advices'.format(self._stateMappingFor('proposed'))
        self.vendors.item_advice_states = (
            "{0}__state__{1}".format(cfg.getId(), waiting_advices_itemcreated_state),
            "{0}__state__{1}".format(cfg.getId(), waiting_advices_proposed_state),)
        # clean MeetingConfig.getItemAdviceStatesForOrg
        notify(ObjectModifiedEvent(self.vendors))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        # from 'itemcreated'
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(item.query_state(), 'itemcreated_waiting_advices')
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.do(item, 'backTo_itemcreated_from_waiting_advices')
        self.assertEqual(item.query_state(), 'itemcreated')

        # from proposed
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self._setItemToWaitingAdvices(item,
                                      'wait_advices_from_%s' % self._stateMappingFor('proposed'))
        self.assertEqual(item.query_state(), '%s_waiting_advices' % self._stateMappingFor('proposed'))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        # 'pmCreator1' may view, not edit
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertFalse(self.transitions(item))
        self.changeUser(self._userAbleToBackFromWaitingAdvices(item.query_state()))
        self.do(item, 'backTo_%s_from_waiting_advices' % self._stateMappingFor('proposed'))
        self.assertEqual(item.query_state(), self._stateMappingFor('proposed'))

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def test_pm_WFA_waiting_advices_may_edit(self):
        '''Test the workflowAdaptation 'waiting_advices'.
           This time we set 'remove_modify_access' to False so Modify access
           is kept on the item set to 'waiting_advices'.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices']):
            return

        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_REMOVE_MODIFY_ACCESS = \
            adaptations.WAITING_ADVICES_REMOVE_MODIFY_ACCESS
        adaptations.WAITING_ADVICES_REMOVE_MODIFY_ACCESS = False
        self._activate_wfas(('waiting_advices', 'waiting_advices_proposing_group_send_back'))
        self.vendors.item_advice_states = ("{0}__state__{1}".format(
            cfg.getId(), 'itemcreated_waiting_advices'), )
        # clean MeetingConfig.getItemAdviceStatesForOrg
        notify(ObjectModifiedEvent(self.vendors))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item._update_after_edit()
        # from 'itemcreated'
        self._setItemToWaitingAdvices(item, 'wait_advices_from_itemcreated')
        self.assertEqual(item.query_state(), 'itemcreated_waiting_advices')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(DeleteObjects, item))
        self.changeUser(self._userAbleToBackFromWaitingAdvices(item.query_state()))
        self.do(item, 'backTo_itemcreated_from_waiting_advices')
        self.assertEqual(item.query_state(), 'itemcreated')

        # back to original configuration
        adaptations.WAITING_ADVICES_REMOVE_MODIFY_ACCESS = \
            original_WAITING_ADVICES_REMOVE_MODIFY_ACCESS

    def test_pm_WFA_waiting_advices_unknown_state(self):
        '''Does not fail to be activated if a from/back state does not exist.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices']):
            return

        from Products.PloneMeeting.model import adaptations
        original_WAITING_ADVICES_FROM_STATES = adaptations.WAITING_ADVICES_FROM_STATES
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES + (
            {'from_states': ('unknown', ),
             'back_states': ('unknown', ), }, )
        self._activate_wfas(('waiting_advices', 'waiting_advices_proposing_group_send_back'))
        itemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        # does not fail and existing states are taken into account
        self.assertEqual(
            sorted([st for st in itemWF.states if 'waiting_advices' in st]),
            ['itemcreated_waiting_advices', 'proposed_waiting_advices'])

        # back to original configuration
        adaptations.WAITING_ADVICES_FROM_STATES = original_WAITING_ADVICES_FROM_STATES

    def test_pm_WFA_waiting_advices_from_last_val_level(self):
        '''Set item to waiting_advices from last validation level.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_proposing_group_send_back',
                                          'waiting_advices_from_last_val_level']):
            return

        self._activate_wfas(('waiting_advices',
                             'waiting_advices_proposing_group_send_back',
                             'waiting_advices_from_last_val_level'))
        cfg.setItemAdviceStates(('itemcreated__or__proposed_waiting_advices', ))

        # make itemcreated last validation level for vendors and proposed for developers
        # select developers for suffix reviewers
        select_org_for_function(self.developers_uid, 'reviewers')
        self.assertFalse('reviewers' in get_all_suffixes(self.vendors_uid))

        # developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # itemcreated, advice not askable
        self.assertFalse([tr for tr in self.transitions(item)
                          if tr.startswith('wait_advices_from_')])
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertTrue([tr for tr in self.transitions(item)
                         if tr.startswith('wait_advices_from_')])
        # ask advice
        # only sendable back to last level
        self.do(item, 'wait_advices_from_proposed')
        self.assertEqual(self.transitions(item), ['backTo_proposed_from_waiting_advices'])

        # vendors
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # itemcreated, advice askable
        self.assertTrue([tr for tr in self.transitions(item)
                         if tr.startswith('wait_advices_from_')])
        # ask advice
        # only sendable back to last level
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(self.transitions(item), ['backTo_itemcreated_from_waiting_advices'])

    def test_pm_WFA_waiting_advices_from_before_last_val_level(self):
        '''Set item to waiting_advices from before last validation level.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_proposing_group_send_back',
                                          'waiting_advices_from_before_last_val_level']):
            return

        self._activate_wfas(('waiting_advices',
                             'waiting_advices_proposing_group_send_back',
                             'waiting_advices_from_before_last_val_level'))
        cfg.setItemAdviceStates(('itemcreated__or__proposed_waiting_advices', ))

        # make itemcreated last validation level for vendors and proposed for developers
        # select developers for suffix reviewers
        select_org_for_function(self.developers_uid, 'reviewers')
        self.assertFalse('reviewers' in get_all_suffixes(self.vendors_uid))

        # developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # itemcreated, advice is askable as before last validation level
        self.assertTrue([tr for tr in self.transitions(item)
                         if tr.startswith('wait_advices_from_')])
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        # not before last level so not possible to send
        self.assertFalse([tr for tr in self.transitions(item)
                          if tr.startswith('wait_advices_from_')])
        # ask advice
        # only sendable back to last level
        self.backToState(item, 'itemcreated')
        self.changeUser('pmCreator1')
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(self.transitions(item), ['backTo_itemcreated_from_waiting_advices'])

        # vendors, does not break when having only 'itemcreated' as validation level
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # itemcreated, advice askable
        self.assertEqual(self.transitions(item), ['validate', 'wait_advices_from_itemcreated'])
        # ask advice
        # only sendable back to last level
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(self.transitions(item), ['backTo_itemcreated_from_waiting_advices'])

    def _check_waiting_advices_from_every_levels(self, cfg):
        """Selecting WFAs
           - 'waiting_advices_from_before_last_val_level' and 'waiting_advices_from_last_val_level';
           - 'waiting_advices_from_every_val_levels'.
           gives same result in default setup with 2 levels of validation (itemcreated/proposed)"""
        cfg.setItemAdviceStates(('itemcreated__or__proposed_waiting_advices', ))

        # make itemcreated last validation level for vendors and proposed for developers
        # select developers for suffix reviewers
        select_org_for_function(self.developers_uid, 'reviewers')
        self.assertFalse('reviewers' in get_all_suffixes(self.vendors_uid))

        # developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # advice askable in both states itemcreated/proposed
        self.assertTrue([tr for tr in self.transitions(item)
                         if tr.startswith('wait_advices_from_')])
        self.proposeItem(item)
        self.changeUser('pmReviewer1')
        self.assertTrue([tr for tr in self.transitions(item)
                         if tr.startswith('wait_advices_from_')])
        # ask advice
        self.do(item, 'wait_advices_from_proposed')
        # each level able to send back to a level he is member of
        self.assertEqual(self.transitions(item), ['backTo_proposed_from_waiting_advices'])
        self.changeUser('pmCreator1')
        self.assertEqual(self.transitions(item), ['backTo_itemcreated_from_waiting_advices'])
        self._addPrincipalToGroup('pmCreator1', get_plone_group_id(self.developers_uid, 'reviewers'))
        self.assertEqual(
            self.transitions(item),
            ['backTo_itemcreated_from_waiting_advices',
             'backTo_proposed_from_waiting_advices'])

        # vendors, does not break when having only 'itemcreated' as validation level
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # itemcreated, advice askable
        self.assertEqual(self.transitions(item), ['validate', 'wait_advices_from_itemcreated'])
        # ask advice
        # only sendable back to last level
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(self.transitions(item), ['backTo_itemcreated_from_waiting_advices'])
        self.changeUser('pmReviewer2')
        self.assertEqual(self.transitions(item), [])

    def test_pm_WFA_waiting_advices_from_last_and_before_last_val_level(self):
        '''Set item to waiting_advices from last and before last validation level.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_proposing_group_send_back',
                                          'waiting_advices_from_before_last_val_level',
                                          'waiting_advices_from_last_val_level']):
            return

        self._activate_wfas(('waiting_advices',
                             'waiting_advices_proposing_group_send_back',
                             'waiting_advices_from_before_last_val_level',
                             'waiting_advices_from_last_val_level'))
        self._check_waiting_advices_from_every_levels(cfg)

    def test_pm_WFA_waiting_advices_from_every_val_levels(self):
        '''Test the 'waiting_advices_from_every_val_levels' WFAdaptation.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_proposing_group_send_back',
                                          'waiting_advices_from_every_val_levels']):
            return

        self._activate_wfas(('waiting_advices',
                             'waiting_advices_proposing_group_send_back',
                             'waiting_advices_from_every_val_levels'))
        self._check_waiting_advices_from_every_levels(cfg)

    def test_pm_WFA_waiting_advices_adviser_send_back(self):
        '''Test the 'waiting_advices_adviser_send_back' WFAdaptation.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_adviser_send_back',
                                          'waiting_advices_from_every_val_levels']):
            return

        self._activate_wfas(('waiting_advices',
                             'waiting_advices_adviser_send_back',
                             'waiting_advices_from_every_val_levels'))
        cfg.setItemAdviceStates(('itemcreated__or__proposed_waiting_advices', ))

        # developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(self.transitions(item), [])
        # adviser may send back
        self.changeUser('pmReviewer2')
        self.assertEqual(self.transitions(item),
                         ['backTo_itemcreated_from_waiting_advices',
                          'backTo_proposed_from_waiting_advices'])
        self.do(item, 'backTo_itemcreated_from_waiting_advices')
        self.assertEqual(item.query_state(), 'itemcreated')

    def test_pm_WFA_waiting_advices_adviser_may_validate(self):
        '''Test the 'waiting_advices_adviser_may_validate' WFAdaptation.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available([
                'waiting_advices',
                'waiting_advices_adviser_send_back',
                'waiting_advices_proposing_group_send_back',
                'waiting_advices_from_every_val_levels',
                'waiting_advices_adviser_may_validate']):
            return

        # back from
        self._activate_wfas(('waiting_advices',
                             'waiting_advices_adviser_send_back',
                             'waiting_advices_proposing_group_send_back',
                             'waiting_advices_from_every_val_levels',
                             'waiting_advices_adviser_may_validate'))
        cfg.setItemAdviceStates(('itemcreated__or__proposed_waiting_advices', ))

        # developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        self.do(item, 'wait_advices_from_itemcreated')
        # proposingGroup may send back
        self.assertEqual(self.transitions(item), ['backTo_itemcreated_from_waiting_advices'])
        # adviser may send back
        self.changeUser('pmReviewer2')
        self.assertEqual(self.transitions(item),
                         ['backTo_itemcreated_from_waiting_advices',
                          'backTo_proposed_from_waiting_advices',
                          'backTo_validated_from_waiting_advices'])
        self.do(item, 'backTo_validated_from_waiting_advices')
        self.assertEqual(item.query_state(), 'validated')

    def test_pm_WFA_waiting_advices_given_advices_required_to_validate(self):
        '''Test the 'waiting_advices_given_advices_required_to_validate' WFAdaptation.'''
        cfg = self.meetingConfig
        # ease override by subproducts
        if not self._check_wfa_available([
                'waiting_advices',
                'waiting_advices_adviser_send_back',
                'waiting_advices_from_last_val_level',
                'waiting_advices_given_advices_required_to_validate']):
            return

        # back from
        self._activate_wfas(('waiting_advices',
                             'waiting_advices_adviser_send_back',
                             'waiting_advices_from_last_val_level',
                             'waiting_advices_given_advices_required_to_validate'))
        cfg.setItemAdviceStates(('itemcreated__or__proposed_waiting_advices', ))

        # developers
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        self.do(item, 'propose')
        # if some advices still must be given, it is not possible to validate
        self.changeUser('pmReviewer1')
        self.assertEqual(self.transitions(item),
                         ['backToItemCreated', 'wait_advices_from_proposed'])
        self.do(item, 'wait_advices_from_proposed')
        # give advice so item may be validated
        self.changeUser('pmReviewer2')
        self.assertEqual(self.transitions(item),
                         ['backTo_proposed_from_waiting_advices'])
        self.addAdvice(item)
        self.do(item, 'backTo_proposed_from_waiting_advices')
        self.assertEqual(self.transitions(item), [])
        self.changeUser('pmReviewer1')
        self.assertEqual(self.transitions(item),
                         ['backToItemCreated', 'validate'])

    def test_pm_WFA_postpone_next_meeting(self):
        '''Test the workflowAdaptation 'postpone_next_meeting'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['postpone_next_meeting']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._postpone_next_meeting_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('postpone_next_meeting', ))
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
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        self.assertEqual(item.query_state(), 'postponed_next_meeting')
        # back transition
        self.do(item, 'backToItemPublished')

    def test_pm_WFA_postpone_next_meeting_back_transition(self):
        '''The back transition may vary if using additional WFAdaptations,
           item may back to 'itempublished', 'itemfrozen', ...'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['postpone_next_meeting']):
            return
        self.changeUser('pmManager')

        # test with only 'postpone_next_meeting' then when using
        # 'postpone_next_meeting' and 'no_publication' togheter if available
        set_of_wfAdaptations = [('postpone_next_meeting', )]
        if 'no_publication' in cfg.listWorkflowAdaptations():
            set_of_wfAdaptations.append(('no_publication', 'postpone_next_meeting'))
        for wfAdaptations in set_of_wfAdaptations:
            # activate the wfAdaptations and check
            self._activate_wfas(wfAdaptations)

            itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
            self.assertEqual(itemWF.states['postponed_next_meeting'].transitions,
                             itemWF.states['accepted'].transitions)
            # transition 'postpone_next_meeting' get out from same state as 'accepted'
            for state in itemWF.states.values():
                if 'accept' in state.transitions:
                    self.assertTrue('postpone_next_meeting' in state.transitions)
                else:
                    self.assertFalse('postpone_next_meeting' in state.transitions)

    def test_pm_WFA_postpone_next_meeting_duplicated_and_validated_advices_inherited(self):
        '''When an item is set to 'postponed_next_meeting', it is automatically duplicated
           and the duplicated item is automatically validated.
           Moreover, advices on the duplicated item are inherited from original item.'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['postpone_next_meeting']):
            return

        self.changeUser('admin')
        org1 = self.create('organization', id='org1', title='NewOrg1', acronym='N.O.1')
        org1_uid = org1.UID()
        org2 = self.create('organization', id='org2', title='NewOrg2', acronym='N.O.2')
        org2_uid = org2.UID()
        org3 = self.create('organization', id='poweradvisers', title='Power advisers', acronym='PA')
        org3_uid = org3.UID()
        self._select_organization(org1_uid)
        self._select_organization(org2_uid)
        self._select_organization(org3_uid)
        cfg.setSelectableAdvisers((self.vendors_uid, org1_uid, org2_uid, org3_uid))
        self._addPrincipalToGroup('pmAdviser1', '{0}_advisers'.format(org3_uid))
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': org2_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setPowerAdvisersGroups((org3_uid, ))
        self._setPowerObserverStates(states=('itemcreated', ))
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        cfg.setItemAdviceViewStates(('itemcreated', ))
        if 'postpone_next_meeting' not in cfg.getWorkflowAdaptations():
            self._activate_wfas(('postpone_next_meeting', ), keep_existing=True)
        cfg.at_post_edit_script()

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        item.setOptionalAdvisers((self.vendors_uid,
                                  '{0}__rowid__unique_id_123'.format(self.developers_uid),
                                  '{0}__rowid__unique_id_456'.format(org2_uid),
                                  org1_uid))
        item._update_after_edit()
        # give advices
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': org3_uid,
                                    'advice_type': u'positive',
                                    'advice_hide_during_redaction': False,
                                    'advice_comment': RichTextValue(u'My comment')})

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        # duplicated and duplicated item is validated
        clonedItem = item.get_successors()[0]
        self.assertEqual(clonedItem.get_predecessor(), item)
        self.assertEqual(clonedItem.query_state(), 'validated')
        # optional and automatic given advices were inherited
        self.assertTrue(clonedItem.adviceIsInherited(self.vendors_uid))
        self.assertTrue(clonedItem.adviceIsInherited(self.developers_uid))
        # optional and automatic advices that were not given are inherited
        # as well as the power adviser advice
        self.assertTrue(clonedItem.adviceIsInherited(org1_uid))
        self.assertTrue(clonedItem.adviceIsInherited(org2_uid))
        self.assertTrue(clonedItem.adviceIsInherited(org3_uid))

    def test_pm_WFA_postpone_next_meeting_advices_inherited(self):
        '''When an item is set to 'postponed_next_meeting', cloned item inherits from every advices.'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['postpone_next_meeting']):
            return
        self.changeUser('pmManager')
        if 'postpone_next_meeting' not in cfg.getWorkflowAdaptations():
            self._activate_wfas(('postpone_next_meeting', ), keep_existing=True)
            cfg.at_post_edit_script()

        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'postpone_next_meeting')
        # duplicated and duplicated item is validated
        clonedItem = item.get_successors()[0]
        self.assertEqual(clonedItem.get_predecessor(), item)
        self.assertEqual(clonedItem.query_state(), 'validated')

    def _check_item_decision_state(self,
                                   wf_adaptation_name,
                                   item_state,
                                   item_transition,
                                   will_be_cloned=False,
                                   additional_wf_transitions=[]):
        """Helper method to check WFA adding an item decision state."""
        # ease override by subproducts
        if not self._check_wfa_available([wf_adaptation_name]):
            return
        self.changeUser('pmManager')
        # make sure no wfas activated
        self._activate_wfas([])
        # check while the wfAdaptation is not activated
        self._item_decision_state_inactive(item_state, item_transition)
        # activate the wfAdaptation and check
        self._activate_wfas((wf_adaptation_name, ))
        self._item_decision_state_active(
            item_state, item_transition, will_be_cloned, additional_wf_transitions)

    def _item_decision_state_inactive(self, item_state, item_transition):
        """Helper method to check WFA adding an item decision state when it is inactive."""
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertFalse(item_transition in itemWF.transitions)
        self.assertFalse(item_state in itemWF.states)

    def _item_decision_state_active(self,
                                    item_state,
                                    item_transition,
                                    will_be_cloned,
                                    additional_wf_transitions):
        """Helper method to check WFA adding an item decision state when it is active."""
        itemWF = self.wfTool.getWorkflowsFor(self.meetingConfig.getItemTypeName())[0]
        self.assertTrue(item_transition in itemWF.transitions)
        self.assertTrue(item_state in itemWF.states)
        # test it
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = self.create('MeetingItem')
        item.setDecision('<p>A decision</p>')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, item_transition)
        self.assertEqual(item.query_state(), item_state)

        if not will_be_cloned:
            # no predecessor was set
            self.assertEqual(item.get_successors(the_objects=False), [])
        else:
            # item was duplicated and new item is in it's initial state
            linked_item = item.get_successors()[0]
            self.assertEqual(linked_item.query_state(), self._initial_state(linked_item))

        if additional_wf_transitions:
            for additional_wf_transition in additional_wf_transitions:
                self.do(item, additional_wf_transition)

        # back transition
        self.do(item, 'backToItemPublished')

    def test_pm_WFA_mark_not_applicable(self):
        '''Test the workflowAdaptation 'mark_not_applicable'.'''
        self._check_item_decision_state(
            wf_adaptation_name='mark_not_applicable',
            item_state='marked_not_applicable',
            item_transition='mark_not_applicable')

    def test_pm_WFA_removed(self):
        '''Test the workflowAdaptation 'removed'.'''
        self._check_item_decision_state(
            wf_adaptation_name='removed',
            item_state='removed',
            item_transition='remove')

    def test_pm_WFA_removed_and_duplicated(self):
        '''Test the workflowAdaptation 'removed_and_duplicated'.'''
        self._check_item_decision_state(
            wf_adaptation_name='removed_and_duplicated',
            item_state='removed',
            item_transition='remove',
            will_be_cloned=True)

    def test_pm_WFA_refused(self):
        '''Test the workflowAdaptation 'refused'.'''
        self._check_item_decision_state(
            wf_adaptation_name='refused',
            item_state='refused',
            item_transition='refuse')

    def test_pm_WFA_pre_accepted(self):
        '''Test the workflowAdaptation 'pre_accepted'.'''
        self._check_item_decision_state(
            wf_adaptation_name='pre_accepted',
            item_state='pre_accepted',
            item_transition='pre_accept',
            additional_wf_transitions=['accept'])

    def test_pm_WFA_reviewers_take_back_validated_item(self):
        '''Test the workflowAdaptation 'reviewers_take_back_validated_item'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['reviewers_take_back_validated_item']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._reviewers_take_back_validated_item_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('reviewers_take_back_validated_item', ))
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
        self.create('Meeting', date=datetime.now() + timedelta(days=1))
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

    def test_pm_WFA_presented_item_back_to_proposed(self):
        '''Test the workflowAdaptation 'presented_item_back_to_proposed'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['presented_item_back_to_proposed']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._presented_item_back_to_proposed_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('presented_item_back_to_proposed', ))
        self._presented_item_back_to_proposed_active()

    def _presented_item_back_to_proposed_inactive(self):
        '''Tests while 'presented_item_back_to_proposed' wfAdaptation is inactive.'''
        # present an item, presented item can not be set back to proposed
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToValidated'])

    def _presented_item_back_to_proposed_active(self):
        '''Tests while 'presented_item_back_to_proposed' wfAdaptation is active.'''
        # present an item, presented item can not be set back to proposed
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToProposed', 'backToValidated'])
        self.do(item, 'backToProposed')
        self.assertEqual(item.query_state(), 'proposed')

    def test_pm_WFA_presented_item_back_to_itemcreated(self):
        '''Test the workflowAdaptation 'presented_item_back_to_itemcreated'.'''
        # ease override by subproducts
        if not self._check_wfa_available(['presented_item_back_to_itemcreated']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._presented_item_back_to_itemcreated_inactive()
        # activate the wfAdaptation and check
        self._activate_wfas(('presented_item_back_to_itemcreated', ))
        self._presented_item_back_to_itemcreated_active()

    def _presented_item_back_to_itemcreated_inactive(self):
        '''Tests while 'presented_item_back_to_itemcreated' wfAdaptation is inactive.'''
        # present an item, presented item can not be set back to itemcreated
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToValidated'])

    def _presented_item_back_to_itemcreated_active(self):
        '''Tests while 'presented_item_back_to_itemcreated' wfAdaptation is active.'''
        # present an item, presented item can not be set back to itemcreated
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToItemCreated', 'backToValidated'])
        self.do(item, 'backToItemCreated')
        self.assertEqual(item.query_state(), 'itemcreated')

    def test_pm_WFA_presented_item_back_to_transitions_do_not_affect_remove_several_items(self):
        '''This makes sure the 'remove-several-items' view is not affected by
           additional back transitions leaving the 'presented' state.'''
        # ease override by subproducts
        if not self._check_wfa_available(['presented_item_back_to_itemcreated']):
            return
        self.changeUser('pmManager')
        self._activate_wfas(('presented_item_back_to_itemcreated', ))
        # create meeting with item then remove it from meeting
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToItemCreated', 'backToValidated'])
        removeView = meeting.restrictedTraverse('@@remove-several-items')
        # the view can receive a single uid (as a string) or several as a list of uids
        removeView(item.UID())
        self.assertEqual(item.query_state(), 'validated')

    def test_pm_WFA_presented_item_back_to_prevalidated(self):
        '''Test the workflowAdaptation 'presented_item_back_to_prevalidated'.'''
        # ease override by subproducts
        self._enablePrevalidation(self.meetingConfig)
        if not self._check_wfa_available(['presented_item_back_to_prevalidated']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._presented_item_back_to_prevalidated_inactive()
        # activate the wfAdaptation and check, must be activated together with 'pre_validation'
        self._enablePrevalidation(self.meetingConfig)
        self._activate_wfas(('presented_item_back_to_prevalidated', ))
        self._presented_item_back_to_prevalidated_active()

    def _presented_item_back_to_prevalidated_inactive(self):
        '''Tests while 'presented_item_back_to_prevalidated' wfAdaptation is inactive.'''
        # present an item, presented item can not be set back to itemcreated
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToValidated'])

    def _presented_item_back_to_prevalidated_active(self):
        '''Tests while 'presented_item_back_to_prevalidated' wfAdaptation is active.'''
        # present an item, presented item can not be set back to itemcreated
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        self.presentItem(item)
        self.assertEqual(self.transitions(item), ['backToPrevalidated', 'backToValidated'])
        self.do(item, 'backToPrevalidated')
        self.assertEqual(item.query_state(), 'prevalidated')

    def test_pm_WFA_accepted_out_of_meeting(self):
        '''Test the workflowAdaptation 'accepted_out_of_meeting'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['accepted_out_of_meeting']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._accepted_out_of_meeting_inactive()
        # activate the wfAdaptation and check
        # if 'reviewers_take_back_validated_item' WFA is available
        # enables it as well as in this WFA, the Review portal content permission
        # is given to reviewers on state 'validated'
        wfas = ('accepted_out_of_meeting', )
        if 'reviewers_take_back_validated_item' in cfg.listWorkflowAdaptations():
            wfas = wfas + ('reviewers_take_back_validated_item', )
        self._activate_wfas(wfas)
        self._accepted_out_of_meeting_active()

    def _accepted_out_of_meeting_inactive(self):
        '''Tests while 'accepted_out_of_meeting' wfAdaptation is inactive.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.validateItem(item)
        self.assertFalse('accept_out_of_meeting' in self.transitions(item))
        # in case 'reviewers_take_back_validated_item' is available
        self.changeUser('pmReviewer1')
        self.assertFalse('accept_out_of_meeting' in self.transitions(item))

    def _accepted_out_of_meeting_active(self):
        '''Tests while 'accepted_out_of_meeting' wfAdaptation is active.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.validateItem(item)
        # not available until MeetingItem.isAcceptableOutOfMeeting is True
        self.assertFalse('accept_out_of_meeting' in self.transitions(item))
        item.setIsAcceptableOutOfMeeting(True)
        self.assertTrue('accept_out_of_meeting' in self.transitions(item))
        # in case 'reviewers_take_back_validated_item' is available
        self.changeUser('pmReviewer1')
        self.assertFalse('accept_out_of_meeting' in self.transitions(item))

        self.changeUser('pmManager')
        self.do(item, 'accept_out_of_meeting')
        self.assertEqual(item.query_state(), 'accepted_out_of_meeting')
        # not duplicated
        self.assertFalse(item.getBRefs())
        self.assertFalse(item.get_successors())
        # back transition
        self.do(item, 'backToValidatedFromAcceptedOutOfMeeting')
        self.assertEqual(item.query_state(), 'validated')

        # test 'accepted_out_of_meeting_and_duplicated' if available
        cfg = self.meetingConfig
        if 'accepted_out_of_meeting_and_duplicated' in cfg.listWorkflowAdaptations():
            wfas = list(cfg.getWorkflowAdaptations())
            wfas.remove('accepted_out_of_meeting')
            wfas.append('accepted_out_of_meeting_and_duplicated')
            self._activate_wfas(wfas)
            self.do(item, 'accept_out_of_meeting')
            duplicated_item = item.get_successors()[0]
            self.assertEqual(duplicated_item.get_predecessor(), item)
            self.assertEqual(duplicated_item.query_state(), 'validated')
            # duplicated_item is not more isAcceptableOutOfMeeting
            self.assertFalse(duplicated_item.getIsAcceptableOutOfMeeting())

    def test_pm_WFA_accepted_out_of_meeting_emergency(self):
        '''Test the workflowAdaptation 'accepted_out_of_meeting_emergency'.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['accepted_out_of_meeting_emergency']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._accepted_out_of_meeting_emergency_inactive()
        # activate the wfAdaptation and check
        # if 'reviewers_take_back_validated_item' WFA is available
        # enables it as well as in this WFA, the Review portal content permission
        # is given to reviewers on state 'validated'
        wfas = ('accepted_out_of_meeting_emergency', )
        if 'reviewers_take_back_validated_item' in cfg.listWorkflowAdaptations():
            wfas = wfas + ('reviewers_take_back_validated_item', )
        self._activate_wfas(wfas)
        self._accepted_out_of_meeting_emergency_active()

    def _accepted_out_of_meeting_emergency_inactive(self):
        '''Tests while 'accepted_out_of_meeting' wfAdaptation is inactive.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.validateItem(item)
        self.assertFalse('accept_out_of_meeting' in self.transitions(item))
        # in case 'reviewers_take_back_validated_item' is available
        self.changeUser('pmReviewer1')
        self.assertFalse('accept_out_of_meeting' in self.transitions(item))

    def _accepted_out_of_meeting_emergency_active(self):
        '''Tests while 'accepted_out_of_meeting' wfAdaptation is active.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.validateItem(item)
        # not available until MeetingItem.isAcceptableOutOfMeeting is True
        self.assertFalse('accept_out_of_meeting_emergency' in self.transitions(item))
        item.setEmergency('emergency_accepted')
        self.assertTrue('accept_out_of_meeting_emergency' in self.transitions(item))
        # in case 'reviewers_take_back_validated_item' is available
        self.changeUser('pmReviewer1')
        self.assertFalse('accept_out_of_meeting_emergency' in self.transitions(item))

        self.changeUser('pmManager')
        self.do(item, 'accept_out_of_meeting_emergency')
        self.assertEqual(item.query_state(), 'accepted_out_of_meeting_emergency')
        # not duplicated
        self.assertFalse(item.getBRefs())
        self.assertEqual(item.get_successors(the_objects=False), [])
        # back transition
        self.do(item, 'backToValidatedFromAcceptedOutOfMeetingEmergency')
        self.assertEqual(item.query_state(), 'validated')

        # test 'accepted_out_of_meeting_emergency_and_duplicated' if available
        cfg = self.meetingConfig
        if 'accepted_out_of_meeting_emergency_and_duplicated' in cfg.listWorkflowAdaptations():
            wfas = list(cfg.getWorkflowAdaptations())
            wfas.remove('accepted_out_of_meeting_emergency')
            wfas.append('accepted_out_of_meeting_emergency_and_duplicated')
            self._activate_wfas(wfas)
            self.do(item, 'accept_out_of_meeting_emergency')
            duplicated_item = item.get_successors()[0]
            self.assertEqual(duplicated_item.get_predecessor(), item)
            self.assertEqual(duplicated_item.query_state(), 'validated')
            # duplicated_item emergency is no more asked
            self.assertEqual(duplicated_item.getEmergency(), 'no_emergency')

    def test_pm_WFA_MeetingManagerCorrectClosedMeeting(self):
        '''A closed meeting may be corrected by MeetingManagers
           if 'meetingmanager_correct_closed_meeting' WFA is enabled.'''
        # ease override by subproducts
        cfg = self.meetingConfig
        if not self._check_wfa_available(['meetingmanager_correct_closed_meeting']):
            return
        self.changeUser('pmManager')
        # check while the wfAdaptation is not activated
        self._meetingmanager_correct_closed_meeting_inactive()
        # activate the wfAdaptation and check
        cfg.setWorkflowAdaptations(('meetingmanager_correct_closed_meeting', ))
        self._meetingmanager_correct_closed_meeting_active()

    def _meetingmanager_correct_closed_meeting_inactive(self):
        '''Tests while 'meetingmanager_correct_closed_meeting' wfAdaptation is inactive.'''
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.closeMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'closed')
        closed_meeting_msg = translate(u'closed_meeting_not_correctable_by_config',
                                       domain='PloneMeeting',
                                       context=self.request)
        # No instance
        may_correct = meeting.wfConditions().mayCorrect()
        self.assertFalse(may_correct)
        self.assertEqual(translate(may_correct.msg, domain='PloneMeeting', context=self.request),
                         closed_meeting_msg)
        # OK for Managers
        self.changeUser('siteadmin')
        self.assertTrue(meeting.wfConditions().mayCorrect())

    def _meetingmanager_correct_closed_meeting_active(self):
        '''Tests while 'meetingmanager_correct_closed_meeting' wfAdaptation is active.'''
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.closeMeeting(meeting)
        self.assertTrue(meeting.wfConditions().mayCorrect())
        self.changeUser('siteadmin')
        self.assertTrue(meeting.wfConditions().mayCorrect())


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testWFAdaptations, prefix='test_pm_'))
    return suite
