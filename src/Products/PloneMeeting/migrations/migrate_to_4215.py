# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4215(Migrator):

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
        self._updateConfigCustomAdvisersDataGrid()
        logger.info('Migrating to PloneMeeting 4215... Done.')


def migrate(context):
    '''This migration function will:

       1) Update MeetingConfig.customAdvisers to add new column "is_delay_calendar_days".

    '''
    migrator = Migrate_To_4215(context)
    migrator.run()
    migrator.finish()
