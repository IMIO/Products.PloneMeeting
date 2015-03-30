# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_4(Migrator):

    def _updateItemsListVisibleFields(self):
        '''MeetingConfig.itemsListVisibleFields stored values changed from
           'description, decision' to 'MeetingItem.description, MeetingItem.decision'.'''
        logger.info('Updating itemsListVisibleFields field for each MeetingConfig...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            fields = cfg.getItemsListVisibleFields()
            if fields and not fields[0].startswith('MeetingItem.'):
                res = []
                for field in fields:
                    res.append('MeetingItem.{0}'.format(field))
                cfg.setItemsListVisibleFields(res)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.4...')
        self.cleanRegistries()
        self._updateItemsListVisibleFields()
        # reinstall so versions are correctly shown in portal_quickinstaller
        # and new stuffs are added (portal_catalog metadata especially, imio.history is installed)
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function will:

       1) Update MeetingConfig.itemsListVisibleFields stored values;
       2) Reinstall PloneMeeting;
    '''
    Migrate_To_3_4(context).run()
# ------------------------------------------------------------------------------
