# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4300(Migrator):

    def _migrateMeetingConfigsToDexterity(self):
        """Migrate MeetingConfig instances from Archetypes OrderedBaseFolder
        to Dexterity Container by re-applying the new DX FTI.

        Field data migration from AT storage to DX storage is handled by the
        Dexterity framework when objects are first accessed after the FTI switch.
        """
        logger.info('Re-applying MeetingConfig DX FTI...')
        load_type_from_package('MeetingConfig', 'Products.PloneMeeting:default')
        logger.info('Re-applying MeetingConfig DX FTI... Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):
        logger.info('Migrating to PloneMeeting 4300...')
        self._migrateMeetingConfigsToDexterity()
        logger.info('Migrating to PloneMeeting 4300... Done.')


def migrate(context):
    '''This migration function will:

       1) Migrate MeetingConfig portal type from Archetypes to Dexterity
          by re-applying the new DX FTI.
    '''
    migrator = Migrate_To_4300(context)
    migrator.run()
    migrator.finish()
