# -*- coding: utf-8 -*-

from collective.documentgenerator.content.pod_template import IPODTemplate
from collective.documentgenerator.content.style_template import IStyleTemplate
from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.content.category import ICategory
from collective.iconifiedcategory.content.subcategory import ISubcategory
from plone.app.blob.interfaces import IATBlob
from Products.CMFCore.Expression import Expression
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


EMPTY_MODEL_SOURCE = \
    """
<model xmlns="http://namespaces.plone.org/supermodel/schema">
    <schema />
</model>"""


class Migrate_To_4208(Migrator):

    def _updateMeetingOptionalBooleanAttrs(self):
        """Boolean attributes (videoconference and extraordinary_session) were
           wrongly always enabled then disabled when bug was fixed...
           Re-enable fields if used on a meeting of the configuration."""
        logger.info('Re-enabling meetings fields videoconference and '
                    'extraordinary_session if used for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            mAttrs = list(cfg.getUsedMeetingAttributes())
            for field_name in ('videoconference', 'extraordinary_session'):
                if field_name not in mAttrs:
                    for brain in self.catalog(portal_type=cfg.getMeetingTypeName()):
                        meeting = brain.getObject()
                        if getattr(meeting, field_name) is True:
                            mAttrs.append(field_name)
                            break
                cfg.setUsedMeetingAttributes(mAttrs)
        logger.info('Done.')

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

    def _updateAnnexDecisionDownloadAction(self):
        """Update the annexDecision portal_type download action condition_expr."""
        logger.info('Updating annexDecision portal_type download action condition_expr...')
        annexDecion = self.portal.portal_types['annexDecision']
        action = annexDecion.getActionObject('object_buttons/download')
        action.condition = Expression('python:object.show_download()')
        logger.info('Done.')

    def _updateContentCategoryPortalTypes(self):
        """Update ContentCategory portal_types, model_source and schema_policy changed."""
        logger.info('Updating ContentCategory portal_types...')
        data = {
            'ContentCategory':
            {'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_pm_content_category"},
            'ContentSubcategory':
            {'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_pm_content_subcategory"},
            'ItemAnnexContentCategory':
            {'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_item_annex_content_category"},
            'ItemAnnexContentSubcategory':
            {'model_source': EMPTY_MODEL_SOURCE,
             'schema_policy': "schema_policy_item_annex_content_subcategory"},
        }
        for portal_type, infos in data.items():
            tinfo = self.portal.portal_types[portal_type]
            tinfo.model_source = infos['model_source']
            tinfo.schema_policy = infos['schema_policy']
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4208...')

        self.updateFacetedFilters(
            xml_filename='default_dashboard_meetings_widgets.xml',
            related_to="meetings")
        self.updateFacetedFilters(
            xml_filename='default_dashboard_meetings_widgets.xml',
            related_to="decisions")

        if not from_migration_to_4200:
            # re-apply actions.xml to update documentation url
            self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'actions')
            self._updateMeetingOptionalBooleanAttrs()
            self._updateAnnexDecisionDownloadAction()
            self._updateContentCategoryPortalTypes()

        self._fixDocumentviewerLayout()
        logger.info('Migrating to PloneMeeting 4208... Done.')


def migrate(context):
    '''This migration function will:

       1) Update searches_decisions faceted config;
       2) Re-apply actions.xml to update documentation URL;
       3) Remove documentviewer layout from annex types and pod templates;
       4) Update annexDecision download action condition_expr;
       5) Upate ContentCategory portal_types model_source and schema_policy;
       6) Fix documentviewer layout on config elements.
    '''
    migrator = Migrate_To_4208(context)
    migrator.run()
    migrator.finish()
