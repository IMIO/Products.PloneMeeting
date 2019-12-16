# -*- coding: utf-8 -*-

from plone import api
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations.migrate_to_4102 import Migrate_To_4102


class Migrate_To_4103(Migrate_To_4102):

    def _fixGroupsAndUsersRoles(self):
        """Make sure the 'Administrators' group exists and has the 'Manager' role.
           Make sure every source_users have the 'Member' role and
           every source_groups does not have the 'Member' role,
           including the 'AuthenticatedUsers' group."""
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

        # manage users, make sure we do not get LDAP users, listMembers to not get LDAP users
        # give 'Member' role to every users
        logger.info("Fixing users, make sure every has the 'Member' role...")
        membership = api.portal.get_tool('portal_membership')
        members = membership.listMembers()
        for member in members:
            if 'Member' not in member.getRoles():
                api.user.grant_roles(user=member, roles=['Member'])

        # remove 'Member' role from every groups, including 'AuthenticatedUsers'
        logger.info("Fixing groups, make sure no more group has the 'Member' role...")
        group_ids = [grp.id for grp in api.group.get_groups()]
        assert('AuthenticatedUsers' in group_ids)
        for group_id in group_ids:
            api.group.revoke_roles(groupname=group_id, roles=['Member'])
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 4103...')
        self._fixGroupsAndUsersRoles()
        self._adaptHolidaysWarningMessage()


def migrate(context):
    '''This migration function will:

       1) Fix groups and users roles (roles 'Manager' and 'Member');
       2) Re-run the step that adapts holidays warning message as imio.pm.locales was not released...
    '''
    migrator = Migrate_To_4103(context)
    migrator.run()
    migrator.finish()
