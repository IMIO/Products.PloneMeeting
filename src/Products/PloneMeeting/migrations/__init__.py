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

from DateTime import DateTime
from imio.helpers.catalog import addOrUpdateColumns
from imio.helpers.catalog import addOrUpdateIndexes
from imio.migrator.migrator import Migrator as BaseMigrator
from plone import api
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.setuphandlers import columnInfos
from Products.PloneMeeting.setuphandlers import indexInfos

import logging


logger = logging.getLogger('PloneMeeting')


class Migrator(BaseMigrator):
    '''Abstract class for creating a migrator.'''

    already_migrated = False

    def __init__(self, context):
        BaseMigrator.__init__(self, context, disable_linkintegrity_checks=True)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        # disable email notifications for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsMailMode = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsMailMode[cfg.getId()] = cfg.getMailMode()
            cfg.setMailMode('deactivated')
        # disable advices invalidation for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsAdvicesInvalidation = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsAdvicesInvalidation[cfg.getId()] = cfg.getEnableAdviceInvalidation()
            cfg.setEnableAdviceInvalidation(False)
        self.profile_name = u'profile-Products.PloneMeeting:default'

    def reorderSkinsLayers(self):
        """Reapply skins of Products.PloneMeeting + self.profile_name."""
        # re-apply the PloneMeeting skins and the self.profile_name skin if different
        self.runProfileSteps('Products.PloneMeeting',
                             steps=['skins'],
                             profile='default')
        if self.profile_name != u'profile-Products.PloneMeeting:default':
            product_name = self.profile_name.split(':')[0][8:]
            self.runProfileSteps(product_name,
                                 steps=['skins'],
                                 profile='default')

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

    def reindexIndexes(self, idxs=[]):
        """Reindex given p_idxs."""
        for idx in idxs:
            logger.info('Reindexing the "{0}" index...'.format(idx))
            self.portal.portal_catalog.reindexIndex(name=idx, REQUEST=None)
        logger.info('Done.')

    def getWorkflows(self, meta_types=['Meeting',
                                       'MeetingItem',
                                       'MeetingItemTemplate',
                                       'MeetingItemRecurring']):
        """Returns every workflows used for every portal_types based on given p_meta_type."""
        portal_types = []
        for cfg in self.tool.objectValues('MeetingConfig'):
            for meta_type in meta_types:
                if meta_type == 'Meeting':
                    portal_types.append(cfg.getMeetingTypeName())
                elif meta_type == 'MeetingItem':
                    portal_types.append(cfg.getItemTypeName())
                else:
                    # MeetingItemXXX type
                    portal_types.append(cfg.getItemTypeName(configType=meta_type))
        wf_ids = [self.wfTool.getWorkflowsFor(portal_type)[0].getId()
                  for portal_type in portal_types]
        return wf_ids

    def addCatalogIndexesAndColumns(self, indexes=True, columns=True):
        """ """
        if indexes:
            addOrUpdateIndexes(self.portal, indexInfos)
        if columns:
            addOrUpdateColumns(self.portal, columnInfos)

    def updateTALConditions(self, old_word, new_word):
        """Update every elements having a tal_condition, replace given old_word by new_word."""
        for brain in api.content.find(
                object_provides='collective.behavior.talcondition.interfaces.ITALConditionable'):
            obj = brain.getObject()
            tal_condition = obj.tal_condition
            if tal_condition and old_word in tal_condition:
                tal_condition = tal_condition.replace(old_word, new_word)
                obj.tal_condition = tal_condition

    def updateHolidays(self):
        '''Update holidays using default holidays.'''
        logger.info('Updating holidays...')
        from Products.PloneMeeting.profiles import PloneMeetingConfiguration
        defaultPMConfig = PloneMeetingConfiguration('', '', '')
        defaultHolidays = [holiday['date'] for holiday in defaultPMConfig.holidays]
        currentHolidays = [holiday['date'] for holiday in self.tool.getHolidays()]
        storedHolidays = list(self.tool.getHolidays())
        highestStoredHoliday = DateTime(storedHolidays[-1]['date'])
        for defaultHoliday in defaultHolidays:
            # update if not there and if higher that highest stored holiday
            if defaultHoliday not in currentHolidays and \
               DateTime(defaultHoliday) > highestStoredHoliday:
                storedHolidays.append({'date': defaultHoliday})
        self.tool.setHolidays(storedHolidays)
        logger.info('Done.')

    def addNewSearches(self):
        """Add new searches by createSearches."""
        logger.info('Adding new searches...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg._createSubFolders()
            cfg.createSearches(cfg._searchesInfo())
        logger.info('Done.')

    def cleanMeetingConfigs(self, field_names=[]):
        """Remove given p_field_names from every MeetingConfigs."""
        logger.info('Cleaning MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for field_name in field_names:
                if base_hasattr(cfg, field_name):
                    delattr(cfg, field_name)
        logger.info('Done.')

    def cleanTool(self, field_names=[]):
        """Remove given p_field_names from ToolPloneMeeting."""
        logger.info('Cleaning ToolPloneMeeting...')
        for field_name in field_names:
            if base_hasattr(self.tool, field_name):
                delattr(self.tool, field_name)
        logger.info('Done.')

    def _already_migrated(self, done=True):
        """Called when a migration is executed several times..."""
        self.already_migrated = True
        logger.info('Already migrated ...')
        if done:
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
        # set adviceInvalidation for every MeetingConfigs back to the right value
        for cfgId in self.cfgsAdvicesInvalidation:
            cfg = getattr(self.tool, cfgId)
            cfg.setEnableAdviceInvalidation(self.cfgsAdvicesInvalidation[cfgId])
        BaseMigrator.finish(self)
