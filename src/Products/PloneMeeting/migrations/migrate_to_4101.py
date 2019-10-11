# -*- coding: utf-8 -*-

from eea.facetednavigation.interfaces import ICriteria
from imio.helpers.catalog import reindexIndexes
from plone import api
from plone.app.contenttypes.migration.dxmigration import migrate_base_class_to_new_class
from plone.namedfile.file import NamedBlobFile
from Products.PloneMeeting.content.organization import PMOrganization
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4101(Migrator):

    def _updateFacetedFilters(self):
        """Update vocabulary used for "Taken over by".
           Make sure the default for contacts 'c5' widget is not a list."""
        logger.info("Updating faceted filter \"Taken over by\" for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            obj = cfg.searches.searches_items
            # update vocabulary for relevant filters
            criteria = ICriteria(obj)
            criteria.edit(
                'c12', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.creatorswithnobodyforfacetedfiltervocabulary'})
            criteria.edit(
                'c27', **{
                    'vocabulary':
                        'Products.PloneMeeting.vocabularies.associatedgroupsvocabulary'})
        logger.info('Done.')

        logger.info("Updating faceted filter \"Defined in\" for 'c5' "
                    "criterion of contacts/orgs-searches...")
        obj = self.portal.contacts.get('orgs-searches')
        # as default is not correct (a string instead a list, we can not use edit or it fails to validate)
        criteria = ICriteria(obj)
        criterion = criteria.get('c5')
        criterion.default = u'collective.contact.plonegroup.interfaces.IPloneGroupContact'
        logger.info('Done.')

    def _updateSearchLastDecisionsQuery(self):
        """The searchlastdecisions collection query was updated to use the
           lasrt-decisions compound criterion adapter."""
        logger.info("Updating collection \"searchlastdecisions\" query for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            collection = cfg.searches.searches_decisions.searchlastdecisions
            # make sure the compound criterion adapter is used
            has_compound_adapter = bool([term for term in collection.query
                                         if term[u'i'] == u'CompoundCriterion'])
            if has_compound_adapter is False:
                query = collection.query
                query.append(
                    {'i': 'CompoundCriterion',
                     'o': 'plone.app.querystring.operation.compound.is',
                     'v': 'last-decisions'})
                collection.setQuery(list(query))
        logger.info('Done.')

    def _updateOrgsDashboardCollectionColumns(self):
        """Make sure the 'review_state' column is not displayed in dashboards displaying organizations."""
        logger.info("Updating dashboard organization collections to remove the \"review_state\" column...")
        orgs_searches_folder = self.portal.contacts.get('orgs-searches')
        # hide the 'review_state' column for orgs related collections
        for org_coll in orgs_searches_folder.objectValues():
            org_coll.customViewFields = [col_name for col_name in org_coll.customViewFields
                                         if col_name != u'review_state']
        logger.info('Done.')

    def _allowDashboardPODTemplateInDirectoryPortalType(self):
        """Add 'DashboardPODTemplate' to 'allowed_content_types' of 'directory' portal_type."""
        logger.info("Adding 'DashboardPODTemplate' to 'allowed_content_types' of 'directory' portal_type...")
        pType = self.portal.portal_types['directory']
        allowed_types = list(pType.allowed_content_types)
        if 'DashboardPODTemplate' not in allowed_types:
            allowed_types.append('DashboardPODTemplate')
            pType.allowed_content_types = allowed_types
        logger.info('Done.')

    def _addDashboardPODTemplateExportOrganizations(self):
        """Add the export organizations DashboardPODTemplate in the contacts directory."""
        logger.info("Adding 'Export CSV DashboardPODTemplate' to 'contacts' directory...")
        pod_template_id = 'export-organizations'
        contacts = self.portal.contacts
        if pod_template_id in contacts.objectIds():
            self._already_migrated()
            return

        profile_path = self.ps._getImportContext(self.profile_name)._profile_path
        odt_path = profile_path + '/../testing/templates/organizations-export.ods'
        odt_file = open(odt_path, 'rb')
        odt_binary = odt_file.read()
        odt_file.close()
        data = {'title': 'Export CSV',
                'pod_formats': ['ods', 'xls'],
                'dashboard_collections': contacts.get('orgs-searches').all_orgs.UID(),
                'odt_file': NamedBlobFile(
                    data=odt_binary,
                    contentType='application/vnd.oasis.opendocument.text',
                    # pt.odt_file could be relative (../../other_profile/templates/sample.odt)
                    filename=u'export-organizations.ods'),
                'use_objects': True,
                }
        podTemplate = api.content.create(
            id=pod_template_id,
            type='DashboardPODTemplate',
            container=contacts,
            **data)
        podTemplate.reindexObject()
        logger.info('Done.')

    def _removeSelectableForPlonegroupFieldOnOrganizations(self):
        '''Remove attribute 'selectable_for_plonegroup' on organizations.'''
        logger.info("Removing attribute 'selectable_for_plonegroup' on every organizations...")
        for brain in self.catalog(portal_type='organization'):
            org = brain.getObject()
            if hasattr(org, 'selectable_for_plonegroup'):
                delattr(org, 'selectable_for_plonegroup')
        logger.info('Done.')

    def _removeTagsParameterInCallToJSCallViewAndReloadInCloneToOtherMCActions(self):
        '''Parameter was remove from JS callViewAndReload, this is stored
           in clone to other mc actions on MeetingItem portal_types.'''
        logger.info("Calling registerPortalTypes for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.registerPortalTypes()
        logger.info('Done.')

    def _moveToMeetingConfigOnMeetingTransitionItemActionToExecute(self):
        '''Field MeetingConfig.onMeetingTransitionItemTransitionToTrigger was moved
           to MeetingConfig.onMeetingTransitionItemActionToExecute.'''
        logger.info("Migrating field onMeetingTransitionItemActionToExecute for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'onMeetingTransitionItemTransitionToTrigger'):
                old_values = cfg.onMeetingTransitionItemTransitionToTrigger
                # move 'item_transition' to 'item_action' and add empty 'tal_expression'
                new_values = []
                for old_value in old_values:
                    new_values.append({'meeting_transition': old_value['meeting_transition'],
                                       'item_action': old_value['item_transition'],
                                       'tal_expression': ''})
                cfg.setOnMeetingTransitionItemActionToExecute(new_values)
                delattr(cfg, 'onMeetingTransitionItemTransitionToTrigger')
        logger.info('Done.')

    def _migrateContactOrganizationPersonsKlass(self):
        """klass used by 'organization' portal_type changed, this is only relevant for
           users using beta versions..."""
        logger.info('Migrating klass of collective.contact Organization to PMOrganization...')
        for brain in self.catalog(portal_type='organization'):
            org = brain.getObject()
            if not isinstance(org, PMOrganization):
                logger.info('Migrating organization at {0}'.format('/'.join(org.getPhysicalPath())))
                migrate_base_class_to_new_class(
                    org,
                    old_class_name='collective.contact.core.content.organization.Organization',
                    new_class_name='Products.PloneMeeting.content.organization.PMOrganization')
        logger.info('Done.')

    def _correctAccessToPODTemplates(self):
        """Correct weird Unauthorized when accessing POD template file."""
        logger.info('Correcting access to POD Templates file...')
        brains = self.catalog(
            object_provides=(
                'collective.documentgenerator.content.pod_template.IPODTemplate',
                'collective.documentgenerator.content.style_template.IStyleTemplate'))
        for brain in brains:
            pod_template = brain.getObject()
            logger.info('Updating access for POD template at {0}'.format(
                '/'.join(pod_template.getPhysicalPath())))
            pod_template.reindexObject()
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4101...')
        self._updateFacetedFilters()
        self._updateSearchLastDecisionsQuery()
        self._updateOrgsDashboardCollectionColumns()
        self._allowDashboardPODTemplateInDirectoryPortalType()
        self._addDashboardPODTemplateExportOrganizations()
        self._removeSelectableForPlonegroupFieldOnOrganizations()
        self._removeTagsParameterInCallToJSCallViewAndReloadInCloneToOtherMCActions()
        self._moveToMeetingConfigOnMeetingTransitionItemActionToExecute()
        self._migrateContactOrganizationPersonsKlass()
        self._correctAccessToPODTemplates()
        self.cleanRegistries()
        # holidays 2020 were added
        self.updateHolidays()
        # refresh if we are not coming from migration to 4.1,
        # in this case it was already refreshed
        if not from_migration_to_41:
            self.reindexIndexesFor(idxs=['get_full_title'], **{'portal_type': ['organization']})
            reindexIndexes(self.portal, idxs=['getTakenOverBy', 'getConfigId'])
            # re-run the Meeting workflows update as there was a bug in Migrator.refreshDatabase
            meeting_wf_ids = self.getWorkflows(meta_types=['Meeting'])
            self.refreshDatabase(catalogs=False, workflows=True, workflowsToUpdate=meeting_wf_ids)
        self.tool.invalidateAllCache()


def migrate(context):
    '''This migration function will:

       1) Update faceted filters for item dashboards;
       2) Update the searchlastdecisions query to use last-decisions compound criterion adapter;
       3) Update columns of collections displaying organizations in dashboard, remove the 'review_state' column;
       4) Add 'DashboardPODTemplate' to the allowed types of a contacts directory;
       5) Add the 'Export CSV' DashboardPODTemplate available on the contacts 'All orgs' dashboard;
       6) Remove the 'selectable_for_plonegroup' attribute on organizations;
       7) Update 'clone to other MC' portal_type action;
       8) Move field MeetingConfig.onMeetingTransitionItemTransitionToTrigger to
          MeetingConfig.onMeetingTransitionItemActionToExecute;
       9) Migrate organizations having klass Organization to klass PMOrganization;
       10) Fix access to POD template file;
       11) Clean registries;
       12) Update holidays to manage 2020;
       13) Reindex catalog indexes :
              - 'getTakenOverBy' as we use an indexer to handle empty value;
              - 'getConfigId' as we store a specific empty value as it is not possible to search on an empty index;
              - 'get_full_title' as indexed value is different than displayed one.
       14) Refresh Meeting workflows so MeetingManager have 'Review portal content' in state 'closed';
       15) Invalidate all cache.
    '''
    migrator = Migrate_To_4101(context)
    migrator.run()
    migrator.finish()
