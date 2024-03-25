# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4214(Migrator):

    def _migrateAdviceEditedItemMailEvents(self):
        """Item mail event "adviceEdited" is replaced by "advice_edited__creators"
           and "adviceEditedOwner" is replaced by "advice_edited__owner"."""
        logger.info('Migrating "adviceEdited" in "MeetingConfig.mailItemEvents"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            mailItemEvents = cfg.getMailItemEvents()
            if "adviceEdited" in mailItemEvents:
                mailItemEvents.remove("adviceEdited")
                mailItemEvents.append("advice_edited__creators")
                cfg.setMailItemEvents(mailItemEvents)
            if "adviceEditedOwner" in mailItemEvents:
                mailItemEvents.remove("adviceEditedOwner")
                mailItemEvents.append("advice_edited__owner")
                cfg.setMailItemEvents(mailItemEvents)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4214...')
        self._migrateAdviceEditedItemMailEvents()
        logger.info('Migrating to PloneMeeting 4214... Done.')


def migrate(context):
    '''This migration function will:

       1) Update values of MeetingConfig.itemMailEvents as format
          of "adviceEdited" values changed.
    '''
    migrator = Migrate_To_4214(context)
    migrator.run()
    migrator.finish()
