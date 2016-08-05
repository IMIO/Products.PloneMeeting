# -*- coding: utf-8 -*-
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

import unittest
import os.path
from AccessControl.SecurityManagement import getSecurityManager
from ZPublisher.HTTPRequest import FileUpload

from zope.event import notify
from zope.traversing.interfaces import BeforeTraverseEvent

from plone import api
from plone.app.testing.helpers import setRoles
from plone.app.testing import login, logout

from Products.PloneTestCase.setup import _createHomeFolder

from imio.helpers.cache import cleanRamCacheFor
import Products.PloneMeeting
# If I do not remove this method, some tests crash.
#from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.config import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.MeetingItem import MeetingItem_schema
from Products.PloneMeeting.Meeting import Meeting_schema
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.testing import PM_TESTING_PROFILE_FUNCTIONAL
from Products.PloneMeeting.tests.helpers import PloneMeetingTestingHelpers
from Products.PloneMeeting.utils import cleanMemoize

# Force application logging level to DEBUG so we can use logger in tests
import sys
import logging
pm_logger = logging.getLogger('PloneMeeting: testing')
pm_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
pm_logger.addHandler(handler)


class TestFile:
    '''Stub class that simulates a file upload from a HTTP POST.'''
    def __init__(self, testFile, filename):
        self.file = testFile
        self.filename = filename
        self.headers = None


class PloneMeetingTestCase(unittest.TestCase, PloneMeetingTestingHelpers):
    '''Base class for defining PloneMeeting test cases.'''

    # Some default content
    descriptionText = '<p>Some description</p>'
    decisionText = '<p>Some decision.</p>'
    schemas = {'MeetingItem': MeetingItem_schema,
               'Meeting': Meeting_schema}
    subproductIgnoredTestFiles = ['testPerformances.py',
                                  'testConversionWithDocumentViewer.py',
                                  'test_robot.py']

    layer = PM_TESTING_PROFILE_FUNCTIONAL

    def setUp(self):
        # Define some useful attributes
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        # configure default workflows so Folder has a workflow
        # make sure we have a default workflow
        self.portal.portal_workflow.setDefaultChain('simple_publication_workflow')
        # setup manually the correct browserlayer, see:
        # https://dev.plone.org/ticket/11673
        notify(BeforeTraverseEvent(self.portal, self.request))
        self.tool = self.portal.portal_plonemeeting
        self.wfTool = self.portal.portal_workflow
        self.pmFolder = os.path.dirname(Products.PloneMeeting.__file__)
        # Create siteadmin user
        self.createUser('siteadmin', ('Member', 'Manager', ))
        # Import the test profile
        self.changeUser('admin')
        # Create some member areas
        for userId in ('pmManager', 'pmCreator1', 'pmCreator2', 'siteadmin'):
            _createHomeFolder(self.portal, userId)
        # Disable notifications mechanism. This way, the test suite may be
        # executed even on production sites that contain many real users.
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.setMailItemEvents([])
            cfg.setMailMeetingEvents([])
        logout()
        # Set the default meeting config
        self.meetingConfig = getattr(self.tool, 'plonemeeting-assembly', None)
        self.meetingConfig2 = getattr(self.tool, 'plonegov-assembly', None)
        # Set the default file and file type for adding annexes
        self.annexFile = 'INSTALL.TXT'
        self.annexFileType = 'financial-analysis'
        self.annexFileTypeDecision = 'decision-annex'
        self.annexFileTypeAdvice = 'advice-annex'

    def tearDown(self):
        self._cleanExistingTmpAnnexFile()

    def createUser(self, username, roles):
        '''Creates a user named p_username with some p_roles.'''
        api.user.create(email='test@test.be',
                        username=username,
                        password=DEFAULT_USER_PASSWORD,
                        roles=[],
                        properties={})
        setRoles(self.portal, username, roles)
        _createHomeFolder(self.portal, username)

    def setMeetingConfig(self, meetingConfigId):
        '''On which meeting config must we work?'''
        self.meetingConfig = getattr(self.tool, meetingConfigId)

    def setCurrentMeeting(self, meeting):
        '''In utils.py, a method is used to get the currently published object
           in the Plone site. Within this test system, it returns None. This
           method allows to simulate that p_meeting is the currently published
           object.'''
        self.portal.REQUEST['PUBLISHED'] = meeting

    def hasPermission(self, permission, obj):
        '''Checks if the currently logged user has the p_permission on p_obj.
           It is not possible to do it for any user, ie:

           user = self.portal.portal_membership.getMemberById(userId)
           return user.has_permission(permission, obj)

           does not work. So we need to change logged user every time.

           Note that p_obj may be a list of object instead of a single object.
           In this case, the method returns True if the currently logged user
           has p_permission on every object of the list.'''

        # make sure we do not have permission check cache problems...
        self.cleanMemoize()

        sm = getSecurityManager()
        res = True
        if type(obj) in (list, tuple):
            for o in obj:
                res = res and sm.checkPermission(permission, o)
        else:
            res = sm.checkPermission(permission, obj)
        return res

    def changeUser(self, loginName):
        '''Logs out currently logged user and logs in p_loginName.'''
        logout()
        self.cleanMemoize()
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.isPowerObserverForCfg')
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.isManager')
        if loginName == 'admin':
            login(self.app, loginName)
        else:
            login(self.portal, loginName)
        self.member = api.user.get_current()
        self.portal.REQUEST['AUTHENTICATED_USER'] = self.member

    def _generateId(self, ploneFolder):
        '''Generate an id for creating an object in p_ploneFolder.'''
        prefix = 'o'
        i = 1
        gotId = False
        while not gotId:
            res = prefix + str(i)
            if not hasattr(ploneFolder, res):
                gotId = True
            else:
                i += 1
        return res

    def getMeetingFolder(self, meetingConfig=None):
        '''Get the meeting folder for the current meeting config.'''
        if not meetingConfig:
            meetingConfig = self.meetingConfig
        return self.tool.getPloneMeetingFolder(meetingConfig.id)

    def create(self,
               objectType,
               folder=None,
               autoAddCategory=True,
               meetingConfig=None,
               isClassifier=False,
               **attrs):
        '''Creates an instance of a meeting (if p_objectType is 'Meeting') or
           meeting item (if p_objectType is 'MeetingItem') and
           returns the created object. p_attrs is a dict of attributes
           that will be given to invokeFactory.'''
        cfg = meetingConfig or self.meetingConfig
        shortName = cfg.getShortName()
        # Some special behaviour occurs if the item to create is
        # a recurring item or an item template
        if objectType == 'MeetingItemRecurring':
            contentType = '%s%s' % (objectType, shortName)
            folder = cfg.recurringitems
        elif objectType == 'MeetingItemTemplate':
            contentType = '%s%s' % (objectType, shortName)
            folder = folder or cfg.itemtemplates
        elif objectType in ('MeetingGroup', 'MeetingConfig'):
            contentType = objectType
            folder = self.tool
        elif objectType in ('MeetingCategory', ):
            contentType = objectType
            if isClassifier:
                folder = cfg.classifiers
            else:
                folder = cfg.categories
        else:
            contentType = '%s%s' % (objectType, shortName)
            folder = self.getMeetingFolder(meetingConfig)
        # Add some computed attributes
        idInAttrs = 'id' in attrs
        if not idInAttrs:
            attrs.update({'id': self._generateId(folder)})
        if objectType == 'MeetingItem':
            if not 'proposingGroup' in attrs.keys():
                cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.getGroupsForUser')
                proposingGroup = self.tool.getGroupsForUser(suffixes=['creators'])
                if len(proposingGroup):
                    attrs.update({'proposingGroup': proposingGroup[0].id})
        obj = getattr(folder, folder.invokeFactory(contentType, **attrs))
        if objectType == 'Meeting':
            self.setCurrentMeeting(obj)
        elif objectType == 'MeetingItem':
            # optionalAdvisers are not set (???) by invokeFactory...
            if 'optionalAdvisers' in attrs:
                obj.setOptionalAdvisers(attrs['optionalAdvisers'])
            # define a category for the item if necessary
            if autoAddCategory and not \
               cfg.getUseGroupsAsCategories() and not \
               obj.getCategory():
                aCategory = cfg.getCategories()[0].getId()
                obj.setCategory(aCategory)
        if hasattr(obj.aq_inner, 'processForm'):
            # at_post_create_script is called by processForm
            # but processForm manage the _at_creation_flag
            # keep id if it was given
            if idInAttrs:
                obj._at_rename_after_creation = False
            obj.processForm()
            if idInAttrs:
                obj._at_rename_after_creation = True
        # make sure we do not have permission check cache problems...
        self.cleanMemoize()
        return obj

    def _cleanExistingTmpAnnexFile(self):
        '''While adding in annex (see code around shutil in addAnnex),
           a temporary file is created.  In case we check assertRaise(Unauthorized, addAnnex, ...)
           the temporary file is not removed, so make sure it is...'''
        originalAnnexPath = os.path.join(self.pmFolder, self.annexFile)
        newAnnexPath = originalAnnexPath[:-4] + '_tmp_for_tests.%s' % originalAnnexPath[-3:]
        if os.path.exists(newAnnexPath):
            os.remove(newAnnexPath)

    def addAnnex(self, item, annexType=None, annexTitle=None,
                 relatedTo='item'):
        '''Adds an annex to p_item. The uploaded file has name p_annexPath,
           which is a path relative to the folder that corresponds to package
           Products.PloneMeeting. If None is provided, a default file is
           uploaded (see self.annexFile). If no p_annexType is provided,
           self.annexFileType is used. If no p_annexTitle is specified, the
           predefined title of the annex type is used.'''
        # copy the default annexFile because ZODB.blob removes (os.remove) a FileUpload
        # after having used it...
        from shutil import copyfile
        originalAnnexPath = os.path.join(self.pmFolder, self.annexFile)
        newAnnexPath = originalAnnexPath[:-4] + '_tmp_for_tests.%s' % originalAnnexPath[-3:]
        copyfile(originalAnnexPath, newAnnexPath)
        annexPath = newAnnexPath
        annexFile = FileUpload(TestFile(
            file(os.path.join(self.pmFolder, annexPath)), annexPath))
        if annexType is None:
            if relatedTo == 'item':
                annexType = self.annexFileType
            elif relatedTo == 'item_decision':
                annexType = self.annexFileTypeDecision
            elif relatedTo == 'advice':
                annexType = self.annexFileTypeAdvice
        fileType = getattr(self.meetingConfig.meetingfiletypes, annexType)
        if annexTitle is None:
            annexTitle = fileType.getPredefinedTitle() or 'Annex title'
        # Create the annex
        idCandidate = None
        IAnnexable(item).addAnnex(idCandidate,
                                  annexTitle,
                                  annexFile,
                                  relatedTo,
                                  meetingFileTypeUID=fileType.UID())
        # Find the last created annex
        annexUid = IAnnexable(item).getAnnexesByType(relatedTo,
                                                     makeSubLists=False,
                                                     typesIds=[annexType])[-1]['UID']
        uid_catalog = self.portal.uid_catalog
        theAnnex = uid_catalog(UID=annexUid)[0].getObject()
        self.assertNotEquals(theAnnex.size(), 0)
        return theAnnex

    def deleteAsManager(self, uid):
        """When we want to remove an item the current user does not have permission to,
           but we are not testing delete permission, do it as a 'Manager'."""
        currentUser = self.member.getId()
        self.changeUser('admin')
        self.portal.restrictedTraverse('@@delete_givenuid')(uid)
        self.changeUser(currentUser)

    def cleanMemoize(self):
        """
          Remove every memoized informations
        """
        # borg localroles are memoized...
        # so while checking local roles twice, there could be problems...
        # remove memoized localroles
        cleanMemoize(self.portal, prefixes=['borg.localrole.workspace.checkLocalRolesAllowed',
                                            'tool-getmeetinggroups-',
                                            'meeting-config-getcategories-',
                                            'meeting-config-gettopics-',
                                            ])

    def _removeConfigObjectsFor(self, meetingConfig, folders=['recurringitems', 'itemtemplates']):
        """
          Helper method for removing some objects from a given p_meetingConfig.
          Given p_folders are folders of the meetingConfig to clean out.
        """
        currentUser = self.member.getId()
        self.changeUser('admin')
        for folder in folders:
            configFolder = getattr(meetingConfig, folder)
            objectIds_to_remove = []
            for item in configFolder.objectValues():
                objectIds_to_remove.append(item.getId())
            configFolder.manage_delObjects(ids=objectIds_to_remove)
        self.changeUser(currentUser)

    def _turnUserIntoPrereviewer(self, member):
        """
          Helper method for adding a given p_member to every '_prereviewers' group
          corresponding to every '_reviewers' group he is in.
        """
        groups = [group for group in member.getGroups() if group.endswith('_%s' % MEETINGREVIEWERS.keys()[0])]
        groups = [group.replace(MEETINGREVIEWERS.keys()[0], MEETINGREVIEWERS.keys()[-1]) for group in groups]
        for group in groups:
            self.portal.portal_groups.addPrincipalToGroup(member.getId(), group)

    # Workflow-related methods -------------------------------------------------
    def do(self, obj, transition, comment=''):
        '''Executes a workflow p_transition on a given p_obj.'''
        self.wfTool.doActionFor(obj, transition, comment=comment)

    def transitions(self, obj):
        '''Returns the list of transitions that the current user may trigger
           on p_obj.'''
        res = [t['id'] for t in self.wfTool.getTransitionsFor(obj)]
        res.sort()
        return res
