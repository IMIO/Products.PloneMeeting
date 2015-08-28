# -*- coding: utf-8 -*-
#
# File: testFaceted.py
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

from DateTime import DateTime
from AccessControl import Unauthorized
from zope.component import queryUtility
from zope.schema.interfaces import IVocabularyFactory
from plone.memoize.instance import Memojito
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase

memPropName = Memojito.propname


class testFaceted(PloneMeetingTestCase):
    '''Tests various aspects of faceted navigation.'''

    def test_pm_RedirectedToOwnPMFolderIfOnAnotherUserPMFolder(self):
        '''In case a user is sent to another user pmFolder, he is redirected
           to his own pmFolder even for Plone Managers, except if it is the Zope admin.'''
        cfgId = self.meetingConfig.getId()
        # get the pmCreator1 pmFolder
        self.changeUser('pmCreator1')
        self.request.RESPONSE.setHeader('location', '')
        creatorPMFolder = self.tool.getPloneMeetingFolder(cfgId)
        creatorPMFolderUrl = creatorPMFolder.absolute_url()
        # access the pmFolder
        creatorPMFolder.restrictedTraverse('@@facetednavigation_view')()
        # user was redirected to his pmFolder '/searches_items'
        self.assertTrue(self.request.RESPONSE.getStatus() == 302)
        self.assertTrue(self.request.RESPONSE.getHeader('location') == creatorPMFolderUrl + '/searches_items')

        # as another simple user, it raises Unauthorized
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, creatorPMFolder.restrictedTraverse, '@@facetednavigation_view')
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, creatorPMFolder.restrictedTraverse, '@@facetednavigation_view')

        # as a Plone admin, the user is redirected to it's own pmFolder
        self.changeUser('siteadmin')
        self.request.RESPONSE.setHeader('location', '')
        siteadminPMFolder = self.tool.getPloneMeetingFolder(cfgId)
        siteadminPMFolderUrl = siteadminPMFolder.absolute_url()
        creatorPMFolder.restrictedTraverse('@@facetednavigation_view')()
        self.assertEquals(self.request.RESPONSE.getHeader('location'),
                          siteadminPMFolderUrl + '/searches_items')

        # if a user is using folder_contents, then he is not redirected
        self.request.RESPONSE.setHeader('location', '')
        self.request.RESPONSE.setStatus(200)
        creatorPMFolder.restrictedTraverse('folder_contents')()
        # user is not redirected
        self.assertFalse(self.request.RESPONSE.getHeader('location'))
        self.assertTrue(self.request.RESPONSE.getStatus() == 200)

    def test_pm_ItemCategoriesVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.categoriesvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        cfg = self.meetingConfig
        cfg.useGroupsAsCategories = False
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.categoriesvocabulary")
        self.assertFalse(getattr(vocab, memPropName, {}))
        # once get, it is cached
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # if we add/remove/edit a category, then the cache is cleaned
        # add a category
        newCatId = cfg.categories.invokeFactory('MeetingCategory', id='new-category', title='New category')
        newCat = getattr(cfg.categories, newCatId)
        newCat.at_post_create_script()
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # edit a category
        newCat.at_post_edit_script()
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # remove a category
        self.portal.restrictedTraverse('@@delete_givenuid')(newCat.UID())
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))

    def test_pm_MeetingDatesVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
           vocabulary, especially because it is cached.'''
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # create a meeting
        self.create('Meeting', date=DateTime('2015/05/05'))
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.meetingdatesvocabulary")
        self.assertFalse(getattr(vocab, memPropName, {}))
        # once get, it is cached
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # if we add/remove/edit a meeting, then the cache is cleaned
        # add a meeting
        meeting = self.create('Meeting', date=DateTime('2015/06/06'))
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # edit a meeting
        meeting.at_post_edit_script()
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # remove a meeting
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))

    def test_pm_ProposingGroupsVocabularies(self):
        '''Test the "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary"
           and "Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary"
           vocabularies, especially because it is cached.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        vocab1 = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        vocab2 = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
        self.assertFalse(getattr(vocab1, memPropName, {}))
        self.assertFalse(getattr(vocab2, memPropName, {}))
        # once get, it is cached
        vocab1(pmFolder)
        vocab2(pmFolder)
        self.assertTrue(getattr(vocab1, memPropName))
        self.assertTrue(getattr(vocab2, memPropName))

        # if we add/remove/edit a group, then the cache is cleaned
        # add a group
        newGroupId = self.tool.invokeFactory('MeetingGroup', id='new-group', title='New group')
        newGroup = getattr(self.tool, newGroupId)
        newGroup.at_post_create_script()
        # cache was cleaned
        self.assertFalse(getattr(vocab1, memPropName, {}))
        self.assertFalse(getattr(vocab2, memPropName, {}))
        vocab1(pmFolder)
        vocab2(pmFolder)
        self.assertTrue(getattr(vocab1, memPropName))
        self.assertTrue(getattr(vocab2, memPropName))

        # edit a group
        newGroup.at_post_edit_script()
        # cache was cleaned
        self.assertFalse(getattr(vocab1, memPropName, {}))
        self.assertFalse(getattr(vocab2, memPropName, {}))
        vocab1(pmFolder)
        vocab2(pmFolder)
        self.assertTrue(getattr(vocab1, memPropName))
        self.assertTrue(getattr(vocab2, memPropName))

        # remove a group
        self.portal.restrictedTraverse('@@delete_givenuid')(newGroup.UID())
        # cache was cleaned
        self.assertFalse(getattr(vocab1, memPropName, {}))
        self.assertFalse(getattr(vocab2, memPropName, {}))

    def test_pm_CreatorsVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.creatorsvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.creatorsvocabulary")
        self.assertFalse(getattr(vocab, memPropName, {}))
        # once get, it is cached
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

        # if a new pmFolder is created, then the cache is cleaned
        # get pmFolder for user 'pmManager'
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # cache was cleaned
        self.assertFalse(getattr(vocab, memPropName, {}))
        vocab(pmFolder)
        self.assertTrue(getattr(vocab, memPropName))

    def test_pm_RedirectedToDefaultSearchPMFolderOnlyIfNecessary(self):
        """This test portlet_plonemeeting.widget_render where we manipulate the redirection,
           returned by the collection widget to the default collection as collections are in the configuration
           and we want the user to be redirected in his meeting folder."""
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        item = self.create('MeetingItem')
        self.assertEquals(self.request.RESPONSE.status, 200)
        item()

        # not redirected
        self.assertEquals(self.request.RESPONSE.status, 200)
        # if we were redirected to the item view, it is still the case
        self.request.RESPONSE.redirect(item.absolute_url())
        self.assertEquals(self.request.RESPONSE.status, 302)
        self.assertEquals(self.request.RESPONSE.getHeader('location'),
                          item.absolute_url())

        # when user is redirected to the default collection in the configuration
        # in place, user is redirected to his pmFolder searches_items folder
        self.request.RESPONSE.redirect(self.meetingConfig.searches.searches_items.absolute_url())
        item()
        self.assertEquals(self.request.RESPONSE.status, 302)
        self.assertEquals(self.request.RESPONSE.getHeader('location'),
                          pmFolder.absolute_url() + '/searches_items')

    def test_pm_DisabledCollectionsAreIgnored(self):
        """If a DashboardCollection is disabled in the MeetingConfig,
           it is not displayed in the vocabulary."""
        searches = self.meetingConfig.searches
        searchAllItems = searches.searches_items.searchallitems
        self.changeUser('pmCreator1')
        vocab = queryUtility(IVocabularyFactory,
                             "Products.PloneMeeting.vocabularies.conditionawarecollectionvocabulary")
        self.assertTrue(searchAllItems in vocab(searches))
        # disable it then test again
        self.changeUser('siteadmin')
        self.do(searchAllItems, 'deactivate')
        self.changeUser('pmCreator1')
        self.assertFalse(searchAllItems in vocab(searches))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testFaceted, prefix='test_pm_'))
    return suite
