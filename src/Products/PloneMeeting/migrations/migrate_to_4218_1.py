# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4218_1(Migrator):

    def _removeUsedPodTemplateIdField(self):
        '''The "used_pod_template_id" field was removed from the annex and annexDecision
           models, the POD template an annex is generated from is stored in "conv_from_uid".
           Existing annexes keep their "used_pod_template_id" attribute, still managed,
           see utils.is_generated_annex.'''
        logger.info('Removing field "used_pod_template_id" from annex and annexDecision...')
        load_type_from_package('annex', 'Products.PloneMeeting:default')
        load_type_from_package('annexDecision', 'Products.PloneMeeting:default')
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4218.1...')
        self._removeUsedPodTemplateIdField()
        logger.info('Migrating to PloneMeeting 4218.1... Done.')


def migrate(context):
    """This migration function will:

       1) Remove field "used_pod_template_id" from the annex and annexDecision types.
    """
    migrator = Migrate_To_4218_1(context)
    migrator.run()
    migrator.finish()
