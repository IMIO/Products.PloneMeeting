# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4211(Migrator):

    def _updateDataRelatedToToolPloneMeetingSimplification(self):
        """ToolPloneMeeting will be moved to the registry,
           most methods are moved or removed, update stored data."""
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

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4211...')
        self._updateDataRelatedToToolPloneMeetingSimplification()
        logger.info('Migrating to PloneMeeting 4211... Done.')


def migrate(context):
    '''This migration function will:

       1) Update code regarding removal of methods that were available on portal_plonemeeting.
    '''
    migrator = Migrate_To_4211(context)
    migrator.run()
    migrator.finish()
