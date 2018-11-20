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

from AccessControl.SecurityManagement import getSecurityManager
from collections import OrderedDict
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_groups
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_config_root
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.testing import testing_logger
from plone import api
from plone import namedfile
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing.helpers import setRoles
from plone.dexterity.utils import createContentInContainer
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.config import TOOL_FOLDER_ANNEX_TYPES
from Products.PloneMeeting.Meeting import Meeting_schema
from Products.PloneMeeting.MeetingItem import MeetingItem_schema
from Products.PloneMeeting.testing import PM_TESTING_PROFILE_FUNCTIONAL
from Products.PloneMeeting.tests.helpers import PloneMeetingTestingHelpers
from Products.PloneMeeting.utils import cleanMemoize
from Products.PloneMeeting.utils import reviewersFor
from plone.app.testing.bbb import _createMemberarea
from z3c.form.testing import TestRequest as z3c_form_TestRequest
from zope.component import getMultiAdapter
from zope.event import notify
from zope.traversing.interfaces import BeforeTraverseEvent
from zope.viewlet.interfaces import IViewletManager

import os.path
import Products.PloneMeeting
import transaction
import unittest


# Force application logging level to DEBUG so we can use logger in tests
pm_logger = testing_logger('PloneMeeting: testing')


class Response:
    def reset(self):
        pass

    def handleException(self, *args):
        pass

    def redirect(self, *args):
        pass


class TestRequest(z3c_form_TestRequest):

    response = Response()
    RESPONSE = Response()


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
        self.own_org = get_own_organization()
        # make organizations easily available thru their id and store uid
        # for each organization, we will have self.developers, self.developers_uid
        # as well as every plone groups : self.vendors_creators, self.developers_reviewers, ...
        for org in self.own_org.objectValues():
            setattr(self, org.getId(), org)
            setattr(self, '{0}_uid'.format(org.getId()), safe_unicode(org.UID()))
            for plone_group_id in get_plone_groups(org.UID(), ids_only=True):
                org_uid, suffix = plone_group_id.split('_')
                setattr(self,
                        '{0}_{1}'.format(org.getId(), suffix),
                        plone_group_id)

        self.pmFolder = os.path.dirname(Products.PloneMeeting.__file__)
        # Import the test profile
        self.changeUser('admin')
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
        self.annexFile = u'FILE.txt'
        self.annexFileType = 'financial-analysis'
        self.annexFileTypeDecision = 'decision-annex'
        self.annexFileTypeAdvice = 'advice-annex'
        self.annexFileTypeMeeting = 'meeting-annex'

    def tearDown(self):
        self._cleanExistingTmpAnnexFile()

    def createUser(self, username, roles=['Member'], groups=[]):
        '''Creates a user named p_username with some p_roles.'''
        newUser = api.user.create(
            email='test@test.be',
            username=username,
            password=DEFAULT_USER_PASSWORD,
            roles=[],
            properties={})
        setRoles(self.portal, username, roles)
        for group in groups:
            self._addPrincipalToGroup(username, group)
        _createMemberarea(self.portal, username)
        return newUser

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
               isClassifier=False,
               **attrs):
        '''Creates an instance of a meeting (if p_objectType is 'Meeting') or
           meeting item (if p_objectType is 'MeetingItem') and
           returns the created object. p_attrs is a dict of attributes
           that will be given to invokeFactory.'''
        cfg = self.meetingConfig
        shortName = cfg.getShortName()
        # Some special behaviour occurs if the item to create is
        # a recurring item or an item template
        if objectType == 'MeetingItemRecurring':
            contentType = '%s%s' % (objectType, shortName)
            folder = cfg.recurringitems
        elif objectType == 'MeetingItemTemplate':
            contentType = '%s%s' % (objectType, shortName)
            folder = folder or cfg.itemtemplates
        elif objectType == 'MeetingConfig':
            contentType = objectType
            folder = self.tool
        elif objectType == 'organization':
            contentType = objectType
            folder = self.own_org
            if 'groups_in_charge' not in attrs:
                attrs['groups_in_charge'] = []
            if 'item_advice_states' not in attrs:
                attrs['item_advice_states'] = []
            if 'item_advice_edit_states' not in attrs:
                attrs['item_advice_edit_states'] = []
            if 'item_advice_view_states' not in attrs:
                attrs['item_advice_view_states'] = []
            if 'certified_signatures' not in attrs:
                attrs['certified_signatures'] = []
        elif objectType == 'MeetingCategory':
            contentType = objectType
            if isClassifier:
                folder = cfg.classifiers
            else:
                folder = cfg.categories
        else:
            contentType = '%s%s' % (objectType, shortName)
            folder = self.getMeetingFolder(cfg)
        # Add some computed attributes
        idInAttrs = 'id' in attrs
        if not idInAttrs:
            attrs.update({'id': self._generateId(folder)})
        if objectType == 'MeetingItem':
            if 'proposingGroup' not in attrs.keys():
                cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting.get_orgs_for_user')
                proposingGroup = self.tool.get_orgs_for_user(suffixes=['creators'])
                if len(proposingGroup):
                    attrs.update({'proposingGroup': proposingGroup[0].UID()})
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
            if objectType == 'Meeting':
                # manage attendees if using it after processForm
                usedMeetingAttrs = cfg.getUsedMeetingAttributes()
                if 'attendees' in usedMeetingAttrs:
                    obj._at_creation_flag = True
                    default_attendees = obj.getDefaultAttendees()
                    default_attendees = OrderedDict(((attendee, 'attendee') for attendee in default_attendees))
                    signatories = []
                    if 'signatories' in usedMeetingAttrs:
                        signatories = obj.getDefaultSignatories()
                    obj._at_creation_flag = False
                    obj._doUpdateContacts(attendees=default_attendees, signatories=signatories)
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

    def _annex_file_content(self):
        current_path = os.path.dirname(__file__)
        f = open(os.path.join(current_path, self.annexFile), 'r')
        annex_file = namedfile.NamedBlobFile(f.read(), filename=self.annexFile)
        return annex_file

    def addAnnex(self,
                 context,
                 annexType=None,
                 annexTitle=None,
                 relatedTo=None,
                 to_print=False,
                 confidential=False,
                 to_sign=False,
                 signed=False):
        '''Adds an annex to p_item.
           If no p_annexType is provided, self.annexFileType is used.
           If no p_annexTitle is specified, the predefined title of the annex type is used.'''

        if annexType is None:
            if context.meta_type == 'MeetingItem':
                if not relatedTo:
                    annexType = self.annexFileType
                elif relatedTo == 'item_decision':
                    annexType = self.annexFileTypeDecision
            elif context.portal_type.startswith('meetingadvice'):
                annexType = self.annexFileTypeAdvice
            elif context.meta_type == 'Meeting':
                annexType = self.annexFileTypeMeeting

        # get complete annexType id that is like
        # 'meeting-config-id-annexes_types_-_item_annexes_-_financial-analysis'
        if relatedTo == 'item_decision':
            context.REQUEST.set('force_use_item_decision_annexes_group', True)
        annexes_config_root = get_config_root(context)
        if relatedTo == 'item_decision':
            context.REQUEST.set('force_use_item_decision_annexes_group', False)
        annexTypeId = calculate_category_id(annexes_config_root.get(annexType))

        annexContentType = 'annex'
        if relatedTo == 'item_decision':
            annexContentType = 'annexDecision'

        theAnnex = createContentInContainer(
            container=context,
            portal_type=annexContentType,
            title=annexTitle or 'Annex',
            file=self._annex_file_content(),
            content_category=annexTypeId,
            to_print=to_print,
            confidential=confidential,
            to_sign=to_sign,
            signed=signed)
        # need to commit the transaction so the stored blob is correct
        # if not done, accessing the blob will raise 'BlobError: Uncommitted changes'
        transaction.commit()
        return theAnnex

    def addAnnexType(self,
                     id,
                     to_print=False,
                     confidential=False,
                     enabled=True,
                     relatedTo='item'):
        cfg = self.meetingConfig
        folder = getattr(cfg, TOOL_FOLDER_ANNEX_TYPES)

        portal_type = 'ContentCategory'
        if relatedTo == 'item':
            portal_type = 'ItemAnnexContentCategory'
            categoryGroupId = 'item_annexes'
        elif relatedTo == 'item_decision':
            portal_type = 'ItemAnnexContentCategory'
            categoryGroupId = 'item_decision_annexes'
        elif relatedTo == 'advice':
            categoryGroupId = 'advice_annexes'
        elif relatedTo == 'meeting':
            categoryGroupId = 'meeting_annexes'

        annexType = api.content.create(
            type=portal_type,
            id=id,
            title=id,
            icon=self._annex_file_content(),
            container=getattr(folder, categoryGroupId),
            to_print=to_print,
            confidential=confidential,
            enabled=enabled
        )
        return annexType

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
                                            'plonegroup-utils-get_organizations-'
                                            ])

    def _removeOrganizations(self):
        """Delete every organizations found in own_org."""
        # remove every users from linked Plone groups so organizations are removable
        for org in self.own_org.objectValues():
            plone_groups = get_plone_groups(org.UID())
            for plone_group in plone_groups:
                for member_id in plone_group.getMemberIds():
                    self.portal.portal_groups.removePrincipalFromGroup(member_id, plone_group.id)
        # unselect every organizations from plonegroup
        api.portal.set_registry_record(ORGANIZATIONS_REGISTRY, [])
        ids_to_remove = self.own_org.objectIds()
        self.own_org.manage_delObjects(ids=ids_to_remove)
        self.cleanMemoize()

    def _removeConfigObjectsFor(self, meetingConfig, folders=['recurringitems', 'itemtemplates']):
        """
          Helper method for removing some objects from a given p_meetingConfig.
          Given p_folders are folders of the meetingConfig to clean out.
        """
        currentUser = self.member.getId()
        self.changeUser('admin')
        for folderId in folders:
            # folder could be subfolder/subsubfolder
            subfolder = meetingConfig
            for subfolderId in folderId.split('/'):
                subfolder = getattr(subfolder, subfolderId)
            objectIds_to_remove = []
            for obj in subfolder.objectValues():
                objectIds_to_remove.append(obj.getId())
            subfolder.manage_delObjects(ids=objectIds_to_remove)
        self.changeUser(currentUser)

    def _turnUserIntoPrereviewer(self, member):
        """
          Helper method for adding a given p_member to every '_prereviewers' group
          corresponding to every '_reviewers' group he is in.
        """
        reviewers = reviewersFor(self.meetingConfig.getItemWorkflow())
        groups = [group for group in member.getGroups() if group.endswith('_%s' % reviewers.keys()[0])]
        groups = [group.replace(reviewers.keys()[0], reviewers.keys()[-1]) for group in groups]
        for group in groups:
            self._addPrincipalToGroup(member.getId(), group)

    # Workflow-related methods -------------------------------------------------
    def do(self, obj, transition, comment=''):
        '''Executes a workflow p_transition on a given p_obj.'''
        self.wfTool.doActionFor(obj, transition, comment=comment)
        self.cleanMemoize()

    def transitions(self, obj):
        '''Returns the list of transitions that the current user may trigger
           on p_obj.'''
        res = [t['id'] for t in self.wfTool.getTransitionsFor(obj)]
        res.sort()
        return res

    def _get_viewlet_manager(self, context, manager_name):
        """ """
        view = BrowserView(context, self.request)
        viewlet_manager = getMultiAdapter(
            (context, self.request, view),
            IViewletManager,
            manager_name)
        viewlet_manager.update()
        return viewlet_manager

    def _get_viewlet(self, context, manager_name, viewlet_name):
        """ """
        viewlet_manager = self._get_viewlet_manager(context, manager_name)
        viewlet = viewlet_manager.get(viewlet_name)
        return viewlet

    def _addPrincipalToGroup(self, principal_id, group_id):
        """We need to changeUser so getGroups is updated."""
        self.portal.portal_groups.addPrincipalToGroup(principal_id, group_id)
        self.changeUser(self.member.getId())
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')

    def _removePrincipalFromGroup(self, principal_id, group_id):
        """We need to changeUser so getGroups is updated."""
        self.portal.portal_groups.removePrincipalFromGroup(principal_id, group_id)
        self.changeUser(self.member.getId())
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
