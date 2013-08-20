# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_0_2(Migrator):

    def _correctCreatedContentLanguage(self):
        '''Make sure every created content is using site default and site default is correct...'''
        DEFAULT_CONTENT_LANGUAGE = 'fr-be'
        # first thing, make sure current language is correct
        languageTool = self.portal.portal_languages
        languageTool.use_combined_language_codes = True
        languageTool.supported_langs = [DEFAULT_CONTENT_LANGUAGE, ]
        languageTool.setDefaultLanguage(DEFAULT_CONTENT_LANGUAGE)
        languageTool.use_request_negotiation = False
        brains = self.portal.portal_catalog(meta_type=['Meeting', 'MeetingItem', ])
        logger.info('Correcting items and meetings language for %d items...' % len(brains))
        for brain in brains:
            itemOrMeeting = brain.getObject()
            itemOrMeeting.setLanguage(DEFAULT_CONTENT_LANGUAGE)
        # migrate also elements from the MeetingConfigs
        for cfg in self.tool.objectValues('MeetingConfig'):
            for item in cfg.recurringitems.objectValues('MeetingItem'):
                item.setLanguage(DEFAULT_CONTENT_LANGUAGE)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.0.2...')

        self._correctCreatedContentLanguage()
        self.refreshDatabase(catalogs=False,
                             catalogsToRebuild=[],
                             workflows=False)
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration :
       1) Corrects content language.
    '''
    Migrate_To_3_0_2(context).run()
# ------------------------------------------------------------------------------
