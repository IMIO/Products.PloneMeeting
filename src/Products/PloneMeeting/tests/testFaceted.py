# -*- coding: utf-8 -*-
#
# File: testFaceted.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_organizations
from datetime import datetime
from eea.facetednavigation.interfaces import IFacetedLayout
from imio.helpers.content import get_vocab
from imio.helpers.content import get_vocab_values
from Products.Archetypes.event import ObjectEditedEvent
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


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
        # make sure the different searches_... views are working
        # check some searches and faceted filters
        searches_items = creatorPMFolder.searches_items()
        self.assertTrue('Items to validate' in searches_items)
        self.assertTrue('section-preferred-meeting' in searches_items)
        self.assertTrue('section-to-send-to' in searches_items)
        searches_meetings = creatorPMFolder.searches_meetings()
        self.assertTrue('Items to validate' in searches_meetings)
        self.assertTrue("section-review-state" in searches_meetings)
        self.assertTrue("section-date" in searches_meetings)
        searches_decisions = creatorPMFolder.searches_decisions()
        self.assertTrue('Items to validate' in searches_decisions)
        self.assertTrue("section-review-state" in searches_decisions)
        self.assertTrue("section-date" in searches_decisions)

    def test_pm_RedirectToNextMeeting(self):
        """When selected, some user profiles will be redirected to the next meeting if it exists
           instead a dashboard displaying items (my items, ...)."""
        cfg = self.meetingConfig
        self.assertEqual(cfg.getRedirectToNextMeeting(), ())
        cfgId = cfg.getId()
        # get the pmCreator1 pmFolder
        self.changeUser('pmCreator1')
        self.request.RESPONSE.setHeader('location', '')
        creatorPMFolder = self.tool.getPloneMeetingFolder(cfgId)
        # access the pmFolder
        creatorPMFolder.searches_items()
        self.assertEqual(self.request.RESPONSE.getHeader('location'), '')
        # redirect app user to next meeting
        self.assertEqual(cfg.listRedirectToNextMeeting().keys(),
                         ['app_users',
                          'meeting_managers',
                          'powerobserver__powerobservers',
                          'powerobserver__restrictedpowerobservers'])
        cfg.setRedirectToNextMeeting(('app_users', ))
        # still searches_items as no meeting exist
        creatorPMFolder.searches_items()
        self.assertEqual(self.request.RESPONSE.getStatus(), 200)
        self.assertEqual(self.request.RESPONSE.getHeader('location'), '')
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_url = meeting.absolute_url()
        # freeze meeting so we are sure it is viewable (depends on WF)
        self.freezeMeeting(meeting)
        self.changeUser('pmCreator1')
        creatorPMFolder.searches_items()
        self.assertEqual(self.request.RESPONSE.getStatus(), 302)
        self.assertEqual(self.request.RESPONSE.getHeader('location'), meeting_url)

    def test_pm_RedirectToNextMeetingWhenMeetingNotViewable(self):
        """If meeting not viewable, user not redirected."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=('closed', ))
        self.assertEqual(cfg.listRedirectToNextMeeting().keys(),
                         ['app_users',
                          'meeting_managers',
                          'powerobserver__powerobservers',
                          'powerobserver__restrictedpowerobservers'])
        cfg.setRedirectToNextMeeting(('powerobserver__powerobservers', ))
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting_url = meeting.absolute_url()
        # not viewable for now
        self.changeUser('powerobserver1')
        pmFolder = self.tool.getPloneMeetingFolder(cfgId)
        # access the pmFolder
        pmFolder.searches_items()
        self.assertEqual(self.request.RESPONSE.getStatus(), 200)
        self.assertEqual(self.request.RESPONSE.getHeader('location'), '')
        # make meeting viewable
        self.closeMeeting(meeting, as_manager=True)
        # when no_redirect in request, user is not redirected
        self.assertEqual(self.request.get('no_redirect'), '1')
        pmFolder.searches_items()
        self.assertEqual(self.request.RESPONSE.getStatus(), 200)
        self.assertEqual(self.request.RESPONSE.getHeader('location'), '')
        # redirected
        self.request.set('no_redirect', 0)
        pmFolder.searches_items()
        self.assertEqual(self.request.RESPONSE.getStatus(), 302)
        self.assertEqual(self.request.RESPONSE.getHeader('location'), meeting_url)

    def test_pm_ItemCategoriesVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.categoriesvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        cfg = self.meetingConfig
        self._enableField('category')
        vocab = get_vocab(cfg,
                          "Products.PloneMeeting.vocabularies.categoriesvocabulary",
                          only_factory=True)
        # once get, it is cached
        terms = vocab(pmFolder)
        # every existing categories are shown, no matter it is disabled
        nbOfCategories = len(cfg.getCategories(onlySelectable=False))
        self.assertEqual(len(terms), nbOfCategories)
        # here we make sure it is cached by changing a category title
        # manually without using the processForm way
        dev = cfg.categories.development
        dev.title = u'New title'
        terms = vocab(pmFolder)
        self.assertNotEquals(terms.by_token['development'].title,
                             cfg.categories.development.title)
        # right correctly edit the category, the vocabulary is invalidated
        notify(ObjectModifiedEvent(dev))
        terms = vocab(pmFolder)
        self.assertEqual(terms.by_token['development'].title,
                         cfg.categories.development.title)

        # if we add/remove a category, then the cache is cleaned too
        # add a category
        newCat = self.create('meetingcategory',
                             id='new-category',
                             title='New category')
        # cache was cleaned, the new value is available
        terms = vocab(pmFolder)
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Events', u'New category', u'New title', u'Research topics'])

        # disable a category
        self._disableObj(newCat)
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
        self._enableField('category')
        vocab = get_vocab(cfg,
                          "Products.PloneMeeting.vocabularies.classifiersvocabulary",
                          only_factory=True)
        # once get, it is cached
        terms = vocab(pmFolder)
        # every existing categories are shown, no matter it is disabled
        nbOfCategories = len(cfg.getCategories(catType='classifiers', onlySelectable=False))
        self.assertEqual(len(terms), nbOfCategories)
        # here we make sure it is cached by changing a category title
        # manually without using the processForm way
        classifier1 = cfg.classifiers.classifier1
        classifier1.title = u'New title'
        terms = vocab(pmFolder)
        classifier1_id = classifier1.getId()
        self.assertNotEquals(terms.by_token[classifier1_id].title,
                             cfg.categories.development.title)
        # right correctly edit the category, the vocabulary is invalidated
        notify(ObjectModifiedEvent(classifier1))
        terms = vocab(pmFolder)
        self.assertEqual(terms.by_token[classifier1_id].title,
                         cfg.classifiers.classifier1.title)

        # if we add/remove a category, then the cache is cleaned too
        # add a classifier
        newClassifier = self.create('meetingcategory',
                                    id='newclassifier',
                                    title='New classifier',
                                    is_classifier=True)
        # cache was cleaned, the new value is available
        terms = vocab(pmFolder)
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New classifier', u'New title'])

        # disable a classifier
        self._disableObj(newClassifier)
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Classifier 2', u'Classifier 3', u'New title', u'New classifier (Inactive)'])
        # term.value is the classifier id
        self.assertEqual(
            [term.value for term in vocab(pmFolder)],
            ['classifier2', 'classifier3', 'classifier1', 'newclassifier'])

        # remove a classifier
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
        self._enableField('category')
        vocab = get_vocab(cfg,
                          "Products.PloneMeeting.vocabularies.categoriesvocabulary",
                          only_factory=True)
        terms_cfg1 = [term.token for term in vocab(pmFolder)]
        # now in cfg2
        cfg2 = self.meetingConfig2
        self.setMeetingConfig(cfg2.getId())
        self._enableField('category', cfg=cfg2)
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
        meeting = self.create('Meeting', date=datetime(2015, 5, 5))
        meetingUID = meeting.UID()
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.meetingdatesvocabulary",
                          only_factory=True)
        # once get, it is cached
        vocab(pmFolder)
        self.assertEqual(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meetingUID])

        # if we add/remove/edit a meeting, then the cache is cleaned
        # add a meeting
        meeting2 = self.create('Meeting', date=datetime(2015, 6, 6))
        meeting2UID = meeting2.UID()
        # cache was cleaned
        self.assertEqual(
            [term.token for term in vocab(pmFolder)._terms],
            [ITEM_NO_PREFERRED_MEETING_VALUE, meeting2UID, meetingUID])
        # edit a meeting
        self.assertEqual(vocab(pmFolder).by_token[meetingUID].title, u'05/05/2015')
        meeting.date = datetime(2015, 7, 7)
        meeting._update_after_edit()
        # cache was cleaned
        self.assertEqual(vocab(pmFolder).by_token[meetingUID].title, u'07/07/2015')

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
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.meetingdatesvocabulary",
                          only_factory=True)
        # create Meetings in cfg1
        self.create('Meeting')
        self.create('Meeting', date=datetime(2015, 5, 6))
        # create Meetings in cfg2
        self.setMeetingConfig(cfg2.getId())
        self.create('Meeting')
        self.create('Meeting', date=datetime(2016, 5, 6))

        self.setMeetingConfig(cfg.getId())
        pmFolder = self.getMeetingFolder()
        terms_cfg1 = [term.token for term in vocab(pmFolder)]
        self.setMeetingConfig(cfg2.getId())
        pmFolder = self.getMeetingFolder()
        terms_cfg2 = [term.token for term in vocab(pmFolder)]
        self.assertNotEqual(terms_cfg1, terms_cfg2)

    def _orgs_to_exclude_from_filter(self):
        return ()

    def test_pm_ProposingGroupsVocabularies(self):
        '''Test proposingGroup related cached vocabularies.'''
        self.changeUser('siteadmin')
        # check test profile values
        self.assertGreater(len(self.proposing_groups), 2)
        # greater than proposing_groups + "My organization"
        self.assertGreater(len(self.all_org), len(self.proposing_groups) + 1)
        # not all proposing groups are activated
        self.assertLess(len(self.active_proposing_groups), len(self.proposing_groups))

        pmFolder = self.getMeetingFolder()
        vocab1 = get_vocab(
            pmFolder,
            "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary",
            only_factory=True)
        vocab2 = get_vocab(
            pmFolder,
            "Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary",
            only_factory=True)
        vocab3 = get_vocab(
            pmFolder,
            "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary",
            only_factory=True)
        vocab4 = get_vocab(
            pmFolder,
            "Products.PloneMeeting.vocabularies.associatedgroupsvocabulary",
            only_factory=True)
        # once get, it is cached
        self.assertEqual(len(vocab1(pmFolder)), len(self.proposing_groups))
        # contains My organization and external organizations
        self.assertEqual(len(vocab2(pmFolder)), len(self.all_org))
        self.assertEqual(len(vocab3(pmFolder)), len(self.proposing_groups))
        # when nothing in config, just displays the orgs selected in plonegroup
        self.assertEqual(len(vocab4(pmFolder)), len(self.active_proposing_groups))

        # if we add/remove/edit an organozation, then the cache is cleaned
        # add an organization
        new_org = self.create('organization', title='NewOrg', acronym='N.O.')
        new_org_uid = new_org.UID()
        self._select_organization(new_org_uid)
        # cache was cleaned
        self.assertEqual(len(vocab1(pmFolder)), len(self.proposing_groups) + 1)
        self.assertEqual(len(vocab2(pmFolder)), len(self.all_org) + 1)
        self.assertEqual(len(vocab3(pmFolder)), len(self.proposing_groups) + 1)
        self.assertEqual(len(vocab4(pmFolder)), len(self.active_proposing_groups) + 1)

        # edit a group
        self.assertEqual(vocab1(pmFolder).by_token[new_org_uid].title, new_org.Title())
        self.assertEqual(vocab2(pmFolder).by_token[new_org_uid].title, new_org.acronym)
        self.assertEqual(vocab3(pmFolder).by_token[new_org_uid].title, new_org.Title())
        self.assertEqual(vocab4(pmFolder).by_token[new_org_uid].title, new_org.Title())
        new_org.title = u'Modified title'
        new_org.acronym = u'Modified acronym'
        notify(ObjectModifiedEvent(new_org))
        # cache was cleaned
        self.assertEqual(vocab1(pmFolder).by_token[new_org_uid].title, new_org.Title())
        self.assertEqual(vocab2(pmFolder).by_token[new_org_uid].title, new_org.acronym)
        self.assertEqual(vocab3(pmFolder).by_token[new_org_uid].title, new_org.Title())
        self.assertEqual(vocab4(pmFolder).by_token[new_org_uid].title, new_org.Title())

        # remove an organization (unselect it first)
        self._select_organization(new_org_uid, remove=True)
        self.portal.restrictedTraverse('@@delete_givenuid')(new_org_uid)
        # cache was cleaned
        # once get, it is cached
        self.assertEqual(len(vocab1(pmFolder)), len(self.proposing_groups))
        self.assertEqual(len(vocab2(pmFolder)), len(self.all_org))
        self.assertEqual(len(vocab3(pmFolder)), len(self.proposing_groups))
        self.assertEqual(len(vocab4(pmFolder)), len(self.active_proposing_groups))
        # activate "End users"
        proposing_groups_terms_titles = sorted([group.title + (not group.active and u' (Inactive)' or u'')
                                                for group in self.proposing_groups])
        self.assertListEqual(
            sorted([term.title for term in vocab1(pmFolder)]), proposing_groups_terms_titles)
        self.assertListEqual(sorted([term.title for term in vocab2(pmFolder)]),
                             sorted([unicode(org.acronym) for org in self.all_org]))
        self.assertListEqual(
            sorted([term.title for term in vocab3(pmFolder)]), proposing_groups_terms_titles)

        associeted_groups = sorted([group.title for group in self.proposing_groups if group.active])
        self.assertListEqual([term.title for term in vocab4(pmFolder)], associeted_groups)
        self._select_organization(self.endUsers_uid)

        proposing_groups_terms_titles = sorted([group.title for group in self.proposing_groups])
        self.assertListEqual(
            sorted([term.title for term in vocab1(pmFolder)]), proposing_groups_terms_titles)
        self.assertListEqual(
            sorted([term.title for term in vocab2(pmFolder)]), sorted([unicode(org.acronym) for org in self.all_org]))
        self.assertListEqual(
            sorted([term.title for term in vocab3(pmFolder)]), proposing_groups_terms_titles)

        associeted_groups = sorted([group.title for group in self.proposing_groups])
        self.assertListEqual([term.title for term in vocab4(pmFolder)], associeted_groups)

    def test_pm_ProposingGroupsForFacetedVocabulary(self):
        '''Test that vocabulary "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary"
           relies on MeetingConfig.groupsHiddenInDashboardFilter.'''
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        pmFolder = self.getMeetingFolder()
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.proposinggroupsforfacetedfiltervocabulary",
                          only_factory=True)
        # by default when MeetingConfig.groupsHiddenInDashboardFilter is empty, every group are returned
        self.assertEqual(cfg.getGroupsHiddenInDashboardFilter(), ())
        # remove extra organizations from profiles
        cfg.setGroupsHiddenInDashboardFilter(self._orgs_to_exclude_from_filter())
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(
            [term.title for term in vocab(pmFolder)],
            [u'Developers', u'Vendors', u'End users (Inactive)'])
        # now define values in MeetingConfig.groupsHiddenInDashboardFilter
        cfg.setGroupsHiddenInDashboardFilter((self.vendors_uid, ) + self._orgs_to_exclude_from_filter())
        notify(ObjectEditedEvent(cfg))
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
        cfg = self.meetingConfig
        self._enableField('category')
        self._enableField('classifier')
        self.changeUser('siteadmin')
        org1 = self.create('organization', id='org1', title='Org 1', acronym='Org1')
        org1_uid = org1.UID()
        org2 = self.create('organization', id='org2', title='Org 2', acronym='Org2')
        org2_uid = org2.UID()
        org3 = self.create('organization', id='org3', title='Org 3', acronym='Org3')
        org3_uid = org3.UID()
        vocab = get_vocab(org1,
                          "Products.PloneMeeting.vocabularies.groupsinchargevocabulary",
                          only_factory=True)

        # for now, no group in charge
        meetingFolder = self.getMeetingFolder()
        self.assertEqual(len(vocab(meetingFolder)), 0)
        # define some group in charge, vocabulary is invalidated when an org is modified
        self.vendors.groups_in_charge = (org1_uid,)
        notify(ObjectModifiedEvent(self.vendors))
        self.developers.groups_in_charge = (org2_uid,)
        notify(ObjectModifiedEvent(self.developers))
        self.assertEqual([term.title for term in vocab(meetingFolder)], ['Org 1', 'Org 2'])

        # create an new org with a groupInCharge directly
        org4 = self.create('organization', id='org4', title='Org 4',
                           acronym='Org4', groups_in_charge=(org3_uid,))
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

        # category, creating an organization invalidates the vocabulary cache
        org5 = self.create('organization', id='org5', title='Org 5', acronym='Org5')
        org5_uid = org5.UID()
        # an already used
        cfg.categories.development.groups_in_charge = [org3_uid]
        # already existing no more used
        cfg.categories.research.groups_in_charge = [org4_uid]
        # new
        cfg.categories.events.groups_in_charge = [org5_uid]
        self.assertEqual(
            [term.title for term in vocab(meetingFolder)],
            ['Org 2', 'Org 3', 'Org 4', 'Org 5'])

        # classifier, creating an organization invalidates the vocabulary cache
        org6 = self.create('organization', id='org6', title='Org 6', acronym='Org6')
        org6_uid = org6.UID()
        # already existing
        cfg.classifiers.classifier1.groups_in_charge = [org5_uid]
        # new
        cfg.classifiers.classifier2.groups_in_charge = [org6_uid]
        self.assertEqual(
            [term.title for term in vocab(meetingFolder)],
            ['Org 2', 'Org 3', 'Org 4', 'Org 5', 'Org 6'])

    def test_pm_CreatorsVocabulary(self):
        '''Test the "Products.PloneMeeting.vocabularies.creatorsvocabulary"
           vocabulary, especially because it is cached.'''
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.creatorsvocabulary",
                          only_factory=True)
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
        vocab = get_vocab(
            pmFolder,
            "Products.PloneMeeting.vocabularies.creatorsforfacetedfiltervocabulary",
            only_factory=True)
        # once get, it is cached
        self.assertEqual(len(vocab(pmFolder)), 3)

        # if a new pmFolder is created, then the cache is cleaned
        # get pmFolder for user 'pmManager'
        self.changeUser('pmManager')
        pmFolder = self.getMeetingFolder()
        # cache was cleaned
        self.assertEqual(len(vocab(pmFolder)), 4)

        cfg.setUsersHiddenInDashboardFilter(('pmCreator1',))
        notify(ObjectEditedEvent(cfg))
        # cache was cleaned and pmCreator is not in the list anymore
        self.assertEqual(len(vocab(pmFolder)), 3)

        cfg.setUsersHiddenInDashboardFilter(())
        notify(ObjectEditedEvent(cfg))
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
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.askedadvicesvocabulary",
                          only_factory=True)
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
        notify(ObjectEditedEvent(cfg))
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
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(len(vocab(pmFolder)), 7)
        self.assertTrue('delay_row_id__unique_id_999' in vocab(pmFolder).by_token)
        # delay is displayed in customAdviser title
        self.assertTrue('11 day(s)' in vocab(pmFolder).by_token['delay_row_id__unique_id_999'].title)
        # edit a customAdviser
        customAdvisers[-1]['delay'] = '12'
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertTrue('12 day(s)' in vocab(pmFolder).by_token['delay_row_id__unique_id_999'].title)
        # remove a customAdviser
        customAdvisers = customAdvisers[:-1]
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(len(vocab(pmFolder)), 6)
        # power advisers are taken into account by the vocabulary
        cfg.setPowerAdvisersGroups([self.endUsers_uid])
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(len(vocab(pmFolder)), 7)
        # inactive term, displayed in term title
        # make a not really expired term, a 'for_item_created_until' in the future
        self.assertEqual(customAdvisers[-1]['row_id'], 'unique_id_789')
        customAdvisers[-1]['for_item_created_until'] = '2099/01/01'
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(vocab(pmFolder).by_token['delay_row_id__unique_id_789'].title,
                         u'Vendors - 20 day(s)')
        customAdvisers[-1]['for_item_created_until'] = '2009/01/01'
        cfg.setCustomAdvisers(customAdvisers)
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(vocab(pmFolder).by_token['delay_row_id__unique_id_789'].title,
                         u'Vendors - 20 day(s) (Inactive)')

    def test_pm_AskedAdvicesVocabularyWithWrongContext(self):
        '''Test the "Products.PloneMeeting.vocabularies.askedadvicesvocabulary"
           vocabulary, when receiving wrong context, may occur during site install or
           DashboardCollection edit.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        cfg = self.meetingConfig
        vocab = get_vocab(cfg,
                          "Products.PloneMeeting.vocabularies.askedadvicesvocabulary",
                          only_factory=True)
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
        self.request['PUBLISHED'] = None
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
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.askedadvicesvocabulary",
                          only_factory=True)
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
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.advicetypesvocabulary",
                          only_factory=True)
        # once get, it is cached
        self.assertEqual(sorted([term.token for term in vocab(pmFolder)]),
                         ['asked_again',
                          'considered_not_given_hidden_during_redaction',
                          'hidden_during_redaction',
                          'negative',
                          'not_given',
                          'positive'])

        # change the MeetingConfig.usedAdvicesTypes
        cfg.setUsedAdviceTypes(('positive', ))
        # cached
        self.assertEqual(sorted([term.token for term in vocab(pmFolder)]),
                         ['asked_again',
                          'considered_not_given_hidden_during_redaction',
                          'hidden_during_redaction',
                          'negative',
                          'not_given',
                          'positive'])
        notify(ObjectEditedEvent(cfg))
        # cache invalidated
        self.assertEqual(sorted([term.token for term in vocab(pmFolder)]),
                         ['asked_again',
                          'considered_not_given_hidden_during_redaction',
                          'hidden_during_redaction',
                          'not_given',
                          'positive'])
        # ToolPloneMeeting.advisersConfig.advice_types
        self.tool.setAdvisersConfig(
            ({'advice_types': ['positive_with_remarks'],
              'base_wf': 'meetingadvice_workflow',
              'default_advice_type': 'positive_with_remarks',
              'org_uids': [self.vendors_uid],
              'portal_type': 'meetingadvice',
              'show_advice_on_final_wf_transition': '1',
              'wf_adaptations': []}, ))
        self.tool.at_post_edit_script()
        notify(ObjectEditedEvent(cfg))
        self.assertEqual(sorted([term.token for term in vocab(pmFolder)]),
                         ['asked_again',
                          'considered_not_given_hidden_during_redaction',
                          'hidden_during_redaction',
                          'not_given',
                          'positive',
                          'positive_with_remarks'])

    def test_pm_PMConditionAwareCollectionVocabulary(self):
        """Test the 'conditionawarecollectionvocabulary'
           essentially because it is cached. """
        # test with 2 members having same groups
        # as pmCreator1
        self.changeUser('pmCreator1')
        creator1_groups = self.member.getGroups()
        pmFolder = self.getMeetingFolder()
        searches = self.meetingConfig.searches
        searchAllItems = searches.searches_items.searchallitems
        vocab_name = "Products.PloneMeeting.vocabularies.conditionawarecollectionvocabulary"
        vocab = get_vocab(pmFolder, vocab_name, only_factory=True)
        self.assertTrue("/pmCreator1/" in vocab(searchAllItems, pmFolder)._terms[0].title[1])
        # as pmCreator1b
        self.changeUser('pmCreator1b')
        creator1_groups = self.member.getGroups()
        creator1b_groups = self.member.getGroups()
        self.assertEqual(creator1_groups, creator1b_groups)
        self.assertTrue("/pmCreator1b/" in vocab(searchAllItems, pmFolder)._terms[0].title[1])
        # invalidated if a collection is edited
        self.assertEqual(vocab(searchAllItems, pmFolder)._terms[0].title[0], u'My items')
        searchMyItems = searches.searches_items.searchmyitems
        searchMyItems.setTitle(u'My items edited')
        notify(ObjectModifiedEvent(searchMyItems))
        self.assertEqual(vocab(searchAllItems, pmFolder)._terms[0].title[0], u'My items edited')
        # invalidated when user groups changed
        # make pmCreator1b no more a creator
        vocab_values = get_vocab_values(searchAllItems, vocab_name, **{'real_context': pmFolder})
        self._removePrincipalFromGroups(self.member.id, [self.developers_creators])
        no_group_vocab_values = get_vocab_values(searchAllItems, vocab_name, **{'real_context': pmFolder})
        self.assertNotEqual(vocab_values, no_group_vocab_values)
        self._addPrincipalToGroup(self.member.id, self.developers_observers)
        observer_vocab_values = get_vocab_values(searchAllItems, vocab_name, **{'real_context': pmFolder})
        self.assertNotEqual(no_group_vocab_values, observer_vocab_values)

    def test_pm_AdviceTypesVocabularyMCAware(self):
        '''Test the "Products.PloneMeeting.vocabularies.advicetypesvocabulary"
           vocabulary, is MeetingConfig aware, especially because it is cached.'''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self.changeUser('siteadmin')
        cfg.setUsedAdviceTypes(('positive', 'negative'))
        cfg2.setUsedAdviceTypes(('positive', ))
        vocab = get_vocab(cfg,
                          "Products.PloneMeeting.vocabularies.advicetypesvocabulary",
                          only_factory=True)
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
        meeting = self.create('Meeting')
        view = meeting.restrictedTraverse('@@meeting_view')
        view()
        self.assertEqual(self.request.RESPONSE.status, 200)

    def test_pm_DisabledCollectionsAreIgnored(self):
        """If a DashboardCollection is disabled in the MeetingConfig,
           it is not displayed in the vocabulary."""
        searches = self.meetingConfig.searches
        searchAllItems = searches.searches_items.searchallitems
        searchAllItems_path = searchAllItems.absolute_url_path()
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        vocab = get_vocab(pmFolder,
                          "Products.PloneMeeting.vocabularies.conditionawarecollectionvocabulary",
                          only_factory=True)
        self.assertTrue(searchAllItems_path in vocab(searches, real_context=pmFolder))
        # disable it then test again
        self.changeUser('siteadmin')
        self._disableObj(searchAllItems, notify_event=True)
        self.changeUser('pmCreator1')
        self.assertFalse(searchAllItems_path in vocab(searches, real_context=pmFolder))

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

    def test_pm_Faceted_annexes_vocabulary(self):
        """Test especially that enabling attributes in various annexes_types works."""
        cfg = self.meetingConfig
        vocab = get_vocab(
            cfg,
            "Products.PloneMeeting.vocabularies.faceted_annexes_vocabulary",
            only_factory=True)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # nothing enabled, vocabulary is empty
        self.assertEqual(vocab(cfg)._terms, [])
        # enable "signed" for item_decision
        self._enable_annex_config(item, param="signed", related_to="item_decision")
        self.assertEqual(
            [term.token for term in vocab(cfg)],
            ['to_sign', 'not_to_sign', 'signed'])
        # enable "confidentiality" for item_annex
        self._enable_annex_config(item)
        self.assertEqual(
            [term.token for term in vocab(cfg)],
            ['confidential', 'not_confidential', 'to_sign', 'not_to_sign', 'signed'])

    def test_pm_CopyGroupsVocabulary(self):
        """Test, especially when using copyGroups and restrictedCopyGroups."""
        cfg = self.meetingConfig
        cfg.setSelectableCopyGroups((self.vendors_reviewers, self.developers_reviewers))
        cfg.setSelectableRestrictedCopyGroups((self.vendors_reviewers, ))
        self._enableField('copyGroups')
        self._enableField('restrictedCopyGroups')
        self.changeUser('pmManager')
        self.assertEqual(
            get_vocab_values(cfg, "Products.PloneMeeting.vocabularies.copygroupsvocabulary"),
            [self.developers_reviewers, self.vendors_reviewers])


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testFaceted, prefix='test_pm_'))
    return suite
