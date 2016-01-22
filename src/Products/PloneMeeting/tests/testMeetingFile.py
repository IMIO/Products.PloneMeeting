# -*- coding: utf-8 -*-
#
# File: testMeetingFile.py
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

from AccessControl import Unauthorized
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.indexes import SearchableText
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testMeetingFile(PloneMeetingTestCase):
    '''Tests the MeetingFileType class methods.'''

    def test_pm_MayChangeToPrint(self):
        '''By default, mayChangeToPrint is only if toPrint activated
           and user may edit the meetingFile.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # not activated in the cfg, not changeable
        self.assertEquals(cfg.getEnableAnnexToPrint(), 'disabled')
        self.assertFalse(annex.adapted().mayChangeToPrint())
        cfg.setEnableAnnexToPrint('enabled_for_info')
        self.assertTrue(annex.adapted().mayChangeToPrint())
        # propose it, no more editable and no more mayChangeToPrint
        self.proposeItem(item)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(annex.adapted().mayChangeToPrint())

    def test_pm_MayChangeConfidentiality(self):
        '''By default, mayChangeConfidentiality is only if activated
           and user may edit the meetingFile and is a Manager.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # not activated in the cfg and user is not a Manager
        self.assertFalse(cfg.getEnableAnnexConfidentiality())
        self.assertFalse(annex.adapted().mayChangeConfidentiality())
        cfg.setEnableAnnexConfidentiality(True)
        self.assertFalse(annex.adapted().mayChangeConfidentiality())
        # validate it so pmManager may see it
        self.validateItem(item)
        self.changeUser('pmManager')
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(annex.adapted().mayChangeConfidentiality())

    def test_pm_MeetingFileFoundInItemSearchableText(self, ):
        '''MeetingFiles title is indexed in the item SearchableText.'''
        ANNEX_TITLE = "SpecialAnnexTitle"
        ITEM_TITLE = "SpecialItemTitle"
        ITEM_DESCRIPTION = "Item description"
        ITEM_DECISION = "Item decision"
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title=ITEM_TITLE)
        item.setDescription(ITEM_DESCRIPTION)
        item.setDecision(ITEM_DECISION)
        item.reindexObject(idxs=['SearchableText', ])
        catalog = self.portal.portal_catalog
        index = catalog.Indexes['SearchableText']
        self.assertTrue(len(catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertFalse(catalog(SearchableText=ANNEX_TITLE))
        self.assertEquals(SearchableText(item)(),
                          'SpecialItemTitle  <p>Item description</p>  <p>Item decision</p> ')
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p'])

        # add an annex and test that the annex title is found in the item's SearchableText
        annex = self.addAnnex(item, annexTitle=ANNEX_TITLE)
        # now querying for ANNEX_TITLE will return the relevant item
        self.assertTrue(len(catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertTrue(len(catalog(SearchableText=ANNEX_TITLE)) == 2)
        self.assertEquals(SearchableText(item)(),
                          'SpecialItemTitle  <p>Item description</p>  <p>Item decision</p>  SpecialAnnexTitle ')
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p', 'specialannextitle'])
        # if we remove the annex, the item is not found anymore when querying
        # on removed annex's title
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertTrue(catalog(SearchableText=ITEM_TITLE))
        self.assertFalse(catalog(SearchableText=ANNEX_TITLE))

    def test_pm_AnnexDefaultValues(self):
        '''When creating an annex, default values are correctly set and item's annexIndex is correct.'''
        cfg = self.meetingConfig
        # enable annex printing
        cfg.setEnableAnnexToPrint(True)
        cfg.setAnnexToPrintDefault(True)
        # enable annex confidentiality
        cfg.setEnableAnnexConfidentiality(True)
        mft = cfg.meetingfiletypes.get('item-annex')
        mft.setIsConfidentialDefault(True)

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item, annexType='item-annex')
        # check that everything is correct
        self.assertTrue(annex.getToPrint())
        self.assertTrue(annex.getIsConfidential())
        annexInfo = item.annexIndex[0]
        self.assertTrue(annexInfo['toPrint'])
        self.assertTrue(annexInfo['isConfidential'])

    def test_pm_ToggleAnnexIsConfidential(self):
        """Test the '@@toggle_annex_is_confidential' view."""
        self.meetingConfig.setEnableAnnexConfidentiality(True)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        view = annex.restrictedTraverse('@@toggle_annex_is_confidential')

        # toggle value
        self.assertTrue(annex.adapted().mayChangeConfidentiality())
        self.assertEquals(annex.getIsConfidential(), False)
        self.assertEquals(item.annexIndex[0]['isConfidential'], False)
        view.toggle()
        self.assertEquals(annex.getIsConfidential(), True)
        self.assertEquals(item.annexIndex[0]['isConfidential'], True)

        # if a user tries to change confidentiality but may not, it raises Unauthorized
        self.proposeItem(item)
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, annex))
        self.assertFalse(annex.adapted().mayChangeConfidentiality())
        self.assertRaises(Unauthorized, view.toggle)
        # isConfidential did not change
        self.assertEquals(annex.getIsConfidential(), True)
        self.assertEquals(item.annexIndex[0]['isConfidential'], True)

    def test_pm_ToggleAnnexToPrint(self):
        """Test the '@@toggle_annex_to_print' view."""
        self.meetingConfig.setEnableAnnexToPrint(True)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        view = annex.restrictedTraverse('@@toggle_annex_to_print')

        # toggle value
        self.assertTrue(annex.adapted().mayChangeToPrint())
        self.assertEquals(annex.getToPrint(), False)
        self.assertEquals(item.annexIndex[0]['toPrint'], False)
        view.toggle()
        self.assertEquals(annex.getToPrint(), True)
        self.assertEquals(item.annexIndex[0]['toPrint'], True)

        # if a user tries to change toPrint but may not, it raises Unauthorized
        self.proposeItem(item)
        self.assertTrue(self.hasPermission(View, annex))
        self.assertFalse(annex.adapted().mayChangeToPrint())
        self.assertRaises(Unauthorized, view.toggle)
        # toPrint did not change
        self.assertEquals(annex.getToPrint(), True)
        self.assertEquals(item.annexIndex[0]['toPrint'], True)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingFile, prefix='test_pm_'))
    return suite
