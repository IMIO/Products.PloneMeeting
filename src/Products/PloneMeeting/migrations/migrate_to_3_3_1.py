# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields


# The migration class ----------------------------------------------------------
class Migrate_To_3_3_1(Migrator):

    def _initNewHTMLFields(self):
        '''The MeetingItem and Meeting receive to new HTML fields 'notes' and 'inAndOutMoves',
           make sure the content_type is correctly set to 'text/html'.'''
        logger.info('Initializing new HTML fields on meeting and items...')
        brains = self.portal.portal_catalog(meta_type=('Meeting', 'MeetingItem', ))
        check_already_migrated = False
        for brain in brains:
            itemOrMeeting = brain.getObject()
            # check if already migrated
            if not check_already_migrated:
                field = itemOrMeeting.getField('notes')
                content_type = field.getContentType(itemOrMeeting, fromBaseUnit=False)
                if content_type == 'text/html':
                    break
                check_already_migrated = True
            # not already migrated, do it...
            forceHTMLContentTypeForEmptyRichFields(itemOrMeeting)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.3.1...')
        self._initNewHTMLFields()
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Init new HTML fields on MeetingItem and Meeting.
    '''
    Migrate_To_3_3_1(context).run()
# ------------------------------------------------------------------------------
