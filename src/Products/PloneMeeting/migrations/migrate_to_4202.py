# -*- coding: utf-8 -*-

from eea.facetednavigation.interfaces import ICriteria
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.event import notify


class Migrate_To_4202(Migrator):

    def _updateFacetedFilters(self):
        """Update vocabulary used for "Taken over by"."""
        logger.info("Updating faceted filter \"Taken over by\" for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            criteria = ICriteria(cfg.searches.searches_items)
            criteria.edit(
                'c12', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorswithnobodyforfacetedfiltervocabulary'})
        logger.info('Done.')

    def _fixPreAcceptedWFA(self):
        """Update MeetingConfigs using the 'pre_accepted' WFA and
           update workflow mappings for items in state 'pre_accepted'."""
        logger.info('Updating "pre_accepted" WFAdaptation for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if 'pre_accepted' in cfg.getWorkflowAdaptations():
                brains = self.catalog(portal_type=cfg.getItemTypeName(), review_state='pre_accepted')
                logger.info('The "pre_accepted" WFAdaptation was found for "{0}", '
                            'updating "{1}" items...'.format(cfg.getId(), len(brains)))
                notify(ObjectEditedEvent(cfg))
                item_wf = cfg.getItemWorkflow(True)
                for brain in brains:
                    item = brain.getObject()
                    changed = item_wf.updateRoleMappingsFor(item)
                    if changed:
                        item.reindexObjectSecurity()
        logger.info('Done.')

    def _fixFacetedFoldersConstrainTypes(self):
        """Fix constrainTypes for every faceted folder stored in user personnal folder."""
        logger.info('Updating searches_... folders constraintypes for every users...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            folders = cfg._get_all_meeting_folders()
            for folder in folders:
                sub_folders = [sub_folder for sub_folder in folder.objectValues('ATFolder')
                               if sub_folder.getId().startswith('searches_')]
                for sub_folder in sub_folders:
                    constrain = IConstrainTypes(sub_folder)
                    constrain.setConstrainTypesMode(1)
                    allowedTypes = []
                    constrain.setLocallyAllowedTypes(allowedTypes)
                    constrain.setImmediatelyAddableTypes(allowedTypes)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4202...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            self._updateFacetedFilters()
            self._fixPreAcceptedWFA()

        # this is not managed by the main upgrade to 4200
        self._fixFacetedFoldersConstrainTypes()


def migrate(context):
    '''This migration function will:

       1) Update the vocabulary used by the "c12" faceted filter (Taken over by);
       2) Fix the MeetingConfigs and items using the 'pre_accepted' WFAdaptation;
       3) Fix constrainTypes for every faceted folder of every users.
    '''
    migrator = Migrate_To_4202(context)
    migrator.run()
    migrator.finish()
