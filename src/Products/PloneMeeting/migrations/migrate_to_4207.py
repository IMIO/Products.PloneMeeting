# -*- coding: utf-8 -*-

from Products.PloneMeeting.config import ManageItemCategoryFields
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
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

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4207...')

        self._configureMeetingCategories()

        logger.info('Migrating to PloneMeeting 4207... Done.')


def migrate(context):
    '''This migration function will:

       1) Configure meeting categories.
    '''
    migrator = Migrate_To_4207(context)
    migrator.run()
    migrator.finish()
