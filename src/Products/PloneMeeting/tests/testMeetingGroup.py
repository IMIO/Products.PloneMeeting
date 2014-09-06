# -*- coding: utf-8 -*-
#
# File: testMeetingGroup.py
#
# Copyright (c) 2007-2013 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import cleanRamCacheFor


class testMeetingGroup(PloneMeetingTestCase):
    '''Tests the MeetingCategory class methods.'''

    def test_pm_CanNotRemoveUsedMeetingGroup(self):
        '''While removing a MeetingGroup, it should raise if it is used somewhere...'''
        self.changeUser('pmManager')
        # make sure self.meetingConfig2 does not interact...
        self._removeItemsDefinedInTool(self.meetingConfig2)
        # create an item
        item = self.create('MeetingItem')
        # default used proposingGroup is 'developers'
        self.assertEquals(item.getProposingGroup(), 'developers')
        # now try to remove corresponding group
        self.changeUser('admin')

        # 1) fails because used in the configuration, in
        # selectableCopyGroups, customAdvisers or powerAdvisersGroups
        self.failIf(self.meetingConfig.getCustomAdvisers())
        self.failIf(self.meetingConfig.getPowerAdvisersGroups())
        self.failUnless('developers_reviewers' in self.meetingConfig.getSelectableCopyGroups())
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingconfig')
        # so remove selectableCopyGroups from the meetingConfigs
        self.meetingConfig.setSelectableCopyGroups(())
        self.meetingConfig2.setSelectableCopyGroups(())
        # define customAdvisers, the exception is also raised
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'delay': '5', }, ])
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingconfig')
        # so remove customAdvisers
        self.meetingConfig.setCustomAdvisers([])
        # define powerAdvisersGroups, the exception is also raised
        self.meetingConfig.setPowerAdvisersGroups(['developers', ])
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingconfig')
        # so remove powerAdvisersGroups
        self.meetingConfig.setPowerAdvisersGroups([])

        # 2) fails because the corresponding Plone groups are not empty
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_plonegroup')
        # so remove every users of these groups
        developers = self.tool.developers
        for ploneGroup in developers.getPloneGroups():
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # check that it works if left users in the Plone groups are
        # "not found" users, aka when you delete a user from Plone without removing him
        # before from groups he is in, a special "not found" user will still be assigned to the groups...
        # to test, add a new user, assign it to the developers_creators group, remove the user
        # it should not complain about 'can_not_delete_meetinggroup_plonegroup'
        membershipTool = getToolByName(self.portal, 'portal_membership')
        membershipTool.addMember(id='new_test_user',
                                 password='12345',
                                 roles=('Member', ),
                                 domains=())
        self.portal.portal_groups.addPrincipalToGroup('new_test_user', 'developers_creators')
        membershipTool.deleteMembers(('new_test_user', ))
        # now we have a 'not found' user in developers_creators
        self.assertTrue(('new_test_user', '<new_test_user: not found>') in
                        self.portal.acl_users.source_groups.listAssignedPrincipals('developers_creators'))
        # but it does not raise an exception with message 'can_not_delete_meetinggroup_plonegroup'
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertNotEquals(cm.exception.message, 'can_not_delete_meetinggroup_plonegroup')

        # 3) complains about a linked meetingitem
        # checks on the item are made around :
        # item.getProposingGroup
        # item.getAssociatedGroups
        # item.adviceIndex
        # item.getCopyGroups
        # so check the 5 possible "states"

        # first check when the item is using 'proposingGroup', it is the case here
        # for item, make sure other conditions are False
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(())
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        item.setCopyGroups(())
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingitem')

        # now check with item having associatedGroups
        item.setProposingGroup('vendors')
        item.setAssociatedGroups(('developers', ))
        item.setOptionalAdvisers(())
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        item.setCopyGroups(())
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingitem')

        # now check with item having optionalAdvisers
        item.setProposingGroup('vendors')
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(('developers', ))
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        item.setCopyGroups(())
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingitem')

        # check with item having copyGroups
        item.setProposingGroup('vendors')
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(())
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        self.meetingConfig.setUseCopies(True)
        item.setCopyGroups(('developers_reviewers', ))
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingitem')

        # remove copyGroups for item so it works...
        item.setCopyGroups(())
        item.at_post_edit_script()
        self.tool.manage_delObjects(['developers', ])
        # the group is actually removed
        self.failIf(hasattr(self.tool, 'developers'))

        # 4) removing a used group in the configuration fails too
        # remove item because it uses 'vendors'
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        self.assertEquals(self.meetingConfig.itemtemplates.template2.getProposingGroup(), 'vendors')
        # then fails because corresponding Plone groups are not empty...
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['vendors', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_plonegroup')
        # so remove them...
        vendors = self.tool.vendors
        for ploneGroup in vendors.getPloneGroups():
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)

        # 5) then fails because used by an item present in the configuration
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['vendors', ])
        self.maxDiff = None
        self.assertEquals(cm.exception.message,
                          translate('can_not_delete_meetinggroup_config_meetingitem',
                                    domain='plone',
                                    mapping={'url': self.meetingConfig.itemtemplates.template2.absolute_url()},
                                    context=self.portal.REQUEST))
        # so remove the item in the config (it could work by changing the proposingGroup too...)
        self.meetingConfig.itemtemplates.manage_delObjects(['template2', ])
        # now it works...
        self.tool.manage_delObjects(['vendors', ])
        # the group is actually removed
        self.failIf(hasattr(self.tool, 'vendors'))

    def test_pm_DeactivatedGroupCanNoMoreBeUsed(self):
        """
          Check that when a MeetingGroup has been deactivated, it is no more useable in any
          functionnality of the application...
        """
        # delete the 'vendors' group so we are sure that methods and conditions
        # we need to remove every items using the 'vendors' group before being able to remove it...
        self.changeUser('admin')
        # make sure self.meetingConfig2 does not interact...
        self._removeItemsDefinedInTool(self.meetingConfig2)
        self.meetingConfig.itemtemplates.manage_delObjects(['template2', ])
        # and remove 'vendors_reviewers' from every MeetingConfig.selectableCopyGroups
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', ))
        self.meetingConfig2.setSelectableCopyGroups(('developers_reviewers', ))
        # and remove users from vendors Plone groups
        vendors = self.tool.vendors
        for ploneGroup in vendors.getPloneGroups():
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # now we can delete it...
        self.tool.manage_delObjects(['vendors', ])
        self.changeUser('pmManager')
        # create an item so we can test vocabularies
        item = self.create('MeetingItem')
        self.assertTrue('developers' in item.listAssociatedGroups())
        self.assertTrue('developers' in item.listProposingGroups())
        self.assertTrue('developers_reviewers' in item.listCopyGroups())
        self.assertTrue('developers' in item.listOptionalAdvisers())
        self.assertTrue(self.tool.userIsAmong('creators'))
        # after deactivation, the group is no more useable...
        self.changeUser('admin')
        developers = self.tool.developers
        self.do(developers, 'deactivate')
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        self.changeUser('pmManager')
        self.assertTrue('developers' not in item.listAssociatedGroups())
        # remove proposingGroup or it will appear in the vocabulary as 'developers' is currently used...
        item.setProposingGroup('')
        self.assertTrue('developers' not in item.listProposingGroups())
        self.assertTrue('developers_reviewers' not in item.listCopyGroups())
        self.assertTrue('developers' not in item.listOptionalAdvisers())
        self.assertTrue(not self.tool.userIsAmong('creators'))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingGroup, prefix='test_pm_'))
    return suite
