# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4213(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4212...')
        self.updatePODTemplatesCode(
            replacements={
                '.adapted().getCertifiedSignatures(': ".getCertifiedSignatures("})
        logger.info('Migrating to PloneMeeting 4213... Done.')


def migrate(context):
    '''This migration function will:

       1) Fix POD template as MeetingItem.getCertifiedSignatures is no more
          an adaptable method.
    '''
    migrator = Migrate_To_4213(context)
    migrator.run()
    migrator.finish()
