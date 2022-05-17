# -*- coding: utf-8 -*-

from eea.facetednavigation.interfaces import ICriteria
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


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
                cfg.at_post_edit_script()
                item_wf = cfg.getItemWorkflow(True)
                for brain in brains:
                    item = brain.getObject()
                    changed = item_wf.updateRoleMappingsFor(item)
                    if changed:
                        item.reindexObjectSecurity()
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4202...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            self._updateFacetedFilters()
            self._fixPreAcceptedWFA()


def migrate(context):
    '''This migration function will:

       1) Update the vocabulary used by the "c12" faceted filter (Taken over by);
       2) Fix the MeetingConfigs and items using the 'pre_accepted' WFAdaptation.
    '''
    migrator = Migrate_To_4202(context)
    migrator.run()
    migrator.finish()
