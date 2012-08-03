# -*- coding: utf-8 -*-
#
# File: ExternalApplication.py
#
# Copyright (c) 2011 by PloneGov
# Generator: ArchGenXML Version 2.6
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<gbastien@commune.sambreville.be>, Stephan GEULETTE
<stephan.geulette@uvcw.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
import urllib, urllib2, httplib, base64, os, os.path, time
from DateTime import DateTime
from persistent.mapping import PersistentMapping
from AccessControl import Unauthorized
from appy.shared.xml_parser import XmlUnmarshaller
from appy.shared.dav import Resource
from appy.shared.utils import typeLetters, copyData, FolderDeleter
from appy.pod import convertToXhtml
from Products.PloneMeeting import FakeBrain
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.profiles import *
defValues = ExternalApplicationDescriptor.get()
from Products.PloneMeeting.utils import \
     sendMail, allowManagerToCreateIn, disallowManagerToCreateIn, \
     clonePermissions, getFieldContent
from Products.PloneMeeting.MeetingConfig import MeetingConfig
from Products.PloneMeeting.model.adaptations import performModelAdaptations
import logging
logger = logging.getLogger('PloneMeeting')
class DistantSiteError(Exception): pass
##/code-section module-header

schema = Schema((

    LinesField(
        name='usages',
        default= defValues.usages,
        widget=MultiSelectionWidget(
            description="Usages",
            description_msgid="extapp_usages_descr",
            format="checkbox",
            label='Usages',
            label_msgid='PloneMeeting_label_usages',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listUsages',
    ),
    StringField(
        name='notifyUrl',
        default= defValues.notifyUrl,
        widget=StringField._properties['widget'](
            description="NotifyUrl",
            description_msgid="notify_url_descr",
            size=70,
            label='Notifyurl',
            label_msgid='PloneMeeting_label_notifyUrl',
            i18n_domain='PloneMeeting',
        ),
        validators=('isURL',),
    ),
    StringField(
        name='notifyEmail',
        default= defValues.notifyEmail,
        widget=StringField._properties['widget'](
            description="NotifyEmail",
            description_msgid="notify_email_descr",
            size=70,
            label='Notifyemail',
            label_msgid='PloneMeeting_label_notifyEmail',
            i18n_domain='PloneMeeting',
        ),
        validators=('isEmail',),
    ),
    StringField(
        name='notifyProxy',
        default= defValues.notifyProxy,
        widget=StringField._properties['widget'](
            description="NotifyProxy",
            description_msgid="notify_proxy_descr",
            size=70,
            label='Notifyproxy',
            label_msgid='PloneMeeting_label_notifyProxy',
            i18n_domain='PloneMeeting',
        ),
        validators=('isURL',),
    ),
    StringField(
        name='notifyLogin',
        default= defValues.notifyLogin,
        widget=StringField._properties['widget'](
            description="NotifyLogin",
            description_msgid="notify_login_descr",
            label='Notifylogin',
            label_msgid='PloneMeeting_label_notifyLogin',
            i18n_domain='PloneMeeting',
        ),
    ),
    StringField(
        name='notifyPassword',
        default= defValues.notifyPassword,
        widget=PasswordWidget(
            description="NotifyPassword",
            description_msgid="notify_password_descr",
            label='Notifypassword',
            label_msgid='PloneMeeting_label_notifyPassword',
            i18n_domain='PloneMeeting',
        ),
    ),
    StringField(
        name='notifyProtocol',
        default= defValues.notifyProtocol,
        widget=SelectionWidget(
            description="NotifyProtocol",
            description_msgid="notify_protocol_descr",
            label='Notifyprotocol',
            label_msgid='PloneMeeting_label_notifyProtocol',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listProtocols',
    ),
    LinesField(
        name='notifyEvents',
        default= defValues.notifyEvents,
        widget=MultiSelectionWidget(
            description="NotifyEvents",
            description_msgid="extapp_notify_events_descr",
            label='Notifyevents',
            label_msgid='PloneMeeting_label_notifyEvents',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listNotifyEvents',
    ),
    StringField(
        name='notifyCondition',
        default= defValues.notifyCondition,
        widget=StringField._properties['widget'](
            description="NotifyCondition",
            description_msgid="notify_condition_descr",
            size=70,
            label='Notifycondition',
            label_msgid='PloneMeeting_label_notifyCondition',
            i18n_domain='PloneMeeting',
        ),
    ),
    StringField(
        name='secondUrl',
        default= defValues.secondUrl,
        widget=StringField._properties['widget'](
            description="SecondUrl",
            description_msgid="second_url_descr",
            size=70,
            label='Secondurl',
            label_msgid='PloneMeeting_label_secondUrl',
            i18n_domain='PloneMeeting',
        ),
        validators=('isURL',),
    ),
    BooleanField(
        name='deferredMeetingImport',
        default= defValues.deferredMeetingImport,
        widget=BooleanField._properties['widget'](
            description="DeferredMeetingImport",
            description_msgid="deferred_meeting_import_descr",
            label='Deferredmeetingimport',
            label_msgid='PloneMeeting_label_deferredMeetingImport',
            i18n_domain='PloneMeeting',
        ),
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

ExternalApplication_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
##/code-section after-schema

class ExternalApplication(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()

    implements(interfaces.IExternalApplication)

    meta_type = 'ExternalApplication'
    _at_rename_after_creation = True

    schema = ExternalApplication_schema

    ##code-section class-header #fill in your manual code here
    URL_NOTIFY_ERROR = 'Application "%s" could not be contacted at URL "%s". ' \
        'I will try to send him a mail instead (if an email address is ' \
        'defined for this application). Error is: %s.'
    CONNECT_ERROR = 'Error while contacting distant site %s (%s).'
    MEETING_ALREADY_IMPORTED = 'Meeting "%s" was NOT imported (already here).'
    MEETING_IN_CREATION = 'Importing meeting "%s"...'
    MEETING_NIGHTWORKED = 'Distant meeting at "%s" will be imported next night.'
    MEETING_CREATED = 'Meeting "%s" was successfully imported in home ' \
        'folder of user "pmManager".'
    MEETING_AND_USER_CREATED = MEETING_CREATED + ' This user has been ' \
        'created (password=meeting) and has roles Member, MeetingManager ' \
        'and MeetingObserverGlobal.'
    MEETING_CONFIG_IN_CREATION = 'Importing meeting config "%s"...'
    MEETING_CONFIG_CREATED = 'Meeting config "%s" successfully imported.'
    SUBOBJECT_IN_CREATION = 'Creating config object "%s"...'
    SUBOBJECT_CREATED = 'Config object "%s" created.'
    ITEM_IN_CREATION = 'Importing item "%s"...'
    ITEM_CREATED = 'Item "%s" created.'
    ANNEX_IN_CREATION = 'Importing annex "%s"...'
    ANNEX_CREATED = 'Annex "%s" created.'
    IMPORTING_TOOL = 'Synchronizing HS tool...'
    TOOL_IMPORTED = 'HS tool was synchronized.'
    IMPORTING_USERS = 'Importing users...'
    USERS_IMPORTED = 'Users were synchronized. %d user(s) added, %d user(s) ' \
                     'deleted, %d user(s) modified (password or name). ' \
                     'A total of %d users are registered on this site.'
    GROUP_ALREADY_IMPORTED = 'Group "%s" was NOT imported (already here).'
    GROUP_IN_CREATION = 'Importing group "%s"...'
    GROUP_CREATED = 'Group "%s" has been imported successfully.'
    SEARCH_RESULT_ERROR = 'An error occurred while performing a search on ' \
                          'a distant site. %s'
    CREATOR_UNKNOWN = "Creator for item '%s' is unknown, so we can't create " \
                      "a folder in its memberarea."
    FOLDER_CREATE_ERROR = "User '%s' does on exist on this site, so we " \
                          "can't create a folder in its memberarea."
    MEMBERAREA_CREATE_ERROR = 'Failed to create memberarea for user "%s" (%s).'

    notBasicMeetingFields = ('id', 'items', 'lateItems', 'creation_date',
        'modification_date', 'frozenDocuments', 'workflowHistory', 'entrances',
        'departures')
    notBasicItemFields = ('id', 'classifier', 'preferredMeeting', 'reference',
        'annexes', 'annexesDecision', 'advices', 'creation_date',
        'modification_date', 'pm_modification_date', 'frozenDocuments',
        'workflowHistory', 'votes', 'predecessor')
    # The following list also contains fields that should not be transferred
    # from a master site to an archive site.
    notBasicToolFields = ('id', 'meetingConfigs', 'meetingGroups',
        'siteStartDate', 'usedColorSystem', 'colorSystemDisabledFor',
        'deferredNotificationsHandling')
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    def listUsages(self):
        '''Returns the list of possible usages: for what usage(s) will this
           external application be useful for?'''
        d = 'PloneMeeting'
        res = [
          # Use it for importing meetings
          ("import", translate('extapp_usage_import', domain=d, context=self)),
          # Use it as a target for exporting meetings
          ("export", translate('extapp_usage_export', domain=d, context=self)),
          # Use it as a target for sending a notification
          ("notify", translate('extapp_usage_notify', domain=d, context=self)),
          # Use it as a place for performing searches
          ("search", translate('extapp_usage_search', domain=d, context=self)),
          # Use it as a database of users for keeping ours in sync with it
          ("users", translate('extapp_usage_users', domain=d, context=self)),
        ]
        return DisplayList(tuple(res))

    def listNotifyEvents(self):
        '''Lists the workflow events that can trigger a notification towards
           an external application.'''
        activeConfigs = self.getParentNode().getActiveConfigs()
        if not activeConfigs: return DisplayList(()) # No cfg yet on this site.
        res = []
        cfg = activeConfigs[0]
        for id, text in cfg.listTransitions('Meeting'):
            res.append(('Meeting.%s' % id, 'Meeting->%s' % text))
        for id, text in cfg.listTransitions('Item'):
            res.append(('MeetingItem.%s' % id, 'Item->%s' % text))
        return DisplayList(tuple(res))

    security.declarePublic('listProtocols')
    def listProtocols(self):
        res = DisplayList(( ("httpGet", 'HTTP GET'),
                            ("httpPost", 'HTTP POST') ))
        return res

    def validate_secondUrl(self, value):
        '''secondUrl is mandatory if 'search' is among usages.'''
        if ('search' in self.REQUEST.get('usages')) and not value:
            return translate('second_url_mandatory', domain='PloneMeeting', context=self)
        return None

    def validate_notifyPassword(self, value):
        '''Password is mandatory if notifyLogin is filled.'''
        if self.REQUEST.get('notifyLogin', None) and not value:
            return translate('password_mandatory', domain='PloneMeeting', context=self)
        return None

    def _unmarshall(self, data, classes={}):
        '''Unmarshalls the p_data, that comes from a distant master site.'''
        if not classes:
            obj = XmlUnmarshaller().parse(data)
        else:
            obj = XmlUnmarshaller(classes=classes).parse(data)
        # Both Plone object ID and UID can be in a list as obj.id. If
        # it is the case, we keep only the Plone id, not the UID.
        if hasattr(obj, 'id') and isinstance(obj.id, list):
            obj.id = obj.id[1]
        # The "type" attribute added by the marshaller has no use for us.
        if hasattr(obj, 'type'): del obj.type
        return obj

    def _sendHttpRequest(self, url=None, usage='import', params={}):
        '''Sends a HTTP request at p_url to the external application. If p_url
           is not specified, self.getNotifyUrl() is used. Returns a 2-tuple:
           1st value tells if the request was successfull or not, 2nd value
           is the response of the external application in case of success or
           the error message in case of failure.'''
        # Encode URL parameters
        if params:
            params = urllib.urlencode(params)
        # Determine protocol to use (for some usages the user has no choice)
        if usage == 'import':   protocol = 'httpGet'
        elif usage == 'search': protocol = 'httpGet'
        else:                   protocol = self.getNotifyProtocol()
        # Determine URL
        if url:
            appUrl = url
        else:
            appUrl = self.getNotifyUrl()
        if (protocol == 'httpGet') and params:
            if '?' in appUrl: sep = '&'
            else: sep = '?'
            appUrl = '%s%s%s' % (appUrl, sep, params)
        # Create the request object
        httpReq = urllib2.Request(appUrl)
        if (protocol == 'httpPost') and params:
            httpReq.add_data(params)
        # Add credentials if needed
        if self.getNotifyLogin():
            auth64 = base64.encodestring('%s:%s' % (self.getNotifyLogin(),
                self.getNotifyPassword()))[:-1]
            httpReq.add_header("Authorization", "Basic %s" % auth64)
        # Specify a proxy if needed
        if self.getNotifyProxy():
            httpReq.set_proxy(self.getNotifyProxy(), 'http')
        # Send the request
        try:
            response = urllib2.urlopen(httpReq)
            res = (True, response.read())
        except IOError, ioe:
            res = (False, convertToXhtml(str(ioe)))
            logger.warn(self.URL_NOTIFY_ERROR% (self.Title(), appUrl, str(ioe)))
        except httplib.HTTPException, he:
            msg = str(he) + '(' + he.__class__.__name__ + ')'
            res = (False, convertToXhtml(msg))
            logger.warn(self.URL_NOTIFY_ERROR % (self.Title(), appUrl, msg))
        return res

    security.declarePublic('notifyExternalApplication')
    def notifyExternalApplication(self, obj=None, event='test'):
        '''Notifies the external app I represent that an p_event has occurred
           on p_obj. If p_obj is None, a dummy URL will be sent for testing
           purposes.'''
        res = None
        mustSendMail = True
        if not obj: objectUrl = '/dummy/object'
        else:       objectUrl = obj.absolute_url_path()
        # Evaluate the notify condition
        condition = self.getNotifyCondition()
        if condition:
            exec 'condition = %s' % condition
        else:
            condition = True
        if not condition: return
        if self.getNotifyUrl():
            mustSendMail = False
            logger.info('Notifying external application "%s" (url "%s") of ' \
                        'event "%s" on object "%s"...' % (self.id, \
                        self.getNotifyUrl(), event, objectUrl))
            success, res = self._sendHttpRequest(params={'object': objectUrl,
                                                         'event':event})
            if not success:
                logger.info('Notification failed.')
                mustSendMail = True
            else:
                logger.info('Notification successfull.')
        # Try to send a mail if needed
        if mustSendMail and self.getNotifyEmail() and obj:
            sendMail([self.getNotifyEmail()], obj, 'eventOccurred')
        return res

    def _encodeParamName(self, name, value):
        '''Return the p_name, encoded with the type of the p_value.'''
        for letter, pythonType in typeLetters.iteritems():
            if type(value) == pythonType:
                return '%s_%s' % (letter, name)
        return 's_%s' % name

    security.declarePrivate('_patchBrainUrls')
    def _patchBrainUrls(self, brains):
        '''p_brains are FakeBrain instances, retrieved from a distant site.
           The problem is: their URL corresponds to the WebDAV URL of the
           corresponding objects on the distant site, not their 'web' URL. So
           in this method we modify their URL with their 'web' URL.'''
        webBaseUrl = self.getSecondUrl()
        if webBaseUrl.endswith('-'):
            webBaseUrl = webBaseUrl[:-1]
            removePrefix = True
        else:
            removePrefix = False
        for brain in brains:
            if not removePrefix:
                suffix = brain.path
            else:
                suffix = brain.path[brain.path.find('/',1):]
            brain.url = '%s%s' % (webBaseUrl, suffix)

    security.declarePublic('callMethod')
    def callMethod(self, name, params, url=None, classes={}):
        '''Calls a distant method named p_name, with p_params, either on the
           distant tool (if p_url is None), either on a specified distant URL.
           p_classes is a mapping that can be given to the unmarshaller to
           specify which classes must be used for which XML tag names.'''
        targetUrl = url or (self.getNotifyUrl() + '/portal_plonemeeting')
        # Encode a type for every param
        args = {'do': name}
        for param, value in params.iteritems():
            args[self._encodeParamName(param, value)] = value
        success, response = self._sendHttpRequest(
            url=targetUrl, usage='search', params=args)
        if success:
            return self._unmarshall(response, classes=classes)
        else:
            logger.warn(self.SEARCH_RESULT_ERROR % response)
            return []

    security.declarePublic('search')
    def search(self, params):
        '''Performs a query in extApp's portal_catalog.'''
        res = self.callMethod('distantSearch', params, classes={'e':FakeBrain})
        self._patchBrainUrls(res)
        return res

    security.declarePublic('listArchivedMeetings')
    def listArchivedMeetings(self):
        '''Gets the list of archived meetings at the PloneMeeting master
           site.'''
        # Gets the meeting config URLs by getting tool information
        toolUrl = self.getNotifyUrl() + '/portal_plonemeeting'
        success, response = self._sendHttpRequest(toolUrl)
        if not success:
            return (False, self.CONNECT_ERROR % (toolUrl, response))
        masterTool = self._unmarshall(response)
        meetings = []
        for configUrl in masterTool.meetingConfigs:
            # Gets the list of archived meetings in this meeting config.
            success, response = self._sendHttpRequest(configUrl)
            if not success:
                return (False, self.CONNECT_ERROR % (configUrl, response))
            masterConfig = self._unmarshall(response)
            configTitle = u'%s (%s)' % (masterConfig.id, masterConfig.title)
            for masterMeeting in masterConfig.availableMeetings:
                # Is this meeting already imported, or in a nightwork?
                status = 'to_import'
                if self.getParentNode().hasNightWork(\
                    meetingUrl=masterMeeting.url):
                    status = 'in_nightwork'
                elif self.portal_catalog(meta_type="Meeting",\
                                         id=masterMeeting.id):
                    status = 'already_imported'
                info = {'title': masterMeeting.title, 'url': masterMeeting.url,
                        'configTitle': configTitle, 'configUrl': configUrl,
                        'configId': masterConfig.id, 'status': status}
                meetings.append(info)
        return True, meetings

    security.declarePublic('listMeetingGroups')
    def listMeetingGroups(self):
        '''Gets the list of available meeting groups in a master site.'''
        toolUrl = self.getNotifyUrl() + '/portal_plonemeeting'
        success, response = self._sendHttpRequest(toolUrl)
        if not success:
            return (False, self.CONNECT_ERROR % (toolUrl, response))
        masterTool = self._unmarshall(response)
        res = []
        for mg in masterTool.meetingGroups:
            res.append( (mg.title, mg.id, mg.acronym, mg.active, mg.url) )
        return (True, res)

    security.declarePublic('importTool')
    def importTool(self):
        '''Synchronizes the local HS tool based on a distant tool.'''
        logger.info(self.IMPORTING_TOOL)
        toolUrl = self.getNotifyUrl() + '/portal_plonemeeting'
        success, response = self._sendHttpRequest(toolUrl)
        if not success: return self.CONNECT_ERROR % (toolUrl, response)
        masterTool = self._unmarshall(response)
        tool = self.getParentNode()
        for name, value in masterTool.__dict__.iteritems():
            if name in self.notBasicToolFields: continue
            try:
                exec 'tool.set%s%s(masterTool.%s)'% (name[0].upper(),
                                                     name[1:], name)
            except AttributeError:
                pass # Both sites may not have exactly the same data models.
        # Model adaptations may need to be performed after this change.
        performModelAdaptations(tool)
        registerClasses()
        res = self.TOOL_IMPORTED
        logger.info(res)
        return res

    security.declarePublic('importMeetingGroup')
    def importMeetingGroup(self, groupUrl=None):
        '''Imports in the tool the distant meeting group at p_groupUrl.'''
        if not groupUrl:
            groupUrl = self.REQUEST.get('groupUrl')
            calledFromPage = True
        else:
            calledFromPage = False
        logger.info(self.GROUP_IN_CREATION % groupUrl)
        success, response = self._sendHttpRequest(groupUrl)
        if not success:
            msg = self.CONNECT_ERROR % (groupUrl, response)
            if calledFromPage: return msg
            else: raise DistantSiteError(msg)
        masterGroup = self._unmarshall(response, classes=GroupDescriptor)
        for suffix in MEETING_GROUP_SUFFIXES: setattr(masterGroup, suffix, [])
        tool = self.portal_plonemeeting
        if not hasattr(tool.aq_base, masterGroup.id):
            tool.addUsersAndGroups([masterGroup])
            group = getattr(tool, masterGroup.id)
            group.adapted().onTransferred(self)
            group.reindexObject()
            res = self.GROUP_CREATED % masterGroup.title
        else:
            res = self.GROUP_ALREADY_IMPORTED % masterGroup.title
        logger.info(res)
        return res

    security.declarePublic('importMeetingGroups')
    def importMeetingGroups(self):
        '''Imports several groups at once.'''
        urls = self.REQUEST.get('masterUrls', None)
        res = ''
        if urls:
            try:
                for url in urls.split('|'):
                    if url:
                        res += self.importMeetingGroup(url) + '<br/>'
            except DistantSiteError, de:
                return str(de)
        return res

    security.declarePublic('importAnnex')
    def importAnnex(self, annexUrl, item, meetingConfig, decisionRelated=False):
        '''Imports the distant annex at p_annexUrl, creates it in p_item which
           is a folder and links it to it, too, through the reference field
           "annexes" or "annexesDecision", depending on p_decisionRelated.'''
        logger.info(self.ANNEX_IN_CREATION % annexUrl)
        success, response = self._sendHttpRequest(annexUrl)
        if not success:
            raise DistantSiteError(self.CONNECT_ERROR % (annexUrl, response))
        masterAnnex = self._unmarshall(response)
        # Determine file type
        fileTypeId = os.path.basename(masterAnnex.meetingFileType[0])
        fileType = getattr(meetingConfig.meetingfiletypes, fileTypeId, None)
        if not fileType:
            # Get the file type on-the-fly.
            fileType = self.importMeetingConfigSubObject(
                TOOL_FOLDER_FILE_TYPES, masterAnnex.meetingFileType[0],
                meetingConfig)
        # Create the meetingFile
        item.invokeFactory('MeetingFile', id=masterAnnex.id,
            file=masterAnnex.file.content, title=masterAnnex.title,
            meetingFileType=(fileType,))
        annex = getattr(item, masterAnnex.id)
        annex.setCreators(masterAnnex.creators)
        # Link the annex to the item
        if decisionRelated:
            annexes = item.getAnnexesDecision()
        else:
            annexes = item.getAnnexes()
        annexes.append(annex)
        if decisionRelated:
            item.setAnnexesDecision(annexes)
        else:
            item.setAnnexes(annexes)
        annex.creation_date = masterAnnex.creation_date
        annex.modification_date = masterAnnex.modification_date
        annex.pm_modification_date = masterAnnex.pm_modification_date
        annex.needsOcr = masterAnnex.needsOcr
        annex.ocrLanguage = masterAnnex.ocrLanguage
        adap = annex.adapted()
        adap.onEdit(isCreated=True)
        adap.onTransferred(self)
        annex.reindexObject()
        annex.modification_date = masterAnnex.modification_date
        logger.info(self.ANNEX_CREATED % annex.Title())

    security.declarePublic('getMemberFolder')
    def getMemberFolder(self, masterItem, meetingConfig):
        '''Gets the destination folder where to create the item imported from
           p_masterItem. We will try to create it if it does not exist. This
           folder will be created within the memberarea of the m_masterItem
           creator. If no such user exists, an error will be raised.'''
        history = getattr(masterItem, 'workflowHistory', None)
        if not history or not history[0].actor:
            raise DistantSiteError(self.CREATOR_UNKNOWN % masterItem.id)
        userId = masterItem.workflowHistory[0].actor
        if not self.acl_users.getUser(userId):
            raise DistantSiteError(self.FOLDER_CREATE_ERROR % userId)
        # Create the memberarea for this user if it does not exist
        if not hasattr(self.Members.aq_base, userId):
            try:
                self.portal_membership.createMemberArea(userId)
                memberArea = getattr(self.Members, userId)
                memberArea.manage_addLocalRoles(userId, ('Owner',))
                logger.info('Created member area for "%s"...' % userId)
            except Exception, e:
                raise DistantSiteError(
                    self.MEMBERAREA_CREATE_ERROR % (userId, str(e)))
        # Get (or create) the p_meetingConfig-related folder in this memberarea
        tool = self.getParentNode()
        return tool.getPloneMeetingFolder(meetingConfig.id, userId)

    security.declarePublic('importItem')
    def importItem(self, itemUrl, meetingConfig, destFolder=None,
                   meeting=None, isLate=False, toIgnore=()):
        '''Imports the p_meetingConfig-related distant item at p_itemUrl.

           The item will be created in p_destFolder if given; if not, we will
           try to import it in the memberarea of the item creator (retrieved
           from the workflow history). If this user does not exist, an error
           will be raised. (we can't create a memberarea for a non existing
           user).

           If p_meeting is given, the item will be linked to it (use this only
           when importing into an archive site. For all other purposes, insert
           this item into a meeting "the normal way", through method
           Meeting.insertItem). If p_meeting is given, you can also specify
           p_isLate, so we will know if we must link it as a normal or late
           item.

           Content of fields whose names are listed in p_toIgnore will not be
           copied into corresponding fields in the destination item.'''
        logger.info(self.ITEM_IN_CREATION % itemUrl)
        success, response = self._sendHttpRequest(itemUrl)
        if not success:
            raise DistantSiteError(self.CONNECT_ERROR % (itemUrl, response))
        masterItem = self._unmarshall(response)
        itemType = meetingConfig.getItemTypeName()
        # Make PloneMeeting aware of the current content type
        self.REQUEST.set('type_name', itemType)
        itemId = masterItem.id
        if not destFolder:
            destFolder = self.getMemberFolder(masterItem, meetingConfig)
        if hasattr(destFolder.aq_base, masterItem.id):
            # Some item IDS may be the same because they are stored in several
            # home folders in the master site.
            itemId = 'item%f' % time.time()
        try:
            itemId = destFolder.invokeFactory(itemType, itemId)
        except Unauthorized:
            user = self.portal_membership.getAuthenticatedMember()
            destFolder.manage_addLocalRoles(user.id, ('Owner',))
            itemId = destFolder.invokeFactory(itemType, itemId)
            destFolder.manage_delLocalRoles([user.id])
        item = getattr(destFolder, itemId)
        # Set item attributes.
        # Resolve reference to the classifier
        if masterItem.classifier and ('classifier' not in toIgnore):
            cFolder = getattr(meetingConfig, TOOL_FOLDER_CLASSIFIERS)
            classifier = getattr(cFolder, masterItem.classifier, None)
            if not classifier:
                # Get the classifier on-the-fly
                classifierUrl = '%s/portal_plonemeeting/%s/%s/%s' % (
                    self.getNotifyUrl(), meetingConfig.id,
                    TOOL_FOLDER_CLASSIFIERS, masterItem.classifier)
                self.importMeetingConfigSubObject(
                    TOOL_FOLDER_CLASSIFIERS, classifierUrl, meetingConfig)
                classifier = getattr(cFolder, masterItem.classifier)
            item.setClassifier(classifier)
        # Download MeetingGroups if needed
        neededGroups = [masterItem.proposingGroup] + masterItem.associatedGroups
        if meetingConfig.getUseGroupsAsCategories() and masterItem.category:
            neededGroups.append(masterItem.category)
        neededGroups = set(neededGroups)
        tool = meetingConfig.getParentNode()
        for groupId in neededGroups:
            if not hasattr(tool, groupId):
                # I need to retrieve this group
                groupUrl = '%s/portal_plonemeeting/%s' % (self.getNotifyUrl(),
                    groupId)
                self.importMeetingGroup(groupUrl)
        # Download categories if needed
        if not meetingConfig.getUseGroupsAsCategories() and \
           masterItem.category and ('category' not in toIgnore):
            category = getattr(meetingConfig.categories.aq_base,
                               masterItem.category, None)
            if not category:
                categoryUrl = '%s/portal_plonemeeting/%s/%s/%s' % (
                    self.getNotifyUrl(), meetingConfig.id,
                    TOOL_FOLDER_CATEGORIES, masterItem.category)
                self.importMeetingConfigSubObject(
                    TOOL_FOLDER_CATEGORIES, categoryUrl, meetingConfig)
        # Download meeting users if needed
        meetingUserIds = set()
        if 'itemSignatories' not in toIgnore:
            for mu in masterItem.itemSignatories: meetingUserIds.add(mu)
        if 'itemAbsents' not in toIgnore:
            for mu in masterItem.itemAbsents: meetingUserIds.add(mu)
        existingIds = meetingConfig.meetingusers.objectIds()
        for mu in meetingUserIds:
            if mu not in existingIds:
                # Import this meeting user on-the-fly
                muUrl = '%s/portal_plonemeeting/%s/%s/%s' % (
                    self.getNotifyUrl(), meetingConfig.id,
                    TOOL_FOLDER_MEETING_USERS, mu)
                self.importMeetingConfigSubObject(
                    TOOL_FOLDER_MEETING_USERS, muUrl, meetingConfig)
        # Set "basic" item attributes
        for name, value in masterItem.__dict__.iteritems():
            if (name in self.notBasicItemFields) or (name in toIgnore): continue
            try:
                exec 'item.set%s%s(masterItem.%s)'% (name[0].upper(),
                                                     name[1:], name)
            except AttributeError:
                pass # Both sites may not have exactly the same data models.
        item.at_post_create_script()
        # Set votes
        if 'votes' not in toIgnore:
            for vote in masterItem.votes:
                item.votes[vote.voter] = vote.voteValue
        # Import the frozen documents linked to this item, if any
        if 'frozenDocuments' not in toIgnore:
            for frozenDoc in masterItem.frozenDocuments:
                docId = '%s_%s.%s' % (
                    item.id, frozenDoc.templateId, frozenDoc.templateFormat)
                # We reconstitute the ID here because the item ID may not be the
                # same as the one from the corresponding item on the master site
                destFolder.invokeFactory('File', id=docId,
                    file=frozenDoc.data.content)
                doc = getattr(destFolder, docId)
                doc.setFormat(frozenDoc.data.mimeType)
                if hasattr(frozenDoc, 'title') and frozenDoc.title:
                    doc.setTitle(frozenDoc.title)
                else:
                    doc.setTitle('Doc')
                clonePermissions(item, doc)
        # Retrieve the workflow history, and add a last "virtual" transition
        # representing the transfer from one site to another.
        history = [event.__dict__ for event in masterItem.workflowHistory]
        # The new item state will be the initial state of the item workflow on
        # the destination site.
        wf = getattr(self.portal_workflow, meetingConfig.getItemWorkflow())
        history.append({'action': u'transfer', 'actor': u'admin',
            'comments':'', 'review_state': wf.initial_state, 'time':DateTime()})
        item.workflow_history = PersistentMapping()
        item.workflow_history['meetingitem_workflow'] = tuple(history)
        # Link the item to the meeting
        if meeting:
            if isLate:
                lateItems = meeting.getLateItems()
                lateItems.append(item)
                meeting.setLateItems(lateItems)
            else:
                items = meeting.getItems()
                items.append(item)
                meeting.setItems(items)
        # Add annexes
        if 'annexes' not in toIgnore:
            for annexUrl in masterItem.annexes:
                self.importAnnex(annexUrl, item, meetingConfig)
            for annexUrl in masterItem.annexesDecision:
                self.importAnnex(annexUrl, item, meetingConfig,
                                 decisionRelated=True)
            item.updateAnnexIndex()
        # Add advices
        if 'advices' not in toIgnore:
            for advice in masterItem.advices:
                item.advices[advice.id] = d = PersistentMapping()
                d['id'] = advice.id
                d['name'] = advice.name
                d['type'] = advice.type[1]
                d['optional'] = advice.optional
                d['comment'] = getattr(advice, 'comment', '')
                d['actor'] = getattr(advice, 'actor', None)
                d['date'] = getattr(advice, 'date', None)
        # Update dates and creators
        item.setCreators(masterItem.creators)
        item.creation_date = masterItem.creation_date
        item.modification_date = masterItem.modification_date
        item.pm_modification_date = masterItem.pm_modification_date
        item.adapted().onTransferred(self)
        item.reindexObject()
        item.modification_date = masterItem.modification_date
        logger.info(self.ITEM_CREATED % item.Title())
        return item, masterItem

    security.declarePublic('importMeetingConfigSubObject')
    def importMeetingConfigSubObject(self, objectType, objectUrl,
        meetingConfig=None, unmarshallOnly=False):
        '''Imports a distant sub-object of type p_objectType at p_objectUrl.
           If unmarshallOnly is True, is simply creates and returns a
           *Descriptor instance unmarshalled from the distant site. Else,
           it also creates the corresponding object in the meeting config.
           p_unmarshallOnly=False occurs when we need to import several objects:
           we do not create them directly but we store unmarshalled instances in
           lists that are defined on a MeetingConfigDescriptor that, in a later
           step, will do the whole job of creating all the corresponding
           sub-objects. p_meetingConfig is necessary only if p_unmarshallonly
           is False.'''
        logger.info(self.SUBOBJECT_IN_CREATION % objectUrl)
        success, response = self._sendHttpRequest(objectUrl)
        if not success:
            raise DistantSiteError(self.CONNECT_ERROR % (objectUrl, response))
        typeInfo = MeetingConfig.subFoldersInfo[objectType]
        exec 'klass = %s' % typeInfo[3]
        masterObject = self._unmarshall(response, classes=klass)
        logger.info(self.SUBOBJECT_CREATED % masterObject.title)
        if unmarshallOnly:
            return masterObject
        else:
            # Create the corresponding object.
            res = None
            if objectType == TOOL_FOLDER_CATEGORIES:
                res = meetingConfig.addCategory(masterObject, True)
            elif objectType == TOOL_FOLDER_CLASSIFIERS:
                res = meetingConfig.addCategory(masterObject, False)
            elif objectType == TOOL_FOLDER_FILE_TYPES:
                res = meetingConfig.addFileType(masterObject, self)
            elif objectType == TOOL_FOLDER_POD_TEMPLATES:
                res = meetingConfig.addPodTemplate(masterObject, self)
            elif objectType == TOOL_FOLDER_MEETING_USERS:
                res = meetingConfig.addMeetingUser(masterObject, self)
            if res:
                res.adapted().onTransferred(self)
                res.reindexObject()
                return res

    security.declarePublic('updateMeetingConfig')
    def updateMeetingConfig(self, configUrl, meetingConfig):
        '''The distant meeting config at p_configUrl already exists; we check
           here if sub-objects have been added, and we import them if it is the
           case.'''
        # Get the distant meeting config
        logger.info(self.MEETING_CONFIG_IN_CREATION % configUrl)
        success, response = self._sendHttpRequest(configUrl)
        if not success:
            raise DistantSiteError(self.CONNECT_ERROR % (configUrl, response))
        masterConfig= self._unmarshall(response,classes=MeetingConfigDescriptor)
        # Import additional sub-objects if any
        for folderName, fInfo in MeetingConfig.subFoldersInfo.iteritems():
            if fInfo[2]:
                folder = getattr(meetingConfig, folderName)
                for objectUrl in getattr(masterConfig, folderName):
                    objectId = os.path.basename(objectUrl)
                    if not hasattr(folder.aq_base, objectId):
                        # Import the new object
                        self.importMeetingConfigSubObject(folderName, objectUrl,
                            meetingConfig)

    security.declarePublic('importMeetingConfigSubObject')
    def importMeetingConfig(self, configUrl):
        '''Imports into this site the distant meeting configuration at
           p_configUrl and returns the created meetingConfig.'''
        # Get the distant meeting config
        logger.info(self.MEETING_CONFIG_IN_CREATION % configUrl)
        success, response = self._sendHttpRequest(configUrl)
        if not success:
            raise DistantSiteError(self.CONNECT_ERROR % (configUrl, response))
        masterConfig= self._unmarshall(response,classes=MeetingConfigDescriptor)
        # Get the sub-objects within this meeting config. Currently, I have
        # only retrieved the URLs to the sub-objects in masterConfig.
        for folderName, fInfo in MeetingConfig.subFoldersInfo.iteritems():
            if fInfo[2]:
                objectsList = []
                for objectUrl in getattr(masterConfig, folderName):
                    masterObject = self.importMeetingConfigSubObject(
                        folderName, objectUrl, unmarshallOnly=True)
                    objectsList.append(masterObject)
                exec 'masterConfig.%s = objectsList' % fInfo[2]
        masterConfig.recurringItems = []
        # Because we are on an "archive" site, I will use the standard workflows
        # with "archiving" adaptation.
        masterConfig.itemWorkflow = 'meetingitem_workflow'
        masterConfig.meetingWorkflow = 'meeting_workflow'
        masterConfig.workflowAdaptations = ['archiving']
        masterConfig.meetingAppDefaultView = 'topic_searchalldecisions'
        masterConfig.itemTopicStates = ('itemarchived',)
        masterConfig.meetingTopicStates = ()
        masterConfig.decisionTopicStates = ('archived',)
        res = self.portal_plonemeeting.createMeetingConfig(masterConfig, self)
        res.adapted().onTransferred(self)
        logger.info(self.MEETING_CONFIG_CREATED % masterConfig.id)
        return res

    security.declarePublic('importMeetingGroup')
    def importMeeting(self, meetingUrl, configUrl, configId, raiseError=False):
        '''Perform the meeting import.'''
        logger.info(self.MEETING_IN_CREATION % meetingUrl)
        rq = self.REQUEST
        destFolder = None # Where the meeting will be created
        try:
            # If the corresponding meeting config does not exist on this site, I
            # must create it first.
            tool = self.getParentNode()
            configIds = [c.id for c in tool.objectValues('MeetingConfig')]
            if configId not in configIds:
                meetingConfig = self.importMeetingConfig(configUrl)
            else:
                meetingConfig = getattr(tool, configId)
                self.updateMeetingConfig(configUrl, meetingConfig)
            # Import the meeting in itself.
            success, response = self._sendHttpRequest(meetingUrl)
            if not success:
                raise DistantSiteError(
                    self.CONNECT_ERROR % (meetingUrl, response))
            masterMeeting = self._unmarshall(response)
            meetingType = meetingConfig.getMeetingTypeName()
            # Make PloneMeeting aware of the current meeting type
            rq.set('type_name', meetingType)
            # If user "pmManager" does not exist, I will create it. Indeed,
            # I need a MeetingManager for storing meetings in its config folder.
            if not self.portal_membership.getMemberById('pmManager'):
                # Create the MeetingManager
                self.portal_registration.addMember('pmManager', 'meeting',
                    ['Member', 'MeetingManager', 'MeetingObserverGlobal'],
                    properties={'username': 'pmManager',
                        'fullname':'Archive user', 'email':'you@plonegov.org'})
                res = self.MEETING_AND_USER_CREATED % masterMeeting.title
            else:
                res = self.MEETING_CREATED % masterMeeting.title
            # I will store meetings and items in the home folder of pmManager
            # (one folder for every meeting + included items).
            portal = self.portal_url.getPortalObject()
            if not hasattr(portal.Members, 'pmManager'):
                portal.portal_membership.createMemberArea('pmManager')
            configFolder = tool.getPloneMeetingFolder(
                meetingConfig.id, 'pmManager')
            if hasattr(configFolder, masterMeeting.id):
                return self.MEETING_ALREADY_IMPORTED % masterMeeting.title
            configFolder.invokeFactory(
                'Folder', masterMeeting.id, title=masterMeeting.title)
            destFolder = getattr(configFolder, masterMeeting.id)
            allowManagerToCreateIn(destFolder)
            meetingId = destFolder.invokeFactory(meetingType, masterMeeting.id)
            meeting = getattr(destFolder, meetingId)
            # Create meeting users if needed
            meetingUserIds = set()
            for mu in masterMeeting.signatories: meetingUserIds.add(mu)
            for mu in masterMeeting.attendees:   meetingUserIds.add(mu)
            for mu in masterMeeting.absents:     meetingUserIds.add(mu)
            for mu in masterMeeting.excused:     meetingUserIds.add(mu)
            existingIds = meetingConfig.meetingusers.objectIds()
            for mu in meetingUserIds:
                if mu not in existingIds:
                    # Import this meeting user on-the-fly
                    muUrl = '%s/meetingusers/%s' % (configUrl, mu)
                    self.importMeetingConfigSubObject(
                        TOOL_FOLDER_MEETING_USERS, muUrl, meetingConfig)
            # Update meeting data
            for fieldName, fieldValue in masterMeeting.__dict__.iteritems():
                if fieldName not in self.notBasicMeetingFields:
                    exec 'meeting.set%s%s(masterMeeting.%s)' % (
                        fieldName[0].upper(), fieldName[1:], fieldName)
            # Import the frozen documents linked to this meeting, if any
            for frozenDoc in masterMeeting.frozenDocuments:
                destFolder.invokeFactory('File', id=frozenDoc.id,
                    file=frozenDoc.data.content)
                doc = getattr(destFolder, frozenDoc.id)
                doc.setTitle(frozenDoc.title)
                doc.setFormat(frozenDoc.data.mimeType)
                clonePermissions(meeting, doc)
            # Get dicts "entrances" and "departures" if present
            if hasattr(masterMeeting, 'entrances'):
                meeting.entrances = PersistentMapping(masterMeeting.entrances)
            if hasattr(masterMeeting, 'departures'):
                meeting.departures = PersistentMapping(masterMeeting.departures)
            # Retrieve the workflow history and add a last "virtual" transition
            # representing the transfer from one site to another.
            history = [e.__dict__ for e in masterMeeting.workflowHistory]
            history.append({'action': u'transfer', 'actor': u'admin',
                'comments': '', 'review_state': u'archived', 'time':DateTime()})
            meeting.workflow_history = PersistentMapping()
            meeting.workflow_history['meeting_workflow'] = tuple(history)
            # Import the items included in this meeting, into the same folder as
            # the meeting itself.
            for itemUrl in masterMeeting.items:
                self.importItem(itemUrl, meetingConfig, destFolder, meeting)
            for itemUrl in masterMeeting.lateItems:
                self.importItem(itemUrl, meetingConfig, destFolder, meeting,
                                isLate=True)
            meeting.creation_date = masterMeeting.creation_date
            meeting.modification_date = masterMeeting.modification_date
            adap = meeting.adapted()
            adap.onEdit(isCreated=True)
            adap.onTransferred(self)
            meeting.reindexObject()
            meeting.modification_date = masterMeeting.modification_date
            disallowManagerToCreateIn(destFolder)
            logger.info(res)
        except DistantSiteError, de:
            res = str(de)
            logger.info(res)
            # Delete the folder where the incomplete meeting was created, if it
            # was created.
            if destFolder:
                # First, remove folder content.
                if destFolder.objectIds():
                    for elem in destFolder.objectValues():
                        if elem.meta_type == 'Meeting':
                            for item in elem.getItems():
                                elem.removeGivenObject(item)
                            for item in elem.getLateItems():
                                elem.removeGivenObject(item)
                        destFolder.removeGivenObject(elem)
                # Then, remove the folder.
                destFolder.getParentNode().removeGivenObject(destFolder)
            if raiseError: raise de
        return res

    security.declarePublic('importArchivedMeeting')
    def importArchivedMeeting(self, meetingUrl=None, configUrl=None,
                              configId=None):
        '''Imports a meeting from a master Plone site. The WebDAV URL of the
           meeting is in the request or in p_meetingUrl.'''
        rq = self.REQUEST
        # Get params from the request
        if not meetingUrl: meetingUrl = rq.get('meetingUrl')
        if not configUrl: configUrl = rq.get('configUrl')
        if not configId: configId = rq.get('configId')
        if self.getDeferredMeetingImport():
            # Don't do it now: add a night work.
            action = 'portal_plonemeeting.%s.importMeeting' % self.getId()
            params = {'meetingUrl':meetingUrl, 'configUrl':configUrl,
                      'configId':configId, 'raiseError': True}
            self.getParentNode().addNightWork(action, 'method', params)
            return self.MEETING_NIGHTWORKED % meetingUrl
        else:
            return self.importMeeting(meetingUrl, configUrl, configId)

    security.declarePublic('importArchivedMeetings')
    def importArchivedMeetings(self):
        '''Imports several meetings at once.'''
        urls = self.REQUEST.get('masterUrls', None)
        res = ''
        if urls:
            for url in urls.split('|'):
                if url:
                    res += self.importArchivedMeeting(url) + '<br/>'
        return res

    security.declarePublic('importUsers')
    def importUsers(self):
        '''Synchronises users with the master site. Every imported user is put
           in a group of people getting role "MeetingObserverGlobal". This group
           is created if it does not exist yet. Every user that does not exist
           on the master site is removed from this site.'''
        logger.info(self.IMPORTING_USERS)
        # Get the users from the master site
        rq = self.REQUEST
        url = self.getNotifyUrl() + '/portal_plonemeeting?do=getPloneUsers'
        success, response = self._sendHttpRequest(url)
        if not success:
            raise DistantSiteError(self.CONNECT_ERROR % (url, response))
        users = self._unmarshall(response)
        # Before importing users, create the 'observers' group if it does not
        # exist.
        groupsDb = self.portal_groups
        groupId = 'observers'
        obsGroup = groupsDb.getGroupById(groupId)
        if not obsGroup:
            groupsDb.addGroup(groupId, title='Archive users')
            groupsDb.setRolesForGroup(groupId, ('MeetingObserverGlobal',))
            logger.info('Group "%s" was created.' % groupId)
        # Add users and update existing ones
        usersDb = self.acl_users.source_users
        propsDb = self.acl_users.mutable_properties
        addedCount = 0
        updatedCount = 0
        masterUserIds = {}
        for mUser in users:
            # Try to find the corresponding user here
            userId = str(mUser.id) # Convert unicode to string
            masterUserIds[userId] = None # We will need this dict afterwards
            localUser = usersDb.getUserById(userId)
            isAdded = False
            if not localUser:
                # We must create the user. We grant him the basic 'Member' role,
                # excepted if it is the special user 'pmManager' that requires
                # to be 'MeetingManager'.
                roles = ['Member']
                if userId == 'pmManager': roles.append('MeetingManager')
                self.acl_users._doAddUser(userId, userId, roles, '')
                localUser = usersDb.getUserById(userId)
                # Set properties for user
                allProps = localUser.getOrderedPropertySheets()[0]._properties
                newProps = {'username': userId, 'email': userId+'@hs.com',
                            'fullname': mUser.name}
                for k,v in newProps.iteritems(): allProps[k] = v
                propsDb._storage[userId] = allProps
                addedCount += 1
                isAdded = True
                # Add this new user to group "observers"
                self.portal_groups.addPrincipalToGroup(userId, groupId)
            # Synchronise name
            newName = mUser.name.encode('utf-8')
            if localUser.getProperty('fullname') != newName:
                propsDb._storage[userId]['fullname'] = newName
                propsDb._storage[userId] = propsDb._storage[userId]
                if not isAdded: updatedCount += 1
            # Synchronise password
            newPassword = str(mUser.password)
            if usersDb._user_passwords[userId] != newPassword:
                usersDb._user_passwords[userId] = newPassword
                if not isAdded: updatedCount += 1
        # Remove users that do not exist anymore
        usersCount = 0
        deletedCount = 0
        toDelete = []
        for userId in usersDb.getUserIds():
            usersCount += 1
            if userId == 'pmManager': continue # Never delete this one.
            if userId not in masterUserIds:
                # We must delete this one
                toDelete.append(userId)
                usersCount -= 1
                deletedCount += 1
        for userId in toDelete:
            self.acl_users._doDelUser(userId)
            logger.info('User "%s" was deleted because inexistent on ' \
                        'master site.' % userId)
        res = self.USERS_IMPORTED % (addedCount, deletedCount, \
                                     updatedCount, usersCount)
        logger.info(res)
        return res

    security.declarePrivate('_getExportName')
    def getExportName(self, elem, type):
        '''Gets the name of the folder or file (filesystem or webdav, depending
           on p_type) where to dump p_elem, which can be a meeting, an item or
           an annex.'''
        if elem.meta_type == 'Meeting':
            return elem.getDate().strftime('%Y_%m_%d_Meeting')
        elif elem.meta_type == 'MeetingItem':
            return '%d_%s' % (elem.getItemNumber(relativeTo='meeting'), elem.id)
        else:
            return elem.id

    security.declarePrivate('getBaseExportFolder')
    def getBaseExportFolder(self):
        '''Gets the local or distant folder where we will export the meeting.'''
        # Identify the export type
        type = None
        url = self.getNotifyUrl()
        if   url.startswith('http://'): type = 'dav'
        elif url.startswith('file://'): type = 'fs'
        if not type:
            raise DistantSiteError("Don\t know how to export to this " \
                                   "kind of resource.")
        # Connect to the base folder where we will export
        if type == 'dav':
            res = Resource(self.getNotifyUrl(), username=self.getNotifyLogin(),
                           password=self.getNotifyPassword())
        elif type == 'fs':
            # The base folder must exist.
            folderName = url[7:]
            if not os.path.isdir(folderName):
                raise DistantSiteError('Folder "%s" does not exist. Please ' \
                                       'create it first.' % folderName)
            res = folderName
        return res, type

    security.declarePrivate('exportFolder')
    def exportFolder(self, folder, element, type):
        '''Creates in some p_folder a sub-folder where to dump p_element
           (a meeting, an item,...).'''
        subFolder = self.getExportName(element, type)
        if type == 'dav':
            folder.mkdir(subFolder)
            # Swith the WebDAV resource to this folder
            folder.uri += '/%s' % subFolder
            subFolder = folder
        elif type == 'fs':
            # The sub-folder where to put the meeting is created or overwritten.
            subFolder = os.path.join(folder, subFolder)
            if os.path.exists(subFolder):
                FolderDeleter.delete(subFolder)
                logger.info('Existing folder "%s" has been overwritten.' % \
                            subFolder)
            try:
                os.mkdir(subFolder)
            except OSError, oe:
                if oe.errno == 36: # File name is too long
                    subFolder = subFolder[:255]
                    os.mkdir(subFolder)
        logger.info('Created folder "%s".' % subFolder)
        return subFolder

    security.declarePrivate('exportFile')
    def exportFile(self, folder, zopeFile, type):
        '''Exports a p_zopeFile into the p_folder.'''
        rawZopeFile = zopeFile.getRawFile()
        fileName = self.getExportName(zopeFile, type)
        if type == 'dav':
            folder.add(rawZopeFile, type='zope', name=fileName)
        elif type == 'fs':
            fileName = os.path.join(folder, fileName)
            f = open(fileName, 'wb')
            copyData(rawZopeFile, f, 'write', type='zope')
            f.close()
        logger.info('Added document "%s".' % fileName)

    security.declarePublic('exportArchivedMeeting')
    def exportArchivedMeeting(self):
        '''Exports, either via WebDAV or on the file system, the meeting whose
           UID is in the request.'''
        # Retrieve the meeting
        meetingUid = self.REQUEST.get('meetingUid')
        meeting = self.uid_catalog(UID=meetingUid)[0].getObject()
        # Get the local or distant folder where to export
        try:
            baseFolder, type = self.getBaseExportFolder()
        except DistantSiteError, dse:
            return str(dse)
        # Get the sub-folder where to export the meeting.
        meetingFolder = self.exportFolder(baseFolder, meeting, type)
        # Put in the meeting folder all frozen documents
        for frozenDoc in meeting.getFrozenDocuments():
            self.exportFile(meetingFolder, frozenDoc, type)
        # Create one sub-folder per item and copy annexes into it
        for item in meeting.getAllItems(ordered=True):
            itemFolder = self.exportFolder(meetingFolder, item, type)
            for annexType in (False, True):
                annexes = item.getAnnexesByType(decisionRelated=annexType,
                                           makeSubLists=False, realAnnexes=True)
                for annex in annexes:
                    self.exportFile(itemFolder, annex, type)
            if type == 'dav':
                itemFolder.uri = os.path.dirname(itemFolder.uri)
        return '"%s" has been successfully exported.' % meeting.Title()

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self): self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self): self.adapted().onEdit(isCreated=False)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'ExternalApplication': return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self): return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''



registerType(ExternalApplication, PROJECTNAME)
# end of class ExternalApplication

##code-section module-footer #fill in your manual code here
def sendNotificationsIfRelevant(object, event):
    '''This method is called every time a transition is fired; it sends
       notifications to external applications that require it.'''
    tool = object.portal_plonemeeting
    for extApp in tool.getActiveExternalApplications(usage='notify'):
        if event in extApp.getNotifyEvents():
            extApp.notifyExternalApplication(object, event)
##/code-section module-footer

