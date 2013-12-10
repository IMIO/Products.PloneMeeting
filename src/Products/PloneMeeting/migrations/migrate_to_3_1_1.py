# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Acquisition import aq_base
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
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

    def _updateAdvices(self):
        '''We do not have a MeetingItem.advices anymore, we use MeetingItem.adviceIndex
           and meetingadvice objects.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Updating advices for %d MeetingItem objects...' % len(brains))
        for brain in brains:
            item = brain.getObject()
            if hasattr(aq_base(item), 'advices'):
                for groupId, advice in aq_base(item).advices.iteritems():
                    if advice['type'] != 'not_given':
                        advice_comment = advice['comment']
                        if not isinstance(advice['comment'], unicode):
                            advice_comment = unicode(advice_comment, 'utf-8')
                        meetingadvice = createContentInContainer(item,
                                                                 'meetingadvice',
                                                                 **{'advice_group': groupId,
                                                                 'advice_type': advice['type'],
                                                                 'advice_comment': RichTextValue(advice_comment)})
                        meetingadvice.setCreators((advice['actor'], ))
                        meetingadvice.setCreationDate(advice['date'])
                delattr(item, 'advices')
                # Update security as local_roles are set by updateAdvices
                item.reindexObject()
        logger.info('Updating advices for items of MeetingConfigs...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for item in cfg.recurringitems.objectValues('MeetingItem'):
                if hasattr(aq_base(item), 'advices'):
                    for groupId, advice in aq_base(item).advices.iteritems():
                        createContentInContainer(item,
                                                 'meetingadvice',
                                                 **{'advice_group': groupId,
                                                    'advice_type': advice['type'],
                                                    'advice_comment': RichTextValue(advice['comment'])})
                    delattr(item, 'advices')
                    item.updateAdvices()
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.1...')
        self._configureCatalogIndexesAndMetadata()
        self._initDefaultBudgetHTML()
        self._updateAdvices()
        # reinstall so 'getDeliberation' index is added and computed
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Removed the 'getDecision' index;
       2) Initialize field MeetingConfig.defaultBudget so it behaves correctly has RichText;
       3) Update advices as we moved from MeetingItem.advices to MeetingItem.adviceIndex;
       4) Reinstall PloneMeeting so new index 'getDeliberation' is added and computed.
    '''
    Migrate_To_3_1_1(context).run()
# ------------------------------------------------------------------------------
