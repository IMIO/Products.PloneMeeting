# -*- coding: utf-8 -*-
#
# File: testOwnOrg.py
#
# Copyright (c) 2018 by Imio.be
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

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.contact.plonegroup.utils import get_plone_groups
from OFS.ObjectManager import BeforeDeleteException
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.i18n import translate
from plone import api
from Products.statusmessages.interfaces import IStatusMessage

import transaction


class testOwnOrg(PloneMeetingTestCase):
    '''Tests the own organization related functionnalities.'''

    def test_pm_CanNotRemoveUsedOrganization(self):
        '''While removing an organization from own organization,
           it should raise if it is used somewhere...'''
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
        self.assertEquals(item.getProposingGroup(), self.developers_uid)

        # now try to remove corresponding organization
        self.changeUser('admin')

        # 1) fails because used in the configuration, in
        # selectableCopyGroups, selectableAdvisers, customAdvisers or powerAdvisersGroups
        self.failIf(cfg.getCustomAdvisers())
        self.failIf(cfg.getPowerAdvisersGroups())
        self.failIf(cfg.getSelectableAdvisers())
        self.failUnless(get_plone_group_id(self.developers_uid, 'reviewers')
                        in cfg.getSelectableCopyGroups())
        can_not_delete_organization_meetingconfig = \
            translate('can_not_delete_organization_meetingconfig',
                      domain="plone",
                      mapping={'cfg_url': cfg.absolute_url()},
                      context=self.request)
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove selectableCopyGroups from the meetingConfigs
        cfg.setSelectableCopyGroups(())
        cfg2.setSelectableCopyGroups(())

        # define selectableAdvisers, the exception is also raised
        cfg.setSelectableAdvisers((self.developers_uid, ))
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove selectableAdvisers
        cfg.setSelectableAdvisers(())

        # define customAdvisers, the exception is also raised
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'delay': '5', }, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove customAdvisers
        cfg.setCustomAdvisers([])

        # define powerAdvisersGroups, the exception is also raised
        cfg.setPowerAdvisersGroups([self.developers_uid, ])
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingconfig)
        # so remove powerAdvisersGroups
        cfg.setPowerAdvisersGroups([])

        # 2) fails because the corresponding Plone groups are not empty
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        can_not_delete_organization_plonegroup = \
            translate('can_not_delete_organization_plonegroup',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_organization_plonegroup)
        # so remove every users of these groups
        for ploneGroup in get_plone_groups(self.developers_uid):
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # check that it works if left users in the Plone groups are
        # "not found" users, aka when you delete a user from Plone without removing him
        # before from groups he is in, a special "not found" user will still be assigned to the groups...
        # to test, add a new user, assign it to the developers_creators group, remove the user
        # it should not complain about 'can_not_delete_organization_plonegroup'
        self._make_not_found_user()
        # but it does not raise an exception with message 'can_not_delete_organization_plonegroup'
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)

        self.assertNotEquals(cm.exception.message, can_not_delete_organization_plonegroup)
        can_not_delete_organization_meetingitem = \
            translate('can_not_delete_organization_meetingitem',
                      domain="plone",
                      context=self.request)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingitem)

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
        self.assertTrue(get_plone_group_id(self.developers_uid, 'advisers')
                        not in item.adviceIndex)
        item.setCopyGroups(())
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)

        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingitem)

        # now check with item having associatedGroups
        item.setProposingGroup(self.vendors_uid)
        item.setAssociatedGroups((self.developers_uid, ))
        item.setOptionalAdvisers(())
        self.assertTrue(get_plone_group_id(self.developers_uid, 'advisers')
                        not in item.adviceIndex)
        item.setCopyGroups(())
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingitem)

        # now check with item having optionalAdvisers
        item.setProposingGroup(self.vendors_uid)
        item.setAssociatedGroups(())
        item.setOptionalAdvisers((self.developers_uid, ))
        self.assertTrue(get_plone_group_id(self.developers_uid, 'advisers')
                        not in item.adviceIndex)
        item.setCopyGroups(())
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingitem)

        # check with groupInCharge
        item.setProposingGroup(self.vendors_uid)
        item.setAssociatedGroups(())
        item.setOptionalAdvisers(())
        self.assertTrue(get_plone_group_id(self.developers_uid, 'advisers')
                        not in item.adviceIndex)
        self._setUpGroupInCharge(item, group=self.developers_uid)
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingitem)

        # check with item having copyGroups
        self._tearDownGroupInCharge(item)
        cfg.setUseCopies(True)
        item.setCopyGroups((get_plone_group_id(self.developers_uid, 'reviewers'), ))
        item._update_after_edit()
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.developers_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message, can_not_delete_organization_meetingitem)

        # remove copyGroups
        item.setCopyGroups(())
        item._update_after_edit()
        # unselect organizations from plonegroup configuration so it works...
        self._select_organization(self.developers_uid, remove=True)
        self.portal.restrictedTraverse('@@delete_givenuid')(
            self.developers_uid, catch_before_delete_exception=False)
        # the group is actually removed
        self.failIf(self.developers in self.own_org)

        # 4) removing a used group in the configuration fails too
        # remove item because it uses 'vendors'
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        self.assertEquals(cfg.itemtemplates.template2.getProposingGroup(), self.vendors_uid)
        # then fails because corresponding Plone groups are not empty...
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)

        self.assertEquals(cm.exception.message, can_not_delete_organization_plonegroup)
        # so remove them...
        for ploneGroup in get_plone_groups(self.vendors_uid):
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)

        # 5) then fails because used by an item present in the configuration
        transaction.commit()
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                self.vendors_uid, catch_before_delete_exception=False)
        self.maxDiff = None
        self.assertEquals(cm.exception.message,
                          translate('can_not_delete_organization_config_meetingitem',
                                    domain='plone',
                                    mapping={'url': cfg.itemtemplates.template2.absolute_url()},
                                    context=self.portal.REQUEST))
        # so remove the item in the config (it could work by changing the proposingGroup too...)
        cfg.itemtemplates.manage_delObjects(['template2', ])
        # unselect organizations from plonegroup configuration so it works...
        self._select_organization(self.vendors_uid, remove=True)
        # now it works...
        self.portal.restrictedTraverse('@@delete_givenuid')(
            self.vendors_uid, catch_before_delete_exception=False)
        # the group is actually removed
        self.failIf(self.vendors in self.own_org)

    def test_pm_CanNotRemoveOrganizationUsedAsGroupInCharge(self):
        '''While removing an organization, it should raise if
           it is used as groupInCharge of another organization.'''
        self.changeUser('siteadmin')
        org1 = self.create('organization', id='org1', title='Org 1', acronym='O1')
        org2 = self.create('organization', id='org2', title='Org 2', acronym='O2')
        org2_uid = org2.UID()
        org1.groups_in_charge = [org2_uid]
        with self.assertRaises(BeforeDeleteException) as cm:
            self.portal.restrictedTraverse('@@delete_givenuid')(
                org2_uid, catch_before_delete_exception=False)
        self.assertEquals(cm.exception.message,
                          translate('can_not_delete_organization_groupincharge',
                                    domain='plone',
                                    mapping={'org_url': org1.absolute_url()},
                                    context=self.portal.REQUEST))

    def test_pm_DeactivatedOrgCanNoMoreBeUsed(self):
        """
          Check that when an organiztion is unselected (deactivated), it is no more useable in any
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
        dev_reviewers = get_plone_group_id(self.developers_uid, 'reviewers')
        self.meetingConfig.setSelectableCopyGroups(
            (dev_reviewers, ))
        self.meetingConfig.setSelectableAdvisers((self.developers_uid, ))
        self.meetingConfig2.setSelectableCopyGroups(
            (dev_reviewers, ))
        self.meetingConfig2.setSelectableAdvisers(
            (self.developers_uid, ))
        # and remove users from vendors Plone groups
        for ploneGroup in get_plone_groups(self.vendors_uid):
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # unselect it
        self._select_organization(self.vendors_uid, remove=True)
        # now we can delete it...
        self.portal.restrictedTraverse('@@delete_givenuid')(
            self.vendors_uid, catch_before_delete_exception=False)
        self.changeUser('pmManager')
        # create an item so we can test vocabularies
        item = self.create('MeetingItem')
        self.assertTrue(self.developers_uid in item.listAssociatedGroups())
        self.assertTrue(self.developers_uid in item.listProposingGroups())
        self.assertTrue(dev_reviewers in item.listCopyGroups())
        self.assertTrue(self.developers_uid in item.listOptionalAdvisers())
        self.assertTrue(self.tool.userIsAmong(['creators']))
        # after deactivation, the group is no more useable...
        self.changeUser('admin')
        self._select_organization(self.developers_uid, remove=True)
        self.changeUser('pmManager')
        self.assertFalse(self.developers_uid in item.listAssociatedGroups())
        # remove proposingGroup or it will appear in the vocabulary as 'developers' is currently used...
        item.setProposingGroup('')
        self.assertFalse(self.developers_uid in item.listProposingGroups())
        self.assertFalse(dev_reviewers in item.listCopyGroups())
        self.assertFalse(self.developers_uid in item.listOptionalAdvisers())
        self.assertFalse(self.tool.userIsAmong(['creators']))

    def test_pm_RedefinedCertifiedSignatures(self):
        """organization.certified_signatures may override what is defined on a MeetingConfig,
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
        # called without computed=True, the actual values defined on the MeetingGroup is returned
        self.assertEquals(self.vendors.get_certified_signatures(), [])
        # with a cfg, cfg values are returned if not overrided
        self.assertEquals(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
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
        self.vendors.certified_signatures = group_certified
        self.assertEquals(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
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
        self.vendors.certified_signatures = group_certified
        self.assertEquals(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
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
        self.vendors.certified_signatures = group_certified
        self.assertEquals(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
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
        self.vendors.certified_signatures = group_certified
        self.assertEquals(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
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
        self.vendors.certified_signatures = group_certified
        self.assertEquals(self.vendors.get_certified_signatures(computed=True, cfg=cfg),
                          ['Function1', 'Name1',
                           'Function2', 'Name2',
                           'Redefined function3', 'Redefined name3'])

    def test_pm_OwnOrgNotDeletable(self):
        """The own_org element is not deletable using delete_uid."""
        self.changeUser('siteadmin')
        self.assertRaises(
            Unauthorized,
            self.portal.restrictedTraverse('@@delete_givenuid'), self.own_org.UID())

    def test_pm_DeactivateOrganization(self):
        """Deactivating an organization will remove every Plone groups from
           every MeetingConfig.selectableCopyGroups field."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('admin')
        # for now, the 'developers_reviewers' is in self.meetingConfig.selectableCopyGroups
        self.assertTrue(self.developers_reviewers in cfg.getSelectableCopyGroups())
        self.assertTrue(self.developers_reviewers in cfg2.getSelectableCopyGroups())
        # when deactivated, it is no more the case...
        self._select_organization(self.developers_uid, remove=True)
        self.assertTrue(self.developers_reviewers not in cfg.getSelectableCopyGroups())
        self.assertTrue(self.developers_reviewers not in cfg2.getSelectableCopyGroups())

    def test_pm_WarnUserWhenAddingNewOrgOutiseOwnOrg(self):
        """ """
        # when added in directory or organization ouside own_org, a message is displayed
        for location in (self.portal.contacts, self.developers):
            add_view = location.restrictedTraverse('++add++organization')
            add_view.ti = self.portal.portal_types.organization
            self.request['PUBLISHED'] = add_view
            messages = IStatusMessage(self.request).show()
            self.assertEqual(len(messages), 0)
            add_view.update()
            messages = IStatusMessage(self.request).show()
            self.assertEqual(len(messages), 1)
            warning_msg = translate(msgid="warning_adding_org_outside_own_org",
                                    domain='PloneMeeting',
                                    context=self.request)
            self.assertEqual(messages[-1].message, warning_msg)
        # when added in own_org, no warning
        add_view = self.own_org.restrictedTraverse('++add++organization')
        add_view.ti = self.portal.portal_types.organization
        self.request['PUBLISHED'] = add_view
        add_view.update()
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testOwnOrg, prefix='test_pm_'))
    return suite
