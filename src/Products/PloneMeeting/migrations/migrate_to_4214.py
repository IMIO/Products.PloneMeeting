# -*- coding: utf-8 -*-

from collections import OrderedDict
from imio.helpers.setup import load_type_from_package
from imio.pyutils.utils import replace_in_list
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.setuphandlers import _configureWebspellchecker


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
        # remove Scayt in CKeditor
        cke_props = self.portal.portal_properties.ckeditor_properties
        cke_props.enableScaytOnStartup = False
        toolbar_Custom = cke_props.toolbar_Custom
        scayt_values = OrderedDict(
            [(",'-','Scayt']", "]"),
             # space after ","
             (", '-','Scayt']", "]"),
             (",'-', 'Scayt']", "]"),
             (", '-', 'Scayt']", "]"),
             # space before "]"
             (", '-','Scayt' ]", "]"),
             (",'-', 'Scayt' ]", "]"),
             (", '-', 'Scayt' ]", "]"),
             # other possibilities, 'Scayt' in the middle
             (",'Scayt',", ","),
             (", 'Scayt',", ",")
         ])

        replaced = False
        for k, v in scayt_values.items():
            if toolbar_Custom.find(k):
                replaced = True
                toolbar_Custom = toolbar_Custom.replace(k, v)
                cke_props.toolbar_Custom = toolbar_Custom
                break
        if replaced is False:
            self.warn(
                logger,
                "In _installIMIOWebSpellChecker could not remove 'Scayt' "
                "option from toolbar_Custom!")

        self.reinstall(['imio.webspellchecker:default'])
        _configureWebspellchecker(self.portal)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4214...')
        # reload ConfigurablePODTemplate to use every_annex_types_vocabulary for field store_as_annex
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        self._migrateAdviceEditedItemMailEvents()
        self._installIMIOWebSpellChecker()
        logger.info('Migrating to PloneMeeting 4214... Done.')


def migrate(context):
    '''This migration function will:

       1) Update values of MeetingConfig.itemMailEvents as format
          of "adviceEdited" values changed;
       2) Install and configure "imio.webspellchecker".
    '''
    migrator = Migrate_To_4214(context)
    migrator.run()
    migrator.finish()
