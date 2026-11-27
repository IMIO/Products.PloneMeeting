# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.migrations.migrate_to_4217 import Migrate_To_4217
from Products.PloneMeeting.migrations.migrate_to_4217_1 import Migrate_To_4217_1
from Products.PloneMeeting.migrations.migrate_to_4217_2 import Migrate_To_4217_2
from Products.PloneMeeting.migrations.migrate_to_4217_3 import Migrate_To_4217_3
from Products.PloneMeeting.migrations.migrate_to_4217_4 import Migrate_To_4217_4
from Products.PloneMeeting.migrations.migrate_to_4218 import Migrate_To_4218


class Migrate_To_4218_1(Migrator):

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4218.1...')
        # sites migrated with the first version of the upgrade step to 4218
        # (4217 -> 4218) did not run upgrade steps 4217.1 to 4217.4 added after,
        # 4217 is run again as it is cheap and the 4216 -> 4217 step was
        # wrongly registered with the 4216 handler for a while
        Migrate_To_4217(self.portal).run()
        Migrate_To_4217_1(self.portal).run()
        Migrate_To_4217_2(self.portal).run()
        Migrate_To_4217_3(self.portal).run()
        Migrate_To_4217_4(self.portal).run()
        # step added to 4218 after its first version
        Migrate_To_4218(self.portal)._configureExtraAllowedContentForCKeditor()
        logger.info('Migrating to PloneMeeting 4218.1... Done.')


def migrate(context):
    '''This migration function will:

       1) Run upgrade steps 4217 to 4217.4, 4217.1 to 4217.4 were added after
          the first version of the upgrade step to 4218;
       2) Configure CKeditor "extraAllowedContent" to accept "tal:" attributes,
          added to the upgrade step to 4218 after its first version.
    '''
    migrator = Migrate_To_4218_1(context)
    migrator.run()
    migrator.finish()
