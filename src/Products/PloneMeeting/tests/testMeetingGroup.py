# -*- coding: utf-8 -*-
#
# File: testMeetingGroup.py
#
# Copyright (c) 2015 by Imio.be
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

import transaction
from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from zExceptions import Redirect

from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.statusmessages.interfaces import IStatusMessage


class testMeetingGroup(PloneMeetingTestCase):
    '''Tests the MeetingCategory class methods.'''

    def test_pm_CanNotRemoveUsedMeetingGroup(self):
        '''While removing a MeetingGroup, it should raise if it is used somewhere...'''
        cfg = self.meetingConfig
        cfg.setSelectableAdvisers(())
        cfg2 = self.meetingConfig2
        self.changeUser('pmManager')
        # delete recurring items, just keep item templates
        self._removeConfigObjectsFor(cfg, folders=['recurringitems', ])
        # make sure cfg2 does not interact...
        self._removeConfigObjectsFor(cfg2)
        # create an item
        item = self.create('MeetingItem')
        # default used proposingGroup is 'developers'
        self.assertEquals(item.getProposingGroup(), 'developers')
        # now try to remove corresponding group
        self.changeUser('admin')

        # 1) fails because used in the configuration, in
        # selectableCopyGroups, selectableAdvisers, customAdvisers or powerAdvisersGroups
        self.failIf(cfg.getCustomAdvisers())
        self.failIf(cfg.getPowerAdvisersGroups())
        self.failIf(cfg.getSelectableAdvisers())
        self.failUnless('developers_reviewers' in cfg.getSelectableCopyGroups())
        can_not_delete_meetinggroup_meetingconfig = \
            translate('can_not_delete_meetinggroup_meetingconfig',
                      domain="plone",
                      context=self.request)
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingconfig)
        # so remove selectableCopyGroups from the meetingConfigs
        cfg.setSelectableCopyGroups(())
        cfg2.setSelectableCopyGroups(())

        # define selectableAdvisers, the exception is also raised
        cfg.setSelectableAdvisers(('developers', ))
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingconfig)
        # so remove selectableAdvisers
        cfg.setSelectableAdvisers(())

        # define customAdvisers, the exception is also raised
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'developers',
              'delay': '5', }, ])
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingconfig)
        # so remove customAdvisers
        cfg.setCustomAdvisers([])

        # define powerAdvisersGroups, the exception is also raised
        cfg.setPowerAdvisersGroups(['developers', ])
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingconfig)
        # so remove powerAdvisersGroups
        cfg.setPowerAdvisersGroups([])

        # 2) fails because the corresponding Plone groups are not empty
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        can_not_delete_meetinggroup_plonegroup = \
            translate('can_not_delete_meetinggroup_plonegroup',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_plonegroup)
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
        self._make_not_found_user()
        # but it does not raise an exception with message 'can_not_delete_meetinggroup_plonegroup'
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])

        self.assertNotEquals(cm.exception.message, can_not_delete_meetinggroup_plonegroup)
        can_not_delete_meetinggroup_meetingitem = \
            translate('can_not_delete_meetinggroup_meetingitem',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingitem)

        # 3) complains about a linked meetingitem
        # checks on the item are made around :
        # item.getProposingGroup
        # item.getAssociatedGroups
        # item.getGroupInCharge
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

        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingitem)

        # now check with item having associatedGroups
        item.setProposingGroup('vendors')
        item.setAssociatedGroups(('developers', ))
        item.setOptionalAdvisers(())
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        item.setCopyGroups(())
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingitem)

        # now check with item having optionalAdvisers
        item.setProposingGroup('vendors')
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(('developers', ))
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        item.setCopyGroups(())
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingitem)

        # check with groupInCharge
        item.setProposingGroup('vendors')
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(())
        self.assertTrue('developers_advisers' not in item.adviceIndex)
        item.setGroupInCharge('developers')
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingitem)

        # check with item having copyGroups
        item.setGroupInCharge('')
        cfg.setUseCopies(True)
        item.setCopyGroups(('developers_reviewers', ))
        item.at_post_edit_script()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_meetingitem)

        # remove copyGroups for item so it works...
        item.setCopyGroups(())
        item.at_post_edit_script()
        self.tool.manage_delObjects(['developers', ])
        # the group is actually removed
        self.failIf(hasattr(self.tool, 'developers'))

        # 4) removing a used group in the configuration fails too
        # remove item because it uses 'vendors'
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        self.assertEquals(cfg.itemtemplates.template2.getProposingGroup(), 'vendors')
        # then fails because corresponding Plone groups are not empty...
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['vendors', ])

        self.assertEquals(cm.exception.message, can_not_delete_meetinggroup_plonegroup)
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
                                    mapping={'url': cfg.itemtemplates.template2.absolute_url()},
                                    context=self.portal.REQUEST))
        # so remove the item in the config (it could work by changing the proposingGroup too...)
        cfg.itemtemplates.manage_delObjects(['template2', ])
        # now it works...
        self.tool.manage_delObjects(['vendors', ])
        # the group is actually removed
        self.failIf(hasattr(self.tool, 'vendors'))

    def test_pm_CanNotRemoveMeetingGroupUsedAsGroupInCharge(self):
        '''While removing a MeetingGroup, it should raise if
           it is used as groupInCharge of another MeetingGroup.'''
        self.changeUser('siteadmin')
        group1 = self.create('MeetingGroup', id='group1', title='Group 1', acronym='G1')
        group2 = self.create('MeetingGroup', id='group2', title='Group 2', acronym='G2')
        group1.setGroupsInCharge(('group2',))
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects([group2.getId()])
        self.assertEquals(cm.exception.message,
                          translate('can_not_delete_meetinggroup_groupincharge',
                                    domain='plone',
                                    mapping={'group_title': group1.Title()},
                                    context=self.portal.REQUEST))

    def test_pm_DeactivatedGroupCanNoMoreBeUsed(self):
        """
          Check that when a MeetingGroup has been deactivated, it is no more useable in any
          functionnality of the application...
        """
        # delete the 'vendors' group so we are sure that methods and conditions
        # we need to remove every items using the 'vendors' group before being able to remove it...
        self.changeUser('admin')
        # make sure self.meetingConfig2 does not interact...
        self._removeConfigObjectsFor(self.meetingConfig2)
        self.meetingConfig.itemtemplates.manage_delObjects(['template2', ])
        # and remove 'vendors_reviewers' from every MeetingConfig.selectableCopyGroups
        # and 'vendors' from every MeetingConfig.selectableAdvisers
        self.meetingConfig.setSelectableCopyGroups(('developers_reviewers', ))
        self.meetingConfig.setSelectableAdvisers(('developers', ))
        self.meetingConfig2.setSelectableCopyGroups(('developers_reviewers', ))
        self.meetingConfig2.setSelectableAdvisers(('developers', ))
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
        self.assertTrue(self.tool.userIsAmong(['creators']))
        # after deactivation, the group is no more useable...
        self.changeUser('admin')
        developers = self.tool.developers
        self.do(developers, 'deactivate')
        self.changeUser('pmManager')
        self.assertTrue('developers' not in item.listAssociatedGroups())
        # remove proposingGroup or it will appear in the vocabulary as 'developers' is currently used...
        item.setProposingGroup('')
        self.assertTrue('developers' not in item.listProposingGroups())
        self.assertTrue('developers_reviewers' not in item.listCopyGroups())
        self.assertTrue('developers' not in item.listOptionalAdvisers())
        self.assertTrue(not self.tool.userIsAmong(['creators']))

    def test_pm_UpdatePloneGroupTitle(self):
        '''When the title of a MeetingGroup changed, the title of linked
           Plone groups is changed accordingly.'''
        developers = self.tool.developers
        devId = developers.getId()
        devTitle = developers.Title()
        # for now created Plone groups are correct
        for suffix in MEETING_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(devId, suffix))
            translatedSuffix = translate(suffix, domain='PloneMeeting', context=self.request)
            self.assertTrue(ploneGroup.getProperty('title') == ('{0} ({1})'.format(devTitle, translatedSuffix)))
        # update MeetingGroup title and check again
        devTitle = 'New developers meeting group title'
        developers.setTitle(devTitle)
        developers.at_post_edit_script()
        # Plone groups title have been updated
        for suffix in MEETING_GROUP_SUFFIXES:
            ploneGroup = self.portal.portal_groups.getGroupById('{0}_{1}'.format(devId, suffix))
            translatedSuffix = translate(suffix, domain='PloneMeeting', context=self.request)
            self.assertTrue(ploneGroup.getProperty('title') == ('{0} ({1})'.format(devTitle, translatedSuffix)))

    def test_pm_RemovedPloneGroupsAreRecreatedOnMeetingGroupEdit(self):
        """When a MeetingGroup is created/edited, it makes sure every Plone groups are
           created or created again if some where deleted..."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        # create a new group and make sure every Plone groups are created
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        # one Plone group created for each MEETING_GROUP_SUFFIXES
        self.assertEquals(len(newGroup.getPloneGroups()), len(MEETING_GROUP_SUFFIXES))

        # remove a Plone group
        newGroup_creators = newGroup.getPloneGroups(suffixes='creators')[0].getId()
        # this will raise a Redirect, catch it so group is removed
        try:
            self.portal.portal_groups.removeGroup(newGroup_creators)
        except Redirect:
            pass
        # now we have a missing group
        self.assertTrue(None in newGroup.getPloneGroups())
        self.assertTrue(newGroup_creators not in newGroup.getPloneGroups())
        # a missing Plone group makes various things fail, like MeetingConfig.listSelectableCopyGroups
        self.assertRaises(AttributeError, cfg.listSelectableCopyGroups)

        # correct this by editing the MeetingGroup
        newGroup.at_post_edit_script()
        self.assertFalse(None in newGroup.getPloneGroups())
        self.assertTrue(cfg.listSelectableCopyGroups())

    def test_pm_RedefinedCertifiedSignatures(self):
        """MeetingGroup.certifiedSignatures may override what is defined on a MeetingConfig,
           either partially (one signature, the other is taken from MeetingConfig) or completely."""
        cfg = self.meetingConfig
        certified = [
            {'signatureNumber': '1',
             'name': 'Name1',
             'function': 'Function1',
             'date_from': '',
             'date_to': '',
             },
            {'signatureNumber': '2',
             'name': 'Name2',
             'function': 'Function2',
             'date_from': '',
             'date_to': '',
             },
        ]
        cfg.setCertifiedSignatures(certified)
        vendors = self.tool.vendors
        # called without computed=True, the actual values defined on the MeetingGroup is returned
        self.assertEquals(vendors.getCertifiedSignatures(), ())
        # with a cfg, cfg values are returned if not overrided
        self.assertEquals(vendors.getCertifiedSignatures(computed=True, context=cfg),
                          ['Function1', 'Name1', 'Function2', 'Name2'])

        # redefine one signature
        group_certified = [
            {'signatureNumber': '2',
             'name': 'Redefined name2',
             'function': 'Redefined function2',
             'date_from': '',
             'date_to': ''},
            ]
        # it validates
        vendors.setCertifiedSignatures(group_certified)
        self.assertEquals(vendors.getCertifiedSignatures(computed=True, context=cfg),
                          ['Function1', 'Name1', 'Redefined function2', 'Redefined name2'])

        # redefine every signatures
        group_certified = [
            {'signatureNumber': '1',
             'name': 'Redefined name1',
             'function': 'Redefined function1',
             'date_from': '',
             'date_to': ''},
            {'signatureNumber': '2',
             'name': 'Redefined name2',
             'function': 'Redefined function2',
             'date_from': '',
             'date_to': ''},
            ]
        vendors.setCertifiedSignatures(group_certified)
        self.assertEquals(vendors.getCertifiedSignatures(computed=True, context=cfg),
                          ['Redefined function1', 'Redefined name1',
                           'Redefined function2', 'Redefined name2'])

        # redefine a third signature
        group_certified = [
            {'signatureNumber': '1',
             'name': 'Redefined name1',
             'function': 'Redefined function1',
             'date_from': '',
             'date_to': ''},
            {'signatureNumber': '2',
             'name': 'Redefined name2',
             'function': 'Redefined function2',
             'date_from': '',
             'date_to': ''},
            {'signatureNumber': '3',
             'name': 'Redefined name3',
             'function': 'Redefined function3',
             'date_from': '',
             'date_to': ''},
            ]
        vendors.setCertifiedSignatures(group_certified)
        self.assertEquals(vendors.getCertifiedSignatures(computed=True, context=cfg),
                          ['Redefined function1', 'Redefined name1',
                           'Redefined function2', 'Redefined name2',
                           'Redefined function3', 'Redefined name3'])

        # redefine a third signature but not the second
        group_certified = [
            {'signatureNumber': '1',
             'name': 'Redefined name1',
             'function': 'Redefined function1',
             'date_from': '',
             'date_to': ''},
            {'signatureNumber': '3',
             'name': 'Redefined name3',
             'function': 'Redefined function3',
             'date_from': '',
             'date_to': ''},
            ]
        vendors.setCertifiedSignatures(group_certified)
        self.assertEquals(vendors.getCertifiedSignatures(computed=True, context=cfg),
                          ['Redefined function1', 'Redefined name1',
                           'Function2', 'Name2',
                           'Redefined function3', 'Redefined name3'])

        # period validity is taken into account
        # redefine a third signature but not the second
        group_certified = [
            {'signatureNumber': '1',
             'name': 'Redefined name1',
             'function': 'Redefined function1',
             'date_from': '2015/01/01',
             'date_to': '2015/05/05'},
            {'signatureNumber': '3',
             'name': 'Redefined name3',
             'function': 'Redefined function3',
             'date_from': '',
             'date_to': ''},
            ]
        vendors.setCertifiedSignatures(group_certified)
        self.assertEquals(vendors.getCertifiedSignatures(computed=True, context=cfg),
                          ['Function1', 'Name1',
                           'Function2', 'Name2',
                           'Redefined function3', 'Redefined name3'])

    def test_pm_UserPloneGroups(self):
        """This will return the Plone groups of a MeetingGroup the current user is in."""
        # add specific users so it works correctly with different testing profile
        membershipTool = api.portal.get_tool('portal_membership')
        membershipTool.addMember(id='test_user1',
                                 password='12345',
                                 roles=('Member', ),
                                 domains=())
        membershipTool.addMember(id='test_user2',
                                 password='12345',
                                 roles=('Member', ),
                                 domains=())
        self.portal.portal_groups.addPrincipalToGroup('test_user1', 'developers_creators')
        self.portal.portal_groups.addPrincipalToGroup('test_user2', 'vendors_advisers')
        self.portal.portal_groups.addPrincipalToGroup('test_user2', 'developers_advisers')
        self.portal.portal_groups.addPrincipalToGroup('test_user2', 'developers_creators')
        self.portal.portal_groups.addPrincipalToGroup('test_user2', 'developers_observers')
        self.portal.portal_groups.addPrincipalToGroup('test_user2', 'developers_reviewers')

        self.changeUser('test_user1')
        self.assertFalse(self.tool.vendors.userPloneGroups())
        self.assertEquals(self.tool.developers.userPloneGroups(),
                          ['developers_creators'])

        self.changeUser('test_user2')
        self.assertEquals(self.tool.vendors.userPloneGroups(),
                          ['vendors_advisers'])
        self.assertEquals(sorted(self.tool.developers.userPloneGroups()),
                          ['developers_advisers', 'developers_creators',
                           'developers_observers', 'developers_reviewers'])
        # we may ask if user is in a specific suffix
        self.assertEquals(self.tool.developers.userPloneGroups(suffixes=['observers']),
                          ['developers_observers'])
        self.assertEquals(sorted(self.tool.developers.userPloneGroups(suffixes=['advisers', 'reviewers'])),
                          ['developers_advisers', 'developers_reviewers'])
        self.assertEquals(sorted(self.tool.developers.userPloneGroups(suffixes=['advisers', 'other_suffix'])),
                          ['developers_advisers'])

    def test_pm_PloneGroupRemoved(self):
        """A Plone group linked to a MeetingGroup can not be removed."""
        self.changeUser('siteadmin')
        # create a group with title containing special characters
        newGroup = self.create('MeetingGroup', title='New group éé', acronym='N.G.')
        newGroup_creators = '{0}_creators'.format(newGroup.getId())
        msg = translate("You cannot delete the group \"${group_id}\", "
                        "linked to MeetingGroup \"${meeting_group}\" !",
                        mapping={'group_id': newGroup_creators,
                                 'meeting_group': safe_unicode(newGroup.Title())},
                        domain='PloneMeeting',
                        context=self.request)
        # no messages for now
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages, [])
        portal_groups = self.portal.portal_groups
        self.assertTrue(newGroup_creators in portal_groups.listGroupIds())
        # manage transaction because we need to revert the removeGroup
        # or group is really removed...
        transaction.commit()
        transaction.begin()
        self.assertRaises(Redirect, portal_groups.removeGroup, newGroup_creators)
        transaction.abort()
        self.assertTrue(newGroup_creators in portal_groups.listGroupIds())
        # the portal_message was added
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[0].message, msg)

        # a Plone group that is not linked to a MeetingGroup is deletable
        self.assertTrue('Reviewers' in portal_groups.listGroupIds())
        portal_groups.removeGroup('Reviewers')
        self.assertFalse('Reviewers' in portal_groups.listGroupIds())

        # Plone groups linked to a MeetingGroup are removable
        # if currently removing the MeetingGroup
        self.assertTrue(newGroup_creators in portal_groups.listGroupIds())
        self.deleteAsManager(newGroup.UID())
        self.assertFalse(newGroup_creators in portal_groups.listGroupIds())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingGroup, prefix='test_pm_'))
    return suite
