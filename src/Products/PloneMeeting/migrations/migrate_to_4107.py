# -*- coding: utf-8 -*-

from plone import api
from Products.cron4plone.browser.configlets.cron_configuration import ICronConfiguration
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.component import queryUtility


class Migrate_To_4107(Migrator):

    def _moveToItemCreatedOnlyUsingTemplate(self):
        """Empty item are now also created using an itemTemplate, move to it."""
        logger.info("Moving to empty item created from an item template...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            default_template = cfg._create_default_item_template()
            if default_template:
                # move it to the top
                folder = default_template.aq_inner.aq_parent
                folder.folder_position_typeaware(position='top', id=default_template.getId())
                # if cfg.itemCreatedOnlyUsingTemplate was True, disable created default template
                if getattr(cfg, 'itemCreatedOnlyUsingTemplate', False) is True:
                    api.content.transition(default_template, transition='deactivate')
        # remove useless MeetingConfig.itemCreatedOnlyUsingTemplate field
        self.cleanMeetingConfigs(field_names=['itemCreatedOnlyUsingTemplate'])
        logger.info('Done.')

    def _registerMeetingFactoryTypes(self):
        """Make sure every relevant portal_types are correctly registered in portal_factory."""
        logger.info("Registering every Meeting types into portal_factory...")
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'factorytool')
        # This will register portal_types to portal_factory
        self.reloadMeetingConfigs()
        logger.info('Done.')

    def _updateUpdateDelayAwareAdvicecsCronJobTime(self):
        """Set @@update-delay-aware-advices cronjob time to 01:45."""
        logger.info("Setting cronjob for @@update-delay-aware-advices to 01:45...")
        cron_configlet = queryUtility(ICronConfiguration, 'cron4plone_config')
        cron_configlet.cronjobs = [u'45 1 * * portal/@@update-delay-aware-advices']
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4107...')
        self._moveToItemCreatedOnlyUsingTemplate()
        self._registerMeetingFactoryTypes()
        self._updateUpdateDelayAwareAdvicecsCronJobTime()
        # reapply typeinfo as imio.zamqp.pm typeinfo was merged into Products.PloneMeeting
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')


def migrate(context):
    '''This migration function will:

       1) Remove field 'itemCreatedOnlyUsingTemplate' from every MeetingConfigs;
       2) Make sure every relevant portal_types are correctly registered in portal_factory;
       3) Set @@update-delay-aware-advices cronjob time to 01:45;
       4) Re-apply typeinfo to include imio.zamqp.pm informations.
    '''
    migrator = Migrate_To_4107(context)
    migrator.run()
    migrator.finish()
