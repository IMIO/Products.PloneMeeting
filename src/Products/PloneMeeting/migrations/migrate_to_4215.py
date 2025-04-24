# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from imio.pyutils.utils import replace_in_list
from Products.PloneMeeting.config import GROUP_MANAGING_ITEM_PG_PREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.model.adaptations import WAITING_ADVICES_NEW_STATE_ID_PATTERN
from Products.PloneMeeting.setuphandlers import _configureWebspellchecker
from Products.PloneMeeting.setuphandlers import _installWebspellchecker


class Migrate_To_4215(Migrator):

    def _initGroupsManagingItemToCfgItemWFValidationLevels(self):
        """Update existing MeetingConfig.itemWFValidationLevels to initialize
           "group_managing_item/extra_groups_managing_item" based on
           "suffix/extra_suffixes" that are removed."""
        logger.info('Updating MeetingConfig.itemWFValidationLevels to initialize '
                    '"group_managing_item/extra_groups_managing_item"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            stored = getattr(cfg, 'itemWFValidationLevels', [])
            for level in stored:
                if 'suffix' not in level:
                    return self._already_migrated()
                # migrate columns 'suffix' to 'group_managing_item' and
                # 'extra_suffixes' to 'extra_groups_managing_item'
                # and remove 'suffix/extra_suffixes'
                level['group_managing_item'] = GROUP_MANAGING_ITEM_PG_PREFIX + level['suffix']
                level['extra_groups_managing_item'] = [
                    GROUP_MANAGING_ITEM_PG_PREFIX + suffix
                    for suffix in list(level['extra_suffixes'])]
                del level['suffix']
                del level['extra_suffixes']
            cfg.setItemWFValidationLevels(stored)

    def _migrateItemsWaitingAdviceState(self):
        """When using MeetingConfig.itemWFValidationLevels to compute
           the waiting_advices state id, we were generating a __or__ complex
           state name, now we go back to any_validation_state_waiting_advices."""
        logger.info('Migrating items waiting advices state name...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            wfas = cfg.getWorkflowAdaptations()
            if 'waiting_advices_from_every_val_levels' in wfas or \
               'waiting_advices_from_before_last_val_level' in wfas or \
               'waiting_advices_from_last_val_level' in wfas:
                # generate old state id
                item_validation_states = cfg.getItemWFValidationLevels(
                    data='state', only_enabled=True)
                state_id = WAITING_ADVICES_NEW_STATE_ID_PATTERN.format(
                    '__or__'.join(item_validation_states))
                self.updateWFStatesAndTransitions(
                    query={'getConfigId': cfg.getId(),
                           'meta_type': 'MeetingItem'},
                    review_state_mappings={
                        state_id: 'any_validation_state_waiting_advices'})
        logger.info('Done.')

    def _updateSearchItemsOfMyCommitteesSearchesCondition(self):
        """As these searches are used only when committees editors are used."""
        logger.info('Updating committees editors searches TAL condition in every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            searchitemsofmycommittees = cfg.searches.searches_items.get('searchitemsofmycommittees')
            if searchitemsofmycommittees:
                searchitemsofmycommittees.tal_condition = "python: cfg.is_committees_using('enable_editors')"
            searchitemsofmycommitteeseditable = cfg.searches.searches_items.get('searchitemsofmycommitteeseditable')
            if searchitemsofmycommitteeseditable:
                searchitemsofmycommitteeseditable.tal_condition = \
                    "python: cfg.is_committees_using('enable_editors')"

    def _updateConfigCustomAdvisersDataGrid(self):
        """MeetingConfig.customAdvisers get a new column "is_delay_calendar_days"."""
        logger.info('Updating datagridfield "customAdvisers" for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            custom_advisers = cfg.getCustomAdvisers()
            for ca in custom_advisers:
                if "is_delay_calendar_days" not in ca:
                    ca["is_delay_calendar_days"] = "0"
            cfg.setCustomAdvisers(custom_advisers)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4215...')
        self._initGroupsManagingItemToCfgItemWFValidationLevels()
        self._migrateItemsWaitingAdviceState()
        self._updateSearchItemsOfMyCommitteesSearchesCondition()
        self._updateConfigCustomAdvisersDataGrid()
        logger.info('Migrating to PloneMeeting 4215... Done.')


def migrate(context):
    '''This migration function will:

       1) Add "groups_managing_item" to every MeetingConfig.itemWFValidationLevels;
       2) Move item waiting_advices states to "any_validation_state_waiting_advices";
       3) Adapt committees editors searches "tal_condition".
       4) Update MeetingConfig.customAdvisers to add new column "is_delay_calendar_days".
    '''
    migrator = Migrate_To_4215(context)
    migrator.run()
    migrator.finish()
