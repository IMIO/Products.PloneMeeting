# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4217_1(Migrator):

    def _configureCssTransforms(self):
        """Fields MeetingConfig.cssClassesToHide and MeetingConfig.hideCssClassesTo
           are replaced by MeetingConfig.cssTransforms."""
        logger.info('Configuring new field "MeetingConfig.cssClassesToHide"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not base_hasattr(cfg, 'cssClassesToHide'):
                continue
            res = []
            if cfg.hideCssClassesTo:
                for css_class in cfg.cssClassesToHide().split('\n'):
                    css_class = css_class.strip()
                    if not css_class:
                        continue
                    row = {}
                    row['css_class'] = css_class
                    row['action'] = 'remove'
                    row['replace_new_content'] = ''
                    row['replace_new_css_class'] = ''
                    row['powerobservers'] = cfg.hideCssClassesTo
                    res.append(row)
            cfg.setCssTransforms(res)
            delattr(cfg, 'cssClassesToHide')
            delattr(cfg, 'hideCssClassesTo')
        logger.info('Done.')

    def _updateGroupsInChargeNotes(self):
        """Update config and init new fields related to groupsInChargeNotes."""
        logger.info('Updating "itemFieldsConfig" about groupsInChargeNotes for every MeetingConfigs...')
        # update MeetingConfig.itemFieldsConfig default for "groupsInChargeNotes"
        for cfg in self.tool.objectValues('MeetingConfig'):
            item_fields_config = cfg.getItemFieldsConfig()
            if "groupsInChargeNotes" not in [row['name'] for row in item_fields_config]:
                # use default value
                default_value = cfg.Schema()['itemFieldsConfig'].getDefault(cfg)
                gic_notes_config = [row for row in default_value if row['name'] == "groupsInChargeNotes"]
                if gic_notes_config:
                    gic_notes_config = gic_notes_config[0]
                    item_fields_config += (gic_notes_config, )
                    cfg.setItemFieldsConfig(item_fields_config)
        # update new fields groupsInChargeNotes on items
        self.initNewHTMLFields(
            query={'meta_type': ('MeetingItem')},
            field_names=('groupsInChargeNotes', ))
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.1...')
        self._configureCssTransforms()
        # re-apply annexDecision as insert-barcode permission
        # changed from ModifyPortalContent to View
        load_type_from_package('annexDecision', 'Products.PloneMeeting:default')
        self._updateGroupsInChargeNotes()
        if not from_migration_to_4200:
            # this will upgrade collective.dms.scanbehavior especially
            self.upgradeAll(omit=['Products.PloneMeeting:default',
                                  self.profile_name.replace('profile-', '')])
        logger.info('Migrating to PloneMeeting 4217.1... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure MeetingConfig.cssTransforms;
       2) Re-apply annexDecision portal_type to update "insert-barcode" permission;
       3) Update config and items for new field MeetingItem.groupsInChargeNotes.
    '''
    migrator = Migrate_To_4217_1(context)
    migrator.run()
    migrator.finish()
