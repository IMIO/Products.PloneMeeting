# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.event import notify


class Migrate_To_4211(Migrator):

    def _migrateConfigHideHistoryTo(self):
        """Values changed and a prefixed with the content_type.
           Originally, every values were about the "MeetingItem"."""
        logger.info('Migrating attribute "hideHistoryTo" for every MeetingConfig...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            new_values = []
            for value in cfg.getHideHistoryTo():
                if value.lower().startswith('meeting'):
                    return self._already_migrated()
                new_values.append("MeetingItem.{0}".format(value))
            if new_values:
                cfg.setHideHistoryTo(new_values)
        logger.info('Done.')

    def _updateSearchCopyGroupsSearchesCondition(self):
        """Use MeetingConfig.show_copy_groups_search."""
        logger.info('Updating copy groups searches TAL condition in every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            searchallitemsincopy = cfg.searches.searches_items.get('searchallitemsincopy')
            if searchallitemsincopy:
                searchallitemsincopy.tal_condition = 'python: cfg.show_copy_groups_search()'
            searchunreaditemsincopy = cfg.searches.searches_items.get('searchunreaditemsincopy')
            if searchunreaditemsincopy:
                searchunreaditemsincopy.tal_condition = \
                    'python: cfg.getEnableLabels() and cfg.show_copy_groups_search()'
        logger.info('Done.')

    def _updateDataRelatedToToolPloneMeetingSimplification(self):
        """ToolPloneMeeting will be moved to the registry,
           most methods are moved or removed, update stored data."""
        logger.info('Updating portal_plonemeeting related data...')
        # reload ConfigurablePODTemplate to be sure that we have the correct portal_type
        # this can have been changed by other upgrade steps
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        prefixes = ('tool',
                    'context.portal_plonemeeting',
                    'here.portal_plonemeeting',
                    'obj.portal_plonemeeting',
                    'self.portal_plonemeeting',
                    'portal_plonemeeting')
        method_names = {'get_labels': 'get_labels',
                        'getAdvicePortalTypeIds': 'getAdvicePortalTypeIds',
                        'getUserName': 'get_user_fullname',
                        'isPowerObserverForCfg': 'isPowerObserverForCfg'}
        replacements = {}
        for prefix in prefixes:
            for orig_method_name, new_method_name in method_names.items():
                # TAL expressions
                self.updateTALConditions(
                    "{0}.{1}".format(prefix, orig_method_name), "utils.{0}".format(new_method_name))
                # compute replacements for POD templates
                replacements["{0}.{1}".format(prefix, orig_method_name)] = "utils.{0}".format(new_method_name)

        # POD templates
        self.updatePODTemplatesCode(replacements)
        logger.info('Done.')

    def _updateItemSearches(self):
        """Make sure every item related searches use sort_on=modified."""
        logger.info('Updating item searches sort_on...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for collection in cfg.searches.searches_items.objectValues():
                collection.sort_on = u'modified'
            livingitems = cfg.searches.searches_items.get('searchlivingitems')
            if livingitems:
                livingitems.query = [
                    {'i': 'CompoundCriterion',
                     'o': 'plone.app.querystring.operation.compound.is',
                     'v': 'living-items'}]
        logger.info('Done.')

    def _updateForItemExportPDFAction(self):
        """Update related to new export PDF action on item:
           - Reload MeetingItem portal_types to add the item-export-pdf-form action;
           - MeetingConfig.enableItemDuplication is moved to MeetingConfig.enabledItemActions."""
        logger.info('Updating for new export PDF action on item...')
        # update MeetingItem portal_types
        # first update MeetingItem base portal_type
        load_type_from_package('MeetingItem', 'Products.PloneMeeting:default')
        for cfg in self.tool.objectValues('MeetingConfig'):
            notify(ObjectEditedEvent(cfg))
            # migrate the MeetingConfig.enableItemDuplication attribute
            if base_hasattr(cfg, 'enableItemDuplication'):
                if cfg.enableItemDuplication:
                    cfg.setEnabledItemActions(('duplication', ))
                delattr(cfg, 'enableItemDuplication')
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4211...')
        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')])
        self._migrateConfigHideHistoryTo()
        self._updateSearchCopyGroupsSearchesCondition()
        self._updateDataRelatedToToolPloneMeetingSimplification()
        self._updateItemSearches()
        self._updateForItemExportPDFAction()
        # add text criterion on item title only
        self.updateFacetedFilters(xml_filename='upgrade_step_4211_add_item_widgets.xml')
        logger.info('Migrating to PloneMeeting 4211... Done.')


def migrate(context):
    '''This migration function will:

       1) Migrate attribute MeetingConfig.hideHistoryTo for MeetingConfig;
       2) Update searchallcopygroups/searchunreaditemsincopy searches tal_condition;
       3) Update code regarding removal of methods that were available on portal_plonemeeting;
       4) Update related to new export PDF action on item;
       5) Add c32 faceted criterion (search on item title only);
       6) Update every item related searches to use sort_on=modified and
          the searchlivingitems to use the 'living-items' compound criterion adapter.
    '''
    migrator = Migrate_To_4211(context)
    migrator.run()
    migrator.finish()
