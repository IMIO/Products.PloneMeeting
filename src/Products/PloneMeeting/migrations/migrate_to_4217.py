# -*- coding: utf-8 -*-

from imio.esign.interfaces import IImioSessionsManagementContext
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.interface import alsoProvides


class Migrate_To_4217(Migrator):

    def _configureEsign(self):
        """Configure imio.esign."""
        logger.info('Configuring imio.esign...')
        # install imio.esign
        self.reinstall(['profile-imio.esign:default'])
        # add searchitemsinesignsessions
        self.addNewSearches()
        # mark every PM Folder with IImioSessionsManagementContext
        # so the @@esign-sessions-listing is available
        #for user_folder in self.portal.Members.objectValues():
        #    mymeetings = getattr(user_folder, 'mymeetings', None)
        #    if not mymeetings:
        #        continue
        #    for cfg in self.tool.objectValues('MeetingConfig'):
        #        meeting_folder = getattr(mymeetings, cfg.getId(), None)
        #        if not meeting_folder:
        #            continue
        #        alsoProvides(meeting_folder, IImioSessionsManagementContext)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217...')
        self._configureEsign()
        logger.info('Migrating to PloneMeeting 4217... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure imio.esign.

    '''
    migrator = Migrate_To_4217(context)
    migrator.run()
    migrator.finish()
