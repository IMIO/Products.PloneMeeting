# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Acquisition import aq_base
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE


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
                    if advice['type'] != NOT_GIVEN_ADVICE_VALUE:
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

    def _finalizeAnnexesCreationProcess(self):
        '''Before, when an item was duplicated with annexes, contained annexes where not fully
           initialized, now it is the case.  Check older annexes and initialize it if necessary.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Finishing creation process for annexes added in %d MeetingItem objects...' % len(brains))
        for brain in brains:
            item = brain.getObject()
            annexes = item.objectValues('MeetingFile')
            for annex in annexes:
                if annex._at_creation_flag:
                    logger.info('Annex at %s was initialized' % annex.absolute_url())
                    annex.processForm()
        logger.info('Done.')

    def _updateMeetingFileTypes(self):
        '''Update MeetingFileTypes as we moved from field 'decisionRelated' that was a boolean
           to 'relatedTo' that is now a list of values in wich available values are 'item', 'item_decision' or 'advice'.
           If MeetingFileType.decisionRelated was False, set MeetingFileType.relatedTo to 'item', if it was True,
           set MeetingFileType.relatedTo to 'item_decision'.'''
        logger.info('Updating MeetingFileTypes relatedTo value')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for mft in cfg.meetingfiletypes.objectValues('MeetingFileType'):
                if not hasattr(aq_base(mft), 'decisionRelated'):
                    # the migration was already executed, we pass...
                    break
                if mft.decisionRelated:
                    mft.setRelatedTo('item_decision')
                else:
                    mft.setRelatedTo('item')
                delattr(mft, 'decisionRelated')
        logger.info('Done.')

    def _updateAnnexIndex(self):
        '''The annexIndex changed (added key 'relatedTo' instead of 'decisionRelated'),
           we need to update it on every items and advices.'''
        logger.info('Updating annexIndex...')
        self.tool.reindexAnnexes()
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.1.1...')
        self._configureCatalogIndexesAndMetadata()
        self._initDefaultBudgetHTML()
        self._updateAdvices()
        self._finalizeAnnexesCreationProcess()
        self._updateMeetingFileTypes()
        self._updateAnnexIndex()
        # reinstall so 'getDeliberation' index is added and computed
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Removed the 'getDecision' index;
       2) Initialize field MeetingConfig.defaultBudget so it behaves correctly has RichText;
       3) Update advices as we moved from MeetingItem.advices to MeetingItem.adviceIndex;
       4) Make sure every existing annexes creation process is correctly finished;
       5) Update MeetingFileTypes as we moved from Boolean:decisionRelated to List:relatedTo;
       6) Update annexIndex as key 'decisionRelated' was replaced by 'relatedTo';
       6) Reinstall PloneMeeting so new index 'getDeliberation' is added and computed.
    '''
    Migrate_To_3_1_1(context).run()
# ------------------------------------------------------------------------------
