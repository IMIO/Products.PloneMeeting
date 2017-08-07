# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger('PloneMeeting')
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_4_1(Migrator):

    def run(self, step=None):
        logger.info('Migrating to PloneMeeting 4.1...')
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=False,
                       dependency_strategy=DEPENDENCY_STRATEGY_NEW)
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        # update portal_catalog, index linkedMeetingUID must be updated
        self.refreshDatabase(catalogsToRebuild=['portal_catalog'],
                             workflows=False)


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Reinstall PloneMeeting and upgrade dependencies;
       2) Reinstall plugin if not PloneMeeting;
       3) Refresh catalogs.
    '''
    migrator = Migrate_To_4_1(context)
    migrator.run()
    migrator.finish()
# ------------------------------------------------------------------------------
