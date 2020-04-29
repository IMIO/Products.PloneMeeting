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

from collective.iconifiedcategory.interfaces import IIconifiedCategorySettings
from DateTime import DateTime
from imio.helpers.cache import cleanRamCacheFor
from plone import api
from Products.PloneMeeting.columns import ItemLinkedMeetingColumn
from Products.PloneMeeting.columns import PMAnnexActionsColumn
from Products.PloneMeeting.columns import PMPrettyLinkColumn
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
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
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=(self._stateMappingFor('itemcreated'), ))
        self.request.cookies['pmShowDescriptions'] = 'true'

        self.changeUser('pmCreator1')
        # create 2 exactly same items, second will be set 'secret'
        publicItem = self.create('MeetingItem',
                                 title='Public item title',
                                 description='Public item description')
        self.addAnnex(publicItem)
        publicItem.setPrivacy('public')
        publicItem._update_after_edit()
        publicBrain = self.catalog(UID=publicItem.UID())[0]
        secretItem = self.create('MeetingItem',
                                 title='Secret item title',
                                 description='Secret item description')
        self.addAnnex(secretItem)
        secretItem.setPrivacy('secret')
        secretItem._update_after_edit()
        secretBrain = self.catalog(UID=secretItem.UID())[0]

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
            u"<div class='pretty_link' title='Secret item title'>"
            u"<span class='pretty_link_content state-itemcreated'>Secret item title <span class='discreet no_access'>"
            u"(You can not access this element)</span></span></div>")

    def test_pm_AnnexActionsColumnShowArrows(self):
        """Arrows are only shown if annex or annexDecision are orderable.
           Only displayed on annexDecisions if only annexDecision addable and no more annex addable."""
        # avoid adding recurring items to created meeting
        self._removeConfigObjectsFor(self.meetingConfig, folders=['recurringitems'])

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision text</p>')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)

        annex1_brain = self.catalog(UID=annex1.UID())[0]
        annex2_brain = self.catalog(UID=annex2.UID())[0]
        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        column = PMAnnexActionsColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        renderedColumnAnnex1 = column.renderCell(annex1_brain)
        renderedColumnAnnex2 = column.renderCell(annex2_brain)
        self.assertTrue(self.hasPermission(AddAnnex, item))
        # sort_categorized_tab must be False to show arrows
        sort_categorized_tab = api.portal.get_registry_record(
            'sort_categorized_tab',
            interface=IIconifiedCategorySettings,
        )
        self.assertTrue(sort_categorized_tab)
        self.assertFalse('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertFalse('folder_position_typeaware?position=up' in renderedColumnAnnex2)
        api.portal.set_registry_record('sort_categorized_tab',
                                       False,
                                       interface=IIconifiedCategorySettings)
        renderedColumnAnnex1 = column.renderCell(annex1_brain)
        renderedColumnAnnex2 = column.renderCell(annex2_brain)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnAnnex2)

        # now test when both annex and annexDecision may be added
        self.validateItem(item)
        self.assertTrue(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))
        annexDecision1 = self.addAnnex(item, relatedTo='item_decision')
        annexDecision2 = self.addAnnex(item, relatedTo='item_decision')
        annexDecision1_brain = self.catalog(UID=annexDecision1.UID())[0]
        annexDecision2_brain = self.catalog(UID=annexDecision2.UID())[0]
        renderedColumnAnnex1 = column.renderCell(annex1_brain)
        renderedColumnAnnex2 = column.renderCell(annex2_brain)
        renderedColumnDecisionAnnex1 = column.renderCell(annexDecision1_brain)
        renderedColumnDecisionAnnex2 = column.renderCell(annexDecision2_brain)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnAnnex2)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnDecisionAnnex1)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnDecisionAnnex2)
        # and it works
        item.folder_position_typeaware(position='down', id=annex1.getId())
        item.folder_position_typeaware(position='up', id=annex2.getId())
        item.folder_position_typeaware(position='down', id=annexDecision1.getId())
        item.folder_position_typeaware(position='up', id=annexDecision2.getId())

        # now when only annexDecision are addable
        meeting = self.create('Meeting', date=DateTime('2016/06/06'))
        self.presentItem(item)
        self.closeMeeting(meeting)
        self.assertFalse(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))
        renderedColumnAnnex1 = column.renderCell(annex1_brain)
        renderedColumnAnnex2 = column.renderCell(annex2_brain)
        renderedColumnDecisionAnnex1 = column.renderCell(annexDecision1_brain)
        renderedColumnDecisionAnnex2 = column.renderCell(annexDecision2_brain)
        self.assertFalse('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertFalse('folder_position_typeaware?position=up' in renderedColumnAnnex2)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnDecisionAnnex1)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnDecisionAnnex2)
        # and it works
        item.folder_position_typeaware(position='up', id=annexDecision1.getId())
        item.folder_position_typeaware(position='down', id=annexDecision2.getId())

    def test_pm_ItemLinkedMeetingColumnWhenMeetingNotViewable(self):
        """Test when link to meeting displayed in the items dashboard."""
        self._setPowerObserverStates(states=('presented', ))
        self._setPowerObserverStates(field_name='meeting_states', states=())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting', date=DateTime('2018/03/21'))

        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        column = ItemLinkedMeetingColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        # item not linked to a meeting
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertEqual(column.renderCell(item_brain), u'-')
        self.presentItem(item)

        # linked and viewable
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertTrue(u"<span class='pretty_link_content state-created'>" in column.renderCell(item_brain))
        # linked but not viewable
        self.changeUser('powerobserver1')
        # column have use_caching=True
        column = ItemLinkedMeetingColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        self.assertTrue(u"<span class='pretty_link_content state-created'>" in column.renderCell(item_brain))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testColumns, prefix='test_pm_'))
    return suite
