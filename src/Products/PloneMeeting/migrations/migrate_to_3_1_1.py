# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_1_1(Migrator):

    def _configureCatalogIndexesAndMetadata(self):
        '''Remove the 'getDecision' index, as it is replaced by 'getDeliberation',
           reindex the 'Description' index as we index the 'text/plain' version now.'''
        logger.info('Configuring portal_catalog')
        if 'getDecision' in self.portal.portal_catalog.indexes():
            self.portal.portal_catalog.delIndex('getDecision')
        self.portal.portal_catalog.manage_reindexIndex('Description')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.1...')
        self._configureCatalogIndexesAndMetadata()
        # reinstall so 'getDeliberation' index is added and computed
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Removed the 'getDecision' index;
       2) Reinstall PloneMeeting so new index 'getDeliberation' is added and computed.
    '''
    Migrate_To_3_1_1(context).run()
# ------------------------------------------------------------------------------
