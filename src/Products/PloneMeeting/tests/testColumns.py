# -*- coding: utf-8 -*-
#
# File: testAdvices.py
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

from imio.helpers.cache import cleanRamCacheFor
from Products.PloneMeeting.columns import PMPrettyLinkColumn
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testColumns(PloneMeetingTestCase):
    '''Tests various aspects of advices management.
       Advices are enabled for PloneGov Assembly, not for PloneMeeting Assembly.'''

    def test_pm_ItemPrettyLinkColumnWhenNotPrivacyViewable(self):
        """When item is not privacyViewable :
           - no link is rendred, only the title;
           - more infos are not displayed."""
        cfg = self.meetingConfig
        cfg.setRestrictAccessToSecretItems(True)
        cfg.setItemRestrictedPowerObserversStates((self.WF_STATE_NAME_MAPPINGS['itemcreated'], ))
        self.request.cookies['pmShowDescriptions'] = 'true'

        self.changeUser('pmCreator1')
        # create 2 exactly same items, second will be set 'secret'
        publicItem = self.create('MeetingItem',
                                 title='Public item title',
                                 description='Public item description')
        self.addAnnex(publicItem)
        publicItem.setPrivacy('public')
        publicItem.at_post_edit_script()
        publicBrain = self.portal.portal_catalog(UID=publicItem.UID())[0]
        secretItem = self.create('MeetingItem',
                                 title='Secret item title',
                                 description='Secret item description')
        self.addAnnex(secretItem)
        secretItem.setPrivacy('secret')
        secretItem.at_post_edit_script()
        secretBrain = self.portal.portal_catalog(UID=secretItem.UID())[0]

        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        column = PMPrettyLinkColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        # as a normal user, everything is viewable
        # link to title, more-infos and annexes
        self.assertTrue(publicItem.adapted().isPrivacyViewable())
        self.assertTrue(secretItem.adapted().isPrivacyViewable())
        publicBrainPrettyLinkColumn = column.renderCell(publicBrain)
        secretBrainPrettyLinkColumn = column.renderCell(secretBrain)
        # link to title
        self.assertTrue("href='{0}'".format(publicBrain.getURL()) in publicBrainPrettyLinkColumn)
        self.assertTrue("href='{0}'".format(secretBrain.getURL()) in secretBrainPrettyLinkColumn)
        # more infos
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        self.assertTrue(' class="pmMoreInfo">' in secretBrainPrettyLinkColumn)
        # annexes
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        self.assertTrue(' class="pmMoreInfo">' in secretBrainPrettyLinkColumn)

        # now as a restricted power observer, secretItem title is only shown (without a link)
        self.changeUser('restrictedpowerobserver1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.assertTrue(publicItem.adapted().isPrivacyViewable())
        self.assertFalse(secretItem.adapted().isPrivacyViewable())
        publicBrainPrettyLinkColumn = column.renderCell(publicBrain)
        secretBrainPrettyLinkColumn = column.renderCell(secretBrain)
        # link to title
        self.assertTrue("href='{0}'".format(publicBrain.getURL()) in publicBrainPrettyLinkColumn)
        # more infos
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        # annexes
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        # the secret item is not accessible
        self.assertEqual(
            secretBrainPrettyLinkColumn,
            u"<div class='pretty_link state-itemcreated' title='Secret item title'>"
            u"<span class='pretty_link_content'>Secret item title <span class='discreet no_access'>"
            u"(You can not access this element)</span></span></div>")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testColumns, prefix='test_pm_'))
    return suite
