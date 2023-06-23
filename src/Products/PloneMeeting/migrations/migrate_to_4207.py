# -*- coding: utf-8 -*-

from Products.Archetypes.event import ObjectEditedEvent
from Products.PloneMeeting.config import ManageItemCategoryFields
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.event import notify
from zope.i18n import translate


class Migrate_To_4207(Migrator):

    def _configureMeetingCategories(self):
        """Add meetingcategories folder to every MeetingConfigs."""
        logger.info('Configuring meeting categories for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # create "meetingcategories" folder
            cfg._createSubFolders()
            # setup permission on categories/classifiers folders
            cfg.categories.manage_permission(
                ManageItemCategoryFields,
                ('Manager', 'Site Administrator'), acquire=0)
            cfg.classifiers.manage_permission(
                ManageItemCategoryFields,
                ('Manager', 'Site Administrator'), acquire=0)
            # rename classifiers folder title (translate it again, translation was updated)
            cfg.classifiers.setTitle(translate(
                "Classifiers",
                domain="PloneMeeting",
                context=self.request))
            cfg.classifiers.reindexObject()
        logger.info('Done.')

    def _updateMeetingAccessForMeetingConfigUsingGroups(self):
        """When using MeetingConfig.usingGroups, Meeting workflow can not use
           MeetingObserverGlobal role, we need to apply the MEETING_REMOVE_MOG_WFA
           WFA and update existing meetings."""
        logger.info('Updating meetings access for MeetingConfigs using usingGroups parameter...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            usingGroups = cfg.getUsingGroups()
            if usingGroups:
                # remove and set usingGroups, this will trigger the update
                cfg.usingGroups = ()
                cfg.setUsingGroups(usingGroups)
                notify(ObjectEditedEvent(cfg))
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4207...')

        self._configureMeetingCategories()
        self._updateMeetingAccessForMeetingConfigUsingGroups()

        logger.info('Migrating to PloneMeeting 4207... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure meeting categories;
       2) Update meeting access of MeetingConfigs using usingGroups.
    '''
    migrator = Migrate_To_4207(context)
    migrator.run()
    migrator.finish()
