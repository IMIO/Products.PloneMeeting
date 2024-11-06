# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from imio.pyutils.utils import replace_in_list
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
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

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4214...')
        # reload ConfigurablePODTemplate to use every_annex_types_vocabulary for field store_as_annex
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        self._migrateAdviceEditedItemMailEvents()
        self._updatePortalTypesTitle()
        # not done for now, we will enable it when necessary
        # self._installIMIOWebSpellChecker()
        # add text criterion on "item title only" again as it was not in default
        # dashboard faceted criteria, new MeetingConfigs created manually in between
        # are missing this new criterion
        self.updateFacetedFilters(xml_filename='upgrade_step_4211_add_item_widgets.xml')
        # holidays 2025 were added
        self.updateHolidays()
        logger.info('Migrating to PloneMeeting 4214... Done.')


def migrate(context):
    '''This migration function will:

       1) Reload ConfigurablePODTemplate as store_as_annex field vocabulary changed;
       2) Update values of MeetingConfig.itemMailEvents as format of
          "adviceEdited" values changed;
       3) Update Meeting/MeetingItem portal_types title as we store the real title now;
       4) Update faceted filters;
       5) Not done for now: install and configure "imio.webspellchecker".

    '''
    migrator = Migrate_To_4214(context)
    migrator.run()
    migrator.finish()
