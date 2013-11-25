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

    def _initDefaultBudgetHTML(self):
        '''We changed type of field MeetingConfig.budgetInfos from text to rich, we need to update
           existing MeetingConfigs so the field is correctly initialized.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Initializing new field MeetingItem.motivation for %d MeetingItem objects...' % len(brains))
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            field = cfg.getField('budgetDefault')
            if field.getContentType(cfg) == 'text/html':
                continue
            cfg.setBudgetDefault(field.get(cfg))
            field.setContentType(cfg, 'text/html')
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.1...')
        self._configureCatalogIndexesAndMetadata()
        self._initDefaultBudgetHTML()
        # reinstall so 'getDeliberation' index is added and computed
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Removed the 'getDecision' index;
       2) Initialize field MeetingConfig.defaultBudget so it behaves correctly has RichText;
       3) Reinstall PloneMeeting so new index 'getDeliberation' is added and computed.
    '''
    Migrate_To_3_1_1(context).run()
# ------------------------------------------------------------------------------
