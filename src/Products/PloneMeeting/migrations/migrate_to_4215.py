# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
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

    def _reloadMeetingConfigsForItemWorkflows(self):
        """Reload MeetingConfigs so if using "return_to_proposing_group" with validation."""
        logger.info("Updating item WF using 'return_to_proposing_group with validation'...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if len([state_id for state_id in cfg.getItemWorkflow(True)
                    if state_id.startswith('returned_to_proposing_group')]) > 1:
                cfg.registerPortalTypes()
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
        self._updateConfigCustomAdvisersDataGrid()
        self._reloadMeetingConfigsForItemWorkflows()
        logger.info('Migrating to PloneMeeting 4215... Done.')


def migrate(context):
    '''This migration function will:

       1) Upgrade all and make sure documentgenerator overrides are re-applied;
       2) Update MeetingConfig.customAdvisers to add new column "is_delay_calendar_days";
       3) Reload MeetingConfigs if using "return_to_proposing_group" with validation.
    '''
    migrator = Migrate_To_4215(context)
    migrator.run()
    migrator.finish()
