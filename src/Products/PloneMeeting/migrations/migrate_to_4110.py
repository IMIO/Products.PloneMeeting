# -*- coding: utf-8 -*-

from plone import api
from plone.app.contenttypes.migration.dxmigration import ContentMigrator
from plone.app.contenttypes.migration.migration import migrate as pac_migrate
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
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
        # adapt allowed_types for each MeetingConfig.categories/MeetingConfig.classifiers folders
        for cfg in self.tool.objectValues('MeetingConfig'):
            for folder_id in ('categories', 'classifiers'):
                folder = cfg.get(folder_id)
                constrain = IConstrainTypes(folder)
                constrain.setConstrainTypesMode(1)
                allowedTypes = ['meetingcategory']
                constrain.setLocallyAllowedTypes(allowedTypes)
                constrain.setImmediatelyAddableTypes(allowedTypes)
        # migrate to DX
        pac_migrate(self.portal, MeetingCategoryMigrator)
        self.removeUnusedPortalTypes(portal_types=['MeetingCategory'])
        # add meetingcategory to types_not_searched
        props = api.portal.get_tool('portal_properties').site_properties
        nsTypes = props.getProperty('types_not_searched')
        if 'meetingcategory' not in nsTypes:
            nsTypes = list(nsTypes)
            # MeetingCategory was removed by removeUnusedPortalTypes
            nsTypes.append('meetingcategory')
            props.manage_changeProperties(types_not_searched=tuple(nsTypes))

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
