# -*- coding: utf-8 -*-
#
# File: testMigrations.py
#
# GNU General Public License (GPL)
#

from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.migrations.migrate_to_4215 import Migrate_To_4215
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

    def test_pm_MigrateItemsWaitingAdviceState(self):
        '''When using MeetingConfig.itemWFValidationLevels to generate the waiting_advices state,
           items using the old "__or__" state id are moved to "any_validation_state_waiting_advices".'''
        cfg = self.meetingConfig
        if not self._check_wfa_available(['waiting_advices',
                                          'waiting_advices_from_every_val_levels']):
            return
        self._activate_wfas(('waiting_advices', 'waiting_advices_from_every_val_levels'))
        cfg.setItemAdviceStates(('any_validation_state_waiting_advices', ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', optionalAdvisers=(self.vendors_uid, ))
        self.do(item, 'wait_advices_from_itemcreated')
        self.assertEqual(item.query_state(), 'any_validation_state_waiting_advices')
        # set item in the old state like before migration
        old_state_id = '{0}_waiting_advices'.format(
            '__or__'.join(cfg.getItemWFValidationLevels(data='state', only_enabled=True)))
        self.changeUser('siteadmin')
        Migrator(self.portal).updateWFStatesAndTransitions(
            query={'UID': item.UID()},
            review_state_mappings={'any_validation_state_waiting_advices': old_state_id})
        self.assertEqual(item.query_state(), old_state_id)
        Migrate_To_4215(self.portal)._migrateItemsWaitingAdviceState()
        self.assertEqual(item.query_state(), 'any_validation_state_waiting_advices')
        self.assertEqual(
            len(self.catalog(UID=item.UID(), review_state='any_validation_state_waiting_advices')), 1)

    def test_pm_UpdateSearchItemsOfMyCommitteesSearchesCondition(self):
        '''Committees editors searches are only available when using committees editors.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        searches = cfg.searches.searches_items
        old_condition = "python: tool.get_orgs_for_user(omitted_suffixes=['observers', ]) " \
            "and cfg.getCommittees()"
        searches.searchitemsofmycommittees.tal_condition = old_condition
        searches.searchitemsofmycommitteeseditable.tal_condition = old_condition
        Migrate_To_4215(self.portal)._updateSearchItemsOfMyCommitteesSearchesCondition()
        self.assertEqual(searches.searchitemsofmycommittees.tal_condition,
                         "python: cfg.is_committees_using('enable_editors')")
        self.assertEqual(searches.searchitemsofmycommitteeseditable.tal_condition,
                         "python: cfg.is_committees_using('enable_editors')")


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMigrations, prefix='test_pm_'))
    return suite
