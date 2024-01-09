# -*- coding: utf-8 -*-

from collective.documentgenerator.content.pod_template import IPODTemplate
from collective.documentgenerator.content.style_template import IStyleTemplate
from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.content.category import ICategory
from collective.iconifiedcategory.content.subcategory import ISubcategory
from imio.helpers.setup import load_type_from_package
from plone.app.blob.interfaces import IATBlob
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


EMPTY_MODEL_SOURCE = \
    """
<model xmlns="http://namespaces.plone.org/supermodel/schema">
    <schema />
</model>"""


class Migrate_To_4209(Migrator):

    def _fixDocumentviewerLayout(self):
        """Now that auto_select_layout is False for documentviewer, make sure
           AnnexTypes and PodTemplates created before do not use this layout."""
        logger.info('Remove documentviewer layout for annex types and pod templates...')
        # disable auto_select_layout
        viewer_settings = GlobalSettings(self.portal)._metadata
        viewer_settings['auto_select_layout'] = False
        brains = self.catalog(object_provides=(
            ICategory.__identifier__,
            ISubcategory.__identifier__,
            IPODTemplate.__identifier__,
            IStyleTemplate.__identifier__,
            IATBlob.__identifier__))
        for brain in brains:
            obj = brain.getObject()
            if base_hasattr(obj, 'layout'):
                obj.manage_delProperties(('layout', ))
        logger.info('Done.')

    def _updateAnnexPortalTypes(self):
        """Update the annex and annexDecision portal_types."""
        logger.info('Updating annex and annexDecision portal_type...')
        # make sure imio.annex is updated before or it overrides portal_type annex
        self.upgradeProfile('imio.annex:default')
        load_type_from_package('annex', 'imio.annex:default', purge_actions=True)
        load_type_from_package('annex', 'Products.PloneMeeting:default')
        load_type_from_package('annexDecision', 'Products.PloneMeeting:default', purge_actions=True)
        logger.info('Done.')

    def _updateContentCategoryPortalTypes(self):
        """Update ContentCategory portal_types, model_source and schema_policy changed."""
        logger.info('Updating ContentCategory portal_types...')
        data = {
            'ContentCategory':
            {'title': 'ContentCategory',
             'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_pm_content_category"},
            'ContentSubcategory':
            {'title': 'ContentSubcategory',
             'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_pm_content_subcategory"},
            'ItemAnnexContentCategory':
            {'title': 'ItemAnnexContentCategory',
             'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_item_annex_content_category"},
            'ItemAnnexContentSubcategory':
            {'title': 'ItemAnnexContentSubcategory',
             'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_item_annex_content_subcategory"},
        }
        for portal_type, infos in data.items():
            tinfo = self.portal.portal_types[portal_type]
            tinfo.title = infos['title']
            tinfo.model_source = infos['model_source']
            tinfo.schema_policy = infos['schema_policy']
        logger.info('Done.')

    def _removeCfgUseCopies(self):
        """Field MeetingConfig.useCopies was removed,
           enable 'copyGroups' in MeetingConfig.usedItemAttributes when relevant."""
        logger.info('Removing field "MeetingConfig.useCopies" from every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not base_hasattr(cfg, 'useCopies'):
                continue
            if cfg.useCopies:
                logger.info("'copyGroups' was enabled for MeetingConfig %s" % cfg.getId())
                used_item_attrs = list(cfg.getUsedItemAttributes())
                used_item_attrs.append('copyGroups')
                cfg.setUsedItemAttributes(used_item_attrs)
                self.updateTALConditions("cfg.getUseCopies()", "'copyGroups' in cfg.getUsedItemAttributes()")
                self.updateTALConditions("cfg/getUseCopies", "python:'copyGroups' in cfg.getUsedItemAttributes()")
            delattr(cfg, 'useCopies')
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4209...')

        if not from_migration_to_4200:
            self._removeBrokenAnnexes()
            self._updateAnnexPortalTypes()
            self._updateContentCategoryPortalTypes()

        self._fixDocumentviewerLayout()
        self._removeCfgUseCopies()

        logger.info('Migrating to PloneMeeting 4209... Done.')


def migrate(context):
    '''This migration function will:

       1) Remove broken annexes;
       2) Remove documentviewer layout from annex types and pod templates;
       3) Update annexDecision download action condition_expr;
       4) Upate ContentCategory portal_types model_source and schema_policy;
       5) Fix documentviewer layout on config elements.
    '''
    migrator = Migrate_To_4209(context)
    migrator.run()
    migrator.finish()
