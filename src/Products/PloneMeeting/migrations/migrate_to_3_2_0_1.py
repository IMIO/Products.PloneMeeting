# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_2_0_1(Migrator):

    def _updateAdvices(self):
        '''Update advices as we store more informations into it to avoid
           too much computation at view time.'''
        logger.info('Updating advices...')
        self.tool._updateAllAdvices()
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.2.0.1...')
        self._updateAdvices()
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Update adviceIndex because we have more informations into it now.
    '''
    Migrate_To_3_2_0_1(context).run()
# ------------------------------------------------------------------------------
