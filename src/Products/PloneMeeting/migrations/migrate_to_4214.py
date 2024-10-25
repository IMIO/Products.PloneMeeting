# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from imio.pyutils.utils import replace_in_list
from Products.PloneMeeting.config import GROUP_MANAGING_ITEM_PG_PREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.model.adaptations import WAITING_ADVICES_NEW_STATE_ID_PATTERN
from Products.PloneMeeting.setuphandlers import _configureWebspellchecker
from Products.PloneMeeting.setuphandlers import _installWebspellchecker


class Migrate_To_4214(Migrator):

    def _migrateAdviceEditedItemMailEvents(self):
        """Item mail event "adviceEdited" is replaced by "advice_edited__creators"
           and "adviceEditedOwner" is replaced by "advice_edited__owner"."""
        logger.info('Migrating "adviceEdited" in "MeetingConfig.mailItemEvents"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            mailItemEvents = list(cfg.getMailItemEvents())
            if "adviceEdited" in mailItemEvents:
                mailItemEvents = replace_in_list(
                    mailItemEvents, "adviceEdited", "advice_edited__creators")
                cfg.setMailItemEvents(mailItemEvents)
            if "adviceEditedOwner" in mailItemEvents:
                mailItemEvents = replace_in_list(
                    mailItemEvents, "adviceEditedOwner", "advice_edited__Owner")
                cfg.setMailItemEvents(mailItemEvents)
        logger.info('Done.')

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

    def _installIMIOWebSpellChecker(self):
        """Configure imio.webspellchecker."""
        logger.info('Install and configure "imio.webspellchecker"...')
        replaced = _installWebspellchecker(self.portal)
        if replaced is False:
            self.warn(
                logger,
                "In _installIMIOWebSpellChecker could not remove 'Scayt' "
                "option from toolbar_Custom!")
        _configureWebspellchecker(self.portal)
        logger.info('Done.')

    def _updatePortalTypesTitle(self):
        """Meeting/MeetingItem portal_types title is now the translated version."""
        logger.info('Updating every Meeting/MeetingItem portal_types title...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.registerPortalTypes()
        logger.info('Done.')

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
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4214...')
        self._initGroupsManagingItemToCfgItemWFValidationLevels()
        # reload ConfigurablePODTemplate to use every_annex_types_vocabulary for field store_as_annex
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        self._migrateAdviceEditedItemMailEvents()
        self._updatePortalTypesTitle()
        self._migrateItemsWaitingAdviceState()
        # not done for now, we will enable it when necessary
        # self._installIMIOWebSpellChecker()
        # add text criterion on "item title only" again as it was not in default
        # dashboard faceted criteria, new MeetingConfigs created manually in between
        # are missing this new criterion
        self.updateFacetedFilters(xml_filename='upgrade_step_4211_add_item_widgets.xml')
        self._updateSearchItemsOfMyCommitteesSearchesCondition()
        logger.info('Migrating to PloneMeeting 4214... Done.')


def migrate(context):
    '''This migration function will:

       1) Reload ConfigurablePODTemplate as store_as_annex field vocabulary changed;
       2) Update values of MeetingConfig.itemMailEvents as format of
          "adviceEdited" values changed;
       3) Update Meeting/MeetingItem portal_types title as we store the real title now;
       4) Update faceted filters (Add "item title only" search criterion again);
       5) Not done for now: install and configure "imio.webspellchecker".
       6) Add "groups_managing_item" to every MeetingConfig.itemWFValidationLevels;
       7) Adapt committees editors searches tal_condition.
    '''
    migrator = Migrate_To_4214(context)
    migrator.run()
    migrator.finish()
