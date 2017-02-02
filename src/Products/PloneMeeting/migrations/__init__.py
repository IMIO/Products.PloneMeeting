# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# GNU General Public License (GPL)
# ------------------------------------------------------------------------------
'''This module defines functions that allow to migrate to a given version of
   PloneMeeting for production sites that run older versions of PloneMeeting.
   You must run every migration function in the right chronological order.
   For example, if your production site runs a version of PloneMeeting as of
   2008_04_01, and two migration functions named
   migrateToPloneMeeting_2008_05_23 and migrateToPloneMeeting_2008_08_29 exist,
   you need to execute migrateToPloneMeeting_2008_05_23 first AND
   migrateToPloneMeeting_2008_08_29 then.

   Migration functions must be run from portal_setup within your Plone site
   through the ZMI. Every migration function corresponds to a import step in
   portal_setup.'''

# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')

from plone import api
from imio.migrator.migrator import Migrator as BaseMigrator


class Migrator(BaseMigrator):
    '''Abstract class for creating a migrator.'''
    def __init__(self, context):
        BaseMigrator.__init__(self, context)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        # disable email notifications for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsMailMode = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsMailMode[cfg.getId()] = cfg.getMailMode()
            cfg.setMailMode('deactivated')
        # disable enable_link_integrity_checks
        self.enable_link_integrity_checks = \
            bool(self.portal.portal_properties.site_properties.enable_link_integrity_checks)
        self.portal.portal_properties.site_properties.manage_changeProperties(
            enable_link_integrity_checks=False)
        # disable advices invalidation for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsAdvicesInvalidation = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsAdvicesInvalidation[cfg.getId()] = cfg.getEnableAdviceInvalidation()
            cfg.setEnableAdviceInvalidation(False)
        self.profile_name = u'profile-Products.PloneMeeting:default'

    def upgradeDependencies(self):
        """Upgrade every dependencies."""
        profile_names = self.ps.getDependenciesForProfile(u'profile-Products.PloneMeeting:default')
        for profile_name in profile_names:
            self.upgradeProfile(profile_name)
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            profile_names = self.ps.getDependenciesForProfile(self.profile_name)
            for profile_name in profile_names:
                self.upgradeProfile(profile_name)

    def reinstall(self, profiles, ignore_dependencies=False, dependency_strategy=None):
        """Override to be able to call _after_reinstall at the end."""
        self._before_reinstall()
        BaseMigrator.reinstall(self, profiles, ignore_dependencies, dependency_strategy)
        self._after_reinstall()

    def _before_reinstall(self):
        """Before self.reinstall hook that let's a subplugin knows that the profile
           will be executed and may launch some migration steps before PM ones."""
        # save CKeditor custom styles
        cke_props = self.portal.portal_properties.ckeditor_properties
        self.menuStyles = cke_props.menuStyles

    def _after_reinstall(self):
        """After self.reinstall hook that let's a subplugin knows that the profile
           has been executed and may launch some migration steps before PM ones."""
        # set back CKeditor custom styles
        cke_props = self.portal.portal_properties.ckeditor_properties
        cke_props.menuStyles = self.menuStyles

    def updateHolidays(self):
        '''Update holidays using default holidays.'''
        logger.info('Updating holidays...')
        from Products.PloneMeeting.profiles import PloneMeetingConfiguration
        defaultPMConfig = PloneMeetingConfiguration('', '', '')
        defaultHolidays = [holiday['date'] for holiday in defaultPMConfig.holidays]
        currentHolidays = [holiday['date'] for holiday in self.tool.getHolidays()]
        storedHolidays = list(self.tool.getHolidays())
        for defaultHoliday in defaultHolidays:
            if not defaultHoliday in currentHolidays:
                storedHolidays.append({'date': defaultHoliday})
        self.tool.setHolidays(storedHolidays)
        logger.info('Done.')

    def run(self):
        '''Must be overridden. This method does the migration job.'''
        raise 'You should have overridden me darling.'''

    def finish(self):
        '''At the end of the migration, you can call this method to log its
           duration in minutes.'''
        # set mailMode for every MeetingConfigs back to the right value
        for cfgId in self.cfgsMailMode:
            cfg = getattr(self.tool, cfgId)
            cfg.setMailMode(self.cfgsMailMode[cfgId])
        # set enable_link_integrity_checks back to original value
        self.portal.portal_properties.site_properties.manage_changeProperties(
            enable_link_integrity_checks=self.enable_link_integrity_checks)
        # set adviceInvalidation for every MeetingConfigs back to the right value
        for cfgId in self.cfgsAdvicesInvalidation:
            cfg = getattr(self.tool, cfgId)
            cfg.setEnableAdviceInvalidation(self.cfgsAdvicesInvalidation[cfgId])
        BaseMigrator.finish(self)
