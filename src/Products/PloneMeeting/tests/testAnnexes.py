# -*- coding: utf-8 -*-
#
# File: testAnnexes.py
#
# Copyright (c) 2016 by Imio.be
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
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from Products.CMFCore.permissions import ModifyPortalContent
from Products.PloneMeeting.indexes import SearchableText
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testAnnexes(PloneMeetingTestCase):
    '''Tests various aspects of annexes management.'''

    def test_pm_MayChangeAnnexConfidentiality(self):
        '''May change if :
           - confidentiality enabled;
           - has the Modify portal content permission;
           - is a MeetingManager.
           '''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        self.assertFalse(annex.confidential)
        self.assertTrue(self.hasPermission(ModifyPortalContent, annex))
        annex_config = get_config_root(annex)
        annex_group = get_group(annex_config, annex)

        self.assertFalse(annex_group.confidentiality_activated)
        view = annex.restrictedTraverse('@@iconified-confidential')
        self.assertRaises(Unauthorized,
                          view.set_values, {'confidential': 'true'})
        # enable confidentiality
        annex_group.confidentiality_activated = True
        # now it fails because not a MeetingManager
        self.assertFalse(self.tool.isManager(annex))
        self.assertRaises(Unauthorized,
                          view.set_values, {'confidential': 'true'})

        # right, now as a MeetingManager, it works
        self.changeUser('pmManager')
        view.set_values({'confidential': 'true'})
        self.assertTrue(annex.confidential)

    def test_pm_GetCategorizedElementsWithConfidentiality(self):
        '''While getting categorized content, the confidentiality is taken into account.
           Also used in the annexes table view and the annexes tooltipster view.'''
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        cfg.setItemRestrictedPowerObserversStates((item_initial_state))
        annex_config = get_config_root(cfg)
        annex_group = get_group(annex_config, cfg)
        annex_group.confidentiality_activated = True

        # hide confidential annexes to restricted power observers
        cfg.setAnnexConfidentialFor(('restricted_power_observers', ))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annexes_table = item.restrictedTraverse('@@iconifiedcategory')
        categorized_child = item.restrictedTraverse('@@categorized-childs')

        annexNotConfidential1 = self.addAnnex(item, annexTitle='Annex 1 not confidential')
        annexNotConfidential2 = self.addAnnex(item, annexTitle='Annex 2 not confidential')
        annexConfidential1 = self.addAnnex(item, annexTitle='Annex 1 confidential')
        annexConfidential1.confidential = True
        notify(ObjectModifiedEvent(annexConfidential1))

        # current user see every annexes as not restricted power observer
        self.assertFalse(self.tool.isPowerObserverForCfg(cfg, isRestricted=True))
        self.assertEqual(set([elt['UID'] for elt in get_categorized_elements(item)]),
                         set((annexNotConfidential1.UID(),
                              annexNotConfidential2.UID(),
                              annexConfidential1.UID())))
        self.assertTrue('Annex 1 confidential' in annexes_table())
        self.assertTrue('Annex 1 confidential' in categorized_child())

        # not viewable by restricted power observers
        self.changeUser('restrictedpowerobserver1')
        self.assertTrue(self.tool.isPowerObserverForCfg(cfg, isRestricted=True))
        self.assertEqual(len(get_categorized_elements(item)), 2)
        self.assertFalse('Annex 1 confidential' in annexes_table())
        self.assertFalse('Annex 1 confidential' in categorized_child())

        # test also for power observers
        cfg.setAnnexConfidentialFor(('power_observers', ))
        # now the restricted power observer may access annexes
        self.assertEqual(len(get_categorized_elements(item)), 3)
        self.assertTrue('Annex 1 confidential' in annexes_table())
        self.assertTrue('Annex 1 confidential' in categorized_child())
        self.changeUser('powerobserver1')
        self.assertEqual(len(get_categorized_elements(item)), 2)
        self.assertFalse('Annex 1 confidential' in annexes_table())
        self.assertFalse('Annex 1 confidential' in categorized_child())
        # remove confidentiality on annex
        annexConfidential1.confidential = False
        notify(ObjectModifiedEvent(annexConfidential1))
        self.assertEqual(len(get_categorized_elements(item)), 3)
        self.assertTrue('Annex 1 confidential' in annexes_table())
        self.assertTrue('Annex 1 confidential' in categorized_child())

    def test_pm_AnnexesTitleFoundInItemSearchableText(self, ):
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
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p', 'specialannextitle'])
        # works also when clear and rebuild catalog
        self.portal.portal_catalog.clearFindAndRebuild()
        itemRID = catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          ['specialitemtitle', 'p', 'item', 'description', 'p',
                           'p', 'item', 'decision', 'p', 'specialannextitle'])
        # if we remove the annex, the item is not found anymore when querying
        # on removed annex's title
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertTrue(catalog(SearchableText=ITEM_TITLE))
        self.assertFalse(catalog(SearchableText=ANNEX_TITLE))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAnnexes, prefix='test_pm_'))
    return suite
