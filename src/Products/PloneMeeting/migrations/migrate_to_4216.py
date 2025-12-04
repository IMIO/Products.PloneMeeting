# -*- coding: utf-8 -*-

from imio.helpers.content import safe_delattr
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.MeetingConfig import defValues
from Products.PloneMeeting.MeetingConfig import PROPOSINGGROUPPREFIX
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator

import copy


class Migrate_To_4216(Migrator):

    def _updateLabelsConfig(self):
        """Update for new field MeetingConfig.labelsConfig."""
        logger.info('Updating for new field "MeetingConfig.labelsConfig"...')
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
            # be defensive with itemLabelsEditableByProposingGroupForever that
            # is recent and could not exist in some MeetingConfigs
            if getattr(cfg, 'itemLabelsEditableByProposingGroupForever', False):
                edit_groups = ['configgroup_meetingmanagers']
                suffixes = tuple(set(cfg.getItemWFValidationLevels(data='suffix', only_enabled=True)))
                edit_groups += [PROPOSINGGROUPPREFIX + suffix for suffix in suffixes]
                labels_config[0]["edit_groups"] = edit_groups
            else:
                labels_config[0]["edit_access_on"] = \
                    'python: cfg.isManager(cfg) or checkPermission("Modify portal content", context)'
                labels_config[0]["edit_access_on_cache"] = "0"
                labels_config[0]["edit_groups"] = []
            cfg.setLabelsConfig(labels_config)
            safe_delattr(cfg, 'itemLabelsEditableByProposingGroupForever')
            # update labels cache for items of this MeetingConfig
            if 'labels' in cfg.getUsedItemAttributes():
                cfg.update_labels_access_cache(redirect=False)
        # reindex the "labels" portal_catalog index as we manage special
        # empty value when no global label selected
        self.reindexIndexes(idxs=['labels'], meta_types=['MeetingItem'])
        logger.info('Done.')

    def _updateFollowUp(self):
        """Update config and init new fields related to follow-up."""
        logger.info('Updating datagridfield "itemFieldsConfig" about followUp for every MeetingConfigs...')
        # update new fields neededFollowUp and providedFollowUp on items
        self.initNewHTMLFields(
            query={'meta_type': ('MeetingItem')},
            field_names=('neededFollowUp', 'providedFollowUp'))
        # add searchitemswithneededfollowup and searchitemswithprovidedfollowup
        self.addNewSearches()
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4216...')
        # remove broken annexes before upgrading collective.iconifiedcategory
        self._removeBrokenAnnexes()
        if not from_migration_to_4200:
            # this will upgrade collective.iconifiedcategory especially
            self.upgradeAll(omit=['Products.PloneMeeting:default',
                                  self.profile_name.replace('profile-', '')])
        self._updateLabelsConfig()
        self._updateFollowUp()
        logger.info('Migrating to PloneMeeting 4216... Done.')


def migrate(context):
    '''This migration function will:

       1) Update application regarding new field MeetingConfig.labelsConfig;
       2) Update config and items regarding follow-up.

    '''
    migrator = Migrate_To_4216(context)
    migrator.run()
    migrator.finish()
