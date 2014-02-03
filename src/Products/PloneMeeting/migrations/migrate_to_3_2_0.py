# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from Acquisition import aq_base
from persistent.mapping import PersistentMapping

from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.content.advice import MeetingAdvice


# The migration class ----------------------------------------------------------
class Migrate_To_3_2_0(Migrator):

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
        original_updateAdviceRowId = MeetingAdvice._updateAdviceRowId

        def _fakeUpdateAdviceRowId(self):
            '''This does almost nothing...'''
            return
        # we override MeetingAdvice._updateAdviceRowId to do nothing
        # because this method expect the MeetingItem.indexAdviser and we do not still have it here
        # this method set the row_id on the created meetingadvice but we do it manually here under
        MeetingAdvice._updateAdviceRowId = _fakeUpdateAdviceRowId
        for brain in brains:
            item = brain.getObject()
            cfg = self.tool.getMeetingConfig(item)
            if hasattr(aq_base(item), 'advices'):
                # first make sure given advices are still selected in the optionalAdvisers
                # or in the automaticAdvisers.  If given advice was optional and is no more
                # in optionalAdvisers, we can add it if it was a mandatory that is no more in
                # automaticAdvisers, we have to Raise...
                storedOptionalAdvisers = list(item.getOptionalAdvisers())
                # store here nasty things we will have to do if we can not find an automatic adviser
                specialAutomaticAdviceHandling = {}
                for key, value in item.advices.items():
                    if value['type'] != NOT_GIVEN_ADVICE_VALUE:
                        if value['optional']:
                            if not key in storedOptionalAdvisers:
                                storedOptionalAdvisers.append(key)
                                item.setOptionalAdvisers(storedOptionalAdvisers)
                        else:
                            # it is supposed to be an automatic adviser...
                            automaticAdvisersIds = [auto['meetingGroupId'] for auto in item.getAutomaticAdvisers()]
                            if not key in automaticAdvisersIds:
                                # find a row in cfg.customAdvisers that could be used...
                                for customAdviser in cfg.getCustomAdvisers():
                                    # if we find a row regarding this group and that is an automatic adviser, use it...
                                    if customAdviser['group'] == key and customAdviser['gives_auto_advice_on']:
                                        specialAutomaticAdviceHandling[key] = customAdviser['row_id']
                                    else:
                                        raise Exception("An automatic adviser lost his configuration...")

                item.adviceIndex = PersistentMapping()
                # in case there were advices asked but not given, we will have to update advice
                for groupId, advice in aq_base(item).advices.iteritems():
                    if advice['type'] != NOT_GIVEN_ADVICE_VALUE:
                        # advices are updated upon each meetingadvice add
                        advice_comment = advice['comment']
                        if not isinstance(advice['comment'], unicode):
                            advice_comment = unicode(advice_comment, 'utf-8')
                        # find the row_id if it is an automatic advice
                        if not advice['optional']:
                            if groupId in specialAutomaticAdviceHandling:
                                row_id = specialAutomaticAdviceHandling[groupId]
                            else:
                                automaticAdvisers = item.getAutomaticAdvisers()
                                for automaticAdviser in automaticAdvisers:
                                    if automaticAdviser['meetingGroupId'] == groupId:
                                        row_id = automaticAdviser['row_id']
                        meetingadvice = createContentInContainer(item,
                                                                 'meetingadvice',
                                                                 **{'advice_group': groupId,
                                                                    'advice_type': advice['type'],
                                                                    'advice_comment': RichTextValue(advice_comment),
                                                                    'advice_row_id': row_id, })
                        meetingadvice.creators = ((advice['actor'], ))
                        meetingadvice.creation_date = advice['date']
                        meetingadvice.modification_date = advice['date']
                delattr(item, 'advices')
                item.updateAdvices()
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
        MeetingAdvice._updateAdviceRowId = original_updateAdviceRowId
        logger.info('Done.')

    def _addBudgetImpactEditorsGroupsByMeetingConfig(self):
        '''Now that we can define some specifig users that will be able to edit budgetInfos related
           informations on an item, we have a group for each MeetingConfig where we will store these
           budgetimpacteditor users.'''
        logger.info('Adding \'budgetimpacteditor\' groups for each meetingConfig')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            cfg.createBudgetImpactEditorsGroup()
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
        logger.info('Updating MeetingFileTypes relatedTo value...')
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

    def _cleanReferencesOnItems(self):
        '''As ReferenceFields 'annexes' and 'annexesDecision' were removed from MeetingItem,
           we need to clean up the at_references folder on every items.'''
        brains = self.portal.portal_catalog(meta_type=('MeetingItem', ))
        logger.info('Cleaning references for %d MeetingItem objects...' % len(brains))
        for brain in brains:
            item = brain.getObject()
            item.deleteReferences(relationship="ItemAnnexes")
            item.deleteReferences(relationship="DecisionAnnexes")
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            for item in cfg.recurringitems.objectValues('MeetingItem'):
                item.deleteReferences(relationship="ItemAnnexes")
                item.deleteReferences(relationship="DecisionAnnexes")
        logger.info('Done.')

    def _finishExternalApplicationRemoval(self):
        '''As we removed the class 'ExternalApplication', we need to update some parts
           that were related :
           - the attribute 'siteStardDate' on portal_plonemeeting;
           - the portal_type 'ExternalApplication';
           - '''
        logger.info('Finishing \'ExternalApplication\' removal...')
        if hasattr(aq_base(self.tool), 'siteStartDate'):
            delattr(aq_base(self.tool), 'siteStartDate')
        if 'ExternalApplication' in self.portal.portal_types.objectIds():
            self.portal.portal_types.manage_delObjects(ids=['ExternalApplication', ])
        logger.info('Done.')

    def _migrateMandatoryAdvisers(self):
        '''
          The MeetingGroup.givesMandatoryAdviceOn attribute disappeared and is replaced
          by the MeetingConfig.customAdvisers management, so migrate givesMandatoryAdviceOn
          attributes.
        '''
        logger.info('Migrating mandatory advisers...')
        # just migrate active MeetingGroups givesMandatoryAdviceOn attribute
        # but remove existing givesMandatoryAdviceOn attribute on every groups
        newMCCustomAdvisersValue = []
        for mGroup in self.tool.getMeetingGroups():
            if not hasattr(aq_base(mGroup), 'givesMandatoryAdviceOn'):
                # already migrated
                return
            givesMandatoryAdviceOn = mGroup.givesMandatoryAdviceOn.replace(' ', '')
            if givesMandatoryAdviceOn and givesMandatoryAdviceOn not in ('python:False', 'python:False;', 'False'):
                newMCCustomAdvisersValue.append(
                    {'group': mGroup.getId(),
                     # we can not do anything else but activate it from the beginning...
                     'for_item_created_from': self.portal.created().strftime('%Y/%m/%d'),
                     'gives_auto_advice_on': givesMandatoryAdviceOn,
                     'row_id': self.portal.generateUniqueId(), })
            delattr(aq_base(mGroup), 'givesMandatoryAdviceOn')
        for cfg in self.tool.getActiveConfigs():
            cfg.setCustomAdvisers(newMCCustomAdvisersValue)
        logger.info('Done.')

    def _addMissingTopics(self):
        '''Make sure the 2 topics 'searchcorrecteditems' and 'searchitemstocorrect'
           exist in each MeetingConfigs.'''
        logger.info('Adding new topics to every MeetingConfigs...')
        # change MeetingConfig.topics info so we can use the MeetingConfig.createTopics
        # method, we will come back to previous value at the end of this method
        from Products.PloneMeeting.MeetingConfig import MeetingConfig
        newTopicsInfo = (
            # Items to advice with delay : need a script to do this search
            ('searchitemstoadvicewithdelay',
            (('Type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ),
             'created',
             'searchItemsToAdviceWithDelay',
             "python: here.portal_plonemeeting.getMeetingConfig(here)."
             "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
             ),
            # Items to advice with exceeded delay : need a script to do this search
            ('searchitemstoadvicewithdexceededelay',
            (('Type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ),
             'created',
             'searchItemsToAdviceWithExceededDelay',
             "python: here.portal_plonemeeting.getMeetingConfig(here)."
             "getUseAdvices() and here.portal_plonemeeting.userIsAmong('advisers')",
             ),
            # Items to correct : search items in state 'returned_to_proposing_group'
            ('searchitemstocorrect',
            (('Type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ('review_state', 'ATListCriterion', ('returned_to_proposing_group',)),
             ),
             'created',
             '',
             "python: here.portal_plonemeeting.userIsAmong('creators') and "
             "'return_to_proposing_group' in here.getWorkflowAdaptations()",
             ),
            # Corrected items : search items for wich previous_review_state was 'returned_to_proposing_group'
            ('searchcorrecteditems',
            (('Type', 'ATPortalTypeCriterion', ('MeetingItem',)),
             ('previous_review_state', 'ATListCriterion', ('returned_to_proposing_group',)),
             ),
             'created',
             '',
             "python: here.portal_plonemeeting.isManager() and "
             "'return_to_proposing_group' in here.getWorkflowAdaptations()",
             ),
        )
        originalTopicsInfos = MeetingConfig.topicsInfo
        MeetingConfig.topicsInfo = newTopicsInfo
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            # createTopics manage the fact that the topic already exists
            cfg.createTopics()
            # now reorder so advice related topics are all together
            for adviceRelatedTopicId in ['searchitemstoadvicewithdexceededelay', 'searchitemstoadvicewithdelay']:
                # find delta, we need to insert into after the 'searchallitemstoadvice' topic
                if not hasattr(cfg.topics, 'searchallitemstoadvice'):
                    logger.error('Unable to find topic \'searchallitemstoadvice\' !!!  '
                                 'New advice related topics will be left at the bottom of available topics!')
                    return
                baseTopic = cfg.topics.searchallitemstoadvice
                everyTopicIds = cfg.topics.objectIds()
                baseTopicPosition = everyTopicIds.index(baseTopic.getId())
                adviceRelatedTopicPosition = everyTopicIds.index(adviceRelatedTopicId)
                delta = adviceRelatedTopicPosition - baseTopicPosition - 1
                cfg.topics.moveObjectsUp(adviceRelatedTopicId, delta=delta)

        MeetingConfig.topicsInfo = originalTopicsInfos
        logger.info('Done.')

    def _adaptMeetingGroupsAdviceStates(self):
        '''The vocabulary of MeetingGroups itemAdviceStates fields changed to take
           into account every active MeetingConfigs and not only the default one, so
           adapt existing values...'''
        logger.info('Migrating MeetingGroups itemAdviceStates attributes...')
        # migrate every existing MeetingGroups
        defaultCfg = self.tool.getDefaultMeetingConfig()
        if not defaultCfg:
            logger.error('Unable to find the default MeetingConfig, \'itemAdviceStates\' '
                         'attributes of MeetingGroups were not migrated !!!')
        defaultCfgId = defaultCfg.getId()
        mappings = {}
        for key, value in defaultCfg.listStates('Item'):
            mappings[key] = '%s__state__%s' % (defaultCfgId, key)
        for mGroup in self.tool.getMeetingGroups():
            if mGroup.getItemAdviceStates():
                newValue = [mappings[state] for state in mGroup.getItemAdviceStates()]
                mGroup.setItemAdviceStates(newValue)
            if mGroup.getItemAdviceEditStates():
                newValue = [mappings[state] for state in mGroup.getItemAdviceEditStates()]
                mGroup.setItemAdviceEditStates(newValue)
            if mGroup.getItemAdviceViewStates():
                newValue = [mappings[state] for state in mGroup.getItemAdviceViewStates()]
                mGroup.setItemAdviceViewStates(newValue)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 3.2.0...')
        # reinstall so 'getDeliberation' index is added and computed, new 'meetingadvice' type is installed, ...
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default', ])
        self._configureCatalogIndexesAndMetadata()
        self._initDefaultBudgetHTML()
        self._migrateMandatoryAdvisers()
        self._updateAdvices()
        self._addBudgetImpactEditorsGroupsByMeetingConfig()
        self._finalizeAnnexesCreationProcess()
        self._updateMeetingFileTypes()
        self._updateAnnexIndex()
        self._cleanReferencesOnItems()
        self._finishExternalApplicationRemoval()
        self._addMissingTopics()
        self._adaptMeetingGroupsAdviceStates()
        # refresh reference_catalog as 2 ReferenceFields were removed on MeetingItem (annexes and annexesDecision)
        self.refreshDatabase(catalogs=True,
                             catalogsToRebuild=['reference_catalog', ],
                             workflows=False)
        self.finish()


# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Reinstall PloneMeeting before migration because we need some stuff configured at install time;
       2) Removed the 'getDecision' index;
       3) Initialize field MeetingConfig.defaultBudget so it behaves correctly has RichText;
       4) Migrate mandatory advisers infos from MeetingGroups to MeetingConfig.customAdvisers;
       5) Update advices as we moved from MeetingItem.advices to MeetingItem.adviceIndex;
       6) Add a 'budgetimpacteditors' group by MeetingConfig;
       7) Make sure every existing annexes creation process is correctly finished;
       8) Update MeetingFileTypes as we moved from Boolean:decisionRelated to List:relatedTo;
       9) Update annexIndex as key 'decisionRelated' was replaced by 'relatedTo';
       10) Clean ItemAnnexes and DecisionAnnexes references on items;
       11) Finish 'ExternalApplication' removal;
       12) Add missing topics regarding the 'send back to proposing group' WFAdaptation;
       13) Reinstall PloneMeeting so new index 'getDeliberation' is added and computed.
    '''
    Migrate_To_3_2_0(context).run()
# ------------------------------------------------------------------------------
