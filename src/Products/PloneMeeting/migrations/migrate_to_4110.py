# -*- coding: utf-8 -*-

from plone import api
from plone.app.contenttypes.migration.dxmigration import ContentMigrator
from plone.app.contenttypes.migration.migration import migrate as pac_migrate
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class MeetingCategoryMigrator(ContentMigrator):
    """For DashboardPODTemplates created after imio.dashboard 0.28 where
       meta_type was removed and so 'Dexterity Item' by default."""
    src_portal_type = 'MeetingCategory'
    src_meta_type = 'MeetingCategory'
    dst_portal_type = 'meetingcategory'
    dst_meta_type = None  # not used

    def migrate_atctmetadata(self):
        """Override to not migrate exclude_from_nav because it does not exist by default
           and it takes parent's value that is an instancemethod and fails at transaction commit..."""
        pass

    def migrate_schema_fields(self):
        self.new.category_id = self.old.getCategoryId()
        self.new.using_groups = self.old.getUsingGroups()
        self.new.category_mapping_when_cloning_to_other_mc = self.old.getCategoryMappingsWhenCloningToOtherMC()
        self.new.groups_in_charge = self.old.getGroupsInCharge()
        self.new.enabled = api.content.get_state(self.old) == 'active' and True or False
        self.new.reindexObject()


class Migrate_To_4110(Migrator):

    def _migrateMeetingCategoryToDX(self):
        ''' '''
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')
        # make sure no workflow used for meetingcategory
        self.wfTool.setChainForPortalTypes(('meetingcategory', ), ('', ))
        pac_migrate(self.portal, MeetingCategoryMigrator)

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4110...')
        self._migrateMeetingCategoryToDX()


def migrate(context):
    '''This migration function will:

       1) Migrate MeetingCategory to meetingcategory.
    '''
    migrator = Migrate_To_4110(context)
    migrator.run()
    migrator.finish()
