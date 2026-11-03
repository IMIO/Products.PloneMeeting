# -*- coding: utf-8 -*-

from Products.PloneMeeting.config import GROUP_MANAGING_ITEM_PG_PREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.model.adaptations import get_waiting_advices_infos


NEW_WAITING_ADVICES_STATE_ID = 'any_validation_state_waiting_advices'
WAITING_ADVICES_SUFFIX = '_waiting_advices'


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

    def _get_old_val_levels_waiting_advices_states(self, cfg, waiting_advices_states):
        """Return the old waiting_advices state ids among p_waiting_advices_states generated
           from MeetingConfig.itemWFValidationLevels for p_cfg, aka states like
           "itemcreated__or__proposed_waiting_advices" made of validation level states.
           A "new_state_id" defined in WAITING_ADVICES_FROM_STATES is kept."""
        custom_state_ids = [infos['new_state_id'] for infos in
                            get_waiting_advices_infos(cfg.getId(real_id=True))
                            if infos.get('new_state_id')]
        # enabled or disabled validation levels, an old state id may contain
        # a validation level that was enabled after items were set in it
        val_states = set(cfg.getItemWFValidationLevels(data='state'))
        res = []
        for state_id in waiting_advices_states:
            if state_id == NEW_WAITING_ADVICES_STATE_ID or state_id in custom_state_ids:
                continue
            if set(state_id[:-len(WAITING_ADVICES_SUFFIX)].split('__or__')).issubset(val_states):
                res.append(state_id)
        return res

    def _migrateItemsWaitingAdviceState(self):
        """When using MeetingConfig.itemWFValidationLevels to compute
           the waiting_advices state id, we were generating a __or__ complex
           state name, now we go back to any_validation_state_waiting_advices.
           Old state ids are the ones of the current item workflow but also the ones
           still used by items, an item may have been set in a state generated before
           a validation level was enabled (that changed the generated state id)."""
        logger.info('Migrating items waiting advices state name...')
        # every waiting_advices review_state used by items of every MeetingConfigs
        used_waiting_advices_states = [
            state_id for state_id in self.catalog.uniqueValuesFor('review_state')
            if state_id.endswith(WAITING_ADVICES_SUFFIX)]
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg_id = cfg.getId()
            item_wf_states = cfg.getItemWorkflow(True).states
            wfas = cfg.getWorkflowAdaptations()
            # states used by items of this MeetingConfig
            cfg_used_states = [
                state_id for state_id in used_waiting_advices_states
                if self.catalog.unrestrictedSearchResults(
                    getConfigId=cfg_id, meta_type='MeetingItem', review_state=state_id)]
            if 'waiting_advices_from_every_val_levels' in wfas or \
               'waiting_advices_from_before_last_val_level' in wfas or \
               'waiting_advices_from_last_val_level' in wfas:
                old_state_ids = self._get_old_val_levels_waiting_advices_states(
                    cfg,
                    set(cfg_used_states).union(
                        [state_id for state_id in item_wf_states
                         if state_id.endswith(WAITING_ADVICES_SUFFIX)]))
                if old_state_ids:
                    logger.info('Migrating states "{0}" for "{1}"...'.format(
                        ', '.join(sorted(old_state_ids)), cfg_id))
                    self.updateWFStatesAndTransitions(
                        query={'getConfigId': cfg_id,
                               'meta_type': 'MeetingItem'},
                        review_state_mappings={
                            state_id: NEW_WAITING_ADVICES_STATE_ID
                            for state_id in old_state_ids},
                        # only update this MeetingConfig, another may use a
                        # real state with same id (like "itemcreated_waiting_advices")
                        cfg_ids=[cfg_id])
            else:
                # not using validation levels for waiting_advices, items may be in an old
                # state if a WFA was removed, we can not fix it, just warn
                orphan_state_ids = [
                    state_id for state_id in self._get_old_val_levels_waiting_advices_states(
                        cfg, cfg_used_states) if state_id not in item_wf_states]
                if orphan_state_ids:
                    self.warn(
                        logger,
                        'Items of "{0}" are in states "{1}" that do not exist in the item '
                        'workflow, they need to be fixed manually!'.format(
                            cfg_id, ', '.join(sorted(orphan_state_ids))))
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
