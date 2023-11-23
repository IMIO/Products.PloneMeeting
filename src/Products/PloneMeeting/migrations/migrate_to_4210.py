# -*- coding: utf-8 -*-

from imio.helpers.content import safe_delattr
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


BARCODE_INSERTED_ATTR_ID = '_barcode_inserted'


class Migrate_To_4210(Migrator):

    def _removeBarcodeInsertedAttrOnAnnexes(self):
        """ """
        logger.info('Removing attribute "_barcode_inserted" on every annexes...')
        brains = self.catalog(portal_type=['annex', 'annexDecision'])
        for brain in brains:
            if brain.scan_id:
                safe_delattr(brain.getObject(), BARCODE_INSERTED_ATTR_ID)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4210...')

        self._removeBarcodeInsertedAttrOnAnnexes()
        self.updateHolidays()  # holidays 2024 were added

        logger.info('Migrating to PloneMeeting 4210... Done.')


def migrate(context):
    '''This migration function will:

       1) Remove attribute "_barcode_inserted" from annexes.
    '''
    migrator = Migrate_To_4210(context)
    migrator.run()
    migrator.finish()
