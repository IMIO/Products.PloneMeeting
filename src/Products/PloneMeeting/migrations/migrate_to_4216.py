# -*- coding: utf-8 -*-

from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.MeetingConfig import defValues
from Products.PloneMeeting.MeetingConfig import PROPOSINGGROUPPREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
import copy


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
            # replace call to getEnableLabels in TAL expressions
            self.updateTALConditions(
                "cfg.getEnableLabels()", "'labels' in cfg.getUsedItemAttributes()")
            # migrate MeetingConfig.itemLabelsEditableByProposingGroupForever
            # if True, let current config, if False, define "edit_access_on"
            # to check for ModifyPortalContent on context or isManager
            # fix labelsConfig as it is taken from MeetingConfigDescriptor
            # for every cfg, it shares the same dict...
            labels_config = copy.deepcopy(defValues.labelsConfig)
            cfg.setLabelsConfig(labels_config)
            if cfg.itemLabelsEditableByProposingGroupForever:
                # remove duplicates
                suffixes = tuple(set(cfg.getItemWFValidationLevels(data='suffix', only_enabled=True)))
                edit_groups = [PROPOSINGGROUPPREFIX + suffix for suffix in suffixes]
                labels_config[0]["edit_groups"] = edit_groups
            else:
                labels_config[0]["edit_access_on"] = \
                    'python: cfg.isManager(cfg) or checkPermission("Modify portal content", context)'
            cfg.setLabelsConfig(labels_config)
            delattr(cfg, 'itemLabelsEditableByProposingGroupForever')
            # update labels cache for items of this MeetingConfig
            cfg.update_labels_access_cache(redirect=False)
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
