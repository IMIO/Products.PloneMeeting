# -*- coding: utf-8 -*-

from Products.PloneMeeting.migrations import Migrator

import logging


logger = logging.getLogger('PloneMeeting')


class Migrate_To_4_0_2(Migrator):

    def run(self, step=None):
        logger.info('Migrating to PloneMeeting 4.0.2...')
        self.updateHolidays()


def migrate(context):
    '''This migration function will:

       1) Update holidays defined on portal_plonemeeting.
    '''
    migrator = Migrate_To_4_0_2(context)
    migrator.run()
    migrator.finish()
