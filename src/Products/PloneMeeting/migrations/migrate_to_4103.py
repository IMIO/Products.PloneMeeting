# -*- coding: utf-8 -*-

from plone import api
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4103(Migrator):

    def _fixAdministratorsGroup(self):
        """Make sure the 'Administrators' group exists and has the 'Manager' role."""
        logger.info("Fixing \"Administrators\" group to have the \"Manager\" role...")
        # create 'Administrators' if it does not exist
        group_name = 'Administrators'
        group = api.group.get(groupname=group_name)
        if not group:
            logger.info("\"{0}\" group was not found, it has been created!".format(group_name))
            group = api.group.create(
                groupname=group_name, title=group_name, roles=['Manager'])
        else:
            if 'Manager' not in group.getRoles():
                api.group.grant_roles(groupname=group_name, roles=['Manager'])
                logger.info("\"{0}\" group did not have \"Manager\" role, "
                            "this was fixed!".format(group_name))
            else:
                logger.info("\"{0}\" group had already \"Manager\" role.".format(group_name))
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 4103...')
        self._fixAdministratorsGroup()


def migrate(context):
    '''This migration function will:

       1) Fix 'Administrators' group to have the 'Manager' role.
    '''
    migrator = Migrate_To_4103(context)
    migrator.run()
    migrator.finish()
