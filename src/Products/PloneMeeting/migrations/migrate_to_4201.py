# -*- coding: utf-8 -*-

from Products.Archetypes.event import ObjectEditedEvent
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.event import notify


class Migrate_To_4201(Migrator):

    def _fixWFsUsingReturnedToProposingGroupWFAdaptation(self):
        '''WFAdaptation returned_to_proposing_group was not correctly set up.'''
        logger.info('Updating every MeetingConfigs "returned_to_proposing_group" configuration...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            returned_states = [state_id for state_id in cfg.getItemWorkflow(True).states
                               if state_id.startswith('returned_to_proposing_group')]
            if returned_states:
                # reload config, this will apply WFA correctly
                notify(ObjectEditedEvent(cfg))
                # update WF permissions for items in relevant states
                item_wf = cfg.getItemWorkflow(True)
                brains = self.catalog(
                    portal_type=cfg.getItemTypeName(), review_state=returned_states)
                for brain in brains:
                    item = brain.getObject()
                    item_wf.updateRoleMappingsFor(item)
                    logger.info('Updating WF role mappings for item at %s' % brain.getPath())
        logger.info('Done.')

    def _disableWscForCKeditor(self):
        '''The link 'Check spell' in Scayt button is broken, hide it.'''
        logger.info('CKeditor, adding "wsc" to the removePlugins property...')
        cke_props = self.portal.portal_properties.ckeditor_properties
        cke_props.removePlugins = (u'wsc',)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):
        logger.info('Migrating to PloneMeeting 4201...')

        self._disableWscForCKeditor()

        # refresh if we are not coming from migration to 4200,
        # in this case it was already refreshed
        if not from_migration_to_4200:
            self._fixWFsUsingReturnedToProposingGroupWFAdaptation()


def migrate(context):
    '''This migration function will:

       1) Fix permissions for items in state 'returned_to_proposing_group';
       2) Remove the 'wsc' plugin from CKeditor.
    '''
    migrator = Migrate_To_4201(context)
    migrator.run()
    migrator.finish()
