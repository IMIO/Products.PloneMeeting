# -*- coding: utf-8 -*-

from ftw.labels.interfaces import ILabelJar
from persistent.mapping import PersistentMapping
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4102(Migrator):

    def _updateFTWLabelsStorage(self):
        """ftw.labels jar was created using dict we need PersistentMappings..."""
        logger.info("Updating ftw.labels jar for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            jar_storage = ILabelJar(cfg).storage
            for k, v in jar_storage.items():
                jar_storage[k] = PersistentMapping(v)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 4102...')
        self._updateFTWLabelsStorage()


def migrate(context):
    '''This migration function will:

       1) Update ftw.labels jar storage to use PersistentMappings.
    '''
    migrator = Migrate_To_4102(context)
    migrator.run()
    migrator.finish()
