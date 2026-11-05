# -*- coding: utf-8 -*-
#
# File: testMigrations.py
#
# GNU General Public License (GPL)
#

from Products.PloneMeeting.config import GROUP_MANAGING_ITEM_PG_PREFIX
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.migrations.migrate_to_4217_4 import Migrate_To_4217_4
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testMigrations(PloneMeetingTestCase):
    '''Tests the migration helpers and steps.'''

    def test_pm_UpdateWFStatesAndTransitions(self):
        '''Migrator.updateWFStatesAndTransitions updates the workflow_history of elements,
           the MeetingConfig and the organizations attributes using item states
           and reindexes the review_state of updated elements.'''
        cfg = self.meetingConfig
        cfg_id = cfg.getId()
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.proposeItem(item)
        proposed_state = item.query_state()
        self.changeUser('siteadmin')
        cfg.setItemAdviceStates((proposed_state, ))
        self.developers.item_advice_states = [u'{0}__state__{1}'.format(cfg_id, proposed_state)]
        # organizations without any stored value are managed
        self.vendors.item_advice_states = None
        self.assertEqual(len(self.catalog(UID=item.UID(), review_state=proposed_state)), 1)
        migrator = Migrator(self.portal)
        migrator.updateWFStatesAndTransitions(
            query={'UID': item.UID()},
            review_state_mappings={proposed_state: 'validated'})
        # workflow_history and review_state index
        self.assertEqual(item.query_state(), 'validated')
        self.assertEqual(len(self.catalog(UID=item.UID(), review_state='validated')), 1)
        # MeetingConfig and organizations attributes
        self.assertEqual(cfg.getItemAdviceStates(), ('validated', ))
        self.assertEqual(self.developers.item_advice_states,
                         [u'{0}__state__validated'.format(cfg_id)])
        self.assertIsNone(self.vendors.item_advice_states)
        # p_cfg_ids limits the MeetingConfigs (and organizations values) to update
        cfg2 = self.meetingConfig2
        cfg2.setItemAdviceStates(('validated', ))
        migrator.updateWFStatesAndTransitions(
            query={'UID': item.UID()},
            review_state_mappings={'validated': proposed_state},
            cfg_ids=[cfg_id])
        self.assertEqual(item.query_state(), proposed_state)
        self.assertEqual(cfg.getItemAdviceStates(), (proposed_state, ))
        self.assertEqual(self.developers.item_advice_states,
                         [u'{0}__state__{1}'.format(cfg_id, proposed_state)])
        self.assertEqual(cfg2.getItemAdviceStates(), ('validated', ))

    def test_pm_MigrateItemsWaitingAdviceState(self):
        '''When using MeetingConfig.itemWFValidationLevels to generate the waiting_advices state,
           items using the old "__or__" state id are moved to "any_validation_state_waiting_advices",
           including items in a state generated before a validation level was enabled.
           Items of a MeetingConfig not using validation levels are not changed.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_from_every_val_levels']):
            return
        self._activate_wfas(('waiting_advices', 'waiting_advices_from_every_val_levels'))
        self._activate_wfas(('waiting_advices', ), cfg=cfg2)
        new_state_id = 'any_validation_state_waiting_advices'
        cfg.setItemAdviceStates((new_state_id, ))
        enabled_states = cfg.getItemWFValidationLevels(data='state', only_enabled=True)
        self.assertTrue(len(enabled_states) > 1)
        # old state id generated with current validation levels
        old_state_id = '{0}_waiting_advices'.format('__or__'.join(enabled_states))
        # old state id generated before a validation level was enabled
        stale_state_id = '{0}_waiting_advices'.format(enabled_states[0])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        stale_item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        # item that was in the old state then went back to itemcreated
        back_item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        for an_item in (item, stale_item, back_item):
            self.do(an_item, 'wait_advices_from_itemcreated')
            self.assertEqual(an_item.query_state(), new_state_id)
        self.changeUser('siteadmin')
        self.do(back_item, 'backTo_itemcreated_from_waiting_advices')
        # item of cfg2 in the "itemcreated_waiting_advices" state generated without validation levels
        self.setMeetingConfig(cfg2.getId())
        cfg2_state_id = 'itemcreated_waiting_advices'
        self.assertTrue(cfg2_state_id in cfg2.getItemWorkflow(True).states)
        cfg2_item = self.create('MeetingItem')
        # item of cfg2 in an orphan old state, not existing in the cfg2 item workflow
        cfg2_enabled_states = cfg2.getItemWFValidationLevels(data='state', only_enabled=True)
        self.assertTrue(len(cfg2_enabled_states) > 1)
        cfg2_orphan_state_id = '{0}_waiting_advices'.format('__or__'.join(cfg2_enabled_states))
        self.assertFalse(cfg2_orphan_state_id in cfg2.getItemWorkflow(True).states)
        cfg2_orphan_item = self.create('MeetingItem')
        # cfg2 uses the real "itemcreated_waiting_advices" state in its parameters,
        # it is the same id as the stale_state_id of cfg (when first level is "itemcreated")
        cfg2.setItemAdviceStates((cfg2_state_id, ))
        # set items in the old states like before migration
        migrator = Migrator(self.portal)
        migrator.updateWFStatesAndTransitions(
            query={'UID': [item.UID(), back_item.UID()]},
            review_state_mappings={new_state_id: old_state_id},
            cfg_ids=[cfg.getId()])
        migrator.updateWFStatesAndTransitions(
            query={'UID': stale_item.UID()},
            review_state_mappings={new_state_id: stale_state_id},
            cfg_ids=[cfg.getId()])
        migrator.updateWFStatesAndTransitions(
            query={'UID': cfg2_item.UID()},
            review_state_mappings={'itemcreated': cfg2_state_id},
            cfg_ids=[cfg2.getId()])
        migrator.updateWFStatesAndTransitions(
            query={'UID': cfg2_orphan_item.UID()},
            review_state_mappings={'itemcreated': cfg2_orphan_state_id},
            cfg_ids=[cfg2.getId()])
        self.assertEqual(cfg.getItemAdviceStates(), (old_state_id, ))
        self.assertEqual(cfg2.getItemAdviceStates(), (cfg2_state_id, ))
        self.assertEqual(item.query_state(), old_state_id)
        self.assertEqual(stale_item.query_state(), stale_state_id)
        self.assertEqual(back_item.query_state(), 'itemcreated')
        self.assertEqual(cfg2_item.query_state(), cfg2_state_id)
        self.assertEqual(len(self.catalog(UID=back_item.UID(), previous_review_state=old_state_id)), 1)

        migrator = Migrate_To_4217_4(self.portal)
        migrator._migrateItemsWaitingAdviceState()
        for an_item in (item, stale_item):
            self.assertEqual(an_item.query_state(), new_state_id)
            self.assertEqual(len(self.catalog(UID=an_item.UID(), review_state=new_state_id)), 1)
        # workflow_history and previous_review_state of item that left the old state
        self.assertEqual(back_item.query_state(), 'itemcreated')
        self.assertEqual(len(self.catalog(UID=back_item.UID(), previous_review_state=new_state_id)), 1)
        # MeetingConfig using the old state id is migrated, without duplicates
        self.assertEqual(cfg.getItemAdviceStates(), (new_state_id, ))
        # cfg2 not using validation levels is not changed, items and parameters
        self.assertEqual(cfg2_item.query_state(), cfg2_state_id)
        self.assertEqual(cfg2.getItemAdviceStates(), (cfg2_state_id, ))
        # item of cfg2 in an orphan state is not changed but reported in the migration warnings
        self.assertEqual(cfg2_orphan_item.query_state(), cfg2_orphan_state_id)
        self.assertEqual(
            migrator.warnings,
            ['Items of "{0}" are in states "{1}" that do not exist in the item '
             'workflow, they need to be fixed manually!'.format(cfg2.getId(), cfg2_orphan_state_id)])

    def test_pm_UpdateSearchItemsOfMyCommitteesSearchesCondition(self):
        '''Committees editors searches are only available when using committees editors.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        searches = cfg.searches.searches_items
        old_condition = "python: tool.get_orgs_for_user(omitted_suffixes=['observers', ]) " \
            "and cfg.getCommittees()"
        searches.searchitemsofmycommittees.tal_condition = old_condition
        searches.searchitemsofmycommitteeseditable.tal_condition = old_condition
        Migrate_To_4217_4(self.portal)._updateSearchItemsOfMyCommitteesSearchesCondition()
        self.assertEqual(searches.searchitemsofmycommittees.tal_condition,
                         "python: cfg.is_committees_using('enable_editors')")
        self.assertEqual(searches.searchitemsofmycommitteeseditable.tal_condition,
                         "python: cfg.is_committees_using('enable_editors')")

    def test_pm_UpdateSearchDecidedItemsCondition(self):
        '''Decided items searches are hidden when the item WF does not have
           any decided state, a customized "tal_condition" is kept.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        decided = cfg.searches.searches_items.searchdecideditems
        unread_decided = cfg.searches.searches_items.searchunreaddecideditems
        decided_condition = "python: cfg.has_item_decided_states()"
        unread_decided_condition = "python: 'labels' in cfg.getUsedItemAttributes() and " \
            "cfg.has_item_decided_states()"
        # old default conditions are migrated
        decided.tal_condition = ''
        unread_decided.tal_condition = "python: 'labels' in cfg.getUsedItemAttributes()"
        Migrate_To_4217_4(self.portal)._updateSearchDecidedItemsCondition()
        self.assertEqual(decided.tal_condition, decided_condition)
        self.assertEqual(unread_decided.tal_condition, unread_decided_condition)
        # customized conditions are kept
        decided.tal_condition = 'python: False'
        unread_decided.tal_condition = 'python: True'
        Migrate_To_4217_4(self.portal)._updateSearchDecidedItemsCondition()
        self.assertEqual(decided.tal_condition, 'python: False')
        self.assertEqual(unread_decided.tal_condition, 'python: True')

    def test_pm_Migrate_To_4217_4(self):
        '''MeetingConfig.itemWFValidationLevels using old "suffix/extra_suffixes" columns
           are migrated, running the migration on a migrated site changes nothing.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        levels = cfg.getItemWFValidationLevels(include_disabled_validated=True)
        # old format
        old_levels = cfg.getItemWFValidationLevels(include_disabled_validated=True)
        for level in old_levels:
            level['suffix'] = level.pop('group_managing_item').replace(GROUP_MANAGING_ITEM_PG_PREFIX, '')
            level['extra_suffixes'] = [
                egmi.replace(GROUP_MANAGING_ITEM_PG_PREFIX, '')
                for egmi in level.pop('extra_groups_managing_item')]
            level.pop('available_on')
        cfg.itemWFValidationLevels = old_levels
        Migrate_To_4217_4(self.portal).run()
        self.assertEqual(cfg.getItemWFValidationLevels(include_disabled_validated=True), levels)
        # run again, nothing changed
        Migrate_To_4217_4(self.portal).run()
        self.assertEqual(cfg.getItemWFValidationLevels(include_disabled_validated=True), levels)


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMigrations, prefix='test_pm_'))
    return suite
