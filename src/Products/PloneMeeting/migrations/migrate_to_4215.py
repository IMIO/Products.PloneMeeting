# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4215(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4215...')
        # update new fields committeeTranscript and votesResult on items
        self.initNewHTMLFields(
            query={'meta_type': ('MeetingItem')},
            field_names=('emergencyMotivation', ))
        logger.info('Done.')
        logger.info('Migrating to PloneMeeting 4215... Done.')


def migrate(context):
    '''This migration function will:

       1) Init new MeetingItem field 'emergencyMotivation'.

    '''
    migrator = Migrate_To_4215(context)
    migrator.run()
    migrator.finish()
