# -*- coding: utf-8 -*-

from Products.PloneMeeting.config import ANONYMIZED_TEXT_INDEXES
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import get_anonymized_css_classes


class Migrate_To_4217_5(Migrator):

    def _reindexAnonymizedText(self):
        """Words of content anonymized for some power observers
           (MeetingConfig.cssTransforms) are now prefixed in the text indexes,
           reindex these indexes for items and meetings of MeetingConfigs
           anonymizing content."""
        logger.info('Reindexing text indexes of items and meetings having anonymized content...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if get_anonymized_css_classes(cfg):
                self.reindexIndexesFor(
                    idxs=list(ANONYMIZED_TEXT_INDEXES),
                    portal_type=cfg.getItemTypeName(configType='all') + [cfg.getMeetingTypeName()])
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.5...')
        self._reindexAnonymizedText()
        logger.info('Migrating to PloneMeeting 4217.5... Done.')


def migrate(context):
    """This migration function will:

       1) Reindex text indexes of items and meetings of MeetingConfigs anonymizing content.
    """
    migrator = Migrate_To_4217_5(context)
    migrator.run()
    migrator.finish()
