# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from imio.pyutils.utils import replace_in_list
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


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

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4214...')
        # reload ConfigurablePODTemplate to use every_annex_types_vocabulary for field store_as_annex
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        self._migrateAdviceEditedItemMailEvents()
        # add text criterion on "item title only" again as it was not in default
        # dashboard faceted criteria, new MeetingConfigs created manually in between
        # are missing this new criterion
        self.updateFacetedFilters(xml_filename='upgrade_step_4211_add_item_widgets.xml')
        logger.info('Migrating to PloneMeeting 4214... Done.')


def migrate(context):
    '''This migration function will:

       1) Update values of MeetingConfig.itemMailEvents as format
          of "adviceEdited" values changed.
    '''
    migrator = Migrate_To_4214(context)
    migrator.run()
    migrator.finish()
