# -*- coding: utf-8 -*-

from Products.PloneMeeting.config import GROUP_MANAGING_ITEM_PG_PREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4217_4(Migrator):

    def _initGroupsManagingItemToCfgItemWFValidationLevels(self):
        """Update existing MeetingConfig.itemWFValidationLevels to initialize
           "group_managing_item/extra_groups_managing_item" based on
           "suffix/extra_suffixes" that are removed and add the "available_on" column."""
        logger.info('Updating MeetingConfig.itemWFValidationLevels to initialize '
                    '"group_managing_item/extra_groups_managing_item/available_on"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            stored = getattr(cfg, 'itemWFValidationLevels', [])
            for level in stored:
                if 'suffix' in level:
                    # migrate columns 'suffix' to 'group_managing_item' and
                    # 'extra_suffixes' to 'extra_groups_managing_item'
                    # and remove 'suffix/extra_suffixes'
                    level['group_managing_item'] = GROUP_MANAGING_ITEM_PG_PREFIX + level['suffix']
                    level['extra_groups_managing_item'] = [
                        GROUP_MANAGING_ITEM_PG_PREFIX + suffix
                        for suffix in list(level.get('extra_suffixes') or [])]
                    del level['suffix']
                    level.pop('extra_suffixes', None)
                if 'available_on' not in level:
                    level['available_on'] = ''
            cfg.setItemWFValidationLevels(stored)
        logger.info('Done.')

    def _migrateItemsWaitingAdviceState(self):
        """When using MeetingConfig.itemWFValidationLevels to compute
           the waiting_advices state id, we were generating a __or__ complex
           state name, now we go back to any_validation_state_waiting_advices."""
        logger.info('Migrating items waiting advices state name...')
        new_state_id_pattern = '{0}_waiting_advices'
        for cfg in self.tool.objectValues('MeetingConfig'):
            wfas = cfg.getWorkflowAdaptations()
            if 'waiting_advices_from_every_val_levels' in wfas or \
               'waiting_advices_from_before_last_val_level' in wfas or \
               'waiting_advices_from_last_val_level' in wfas:
                # generate old state id
                item_validation_states = cfg.getItemWFValidationLevels(
                    data='state', only_enabled=True)
                state_id = new_state_id_pattern.format(
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
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.4...')
        self._initGroupsManagingItemToCfgItemWFValidationLevels()
        self._migrateItemsWaitingAdviceState()
        self._updateSearchItemsOfMyCommitteesSearchesCondition()
        if not from_migration_to_4200:
            # regenerate item workflows as validation levels changed
            self.reloadMeetingConfigs()
        logger.info('Migrating to PloneMeeting 4217.4... Done.')


def migrate(context):
    """This migration function will:

       1) Add "groups_managing_item" and "available_on" to every MeetingConfig.itemWFValidationLevels;
       2) Move item waiting_advices states to "any_validation_state_waiting_advices";
       3) Adapt committees editors searches "tal_condition";
       4) Reload MeetingConfigs so item workflows are regenerated.
    """
    migrator = Migrate_To_4217_4(context)
    migrator.run()
    migrator.finish()
