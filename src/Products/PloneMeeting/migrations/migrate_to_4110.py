# -*- coding: utf-8 -*-

from plone import api
from plone.app.contenttypes.migration.dxmigration import ContentMigrator
from plone.app.contenttypes.migration.migration import migrate as pac_migrate
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.i18n import translate


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
        '''Migrate from AT MeetingCategory to DX meetingcategory.'''
        logger.info('Migrating MeetingCategory from AT to DX...')
        # update item classifier
        # migrate references
        pghandler = ZLogHandler(steps=100)
        brains = self.portal.reference_catalog(relationship='ItemClassification')
        pghandler.init('Updating field MeetingItem.classifier...', len(brains))
        pghandler.info('Updating field MeetingItem.classifier...')
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            relation = brain.getObject()
            item = relation.getSourceObject()
            classifier = relation.getTargetObject()
            item.setClassifier(classifier.getId())
            item.reindexObject(idxs=['getRawClassifier'])
        # deleteReferences in a second phase
        for brain in brains:
            relation = brain.getObject()
            item = relation.getSourceObject()
            item.deleteReferences('ItemClassification')
        pghandler.finish()

        logger.info('Migrating categories and classifiers in configuration...')
        # make sure new portal_type meetingcategory is installed
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'typeinfo')
        # make sure no workflow used for meetingcategory
        self.wfTool.setChainForPortalTypes(('meetingcategory', ), ('', ))
        # adapt allowed_types for each MeetingConfig.categories/classifiers folders
        for cfg in self.tool.objectValues('MeetingConfig'):
            for folder_id in ('categories', 'classifiers'):
                constrain = IConstrainTypes(getattr(cfg, folder_id))
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
        logger.info('Done.')

    def _updateOrgsDashboardCollectionColumns(self):
        """Enable column 'PloneGroupUsersGroupsColumn' in contacts collections displaying organizations."""
        logger.info("Updating dashboard organization collections to remove the \"review_state\" column...")
        orgs_searches_folder = self.portal.contacts.get('orgs-searches')
        # enable 'PloneGroupUsersGroupsColumn' just after 'SelectedInPlonegroupColumn'
        for org_coll in orgs_searches_folder.objectValues():
            customViewFields = list(org_coll.customViewFields)
            if 'PloneGroupUsersGroupsColumn' not in customViewFields:
                customViewFields.insert(
                    customViewFields.index('SelectedInPlonegroupColumn') + 1,
                    'PloneGroupUsersGroupsColumn')
                org_coll.customViewFields = customViewFields
        logger.info('Done.')

    def _enableDateinputJSResource(self):
        """Make sure '++resource++plone.app.jquerytools.dateinput.js' is enabled in portal_javascripts."""
        logger.info("Enabling '++resource++plone.app.jquerytools.dateinput.js' in portal_javascripts...")
        resource = self.portal.portal_javascripts.getResource('++resource++plone.app.jquerytools.dateinput.js')
        resource.setEnabled(True)
        logger.info('Done.')

    def _addPageBreakStyleToCKEditor(self):
        """Add new style 'page-break' to CKeditor styles."""
        logger.info("Adding style 'page-break' to CKEditor styles...")
        cke_props = self.portal.portal_properties.ckeditor_properties
        if cke_props.menuStyles.find('page-break') == -1:
            msg_page_break = translate('ckeditor_style_page_break',
                                       domain='PloneMeeting',
                                       context=self.request).encode('utf-8')
            menuStyles = cke_props.menuStyles
            page_break_style = "{{ name : '{0}'\t\t, element : 'p', attributes : " \
                "{{ 'class' : 'page-break' }} }},\n]".format(msg_page_break)
            # last element, check if we need a ',' before or not...
            strippedMenuStyles = menuStyles.replace(' ', '').replace('\n', '').replace('\r', '')
            if ',]' not in strippedMenuStyles:
                menuStyles = menuStyles.replace('\n]', ']')
                page_break_style = ",\n" + page_break_style
            menuStyles = menuStyles.replace(']', page_break_style)
            cke_props.menuStyles = menuStyles
            logger.info("Style 'page-break' was added...")
        else:
            logger.info("Style 'page-break' already exists and was not added...")
        logger.info('Done.')

    def _migrateToMeetingItemTemplatesToStoreAsAnnex(self):
        """Single value field MeetingConfig.meetingItemTemplateToStoreAsAnnex was moved
           to multi valued field MeetingConfig.meetingItemTemplatesToStoreAsAnnex."""
        logger.info("Migrating MeetingConfig.meetingItemTemplateToStoreAsAnnex to "
                    "MeetingConfig.meetingItemTemplatesToStoreAsAnnex...")
        old_field_name = 'meetingItemTemplateToStoreAsAnnex'
        new_field_name = 'meetingItemTemplatesToStoreAsAnnex'
        for cfg in self.tool.objectValues('MeetingConfig'):
            if base_hasattr(cfg, old_field_name):
                old_field_value = getattr(cfg, old_field_name)
                if old_field_value:
                    setattr(cfg, new_field_name, [old_field_value])
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4110...')
        self._migrateMeetingCategoryToDX()
        self._updateOrgsDashboardCollectionColumns()
        self._enableDateinputJSResource()
        self._addPageBreakStyleToCKEditor()
        self._migrateToMeetingItemTemplatesToStoreAsAnnex()
        # update collective.contact.plonegroup
        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')])


def migrate(context):
    '''This migration function will:

       1) Migrate MeetingCategory to meetingcategory.
       2) Enable column 'PloneGroupUsersGroupsColumn' of for contacts collections displaying organizations;
       3) Make sure '++resource++plone.app.jquerytools.dateinput.js' is enabled in portal_javascripts;
       4) Add new style 'page-break' to CKEditor;
       5) Migrate MeetingConfig.meetingItemTemplateToStoreAsAnnex to MeetingConfig.meetingItemTemplatesToStoreAsAnnex;
       6) Apply every pending upgrades.
    '''
    migrator = Migrate_To_4110(context)
    migrator.run()
    migrator.finish()
