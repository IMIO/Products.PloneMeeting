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

from AccessControl import Unauthorized
from DateTime import DateTime
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.component import queryUtility
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory


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
        self.assertEqual(creatorPMFolder.getLayout(), 'facetednavigation_view')
        creatorPMFolderUrl = creatorPMFolder.absolute_url()
        # access the pmFolder
        creatorPMFolder()
        # user was redirected to his pmFolder '/searches_items'
        self.assertTrue(self.request.RESPONSE.getStatus() == 302)
        self.assertTrue(
            self.request.RESPONSE.getHeader('location') == creatorPMFolderUrl + '/searches_items')

        # as another simple user or MeetingManager, Unauthorized as other pm folder is private
        self.changeUser('pmReviewer1')
        self.assertRaises(Unauthorized, creatorPMFolder.restrictedTraverse, '@@facetednavigation_view')
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, creatorPMFolder.restrictedTraverse, '@@facetednavigation_view')

        # as a Plone admin, the user is redirected to it's own pmFolder
        self.changeUser('siteadmin')
        self.request.RESPONSE.setHeader('location', '')
        siteadminPMFolder = self.tool.getPloneMeetingFolder(cfgId)
        siteadminPMFolderUrl = siteadminPMFolder.absolute_url()
        creatorPMFolder()
        self.assertEquals(
            self.request.RESPONSE.getHeader('location'), siteadminPMFolderUrl + '/searches_items')

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
        cfg.setUseGroupsAsCategories(False)
        vocab = queryUtility(IVocabularyFactory,
                             "Products.PloneMeeting.vocabularies.categoriesvocabulary")
        # once get, it is cached
        terms = vocab(pmFolder)
        # every existing categories are shown, no matter it is disabled
        nbOfCategories = len(cfg.getCategories(onlySelectable=False, caching=False))
        self.assertEquals(len(terms), nbOfCategories)
        # here we make sure it is cached by changing a category title
        # manually without using the processForm way
        dev = cfg.categories.development
        dev.title = u'New title'
        terms = vocab(pmFolder)
        self.assertNotEquals(terms.by_token['development'].title,
                             cfg.categories.development.title)
        # right correctly edit the category, the vocabulary is invalidated
        dev.at_post_edit_script()
        terms = vocab(pmFolder)
        self.assertEquals(terms.by_token['development'].title,
                          cfg.categories.development.title)

        # if we add/remove a category, then the cache is cleaned too
        # add a category
        newCat = self.create('MeetingCategory',
                             id='new-category',
                             title='New category')
        # cache was cleaned, the new value is available
        terms = vocab(pmFolder)
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Events', u'New category', u'New title', u'Research topics'])

        # disable a category
        self.do(newCat, 'deactivate')
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Events', u'New title', u'Research topics', u'New category (Inactive)'])
        # term.value is the category id
        self.assertEquals(
            [term.value for term in vocab(pmFolder)],
            [u'events', u'development', u'research', u'new-category'])

        # remove a category
        self.portal.restrictedTraverse('@@delete_givenuid')(newCat.UID())
        # cache was cleaned
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Events', u'New title', u'Research topics'])

    def test_pm_ItemClassifiersVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.classifiersvocabulary"
           vocabulary, especially because it is cached. It relies on the categoriesvocabulary.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        cfg = self.meetingConfig
        cfg.setUseGroupsAsCategories(False)
        vocab = queryUtility(IVocabularyFactory,
                             "Products.PloneMeeting.vocabularies.classifiersvocabulary")
        # once get, it is cached
        terms = vocab(pmFolder)
        # every existing categories are shown, no matter it is disabled
        nbOfCategories = len(cfg.getCategories(classifiers=True, onlySelectable=False, caching=False))
        self.assertEquals(len(terms), nbOfCategories)
        # here we make sure it is cached by changing a category title
        # manually without using the processForm way
        classifier1 = cfg.classifiers.classifier1
        classifier1.title = u'New title'
        terms = vocab(pmFolder)
        classifier1_UID = classifier1.UID()
        self.assertNotEquals(terms.by_token[classifier1_UID].title,
                             cfg.categories.development.title)
        # right correctly edit the category, the vocabulary is invalidated
        classifier1.at_post_edit_script()
        terms = vocab(pmFolder)
        self.assertEquals(terms.by_token[classifier1_UID].title,
                          cfg.classifiers.classifier1.title)

        # if we add/remove a category, then the cache is cleaned too
        # add a classifier
        newClassifier = self.create('MeetingCategory',
                                    id='newclassifier',
                                    title='New classifier',
                                    isClassifier=True)
        # cache was cleaned, the new value is available
        terms = vocab(pmFolder)
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New classifier', u'New title'])

        # disable a category
        self.do(newClassifier, 'deactivate')
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New title', u'New classifier (Inactive)'])
        # term.value is the category id
        self.assertEquals(
            [term.value for term in vocab(pmFolder)],
            [cfg.classifiers.classifier2.UID(),
             cfg.classifiers.classifier3.UID(),
             cfg.classifiers.classifier1.UID(),
             cfg.classifiers.newclassifier.UID()])

        # remove a category
        self.portal.restrictedTraverse('@@delete_givenuid')(newClassifier.UID())
        # cache was cleaned
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New title'])

    def test_pm_ItemCategoriesVocabularyMCAware(self):
        '''Test that "Products.PloneMeeting.vocabularies.categoriesvocabulary"
           vocabulary, is MeetingConfig aware, especially because it is cached.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        cfg = self.meetingConfig
        cfg.setUseGroupsAsCategories(False)
        vocab = queryUtility(IVocabularyFactory,
                             "Products.PloneMeeting.vocabularies.categoriesvocabulary")
        terms_cfg1 = [term.token for term in vocab(pmFolder)]
        # now in cfg2
        cfg2 = self.meetingConfig2
        self.setMeetingConfig(cfg2.getId())
        cfg2.setUseGroupsAsCategories(False)
        pmFolder = self.getMeetingFolder()
        terms_cfg2 = [term.token for term in vocab(pmFolder)]
        self.assertNotEqual(terms_cfg1, terms_cfg2)

    def test_pm_MeetingDatesVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
           vocabulary, especially because it is cached.'''
        self._removeConfigObjectsFor(self.meetingConfig)
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # create a meeting
        meeting = self.create('Meeting', date=DateTime('2015/05/05'))
        meetingUID = meeting.UID()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.meetingdatesvocabulary")
        # once get, it is cached
        vocab(pmFolder)
        self.assertEquals(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meetingUID])

        # if we add/remove/edit a meeting, then the cache is cleaned
        # add a meeting
        meeting2 = self.create('Meeting', date=DateTime('2015/06/06'))
        meeting2UID = meeting2.UID()
        # cache was cleaned
        self.assertEquals(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meeting2UID, meetingUID])
        # edit a meeting
        self.assertEquals(vocab(pmFolder).by_token[meetingUID].title, meeting.Title())
        meeting.setDate(DateTime('2015/06/06'))
        meeting._update_after_edit()
        # cache was cleaned
        self.assertEquals(vocab(pmFolder).by_token[meetingUID].title, meeting.Title())

        # remove a meeting
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        # cache was cleaned
        self.assertEquals(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meeting2UID])

    def test_pm_MeetingDatesVocabularyMCAware(self):
        '''Test that "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
           vocabulary, is MeetingConfig aware, especially because it is cached.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory,
                             "Products.PloneMeeting.vocabularies.meetingdatesvocabulary")
        # create Meetings in cfg1
        self.create('Meeting', date=DateTime('2015/05/05'))
        self.create('Meeting', date=DateTime('2015/05/06'))
        # create Meetings in cfg2
        self.setMeetingConfig(cfg2.getId())
        self.create('Meeting', date=DateTime('2016/05/05'))
        self.create('Meeting', date=DateTime('2016/05/06'))

        self.setMeetingConfig(cfg.getId())
        pmFolder = self.getMeetingFolder()
        terms_cfg1 = [term.token for term in vocab(pmFolder)]
        self.setMeetingConfig(cfg2.getId())
        pmFolder = self.getMeetingFolder()
        terms_cfg2 = [term.token for term in vocab(pmFolder)]
        self.assertNotEqual(terms_cfg1, terms_cfg2)

    def test_pm_ProposingGroupsVocabularies(self):
        '''Test the "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary",
           "Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary" and
           "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary"
           vocabularies, especially because it is cached.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        vocab1 = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        vocab2 = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
        vocab3 = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary")
        # once get, it is cached
        self.assertEquals(len(vocab1(pmFolder)), 3)
        self.assertEquals(len(vocab2(pmFolder)), 3)
        self.assertEquals(len(vocab3(pmFolder)), 3)

        # if we add/remove/edit a group, then the cache is cleaned
        # add a group
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        newGroupId = newGroup.getId()
        # cache was cleaned
        self.assertEquals(len(vocab1(pmFolder)), 4)
        self.assertEquals(len(vocab2(pmFolder)), 4)
        self.assertEquals(len(vocab3(pmFolder)), 4)

        # edit a group
        self.assertEquals(vocab1(pmFolder).by_token[newGroupId].title, newGroup.Title())
        self.assertEquals(vocab2(pmFolder).by_token[newGroupId].title, newGroup.getAcronym())
        self.assertEquals(vocab3(pmFolder).by_token[newGroupId].title, newGroup.Title())
        newGroup.setTitle(u'Modified title')
        newGroup.setAcronym(u'Modified acronym')
        newGroup.at_post_edit_script()
        # cache was cleaned
        self.assertEquals(vocab1(pmFolder).by_token[newGroupId].title, newGroup.Title())
        self.assertEquals(vocab2(pmFolder).by_token[newGroupId].title, newGroup.getAcronym())
        self.assertEquals(vocab3(pmFolder).by_token[newGroupId].title, newGroup.Title())

        # remove a group
        self.portal.restrictedTraverse('@@delete_givenuid')(newGroup.UID())
        # cache was cleaned
        self.assertEquals(len(vocab1(pmFolder)), 3)
        self.assertEquals(len(vocab2(pmFolder)), 3)
        self.assertEquals(len(vocab3(pmFolder)), 3)

        # activate "End users"
        self.assertEquals(
            [term.title for term in vocab1(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        self.assertEquals(
            [term.title for term in vocab2(pmFolder)],
            [u'Devel', u'Devil', u'EndUsers'])
        self.assertEquals(
            [term.title for term in vocab3(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        self.do(self.tool.endUsers, 'activate')
        self.assertEquals(
            [term.title for term in vocab1(pmFolder)],
            [u'Developers', u'End users', u'Vendors'])
        self.assertEquals(
            [term.title for term in vocab2(pmFolder)],
            [u'Devel', u'Devil', u'EndUsers'])
        self.assertEquals(
            [term.title for term in vocab3(pmFolder)],
            [u'Developers', u'End users', u'Vendors'])

    def test_pm_ProposingGroupsForFacetedVocabulary(self):
        '''Test that vocabulary "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary"
           relies on MeetingConfig.groupsHiddenInDashboardFilter.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary")
        # by default when MeetingConfig.groupsHiddenInDashboardFilter is empty, every groups are returned
        self.assertEqual(cfg.getGroupsHiddenInDashboardFilter(), ())
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        # now define values in MeetingConfig.groupsHiddenInDashboardFilter
        cfg.setGroupsHiddenInDashboardFilter(('vendors', ))
        cfg.at_post_edit_script()
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'End users (Inactive)'])

        # activate "End users"
        self.do(self.tool.endUsers, 'activate')
        self.assertEquals(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'End users'])

    def test_pm_GroupsInChargeVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.groupsinchargevocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('siteadmin')
        vendors = self.tool.vendors
        developers = self.tool.developers
        self.create('MeetingGroup', id='group1', title='Group 1', acronym='G1')
        self.create('MeetingGroup', id='group2', title='Group 2', acronym='G2')
        self.create('MeetingGroup', id='group3', title='Group 3', acronym='G3')
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.groupsinchargevocabulary")

        # for now, no group in charge
        self.assertEqual(len(vocab(self.portal)), 0)
        # define some group in charge, vocabulary is invalidated when a group is modified
        vendors.setGroupsInCharge(('group1',))
        vendors.at_post_edit_script()
        developers.setGroupsInCharge(('group2',))
        developers.at_post_edit_script()
        self.assertEqual([term.title for term in vocab(self.portal)], ['Group 1', 'Group 2'])

        # create an new group with a groupInCharge directly
        self.create('MeetingGroup', id='group4', title='Group 4',
                    acronym='G4', groupsInCharge=('group3',))
        self.assertEqual([term.title for term in vocab(self.portal)], ['Group 1', 'Group 2', 'Group 3'])

        # change a group in charge
        vendors.setGroupsInCharge(('group4',))
        vendors.at_post_edit_script()
        self.assertEqual([term.title for term in vocab(self.portal)], ['Group 2', 'Group 3', 'Group 4'])

        # unselect a group in charge
        vendors.setGroupsInCharge(())
        vendors.at_post_edit_script()
        self.assertEqual([term.title for term in vocab(self.portal)], ['Group 2', 'Group 3'])

    def test_pm_CreatorsVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.creatorsvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.creatorsvocabulary")
        # once get, it is cached
        self.assertEquals(len(vocab(pmFolder)), 3)

        # if a new pmFolder is created, then the cache is cleaned
        # get pmFolder for user 'pmManager'
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # cache was cleaned
        self.assertEquals(len(vocab(pmFolder)), 4)

    def test_pm_AskedAdvicesVocabularies(self):
        '''Test the "Products.PloneMeeting.vocabularies.askedadvicesvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        customAdvisers = [{'row_id': 'unique_id_000',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '2',
                           'delay_label': ''},
                          {'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '5',
                           'delay_label': ''},
                          {'row_id': 'unique_id_456',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10',
                           'delay_label': ''},
                          {'row_id': 'unique_id_789',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '20',
                           'delay_label': ''}]
        cfg.setCustomAdvisers(customAdvisers)
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.askedadvicesvocabulary")
        # we have 4 delay-aware advisers and 2 adviser groups selectable as optional
        delayAdvisers = [adviser for adviser in cfg.getCustomAdvisers() if adviser['delay']]
        self.assertEquals(len(delayAdvisers), 4)
        self.assertEquals(len(self.tool.getMeetingGroups(notEmptySuffix='advisers')), 2)
        # once get, it is cached
        self.assertEquals(len(vocab(pmFolder)), 6)

        # if we add/remove/edit a group, then the cache is cleaned
        # add a group
        newGroup = self.create('MeetingGroup', title='NewGroup', acronym='N.G.')
        newGroupId = newGroup.getId()
        # cache was cleaned
        self.assertEquals(len(vocab(pmFolder)), 7)
        # edit a group
        self.assertEquals(vocab(pmFolder).by_token['real_group_id__{0}'.format(newGroupId)].title,
                          newGroup.Title())
        newGroup.setTitle(u'Modified title')
        newGroup.at_post_edit_script()
        # cache was cleaned
        self.assertEquals(vocab(pmFolder).by_token['real_group_id__{0}'.format(newGroupId)].title,
                          newGroup.Title())
        # remove a group
        self.portal.restrictedTraverse('@@delete_givenuid')(newGroup.UID())
        # cache was cleaned
        self.assertEquals(len(vocab(pmFolder)), 6)

        # if we add/remove/edit a customAdviser, then the cache is cleaned
        # add a customAdviser
        customAdvisers.append({'row_id': 'unique_id_999',
                               'group': 'vendors',
                               'gives_auto_advice_on': '',
                               'for_item_created_from': '2012/01/01',
                               'delay': '11',
                               'delay_label': 'New delay'})
        cfg.setCustomAdvisers(customAdvisers)
        cfg.at_post_edit_script()
        self.assertEquals(len(vocab(pmFolder)), 7)
        self.assertTrue('delay_real_group_id__unique_id_999' in vocab(pmFolder).by_token)
        # delay is displayed in customAdviser title
        self.assertTrue('11 day(s)' in vocab(pmFolder).by_token['delay_real_group_id__unique_id_999'].title)
        # edit a customAdviser
        customAdvisers[-1]['delay'] = '12'
        cfg.setCustomAdvisers(customAdvisers)
        cfg.at_post_edit_script()
        self.assertTrue('12 day(s)' in vocab(pmFolder).by_token['delay_real_group_id__unique_id_999'].title)
        # remove a customAdviser
        customAdvisers = customAdvisers[:-1]
        cfg.setCustomAdvisers(customAdvisers)
        cfg.at_post_edit_script()
        self.assertEquals(len(vocab(pmFolder)), 6)

    def test_pm_AskedAdvicesVocabulariesMCAware(self):
        '''Test the "Products.PloneMeeting.vocabularies.askedadvicesvocabulary"
           vocabulary, is MeetingConfig aware, especially because it is cached.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        customAdvisers = [{'row_id': 'unique_id_000',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '2',
                           'delay_label': ''},
                          {'row_id': 'unique_id_123',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '5',
                           'delay_label': ''},
                          {'row_id': 'unique_id_456',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10',
                           'delay_label': ''},
                          {'row_id': 'unique_id_789',
                           'group': 'vendors',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '20',
                           'delay_label': ''}]
        cfg.setCustomAdvisers(customAdvisers)
        customAdvisers = [{'row_id': 'unique_id_999',
                           'group': 'developers',
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '20',
                           'delay_label': ''}]
        cfg2.setCustomAdvisers(customAdvisers)
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.askedadvicesvocabulary")
        terms_cfg1 = [term.token for term in vocab(pmFolder)]
        self.setMeetingConfig(cfg2.getId())
        pmFolder = self.getMeetingFolder()
        terms_cfg2 = [term.token for term in vocab(pmFolder)]
        self.assertNotEqual(terms_cfg1, terms_cfg2)

    def test_pm_AdviceTypesVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.advicetypesvocabulary"
           vocabulary, especially because it is cached.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        cfg.setUsedAdviceTypes(('positive', 'negative'))
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.advicetypesvocabulary")
        # once get, it is cached
        self.assertEquals(len(vocab(pmFolder)), 5)

        # change the MeetingConfig.usedAdvicesTypes
        cfg.setUsedAdviceTypes(('positive', ))
        cfg.at_post_edit_script()
        self.assertEquals(len(vocab(pmFolder)), 4)

    def test_pm_AdviceTypesVocabularyMCAware(self):
        '''Test the "Products.PloneMeeting.vocabularies.advicetypesvocabulary"
           vocabulary, is MeetingConfig aware, especially because it is cached.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('siteadmin')
        cfg.setUsedAdviceTypes(('positive', 'negative'))
        cfg2.setUsedAdviceTypes(('positive', ))
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.advicetypesvocabulary")

        pmFolder = self.getMeetingFolder()
        terms_cfg1 = [term.token for term in vocab(pmFolder)]
        self.setMeetingConfig(cfg2.getId())
        pmFolder = self.getMeetingFolder()
        terms_cfg2 = [term.token for term in vocab(pmFolder)]
        self.assertNotEqual(terms_cfg1, terms_cfg2)

    def test_pm_RedirectedToDefaultSearchPMFolderOnlyIfNecessary(self):
        """This test portlet_plonemeeting.widget_render where we manipulate the redirection,
           returned by the collection widget to the default collection as collections are in the configuration
           and we want the user to be redirected in his meeting folder."""
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        item = self.create('MeetingItem')

        # call to pmFolder redirects to searches_items
        self.assertEquals(self.request.RESPONSE.status, 200)
        pmFolder()
        self.assertEquals(self.request.RESPONSE.status, 302)
        self.assertEquals(
            self.request.RESPONSE.getHeader('location'), pmFolder.absolute_url() + '/searches_items')

        # not redirected if on an item
        self.request.RESPONSE.status = 200
        item()
        self.assertEquals(self.request.RESPONSE.status, 200)

        # not redirected if on an meeting
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        meeting = self.create('Meeting', date=DateTime('2018/05/23'))
        meeting.restrictedTraverse('view')()
        self.assertEquals(self.request.RESPONSE.status, 200)

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
        searchAllItems.enabled = False
        # invalidate vocabulary cache
        notify(ObjectModifiedEvent(searchAllItems))
        self.changeUser('pmCreator1')
        self.assertFalse(searchAllItems in vocab(searches))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testFaceted, prefix='test_pm_'))
    return suite
