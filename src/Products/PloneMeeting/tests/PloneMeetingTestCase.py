# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 by PloneGov
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

from zope.annotation.interfaces import IAnnotations

from plone.app.testing.helpers import setRoles
from plone.app.testing import login, logout

from Products.PloneTestCase.setup import _createHomeFolder

import Products.PloneMeeting
# If I do not remove this method, some tests crash.
#from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.MeetingItem import MeetingItem_schema
from Products.PloneMeeting.Meeting import Meeting_schema

from Products.PloneMeeting.testing import PM_TESTS_PROFILE_FUNCTIONAL

# ------------------------------------------------------------------------------
class TestFile:
    '''Stub class that simulates a file upload from a HTTP POST.'''
    def __init__(self, testFile, filename):
        self.file = testFile
        self.filename = filename
        self.headers = None

# ------------------------------------------------------------------------------
class PloneMeetingTestCase(unittest.TestCase):
    '''Base class for defining PloneMeeting test cases.'''

    # Some default content
    descriptionText = '<p>Some description</p>'
    decisionText = '<p>Some decision.</p>'
    schemas = {'MeetingItem':MeetingItem_schema, 'Meeting':Meeting_schema}

    layer = PM_TESTS_PROFILE_FUNCTIONAL

    def setUp(self):
        # Define some useful attributes
        self.portal = self.layer['portal']
        self.tool = self.portal.portal_plonemeeting
        self.wfTool = self.portal.portal_workflow
        self.pmFolder = os.path.dirname(Products.PloneMeeting.__file__)
        # Create admin user
        # Do not use 'userFolderAddUser' to avoid bug in Container
        self.createUser('admin', ('Member','Manager'))
        # Import the test profile
        login(self.portal, 'admin')
        #setup_tool = getToolByName(self.portal, 'portal_setup')
        #setup_tool.runImportStepFromProfile(
        #    'profile-Products.PloneMeeting:test', 'initializetool-PloneMeeting',
        #    run_dependencies=True)
        # Create some member areas
        for userId in ('pmManager', 'pmCreator1', 'pmCreator2'):
            _createHomeFolder(self.portal, userId)
        # Disable notifications mechanism. This way, the test suite may be
        # executed even on production sites that contain many real users.
        for meetingConfig in self.tool.objectValues('MeetingConfig'):
            meetingConfig.setMailItemEvents([])
            meetingConfig.setMailMeetingEvents([])
        logout()
        # Set the default meeting config
        self.meetingConfig = getattr(self.tool, 'plonemeeting-assembly', None)
        self.meetingConfig2 = getattr(self.tool, 'plonegov-assembly', None)
        # Set the default file and file type for adding annexes
        self.annexFile = 'README.txt'
        self.annexFileType = 'financial-analysis'
        self.annexFileTypeDecision = 'decision-annex'

    def createUser(self, username, roles):
        '''Creates a user named p_username with some p_roles.'''
        pms = self.portal.portal_membership
        pms.addMember(username, 'password', [], [])
        setRoles(self.portal, username, roles)

    def setMeetingConfig(self, meetingConfigId):
        '''On which meeting config must we work?'''
        self.meetingConfig = getattr(self.tool, meetingConfigId)

    def setCurrentMeeting(self, meeting):
        '''In utils.py, a method is used to get the currently published object
           in the Plone site. Within this test system, it returns None. This
           method allows to simulate that p_meeting is the currently published
           object.'''
        meeting.REQUEST['PUBLISHED'] = meeting

    def hasPermission(self, permission, obj):
        '''Checks if the currently logged user has the p_permission on p_obj.
           It is not possible to do it for any user, ie:

           user = self.portal.portal_membership.getMemberById(userId)
           return user.has_permission(permission, obj)

           does not work. So we need to change logged user every time.

           Note that p_obj may be a list of object instead of a single object.
           In this case, the method returns True if the currently logged user
           has p_permission on every object of the list.'''
        # borg localroles are memoized...
        # so while checking local roles twice, there could be problems...
        # remove memoized localroles
        annotations = IAnnotations(self.portal.REQUEST)
        annotations_to_delete = []
        for annotation in annotations.keys():
            if annotation.startswith('borg.localrole.workspace.checkLocalRolesAllowed'):
                annotations_to_delete.append(annotation)

        for annotation_to_delete in annotations_to_delete:
            del annotations[annotation_to_delete]

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
        login(self.portal, loginName)

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

    def getMeetingFolder(self):
        '''Get the meeting folder for the current meeting config.'''
        return self.tool.getPloneMeetingFolder(self.meetingConfig.id)

    def create(self, objectType, folder=None, **attrs):
        '''Creates an instance of a meeting (if p_objectType is 'Meeting') or
           meeting item (if p_objectType is 'MeetingItem') and
           returns the created object. p_attrs is a dict of attributes
           that will be given to invokeFactory.'''
        shortName = self.meetingConfig.getShortName()
        # Some special behaviour occurs if the thing to create is a recurring
        # item
        isRecurringItem = objectType.startswith('Recurring')
        if isRecurringItem:
            contentType =  '%s%s' % (objectType[9:], shortName)
            folder = self.meetingConfig.recurringitems
        elif objectType in ('MeetingGroup', 'MeetingConfig'):
            contentType = objectType
            folder = self.tool
        else:
            contentType = '%s%s' % (objectType, shortName)
            folder = self.getMeetingFolder()
        # Add some computed attributes
        attrs.update( {'id': self._generateId(folder)} )
        if objectType == 'MeetingItem':
            if not 'proposingGroup' in attrs.keys():
                proposingGroup = self.tool.getGroups(suffix="creators")
                if len(proposingGroup):
                    attrs.update({'proposingGroup': proposingGroup[0].id})
        obj = getattr(folder, folder.invokeFactory(contentType, **attrs))
        if objectType == 'Meeting':
            self.setCurrentMeeting(obj)
        elif objectType == 'MeetingItem':
            # optionalAdvisers are not set (???) by invokeFactory...
            if 'optionalAdvisers' in attrs:
                obj.setOptionalAdvisers(attrs['optionalAdvisers'])
        # Some attributes in attrs are not taken into account. 
        # The setAttributes method can set attrs after the object is created.
        if hasattr(obj.aq_inner, 'processForm'):
            # at_post_create_script is called by processForm
            # but processForm manage the _at_creation_flag
            obj.processForm()
        return obj

    def setAttributes(self, obj, **attrs):
        '''Set the attributes contained in p_attrs on an object p_obj. Some
           attributes cannot be set in invokeFactory because related permissions
           are given in at_post_create or for unknown reasons.'''
        metatype = obj.meta_type
        if not self.schemas.has_key(metatype):
            print "Metatype %s not present in schemas %s" % \
                  (metatype, self.schemas)
            return
        schema = self.schemas[metatype]
        for key in attrs.keys():
            if not schema.has_key(key):
                print "Field %s not present in schema %s" % (key, metatype)
                continue
            field = schema[key]
            field.getMutator(obj)(attrs[key])
        if hasattr(obj.aq_inner, 'at_post_edit_script'):
            obj.at_post_edit_script()

    def addAnnex(self, item, annexPath=None, annexType=None, annexTitle=None,
                 decisionRelated=False):
        '''Adds an annex to p_item. The uploaded file has name p_annexPath,
           which is a path relative to the folder that corresponds to package
           Products.PloneMeeting. If None is provided, a default file is
           uploaded (see self.annexFile). If no p_annexType is provided,
           self.annexFileType is used. If no p_annexTitle is specified, the
           predefined title of the annex type is used.'''
        # Find the needed information for creating the annex
        if annexPath == None:
            annexPath = self.annexFile
        #copy the default annexFile because ZODB.blob removes (os.remove) a FileUpload
        #after having used it...
        from shutil import copyfile
        originalAnnexPath = os.path.join(self.pmFolder, annexPath)
        newAnnexPath = originalAnnexPath[:-4] + '_tmp' + '.txt'
        copyfile(originalAnnexPath, newAnnexPath)
        annexPath = newAnnexPath
        annexFile = FileUpload(TestFile(
            file(os.path.join(self.pmFolder, annexPath)), annexPath))
        if annexType == None:
            if decisionRelated:
                annexType = self.annexFileTypeDecision
            else:
                annexType = self.annexFileType
        fileType = getattr(self.meetingConfig.meetingfiletypes, annexType)
        if annexTitle == None:
            annexTitle = fileType.getPredefinedTitle()
        # Create the annex
        idCandidate = None
        item.addAnnex(idCandidate, annexType, annexTitle, annexFile,
                      str(decisionRelated), meetingFileType=fileType)
        # Find the last created annex
        annexUid = item.getAnnexesByType(decisionRelated, makeSubLists=False,
                                         typesIds=[annexType])[-1]['uid']
        theAnnex = item.uid_catalog(UID=annexUid)[0].getObject()
        self.assertNotEquals(theAnnex.size(), 0)
        return theAnnex

    # Workflow-related methods -------------------------------------------------
    def do(self, obj, transition):
        '''Executes a workflow p_transition on a given p_obj.'''
        self.wfTool.doActionFor(obj, transition)

    def transitions(self, obj):
        '''Returns the list of transitions that the current user may trigger
           on p_obj.'''
        return [t['id'] for t in self.wfTool.getTransitionsFor(obj)]
# ------------------------------------------------------------------------------
