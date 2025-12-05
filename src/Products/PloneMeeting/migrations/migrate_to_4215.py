# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from imio.webspellchecker.config import set_disable_autosearch_in
from Products.PloneMeeting.config import GROUP_MANAGING_ITEM_PG_PREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


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

    def _reloadMeetingConfigsForItemWorkflows(self):
        """Reload MeetingConfigs if using "return_to_proposing_group" with validation."""
        logger.info("Updating item WF using 'return_to_proposing_group with validation'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if len([state_id for state_id in cfg.getItemWorkflow(True)
                    if state_id.startswith('returned_to_proposing_group')]) > 1:
                cfg.registerPortalTypes()
        logger.info('Done.')

    def _fixWSCConfigAndCleanBrokenAnnexes(self):
        """WSC could sometimes break quickupload leading to broken annexes.
           Adapt WSC config so it is no more used in quickupload and clean broken annexes."""
        logger.info("Updating WSC config and removing broken annexes...")
        if self.portal.portal_quickinstaller.isProductInstalled('imio.webspellchecker'):
            # disable WSC in quickupload
            set_disable_autosearch_in(
                u'["#form-widgets-title", "#form-widgets-description", '
                u'".select2-focusser", ".select2-input"]')
            # remove broken annexes
            self._removeBrokenAnnexes()
        logger.info('Done.')

    def _updateWFWriteMarginalNotesPermission(self):
        """Re-apply WFs (portal_setup and MeetingConfig) as WriteMarginalNotes
           permission is now available when item is "presented"."""
        logger.info("Updating workflows 'WriteMarginalNotes' permission...")
        # update workflow definition
        self.runProfileSteps('Products.PloneMeeting', steps=['workflow'], profile='default')
        # reload every MeetingConfigs so WF are updated
        self.reloadMeetingConfigs()
        # update every "presented" items
        for cfg in self.tool.objectValues('MeetingConfig'):
            item_wf = cfg.getItemWorkflow(True)
            for brain in self.catalog(portal_type=cfg.getItemTypeName(), review_state="presented"):
                item = brain.getObject()
                item_wf.updateRoleMappingsFor(item)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4215...')
        if not from_migration_to_4200:
            # this will upgrade collective.contact.core especially
            # that reinstalls imio.fpaudit, that will itself reinstall collective.documentgenerator
            self.upgradeAll(omit=['Products.PloneMeeting:default',
                                  self.profile_name.replace('profile-', '')])
            # reload ConfigurablePODTemplate
            load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
            # hide document-generation-link default viewlet
            self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'viewlets')
        self._initGroupsManagingItemToCfgItemWFValidationLevels()
        self._migrateItemsWaitingAdviceState()
        self._updateSearchItemsOfMyCommitteesSearchesCondition()
        self._updateConfigCustomAdvisersDataGrid()
        self._reloadMeetingConfigsForItemWorkflows()
        self._fixWSCConfigAndCleanBrokenAnnexes()
        self._updateWFWriteMarginalNotesPermission()
        logger.info('Migrating to PloneMeeting 4215... Done.')


def migrate(context):
    '''This migration function will:

       1) Upgrade all and make sure documentgenerator overrides are re-applied;
       2) Add "groups_managing_item" to every MeetingConfig.itemWFValidationLevels;
       3) Move item waiting_advices states to "any_validation_state_waiting_advices";
       4) Adapt committees editors searches "tal_condition".
       5) Update MeetingConfig.customAdvisers to add new column "is_delay_calendar_days";
       6) Reload MeetingConfigs if using "return_to_proposing_group" with validation;
       7) Fix WSC config and remove broken annexes;
       8) Update "WriteMarginalNotes" for every item WF and "presented" items.
    '''
    migrator = Migrate_To_4215(context)
    migrator.run()
    migrator.finish()
