# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from Products.Archetypes.event import ObjectEditedEvent
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.event import notify


class Migrate_To_4211(Migrator):

    def _updateDataRelatedToToolPloneMeetingSimplification(self):
        """ToolPloneMeeting will be moved to the registry,
           most methods are moved or removed, update stored data."""
        logger.info('Updating portal_plonemeeting related data...')
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

    def _updateItemSearchesSortOn(self):
        """Make sure every item related searches use sort_on=modified."""
        logger.info('Updating item searches sort_on...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            for collection in cfg.searches.searches_items.objectValues():
                collection.sort_on = u'modified'
        logger.info('Done.')

    def _reloadItemTypes(self):
        """Reload MeetingItem portal_types to add the item-export-pdf-form action."""
        logger.info('Reloading MeetingItem portal_types...')
        # first update MeetingItem base portal_type
        load_type_from_package('MeetingItem', 'Products.PloneMeeting:default')
        for cfg in self.tool.objectValues('MeetingConfig'):
            notify(ObjectEditedEvent(cfg))
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4211...')
        self._updateDataRelatedToToolPloneMeetingSimplification()
        self._updateItemSearchesSortOn()
        self._reloadItemTypes()
        # add text criterion on item title only
        self.updateFacetedFilters(xml_filename='upgrade_step_4211_add_item_widgets.xml')
        logger.info('Migrating to PloneMeeting 4211... Done.')


def migrate(context):
    '''This migration function will:

       1) Update code regarding removal of methods that were available on portal_plonemeeting;
       2) Update every item related searches to use sort_on=modified;
       3) Reload MeetingItem portal_type to add item-export-pdf action;
       4) Add c32 faceted criterion (search on item title only).
    '''
    migrator = Migrate_To_4211(context)
    migrator.run()
    migrator.finish()
