# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from AccessControl.SecurityManagement import getSecurityManager
from collections import OrderedDict
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_groups
from collective.documentviewer.config import CONVERTABLE_TYPES
from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from copy import deepcopy
from datetime import datetime
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import cleanRamCache
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import get_vocab_values
from imio.helpers.content import object_values
from imio.helpers.content import richtextval
from imio.helpers.testing import testing_logger
from imio.helpers.workflow import get_transitions
from plone import api
from plone import namedfile
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing.bbb import _createMemberarea
from plone.app.testing.helpers import setRoles
from plone.dexterity.utils import createContentInContainer
from plone.dexterity.utils import iterSchemata
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFPlone.utils import base_hasattr
from Products.Five.browser import BrowserView
from Products.PloneMeeting.browser.meeting import get_default_attendees
from Products.PloneMeeting.browser.meeting import get_default_signatories
from Products.PloneMeeting.browser.meeting import get_default_voters
from Products.PloneMeeting.config import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import TOOL_FOLDER_ANNEX_TYPES
from Products.PloneMeeting.testing import PM_TESTING_PROFILE_FUNCTIONAL
from Products.PloneMeeting.tests.helpers import PloneMeetingTestingHelpers
from Products.PloneMeeting.utils import cleanMemoize
from z3c.form.testing import TestRequest as z3c_form_TestRequest
from z3c.relationfield.relation import RelationValue
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.event import notify
from zope.interface import Invalid
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import ObjectModifiedEvent
from zope.traversing.interfaces import BeforeTraverseEvent
from zope.viewlet.interfaces import IViewletManager

import os.path
import Products.PloneMeeting
import transaction
import unittest


# Force application logging level to DEBUG so we can use logger in tests
pm_logger = testing_logger('PloneMeeting: testing')

IMG_BASE64_DATA = "data:image/gif;base64,R0lGODlhCgAKAPcAAP////79/f36+/3z8/zy8/rq7Prm6Pnq7P" \
    "je4vTx8vPg5O6gqe2gqOq4v+igqt9tetxSYNs7Tdo5TNc5TNUbMdUbMNQRKNIKIdIJINIGHdEGHtEDGtACFdAA" \
    "FtAAFNAAEs8AFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAACIAIP3sAAoACBL2OAAAAPjHWRQAABUKiAAAABL2FAAAAhL+dPkBhPm4MP" \
    "///xL2YPZNegAAAAAQAAAABgAAAAAAABL2wAAAAAAARRL25PEPfxQAAPEQAAAAAAAAA/3r+AAAAAAAGAAAABL2" \
    "uAAAQgAAABL2pAAAAAAAAAAAAAAADAAAAgABAfDTAAAAmAAAAAAAAAAAABL27Mku0AAQAAAAAAAAAEc1MUaDsA" \
    "AAGBL3FPELyQAAAAABEgAAAwAAAQAAAxL22AAAmBL+dPO4dPPKQP///0c70EUoOQAAmMku0AAQABL3TAAAAEaD" \
    "sEc1MUaDsAAABkT98AABEhL3wAAALAAAQAAAQBL3kQAACSH5BAEAAAAALAAAAAAKAAoAQAhGAAEIHEhw4IIIFC" \
    "AsKCBwQAQQFyKCeKDAIEKFDAE4hBiRA0WCAwwUBLCAA4cMICg0YIjAQoaIFzJMSCCw5EkOKjM2FDkwIAA7"


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

    def __setitem__(self, attr, value):
        """ """
        self.__setattr__(attr, value)

    def __getitem__(self, attr):
        return self.__getattr__(attr)


class TestFile:
    '''Stub class that simulates a file upload from a HTTP POST.'''
    def __init__(self, testFile, filename):
        self.file = testFile
        self.filename = filename
        self.headers = None


class DefaultData(object):
    """Class used to be passed to a default method."""
    def __init__(self, context):
        self.context = context


class PloneMeetingTestCase(unittest.TestCase, PloneMeetingTestingHelpers):
    '''Base class for defining PloneMeeting test cases.'''

    # Some default content
    descriptionText = '<p>Some description</p>'
    motivationText = '<p>Some motivation.</p>'
    decisionText = '<p>Some decision.</p>'
    subproductIgnoredTestFiles = ['testPerformances.py',
                                  'test_robot.py']

    layer = PM_TESTING_PROFILE_FUNCTIONAL

    cfg1_id = 'plonemeeting-assembly'
    cfg2_id = 'plonegov-assembly'

    external_image1 = \
        "https://fastly.picsum.photos/id/22/400/400.jpg?hmac=Id8VAtx7v59BrMxVGFbHMrf-93mskILQzmMJ__Tzww8"
    external_image2 = \
        "https://fastly.picsum.photos/id/1025/400/300.jpg?hmac=5qUnaqytITcD06pLxsGw7l_twswo9b9p9c8zz_tdpMc"
    external_image3 = \
        "https://fastly.picsum.photos/id/1035/600/400.jpg?hmac=mnooh0fwG-2MIGW-xTUcYO6wyyx9LNdZK4RM6R2SA7A"
    external_image4 = \
        "https://fastly.picsum.photos/id/1062/600/500.jpg?hmac=ZoUBWDuRcsyqDbBPOj5jEU1kHgJ5iGO1edk1-QYode8"

    def setUp(self):
        # enable full diff in failing tests
        self.maxDiff = None
        # Define some useful attributes
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.changeUser('admin')
        # setup manually the correct browserlayer, see:
        # https://dev.plone.org/ticket/11673
        notify(BeforeTraverseEvent(self.portal, self.request))
        self.tool = self.portal.portal_plonemeeting
        self.catalog = self.portal.portal_catalog
        self.wfTool = self.portal.portal_workflow
        self.own_org = get_own_organization()
        # make organizations easily available through their id and store uid
        # for each organization, we will have self.developers, self.developers_uid
        # as well as every plone groups : self.vendors_creators, self.developers_reviewers, ...
        # include organizations outside own_org as well
        self.proposing_groups = object_values(self.own_org, 'PMOrganization')
        self.all_org = object_values(self.own_org.aq_parent, 'PMOrganization') + self.proposing_groups
        self.active_proposing_groups = [org for org in self.proposing_groups if org.active]
        self.inactive_proposing_groups = [org for org in self.proposing_groups if not org.active]
        orgs = object_values(self.own_org, 'PMOrganization') + \
            object_values(self.own_org.aq_parent, 'PMOrganization')
        for org in orgs:
            org_id = org.getId().replace('-', '_')
            setattr(self, org_id, org)
            setattr(self, '{0}_uid'.format(org_id), org.UID())
            for plone_group_id in get_plone_groups(org.UID(), ids_only=True):
                org_uid, suffix = plone_group_id.split('_')
                setattr(self,
                        '{0}_{1}'.format(org_id, suffix),
                        plone_group_id)
        # make held_position easily available as well
        i = 1
        for person in object_values(self.portal.contacts, 'PMPerson'):
            setattr(self,
                    'hp{0}'.format(i),
                    object_values(person, 'PMHeldPosition')[0])
            setattr(self,
                    'hp{0}_uid'.format(i),
                    object_values(person, 'PMHeldPosition')[0].UID())
            i += 1

        self.pmFolder = os.path.dirname(Products.PloneMeeting.__file__)
        # Disable notifications mechanism. This way, the test suite may be
        # executed even on production sites that contain many real users.
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg.setMailItemEvents([])
            cfg.setMailMeetingEvents([])
        logout()

        # Set the default meeting config
        self.meetingConfig = getattr(self.tool, self.cfg1_id, None)
        self.meetingConfig2 = getattr(self.tool, self.cfg2_id, None)
        # Set the default file and file type for adding annexes
        self.annexFile = u'FILE.txt'
        self.annexFilePDF = u'file_correct.pdf'
        self.annexFileCorruptedPDF = u'file_errorDuringConversion.pdf'
        self.annexFileType = 'financial-analysis'
        self.annexFileTypeDecision = 'decision-annex'
        self.annexFileTypeAdvice = 'advice-annex'
        self.annexFileTypeMeeting = 'meeting-annex'
        # log current test module and method name
        test_num = self._resultForDoCleanups.testsRun
        test_total = self._resultForDoCleanups.count
        pm_logger.info('Executing [{0}/{1}] {2}:{3}'.format(
            test_num, test_total, self.__class__.__name__, self._testMethodName))
        # necessary for MeetingItem.MeetingItemWorkflowConditions._check_required_data
        self.request.set('imio.actionspanel_portal_cachekey', True)

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

    def changeUser(self, loginName, clean_memoize=True):
        '''Logs out currently logged user and logs in p_loginName.'''
        logout()
        if clean_memoize:
            # necessary to invalidate imio.helpers.patches._listAllowedRolesAndUsers
            # or a catalog query reuses cached allowedRolesAndUsers
            cleanRamCache()
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

    def getMeetingFolder(self, meetingConfig=None, userId=None):
        '''Get the meeting folder for the current meeting config.'''
        if not meetingConfig:
            meetingConfig = self.meetingConfig
        return self.tool.getPloneMeetingFolder(meetingConfig.id, userId=userId)

    def create(self,
               objectType,
               folder=None,
               autoAddCategory=True,
               is_classifier=False,
               **attrs):
        '''Creates an instance of a meeting (if p_objectType is 'Meeting') or
           meeting item (if p_objectType is 'MeetingItem') and
           returns the created object. p_attrs is a dict of attributes
           that will be given to invokeFactory.'''
        cfg = self.meetingConfig
        shortName = cfg.getShortName()
        # Some special behaviour occurs if the item to create is
        # a recurring item or an item template
        contentType = objectType
        if objectType == 'MeetingItemRecurring':
            contentType = '%s%s' % (objectType, shortName)
            folder = cfg.recurringitems
        elif objectType == 'MeetingItemTemplate':
            contentType = '%s%s' % (objectType, shortName)
            folder = folder or cfg.itemtemplates
        elif objectType == 'MeetingConfig':
            folder = self.tool
        elif objectType == 'organization':
            folder = folder or self.own_org
        elif objectType == 'person':
            folder = self.portal.contacts
        elif objectType == 'held_position':
            if folder is None:
                raise Exception(
                    'The "folder" parameter must be a person when creating a held_position!')
            if "organization" not in attrs:
                attrs['position'] = self._relation(self.own_org)
        elif objectType == 'meetingcategory':
            if is_classifier:
                folder = cfg.classifiers
            else:
                folder = cfg.categories
        elif objectType == 'ConfigurablePODTemplate':
            folder = cfg.podtemplates
        else:
            contentType = '%s%s' % (objectType, shortName)
            folder = self.getMeetingFolder(cfg)
        # Add some computed attributes
        idInAttrs = 'id' in attrs
        if not idInAttrs:
            attrs.update({'id': self._generateId(folder)})
        if objectType == 'Meeting' and attrs.get('date', None) is None:
            attrs.update({'date': datetime.now()})
        if objectType == 'MeetingItem':
            if 'proposingGroup' not in attrs.keys():
                cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting._get_org_uids_for_user')
                proposingGroupUids = self.tool.get_orgs_for_user(suffixes=['creators'])
                if len(proposingGroupUids):
                    attrs.update({'proposingGroup': proposingGroupUids[0]})
        obj = getattr(folder, folder.invokeFactory(contentType, **attrs))
        if objectType == 'Meeting':
            self.setCurrentMeeting(obj)
        elif objectType == 'MeetingItem':
            # optionalAdvisers are not set (???) by invokeFactory...
            if 'optionalAdvisers' in attrs:
                obj.setOptionalAdvisers(attrs['optionalAdvisers'])
            # rich text fields are not set (???) by invokeFactory...
            rich_fields = ['motivation', 'decision', 'decisionSuite', 'decisionEnd', 'votesResult']
            for rich_field in rich_fields:
                if rich_field in attrs:
                    field = obj.getField(rich_field)
                    field.set(obj, attrs[rich_field])
            # define a category for the item if necessary
            if autoAddCategory and \
               'category' in cfg.getUsedItemAttributes() and \
               not obj.getCategory():
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
            # manage attendees if using it
            usedMeetingAttrs = cfg.getUsedMeetingAttributes()
            if 'attendees' in usedMeetingAttrs:
                default_attendees = get_default_attendees(cfg)
                default_attendees = OrderedDict((
                    (attendee, 'attendee') for attendee in default_attendees))
                signatories = []
                if 'signatories' in usedMeetingAttrs:
                    signatories = get_default_signatories(cfg)
                voters = []
                if cfg.getUseVotes():
                    voters = get_default_voters(cfg)
                obj._do_update_contacts(attendees=default_attendees,
                                        signatories=signatories,
                                        voters=voters)
            # manage default values
            add_form = folder.restrictedTraverse('++add++{0}'.format(obj.portal_type))
            add_form.update()
            for field_name, widget in add_form.form_instance.w.items():
                if widget.value and \
                   not getattr(obj, field_name) and \
                   isinstance(widget.value, (str, unicode)):
                    setattr(obj, field_name, widget.field.fromUnicode(widget.value))

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

    def _annex_file_content(self, annexFile=None):
        current_path = os.path.dirname(__file__)
        annexFile = annexFile or self.annexFile
        f = open(os.path.join(current_path, annexFile), 'r')
        annex_file = namedfile.NamedBlobFile(f.read(), filename=annexFile)
        return annex_file

    def addAnnex(self,
                 context,
                 annexType=None,
                 annexTitle=None,
                 annexDescription=None,
                 relatedTo=None,
                 to_print=False,
                 confidential=False,
                 to_sign=False,
                 signed=False,
                 publishable=False,
                 annexFile=None,
                 scan_id=None):
        '''Adds an annex to p_item.
           If no p_annexType is provided, self.annexFileType is used.
           If no p_annexTitle is specified, the predefined title of the annex type is used.'''

        if annexType is None:
            if context.getTagName() == 'MeetingItem':
                if not relatedTo:
                    annexType = self.annexFileType
                elif relatedTo == 'item_decision':
                    annexType = self.annexFileTypeDecision
            elif context.portal_type.startswith('meetingadvice'):
                annexType = self.annexFileTypeAdvice
            elif context.getTagName() == 'Meeting':
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

        # scan_id is removed by default
        self.request.set(ITEM_SCAN_ID_NAME, scan_id)
        annex = createContentInContainer(
            container=context,
            portal_type=annexContentType,
            title=annexTitle or 'Annex',
            description=annexDescription,
            file=self._annex_file_content(annexFile=annexFile),
            content_category=annexTypeId,
            to_print=to_print,
            confidential=confidential,
            to_sign=to_sign,
            signed=signed,
            publishable=publishable,
            scan_id=scan_id)
        self.request.set(ITEM_SCAN_ID_NAME, None)

        class DummyData(object):
            def __init__(self, context, contentType, content_category):
                self.__context__ = context
                self.contentType = contentType
                self.content_category = content_category

        data = DummyData(annex, annex.file.contentType, annex.content_category)
        for schema in iterSchemata(annex):
            try:
                schema.validateInvariants(data, [])
            except Invalid as exc:
                unrestrictedRemoveGivenObject(annex)
                raise(exc)

        # need to commit the transaction so the stored blob is correct
        # if not done, accessing the blob will raise 'BlobError: Uncommitted changes'
        transaction.commit()
        return annex

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

    def addAdvice(self,
                  item,
                  advice_group=None,
                  advice_type=u"positive",
                  advice_comment=u"My comment",
                  advice_hide_during_redaction=False,
                  advice_portal_type='meetingadvice'):
        if not advice_group:
            advice_group = self.vendors_uid
        # manage MeetingConfig.defaultAdviceHiddenDuringRedaction
        # as it only works while added ttw
        if not advice_hide_during_redaction:
            advice_hide_during_redaction = advice_portal_type in \
                self.meetingConfig.getDefaultAdviceHiddenDuringRedaction()
        advice = createContentInContainer(
            item,
            advice_portal_type,
            **{'advice_group': advice_group,
               'advice_type': advice_type,
               'advice_hide_during_redaction': advice_hide_during_redaction,
               'advice_comment': richtextval(advice_comment)})
        return advice

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
        cleanMemoize(self.portal,
                     prefixes=['borg.localrole.workspace.checkLocalRolesAllowed',
                               'tool-getmeetinggroups-',
                               'meeting-config-getcategories-',
                               'meeting-config-gettopics-',
                               'plonegroup-utils-get_organizations-',
                               'PloneMeeting-MeetingConfig-getMeetingsAcceptingItems',
                               'PloneMeeting-tool-get_orgs_for_user'])

    def _removeOrganizations(self):
        """Delete every organizations found in own_org."""
        # remove every users from linked Plone groups so organizations are removable
        for org in self.own_org.objectValues():
            plone_groups = get_plone_groups(org.UID())
            for plone_group in plone_groups:
                for member_id in plone_group.getMemberIds():
                    self.portal.portal_groups.removePrincipalFromGroup(member_id, plone_group.id)
            # empty groups_in_charge
            org.groups_in_charge = []
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
                # can not remove the ITEM_DEFAULT_TEMPLATE_ID
                if folderId == 'itemtemplates' and \
                   obj.getId() == ITEM_DEFAULT_TEMPLATE_ID:
                    if obj.query_state() == 'active':
                        # disable it instead removing it
                        api.content.transition(obj, 'deactivate')
                    continue
                objectIds_to_remove.append(obj.getId())
            subfolder.manage_delObjects(ids=objectIds_to_remove)
        self.changeUser(currentUser)

    def _turnUserIntoPrereviewer(self, member):
        """
          Helper method for adding a given p_member to every '_prereviewers' group
          corresponding to every '_reviewers' group he is in.
        """
        reviewers = self.meetingConfig.reviewersFor()
        groups = [group for group in member.getGroups() if group.endswith('_%s' % reviewers.keys()[0])]
        groups = [group.replace(reviewers.keys()[0], reviewers.keys()[-1]) for group in groups]
        for group in groups:
            self._addPrincipalToGroup(member.getId(), group)

    # Workflow-related methods -------------------------------------------------
    def do(self, obj, transition, comment='', clean_memoize=True):
        '''Executes a workflow p_transition on a given p_obj.'''
        self.wfTool.doActionFor(obj, transition, comment=comment)
        if clean_memoize:
            self.cleanMemoize()

    def transitions(self, obj):
        '''Returns the list of transition ids that the current user
           may trigger on p_obj.'''
        return sorted(get_transitions(obj))

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
        viewlet.update()
        return viewlet

    def _addPrincipalToGroup(self, principal_id, group_id):
        """We need to changeUser so getGroups is updated."""
        self.portal.portal_groups.addPrincipalToGroup(principal_id, group_id)
        self.changeUser(self.member.getId())

    def _removePrincipalFromGroups(self, principal_id, group_ids):
        """We need to changeUser so getGroups is updated."""
        for group_id in group_ids:
            self.portal.portal_groups.removePrincipalFromGroup(principal_id, group_id)
        self.changeUser(self.member.getId())

    def _setPowerObserverStates(self,
                                cfg=None,
                                observer_type='powerobservers',
                                field_name='item_states',
                                states=[],
                                access_on=''):
        """Change power observers states for item or meeting."""
        if not cfg:
            cfg = self.meetingConfig
        power_observers = deepcopy(cfg.getPowerObservers())
        for po_infos in power_observers:
            if po_infos['row_id'] == observer_type:
                po_infos[field_name] = states
                if field_name == 'item_states':
                    po_infos['item_access_on'] = access_on
                else:
                    po_infos['meeting_access_on'] = access_on
        cfg.setPowerObservers(power_observers)

    def _activate_wfas(self, wfas, cfg=None, keep_existing=False):
        """Activate given p_wfas, we clean wfas, apply,
           then set given p_wfas and apply again."""
        if isinstance(wfas, basestring):
            wfas = [wfas]
        currentUser = self.member.getId()
        self.changeUser('siteadmin')
        if cfg is None:
            cfg = self.meetingConfig
        if not keep_existing:
            cfg.setWorkflowAdaptations(())
            notify(ObjectEditedEvent(cfg))
        else:
            wfas = tuple(set(tuple(wfas) + cfg.getWorkflowAdaptations()))
        if wfas:
            cfg.setWorkflowAdaptations(wfas)
            notify(ObjectEditedEvent(cfg))
        self.changeUser(currentUser)

    def _deactivate_wfas(self, wfas, cfg=None):
        """Deactivate given p_wfas."""
        if isinstance(wfas, basestring):
            wfas = [wfas]
        currentUser = self.member.getId()
        self.changeUser('siteadmin')
        if cfg is None:
            cfg = self.meetingConfig
        wfas = [wfa for wfa in cfg.getWorkflowAdaptations()
                if wfa not in wfas]
        cfg.setWorkflowAdaptations(wfas)
        notify(ObjectEditedEvent(cfg))
        self.changeUser(currentUser)

    def _activate_config(self,
                         field_name,
                         value,
                         cfg=None,
                         keep_existing=True,
                         remove=False,
                         reload=True):
        """Helper to activate a value in the configuration."""
        cfg = cfg or self.meetingConfig
        field = cfg.getField(field_name)
        values = list(field.get(cfg))
        if remove:
            values.remove(value)
        else:
            if keep_existing:
                values.append(value)
            else:
                values = [value]
        field.getMutator(cfg)(values)
        if reload:
            currentUser = self.member.getId()
            self.changeUser('siteadmin')
            notify(ObjectEditedEvent(cfg))
            self.changeUser(currentUser)

    def _enableAutoConvert(self, enable=True):
        """Enable collective.documentviewer auto_convert."""
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_convert = enable
        # False or every portal_type having a file is converted, like PODTemplate, ...
        gsettings.auto_select_layout = False
        gsettings.auto_layout_file_types = CONVERTABLE_TYPES.keys()
        self.tool.at_post_edit_script()
        return gsettings

    def _enable_column(self, column_name, cfg=None, related_to='MeetingItem', enable=True):
        """ """
        cfg = cfg or self.meetingConfig
        column_names = cfg.getItemColumns() if related_to == 'MeetingItem' else cfg.getMeetingColumns()
        if column_name not in column_names:
            column_names += (column_name, )
            if related_to == 'MeetingItem':
                cfg.setItemColumns(column_names)
            else:
                cfg.setMeetingColumns(column_names)
            cfg.updateCollectionColumns()
            return True

    def _enableField(self, field_names, cfg=None, related_to='MeetingItem', enable=True, reload=False):
        """ """
        if not hasattr(field_names, "__iter__"):
            field_names = [field_names]
        cfg = cfg or self.meetingConfig
        for field_name in field_names:
            if related_to == 'MeetingItem':
                usedItemAttrs = list(cfg.getUsedItemAttributes())
                # make sure we are not playing with a field_name that does not exist
                if field_name not in cfg.getField('usedItemAttributes').Vocabulary(cfg):
                    raise Exception("\"%s\" does not exist in usedItemAttributes" % field_name)
                if enable and field_name not in usedItemAttrs:
                    usedItemAttrs.append(field_name)
                elif not enable and field_name in usedItemAttrs:
                    usedItemAttrs.remove(field_name)
                cfg.setUsedItemAttributes(usedItemAttrs)
            elif related_to == 'Meeting':
                usedMeetingAttrs = list(cfg.getUsedMeetingAttributes())
                # make sure we are not playing with a field_name that does not exist
                if field_name not in cfg.getField('usedMeetingAttributes').Vocabulary(cfg):
                    raise Exception("\"%s\" does not exist in usedMeetingAttributes" % field_name)
                if enable and field_name not in usedMeetingAttrs:
                    usedMeetingAttrs.append(field_name)
                elif not enable and field_name in usedMeetingAttrs:
                    usedMeetingAttrs.remove(field_name)
                cfg.setUsedMeetingAttributes(tuple(usedMeetingAttrs))
        if reload:
            currentUser = self.member.getId()
            self.changeUser('siteadmin')
            notify(ObjectEditedEvent(cfg))
            self.changeUser(currentUser)
        else:
            cleanRamCacheFor('Products.PloneMeeting.MeetingItem.attribute_is_used')
            cleanRamCacheFor('Products.PloneMeeting.content.meeting.attribute_is_used')

    def _enable_annex_config(self,
                             obj,
                             param="confidentiality",
                             related_to=None,
                             enable=True):
        """p_fct possible values are :
           - confidentiality (default);
           - to_be_printed;
           - signed;
           - publishable."""
        if related_to == 'item_decision':
            self.request.set('force_use_item_decision_annexes_group', True)
        annexes_config_root = get_config_root(obj)
        if related_to == 'item_decision':
            self.request.set('force_use_item_decision_annexes_group', False)

        annex_group = get_group(annexes_config_root, obj)
        attr_name = "{0}_activated".format(param)
        setattr(annex_group, attr_name, enable)

    def _enable_action(self, action, related_to="MeetingItem", enable=True):
        """Enable an action for given p_related_to element."""
        cfg = self.meetingConfig
        if related_to == "MeetingItem":
            if enable and action not in cfg.getEnabledItemActions():
                actions = cfg.getEnabledItemActions() + (action, )
                cfg.setEnabledItemActions(actions)
                notify(ObjectEditedEvent(cfg))
            elif not enable and action in cfg.getEnabledItemActions():
                actions = list(cfg.getEnabledItemActions())
                actions.remove(action)
                cfg.setEnabledItemActions(actions)
                notify(ObjectEditedEvent(cfg))

    def _disableObj(self, obj, notify_event=True):
        """ """
        # using field 'enabled'
        if base_hasattr(obj, 'enabled'):
            obj.enabled = False
            obj.reindexObject(idxs=['enabled'])
        else:
            # using workflow
            self.do(obj, 'deactivate')
        if notify_event:
            # manage cache
            notify(ObjectModifiedEvent(obj))
        self.cleanMemoize()

    def _check_wfa_available(self, wfas, related_to='MeetingItem'):
        available = True
        if related_to == 'MeetingItem':
            available_wfas = get_vocab_values(self.meetingConfig, 'WorkflowAdaptations')
        elif related_to == 'MeetingAdvice':
            available_wfas = get_vocab_values(self.tool, 'AdviceWorkflowAdaptations')

        for wfa in wfas:
            if wfa not in available_wfas:
                available = False
                pm_logger.info('Bypassing {0} because WFAdaptation {1} is not available!'.format(
                    self._testMethodName, wfa))
                break
        return available

    def validate_at_fields(self, obj):
        """ """
        errors = {}
        for field_name in obj.Schema().keys():
            field = obj.getField(field_name)
            field.validate(field.getAccessor(obj)(), obj, errors)
        return errors

    def _relation(self, obj):
        """ """
        intids = getUtility(IIntIds)
        return RelationValue(intids.getId(obj))
