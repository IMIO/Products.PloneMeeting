# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_1_1(Migrator):

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.1...')

        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Nothing yet...
    '''
    Migrate_To_3_1_1(context).run()
# ------------------------------------------------------------------------------
