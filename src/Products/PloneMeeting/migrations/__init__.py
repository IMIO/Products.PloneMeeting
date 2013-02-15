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
import time
from Products.CMFCore.utils import getToolByName
import logging
logger = logging.getLogger('PloneMeeting')

# ------------------------------------------------------------------------------
class Migrator:
    '''Abstract class for creating a migrator.'''
    def __init__(self, context):
        self.context = context
        self.portal = context.portal_url.getPortalObject()
        self.tool = getToolByName(self.portal, 'portal_plonemeeting')
        self.startTime = time.time()
        # disable email notifications for every MeetingConfigs and save
        # current state to set it back after migration in self.finish
        self.cfgsMailMode = {}
        for cfg in self.tool.objectValues('MeetingConfig'):
            self.cfgsMailMode[cfg.getId()] = cfg.getMailMode()
            cfg.setMailMode('deactivated')

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
        seconds = time.time() - self.startTime
        logger.info('Migration finished in %d minute(s).' % (seconds/60))

    def refreshDatabase(self, catalogs=True,
        catalogsToRebuild=['portal_catalog'], workflows=False):
        '''After the migration script has been executed, it can be necessary to
           update the Plone catalogs and/or the workflow settings on every
           database object if workflow definitions have changed. We can pass
           catalog ids we want to 'clear and rebuild' using
           p_catalogsToRebuild.'''
        if catalogs:
            logger.info('Recataloging...')
            # Manage the catalogs we want to clear and rebuild
            # We have to call another method as clear=1 passed to refreshCatalog
            #does not seem to work as expected...
            for catalog in catalogsToRebuild:
                catalogObj = getattr(self.portal, catalog)
                catalogObj.clearFindAndRebuild()
            catalogIds = ('portal_catalog', 'reference_catalog', 'uid_catalog')
            for catalogId in catalogIds:
                if not catalogId in catalogsToRebuild:
                    catalogObj = getattr(self.portal, catalogId)
                    catalogObj.refreshCatalog(clear=0)
        if workflows:
            logger.info('Refresh workflow-related information on every ' \
                        'object of the database...')
            self.portal.portal_workflow.updateRoleMappings()

    def reinstall(self, profiles=[u'profile-Products.PloneMeeting:default',]):
        '''Allows to reinstall a series of p_profiles.'''
        logger.info('Reinstalling product(s) %s...' % ', '.join([profile[8:] for profile in profiles]))
        for profile in profiles:
            try:
                self.portal.portal_setup.runAllImportStepsFromProfile(profile)
            except KeyError:
                logger.error('Profile %s not found!' % profile)
        logger.info('Done.')
# ------------------------------------------------------------------------------
