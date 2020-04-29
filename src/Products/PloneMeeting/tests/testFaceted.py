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
from collective.contact.plonegroup.utils import get_organizations
from DateTime import DateTime
from eea.facetednavigation.interfaces import IFacetedLayout
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
        # check faceted_layout
        self.assertEqual(IFacetedLayout(creatorPMFolder).layout, 'faceted-table-items')
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
        self.assertEqual(
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
        self.assertEqual(len(terms), nbOfCategories)
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
        self.assertEqual(terms.by_token['development'].title,
                         cfg.categories.development.title)

        # if we add/remove a category, then the cache is cleaned too
        # add a category
        newCat = self.create('MeetingCategory',
                             id='new-category',
                             title='New category')
        # cache was cleaned, the new value is available
        terms = vocab(pmFolder)
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Events', u'New category', u'New title', u'Research topics'])

        # disable a category
        self.do(newCat, 'deactivate')
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Events', u'New title', u'Research topics', u'New category (Inactive)'])
        # term.value is the category id
        self.assertEqual(
            [term.value for term in vocab(pmFolder)],
            [u'events', u'development', u'research', u'new-category'])

        # remove a category
        self.portal.restrictedTraverse('@@delete_givenuid')(newCat.UID())
        # cache was cleaned
        self.assertEqual(
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
        self.assertEqual(len(terms), nbOfCategories)
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
        self.assertEqual(terms.by_token[classifier1_UID].title,
                         cfg.classifiers.classifier1.title)

        # if we add/remove a category, then the cache is cleaned too
        # add a classifier
        newClassifier = self.create('MeetingCategory',
                                    id='newclassifier',
                                    title='New classifier',
                                    isClassifier=True)
        # cache was cleaned, the new value is available
        terms = vocab(pmFolder)
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New classifier', u'New title'])

        # disable a category
        self.do(newClassifier, 'deactivate')
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New title', u'New classifier (Inactive)'])
        # term.value is the category id
        self.assertEqual(
            [term.value for term in vocab(pmFolder)],
            [cfg.classifiers.classifier2.UID(),
             cfg.classifiers.classifier3.UID(),
             cfg.classifiers.classifier1.UID(),
             cfg.classifiers.newclassifier.UID()])

        # remove a category
        self.portal.restrictedTraverse('@@delete_givenuid')(newClassifier.UID())
        # cache was cleaned
        self.assertEqual(
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
        self.assertEqual(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meetingUID])

        # if we add/remove/edit a meeting, then the cache is cleaned
        # add a meeting
        meeting2 = self.create('Meeting', date=DateTime('2015/06/06'))
        meeting2UID = meeting2.UID()
        # cache was cleaned
        self.assertEqual(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meeting2UID, meetingUID])
        # edit a meeting
        self.assertEqual(vocab(pmFolder).by_token[meetingUID].title, meeting.Title())
        meeting.setDate(DateTime('2015/06/06'))
        meeting._update_after_edit()
        # cache was cleaned
        self.assertEqual(vocab(pmFolder).by_token[meetingUID].title, meeting.Title())

        # remove a meeting
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        # cache was cleaned
        self.assertEqual(
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
        '''Test proposingGroup related cached vocabularies.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        vocab1 = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
        vocab2 = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary")
        vocab3 = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary")
        # once get, it is cached
        self.assertEqual(len(vocab1(pmFolder)), 3)
        # contains My organization
        self.assertEqual(len(vocab2(pmFolder)), 4)
        self.assertEqual(len(vocab3(pmFolder)), 3)

        # if we add/remove/edit an organozation, then the cache is cleaned
        # add an organization
        new_org = self.create('organization', title='NewOrg', acronym='N.O.')
        new_org_uid = new_org.UID()
        self._select_organization(new_org_uid)
        # cache was cleaned
        self.assertEqual(len(vocab1(pmFolder)), 4)
        self.assertEqual(len(vocab2(pmFolder)), 5)
        self.assertEqual(len(vocab3(pmFolder)), 4)

        # edit a group
        self.assertEqual(vocab1(pmFolder).by_token[new_org_uid].title, new_org.Title())
        self.assertEqual(vocab2(pmFolder).by_token[new_org_uid].title, new_org.acronym)
        self.assertEqual(vocab3(pmFolder).by_token[new_org_uid].title, new_org.Title())
        new_org.title = u'Modified title'
        new_org.acronym = u'Modified acronym'
        notify(ObjectModifiedEvent(new_org))
        # cache was cleaned
        self.assertEqual(vocab1(pmFolder).by_token[new_org_uid].title, new_org.Title())
        self.assertEqual(vocab2(pmFolder).by_token[new_org_uid].title, new_org.acronym)
        self.assertEqual(vocab3(pmFolder).by_token[new_org_uid].title, new_org.Title())

        # remove an organization (unselect it first)
        self._select_organization(new_org_uid, remove=True)
        self.portal.restrictedTraverse('@@delete_givenuid')(new_org_uid)
        # cache was cleaned
        self.assertEqual(len(vocab1(pmFolder)), 3)
        self.assertEqual(len(vocab2(pmFolder)), 4)
        self.assertEqual(len(vocab3(pmFolder)), 3)

        # activate "End users"
        self.assertEqual(
            [term.title for term in vocab1(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        self.assertEqual(
            [term.title for term in vocab2(pmFolder)],
            [u'None', u'Devel', u'Devil', u'EndUsers'])
        self.assertEqual(
            [term.title for term in vocab3(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        self._select_organization(self.endUsers_uid)
        self.assertEqual(
            [term.title for term in vocab1(pmFolder)],
            [u'Developers', u'End users', u'Vendors'])
        self.assertEqual(
            [term.title for term in vocab2(pmFolder)],
            [u'None', u'Devel', u'Devil', u'EndUsers'])
        self.assertEqual(
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
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        # now define values in MeetingConfig.groupsHiddenInDashboardFilter
        cfg.setGroupsHiddenInDashboardFilter((self.vendors_uid, ))
        cfg.at_post_edit_script()
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'End users (Inactive)'])

        # select "End users"
        self._select_organization(self.endUsers_uid)
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'End users'])

    def test_pm_GroupsInChargeVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.groupsinchargevocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('siteadmin')
        org1 = self.create('organization', id='org1', title='Org 1', acronym='Org1')
        org1uid = org1.UID()
        org2 = self.create('organization', id='org2', title='Org 2', acronym='Org2')
        org2uid = org2.UID()
        org3 = self.create('organization', id='org3', title='Org 3', acronym='Org3')
        org3uid = org3.UID()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.groupsinchargevocabulary")

        # for now, no group in charge
        meetingFolder = self.getMeetingFolder()
        self.assertEqual(len(vocab(meetingFolder)), 0)
        # define some group in charge, vocabulary is invalidated when an org is modified
        self.vendors.groups_in_charge = (org1uid,)
        notify(ObjectModifiedEvent(self.vendors))
        self.developers.groups_in_charge = (org2uid,)
        notify(ObjectModifiedEvent(self.developers))
        self.assertEqual([term.title for term in vocab(meetingFolder)], ['Org 1', 'Org 2'])

        # create an new org with a groupInCharge directly
        org4 = self.create('organization', id='org4', title='Org 4',
                           acronym='Org4', groups_in_charge=(org3uid,))
        org4_uid = org4.UID()
        self._select_organization(org4_uid)
        self.assertEqual([term.title for term in vocab(meetingFolder)], ['Org 1', 'Org 2', 'Org 3'])

        # change a group in charge
        self.vendors.groups_in_charge = (org4_uid,)
        notify(ObjectModifiedEvent(self.vendors))
        self.assertEqual([term.title for term in vocab(meetingFolder)], ['Org 2', 'Org 3', 'Org 4'])

        # unselect a group in charge
        self.vendors.groups_in_charge = ()
        notify(ObjectModifiedEvent(self.vendors))
        self.assertEqual([term.title for term in vocab(meetingFolder)], ['Org 2', 'Org 3'])

    def test_pm_CreatorsVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.creatorsvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.creatorsvocabulary")
        # once get, it is cached
        self.assertEqual(len(vocab(pmFolder)), 3)

        # if a new pmFolder is created, then the cache is cleaned
        # get pmFolder for user 'pmManager'
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # cache was cleaned
        self.assertEqual(len(vocab(pmFolder)), 4)

    def test_pm_CreatorsForFacetedVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.creatorsforfacetedvocabulary"
                   vocabulary, especially because it is cached.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(
            IVocabularyFactory,
            "Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary")
        # once get, it is cached
        self.assertEqual(len(vocab(pmFolder)), 3)

        # if a new pmFolder is created, then the cache is cleaned
        # get pmFolder for user 'pmManager'
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # cache was cleaned
        self.assertEqual(len(vocab(pmFolder)), 4)

        cfg.setUsersHiddenInDashboardFilter(('pmCreator1',))
        cfg.at_post_edit_script()
        # cache was cleaned and pmCreator is not in the list anymore
        self.assertEqual(len(vocab(pmFolder)), 3)

        cfg.setUsersHiddenInDashboardFilter(())
        cfg.at_post_edit_script()
        # cache was cleaned and pmCreator is back in the list
        self.assertEqual(len(vocab(pmFolder)), 4)

    def test_pm_AskedAdvicesVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.askedadvicesvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        customAdvisers = [{'row_id': 'unique_id_000',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '2',
                           'delay_label': ''},
                          {'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '5',
                           'delay_label': ''},
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10',
                           'delay_label': ''},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '20',
                           'delay_label': ''}]
        cfg.setCustomAdvisers(customAdvisers)
        pmFolder = self.getMeetingFolder()
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.askedadvicesvocabulary")
        # we have 4 delay-aware advisers and 2 adviser groups selectable as optional
        delayAdvisers = [adviser for adviser in cfg.getCustomAdvisers() if adviser['delay']]
        self.assertEqual(len(delayAdvisers), 4)
        self.assertEqual(len(get_organizations(not_empty_suffix='advisers')), 2)
        # once get, it is cached, it includes customAdvisers and MeetingConfig.selectableAdvisers
        self.assertEqual(len(vocab(pmFolder)), 6)

        # if we select a new organization, then the cache is cleaned
        # add an organization
        new_org = self.create('organization', title='New organization', acronym='N.G.')
        new_org_uid = new_org.UID()
        cfg.setSelectableAdvisers(cfg.getSelectableAdvisers() + (new_org_uid, ))
        # cache was cleaned
        self.assertEqual(len(vocab(pmFolder)), 7)
        # edit an organization
        new_org_term_id = 'real_org_uid__{0}'.format(new_org_uid)
        self.assertEqual(vocab(pmFolder).by_token[new_org_term_id].title, 'New organization (Inactive)')
        new_org.title = u'Modified title'
        notify(ObjectModifiedEvent(new_org))
        # cache was cleaned
        self.assertEqual(vocab(pmFolder).by_token[new_org_term_id].title, 'Modified title (Inactive)')
        # select the organization, cache is cleaned
        self._select_organization(new_org_uid)
        self.assertEqual(vocab(pmFolder).by_token[new_org_term_id].title, 'Modified title')
        # remove an organization
        # first need to unselect it
        self._select_organization(new_org_uid, remove=True)
        self.portal.restrictedTraverse('@@delete_givenuid')(new_org_uid)
        # cache was cleaned
        self.assertEqual(len(vocab(pmFolder)), 6)

        # if we add/remove/edit a customAdviser, then the cache is cleaned
        # add a customAdviser
        customAdvisers.append({'row_id': 'unique_id_999',
                               'org': self.vendors_uid,
                               'gives_auto_advice_on': '',
                               'for_item_created_from': '2012/01/01',
                               'delay': '11',
                               'delay_label': 'New delay'})
        cfg.setCustomAdvisers(customAdvisers)
        cfg.at_post_edit_script()
        self.assertEqual(len(vocab(pmFolder)), 7)
        self.assertTrue('delay_row_id__unique_id_999' in vocab(pmFolder).by_token)
        # delay is displayed in customAdviser title
        self.assertTrue('11 day(s)' in vocab(pmFolder).by_token['delay_row_id__unique_id_999'].title)
        # edit a customAdviser
        customAdvisers[-1]['delay'] = '12'
        cfg.setCustomAdvisers(customAdvisers)
        cfg.at_post_edit_script()
        self.assertTrue('12 day(s)' in vocab(pmFolder).by_token['delay_row_id__unique_id_999'].title)
        # remove a customAdviser
        customAdvisers = customAdvisers[:-1]
        cfg.setCustomAdvisers(customAdvisers)
        cfg.at_post_edit_script()
        self.assertEqual(len(vocab(pmFolder)), 6)

    def test_pm_AskedAdvicesVocabularyWithWrongContext(self):
        '''Test the "Products.PloneMeeting.vocabularies.askedadvicesvocabulary"
           vocabulary, when receiving wrong context, may occur during site install or
           DashboardCollection edit.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=DateTime('2020/04/01'))
        cfg = self.meetingConfig
        vocab = queryUtility(IVocabularyFactory, "Products.PloneMeeting.vocabularies.askedadvicesvocabulary")
        # working context
        pmFolder = self.getMeetingFolder()
        self.assertEqual(len(vocab(pmFolder)), 2)
        self.assertEqual(len(vocab(cfg)), 2)
        self.assertEqual(len(vocab(item)), 2)
        self.assertEqual(len(vocab(meeting)), 2)
        # do not fail on weird context
        self.assertEqual(len(vocab(self.portal)), 0)
        self.assertEqual(len(vocab(self.portal.contacts)), 0)
        self.assertEqual(len(vocab(self.app)), 0)
        self.assertEqual(len(vocab(None)), 0)

    def test_pm_AskedAdvicesVocabularyMCAware(self):
        '''Test the "Products.PloneMeeting.vocabularies.askedadvicesvocabulary"
           vocabulary, is MeetingConfig aware, especially because it is cached.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        customAdvisers = [{'row_id': 'unique_id_000',
                           'org': self.developers_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '2',
                           'delay_label': ''},
                          {'row_id': 'unique_id_123',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '5',
                           'delay_label': ''},
                          {'row_id': 'unique_id_456',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '10',
                           'delay_label': ''},
                          {'row_id': 'unique_id_789',
                           'org': self.vendors_uid,
                           'gives_auto_advice_on': '',
                           'for_item_created_from': '2012/01/01',
                           'delay': '20',
                           'delay_label': ''}]
        cfg.setCustomAdvisers(customAdvisers)
        customAdvisers = [{'row_id': 'unique_id_999',
                           'org': self.developers_uid,
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
        self.assertEqual(len(vocab(pmFolder)), 5)

        # change the MeetingConfig.usedAdvicesTypes
        cfg.setUsedAdviceTypes(('positive', ))
        cfg.at_post_edit_script()
        self.assertEqual(len(vocab(pmFolder)), 4)

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
        self.assertEqual(self.request.RESPONSE.status, 200)
        pmFolder()
        self.assertEqual(self.request.RESPONSE.status, 302)
        self.assertEqual(
            self.request.RESPONSE.getHeader('location'), pmFolder.absolute_url() + '/searches_items')

        # not redirected if on an item
        self.request.RESPONSE.status = 200
        item()
        self.assertEqual(self.request.RESPONSE.status, 200)

        # not redirected if on an meeting
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        meeting = self.create('Meeting', date=DateTime('2018/05/23'))
        meeting.restrictedTraverse('view')()
        self.assertEqual(self.request.RESPONSE.status, 200)

    def test_pm_DisabledCollectionsAreIgnored(self):
        """If a DashboardCollection is disabled in the MeetingConfig,
           it is not displayed in the vocabulary."""
        searches = self.meetingConfig.searches
        searchAllItems = searches.searches_items.searchallitems
        searchAllItems_path = searchAllItems.absolute_url_path()
        self.changeUser('pmCreator1')
        vocab = queryUtility(IVocabularyFactory,
                             "Products.PloneMeeting.vocabularies.conditionawarecollectionvocabulary")
        self.assertTrue(searchAllItems_path in vocab(searches))
        # disable it then test again
        self.changeUser('siteadmin')
        searchAllItems.enabled = False
        # invalidate vocabulary cache
        notify(ObjectModifiedEvent(searchAllItems))
        self.changeUser('pmCreator1')
        self.assertFalse(searchAllItems_path in vocab(searches))

    def test_pm_SearchableTextQueryOnSpecialCharacters(self):
        """Make sure it is possible to query on "décision" and "decision"."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title="SpecialDécision")
        self.assertEqual(len(self.catalog(SearchableText="SpecialDécision")), 1)
        self.assertEqual(len(self.catalog(SearchableText="specialdécision")), 1)
        self.assertEqual(len(self.catalog(SearchableText="SpecialDecision")), 1)
        self.assertEqual(len(self.catalog(SearchableText="specialdecision")), 1)
        item.setTitle("SpecialDecision")
        item.reindexObject()
        self.assertEqual(len(self.catalog(SearchableText="SpecialDécision")), 1)
        self.assertEqual(len(self.catalog(SearchableText="specialdécision")), 1)
        self.assertEqual(len(self.catalog(SearchableText="SpecialDecision")), 1)
        self.assertEqual(len(self.catalog(SearchableText="specialdecision")), 1)
        # not found
        self.assertEqual(len(self.catalog(SearchableText="specialdecisions")), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testFaceted, prefix='test_pm_'))
    return suite
