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
        self.assertTrue(self.request.RESPONSE.getHeader('location') == siteadminPMFolderUrl + '/searches_items')

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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testFaceted, prefix='test_pm_'))
    return suite
