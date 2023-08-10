# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4208(Migrator):

    def _updateMeetingOptionalBooleanAttrs(self):
        """Boolean attributes (videoconference and extraordinary_session) were
           wrongly always enabled then disabled when bug was fixed...
           Re-enable fields if used on a meeting of the configuration."""
        logger.info('Re-enabling meetings fields videoconference and '
                    'extraordinary_session if used for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            mAttrs = list(cfg.getUsedMeetingAttributes())
            for field_name in ('videoconference', 'extraordinary_session'):
                if field_name not in mAttrs:
                    for brain in self.catalog(portal_type=cfg.getMeetingTypeName()):
                        meeting = brain.getObject()
                        if getattr(meeting, field_name) is True:
                            mAttrs.append(field_name)
                            break
                cfg.setUsedMeetingAttributes(mAttrs)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4208...')

        self.updateFacetedFilters(
            xml_filename='default_dashboard_meetings_widgets.xml',
            related_to="meetings")
        self.updateFacetedFilters(
            xml_filename='default_dashboard_meetings_widgets.xml',
            related_to="decisions")

        if not from_migration_to_4200:
            # re-apply actions.xml to update documentation url
            self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'actions')
            self._updateMeetingOptionalBooleanAttrs()

        logger.info('Migrating to PloneMeeting 4208... Done.')


def migrate(context):
    '''This migration function will:

       1) Update searches_decisions faceted config;
       2) Re-apply actions.xml to update documentation URL.
    '''
    migrator = Migrate_To_4208(context)
    migrator.run()
    migrator.finish()
