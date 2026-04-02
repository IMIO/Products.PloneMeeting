# -*- coding: utf-8 -*-

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

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4217.1...')
        self._configureCssTransforms()
        logger.info('Migrating to PloneMeeting 4217.1... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure MeetingConfig.cssTransforms.
    '''
    migrator = Migrate_To_4217_1(context)
    migrator.run()
    migrator.finish()
