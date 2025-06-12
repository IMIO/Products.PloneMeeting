# -*- coding: utf-8 -*-

from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4216(Migrator):

    def _updateLabelsConfig(self):
        """Update for new field MeetingConfig.labelsConfig."""
        logger.info('Updaging for new field "MeetingConfig.labelsConfig"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # migrate MeetingConfig.enableLabels to MeetingConfig.usedItemAttributes
            if not base_hasattr(cfg, 'enableLabels'):
                continue
            if cfg.enableLabels:
                logger.info("'labels' was enabled for MeetingConfig %s" % cfg.getId())
                used_item_attrs = list(cfg.getUsedItemAttributes())
                used_item_attrs.append('labels')
                cfg.setUsedItemAttributes(used_item_attrs)
            delattr(cfg, 'enableLabels')
            # replace call to getEnaleLabels in TAL expressions
            self.updateTALConditions(
                "cfg.getEnableLabels()", "'labels' in cfg.getUsedAttributes()")
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4216...')
        self._updateLabelsConfig()
        logger.info('Migrating to PloneMeeting 4216... Done.')


def migrate(context):
    '''This migration function will:

       1) Update application regarding new field MeetingConfig.labelsConfig.

    '''
    migrator = Migrate_To_4216(context)
    migrator.run()
    migrator.finish()
