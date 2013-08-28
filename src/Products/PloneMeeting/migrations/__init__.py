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
from Products.CMFCore.utils import getToolByName

from imio.migrator.migrator import Migrator as BaseMigrator


class Migrator(BaseMigrator):
    '''Abstract class for creating a migrator.'''
    def __init__(self, context):
        BaseMigrator.__init__(self, context)
        self.tool = getToolByName(self.portal, 'portal_plonemeeting')
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
