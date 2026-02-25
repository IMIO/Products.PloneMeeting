# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4217(Migrator):

    def _configureEsign(self):
        """Configure imio.esign."""
        logger.info('Configuring imio.esign...')
        # install imio.esign
        self.reinstall(['profile-imio.esign:default'])
        # add searchitemsinesignsessions
        self.addNewSearches()
        # update type ConfigurablePODTemplate to add esign_signers_expr field
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        # create esignwatchers group per MeetingConfig
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg._createOrUpdateAllPloneGroups()
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217...')
        if not from_migration_to_4200:
            # this will upgrade collective.contact.plonegroup especially
            self.upgradeAll(omit=['Products.PloneMeeting:default',
                                  self.profile_name.replace('profile-', '')])
        self._configureEsign()
        logger.info('Migrating to PloneMeeting 4217... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure imio.esign.

    '''
    migrator = Migrate_To_4217(context)
    migrator.run()
    migrator.finish()
