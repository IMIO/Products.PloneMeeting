# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 by PloneGov
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

import os
import os.path
import re
import urlparse
import socket
from appy.shared.diff import HtmlDiff
from datetime import timedelta
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
from DateTime import DateTime
from AccessControl import getSecurityManager
from zope.i18n import translate
from zope.component.interfaces import ObjectEvent
from zope.interface import implements
from imio.helpers.xhtml import removeBlanks, xhtmlContentIsEmpty
from Products.CMFCore.utils import getToolByName
from Products.MailHost.MailHost import MailHostError
from Products.CMFCore.permissions import View, AccessContentsInformation, ModifyPortalContent, DeleteObjects
from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.config import TOOL_ID
from Products.PloneMeeting.interfaces import IMeetingItemCustom, IMeetingCustom, IMeetingCategoryCustom, \
    IMeetingConfigCustom, IMeetingFileCustom, IMeetingFileTypeCustom, IMeetingGroupCustom, IPodTemplateCustom, \
    IToolPloneMeetingCustom, IMeetingUserCustom, IAnnexable, \
    IAdvicesUpdatedEvent, IItemDuplicatedEvent, IItemDuplicatedFromConfigEvent
import logging
logger = logging.getLogger('PloneMeeting')

KEEP_WITH_NEXT_STYLES = {'para': 'pmParaKeepWithNext',
                         'item': 'podItemKeepWithNext'}

# PloneMeetingError-related constants ------------------------------------------
WRONG_INTERFACE_NAME = 'Wrong interface name "%s". You must specify the full ' \
                       'interface package name.'
WRONG_INTERFACE_PACKAGE = 'Could not find package "%s".'
WRONG_INTERFACE = 'Interface "%s" not found in package "%s".'

# ------------------------------------------------------------------------------
monthsIds = {1:  'month_jan', 2:  'month_feb', 3:  'month_mar', 4:  'month_apr',
             5:  'month_may', 6:  'month_jun', 7:  'month_jul', 8:  'month_aug',
             9:  'month_sep', 10: 'month_oct', 11: 'month_nov', 12: 'month_dec'}

weekdaysIds = {0: 'weekday_sun', 1: 'weekday_mon', 2: 'weekday_tue',
               3: 'weekday_wed', 4: 'weekday_thu', 5: 'weekday_fri',
               6: 'weekday_sat'}

adaptables = {
    'MeetingItem': {'method': 'getItem', 'interface': IMeetingItemCustom},
    'Meeting': {'method': 'getMeeting', 'interface': IMeetingCustom},
    # No (condition or action) workflow-related adapters are defined for the
    # following content types; only a Custom adapter.
    'MeetingCategory': {'method': None, 'interface': IMeetingCategoryCustom},
    'MeetingConfig': {'method': None, 'interface': IMeetingConfigCustom},
    'MeetingFile': {'method': None, 'interface': IMeetingFileCustom},
    'MeetingFileType': {'method': None, 'interface': IMeetingFileTypeCustom},
    'MeetingGroup': {'method': None, 'interface': IMeetingGroupCustom},
    'PodTemplate': {'method': None, 'interface': IPodTemplateCustom},
    'ToolPloneMeeting': {'method': None, 'interface': IToolPloneMeetingCustom},
    'MeetingUser': {'method': None, 'interface': IMeetingUserCustom},
}


def getInterface(interfaceName):
    '''Gets the interface named p_interfaceName.'''
    elems = interfaceName.split('.')
    if len(elems) < 2:
        raise PloneMeetingError(WRONG_INTERFACE_NAME % interfaceName)
    interfaceName = elems[len(elems)-1]
    packageName = ''
    for elem in elems[:-1]:
        if not packageName:
            point = ''
        else:
            point = '.'
        packageName += '%s%s' % (point, elem)
    try:
        res = None
        exec 'import %s' % packageName
        exec 'res = %s.%s' % (packageName, interfaceName)
        return res
    except ImportError:
        raise PloneMeetingError(WRONG_INTERFACE_PACKAGE % packageName)
    except AttributeError:
        raise PloneMeetingError(WRONG_INTERFACE % (interfaceName, packageName))


def getWorkflowAdapter(obj, conditions):
    '''Gets the adapter, for a PloneMeeting object that proposes methods that
       may be used as workflow conditions (if p_conditions is True) or actions
       (if p_condition is False).'''
    tool = getToolByName(obj, TOOL_ID)
    meetingConfig = tool.getMeetingConfig(obj)
    interfaceMethod = adaptables[obj.meta_type]['method']
    if conditions:
        interfaceMethod += 'Conditions'
    else:
        interfaceMethod += 'Actions'
    interfaceLongName = None
    exec 'interfaceLongName = meetingConfig.%sInterface()' % interfaceMethod
    return getInterface(interfaceLongName)(obj)


def getCustomAdapter(obj):
    '''Tries to get the custom adapter for a PloneMeeting object. If no adapter
       is defined, returns the object.'''
    res = obj
    theInterface = adaptables[obj.meta_type]['interface']
    try:
        res = theInterface(obj)
    except TypeError:
        pass
    return res

methodTypes = ('FSPythonScript', 'FSControllerPythonScript', 'instancemethod')


def getCurrentMeetingObject(context):
    '''What is the object currently published by Plone ?'''
    obj = context.REQUEST.get('PUBLISHED')
    className = obj.__class__.__name__
    if not (className in ('Meeting', 'MeetingItem')):
        # check if we are on a Script or so or calling a BrowserView
        if className in methodTypes or 'SimpleViewClass' in className:
            # We are changing the state of an element. We must then check the
            # referer
            refererUrl = context.REQUEST.get('HTTP_REFERER')
            referer = urlparse.urlparse(refererUrl)[2]
            if referer.endswith('/view') or \
               referer.endswith('/edit') or \
               referer.endswith('/search_form') or \
               referer.endswith('/plonemeeting_topic_view'):
                referer = os.path.dirname(referer)
            # We add the portal path if necessary
            # (in case Apache rewrites the uri for example)
            portal_path = context.portal_url.getPortalPath()
            if not referer.startswith(portal_path):
                # The rewrite rule has modified the URL. First, remove any
                # added URL prefix.
                if referer.find('/Members/') != -1:
                    referer = referer[referer.index('/Members/'):]
                # Then, add the real portal as URL prefix.
                referer = portal_path + referer
            res = context.portal_catalog(path=referer)
            if res:
                obj = res[0].getObject()
        else:
            # Check the parent (if it has sense)
            if hasattr(obj, 'getParentNode'):
                obj = obj.getParentNode()
                if not (obj.__class__.__name__ in ('Meeting', 'MeetingItem')):
                    obj = None
            else:
                # It can be a method with attribute im_class
                obj = None
    if obj and not obj.meta_type == 'Meeting':
        obj = None
    return obj


def fieldIsEmpty(name, obj, useParamValue=False, value=None):
    '''If field named p_name on p_obj empty ? The method checks emptyness of
       given p_value if p_useParamValue is True instead.'''
    field = obj.getField(name)
    if useParamValue:
        value = value
    else:
        value = field.get(obj)
    widgetName = field.widget.getName()
    if widgetName == 'RichWidget':
        return xhtmlContentIsEmpty(value)
    elif widgetName == 'BooleanWidget':
        return value is None
    else:
        return not value


def checkPermission(permission, obj):
    '''We must call getSecurityManager() each time we need to check a
       permission.'''
    sm = getSecurityManager()
    return sm.checkPermission(permission, obj)


# Mail sending machinery -------------------------------------------------------
class EmailError(Exception):
    pass
SENDMAIL_ERROR = 'Error while sending mail: %s.'
ENCODING_ERROR = 'Encoding error while sending mail: %s.'
MAILHOST_ERROR = 'Error with the MailServer while sending mail: %s.'


def _getEmailAddress(name, email, encoding='utf-8'):
    '''Creates a full email address from a p_name and p_email.'''
    res = email
    if name:
        res = name.decode(encoding) + ' <%s>' % email
    return res.encode(encoding)


def _sendMail(obj, body, recipients, fromAddress, subject, format,
              attachments=None):
    '''Sends a mail. p_mto can be a single email or a list of emails.'''
    # Hide the whole list of recipients if we must send the mail to many.
    bcc = None
    if not isinstance(recipients, basestring):
        bcc = recipients
        recipients = fromAddress
    # Construct the data structures for the attachments if relevant
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body))
        body = msg
        for fileName, fileContent in attachments:
            part = MIMEBase('application', 'octet-stream')
            if hasattr(fileContent, 'data'):
                # It is a File instance coming from the DB (frozen doc)
                payLoad = ''
                data = fileContent.data
                while data is not None:
                    payLoad += data.data
                    data = data.next
            else:
                payLoad = fileContent
            part.set_payload(payLoad)
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % fileName)
            body.attach(part)
    try:
        obj.MailHost.secureSend(body, recipients, fromAddress, subject, mbcc=bcc,
                                subtype=format, charset='utf-8')
    except socket.error, sg:
        raise EmailError(SENDMAIL_ERROR % str(sg))
    except UnicodeDecodeError, ue:
        raise EmailError(ENCODING_ERROR % str(ue))
    except MailHostError, mhe:
        raise EmailError(MAILHOST_ERROR % str(mhe))
    except Exception, e:
        raise EmailError(SENDMAIL_ERROR % str(e))


def sendMail(recipients, obj, event, attachments=None, mapping={}):
    '''Sends a mail related to p_event that occurred on p_obj to
       p_recipients. If p_recipients is None, the mail is sent to
       the system administrator.'''
    # Do not sent any mail if mail mode is "deactivated".
    tool = obj.portal_plonemeeting
    cfg = tool.getMeetingConfig(obj) or tool.getActiveConfigs()[0]
    mailMode = cfg.getMailMode()
    if mailMode == 'deactivated':
        return
    enc = obj.portal_properties.site_properties.getProperty('default_charset')
    # Compute user name
    pms = obj.portal_membership
    userName = pms.getAuthenticatedMember().id
    userInfo = pms.getMemberById(userName)
    if userInfo.getProperty('fullname'):
        userName = userInfo.getProperty('fullname').decode(enc)
    # Compute list of MeetingGroups for this user
    userGroups = ', '.join([g.Title() for g in tool.getGroupsForUser()])
    # Create the message parts
    d = 'PloneMeeting'
    portal = obj.portal_url.getPortalObject()
    portalUrl = tool.getPublicUrl().strip()
    if not portalUrl:
        portalUrl = portal.absolute_url()
    if mapping:
        # we need every mappings to be unicode
        for elt in mapping:
            if not isinstance(mapping[elt], unicode):
                mapping[elt] = unicode(mapping[elt], enc)
        translationMapping = mapping
    else:
        translationMapping = {}
    translationMapping.update({
        'portalUrl': portalUrl, 'portalTitle': portal.Title().decode(enc),
        'objectTitle': obj.Title().decode(enc), 'objectUrl': obj.absolute_url(),
        'meetingTitle': '', 'meetingLongTitle': '', 'itemTitle': '', 'user': userName,
        'objectDavUrl': obj.absolute_url_path(), 'groups': userGroups,
        'meetingConfigTitle': cfg.Title().decode(enc),
    })
    if obj.meta_type == 'Meeting':
        translationMapping['meetingTitle'] = obj.Title().decode(enc)
        translationMapping['meetingLongTitle'] = tool.formatDate(obj.getDate(), prefixed=True)
        translationMapping['meetingState'] = translate(obj.queryState(),
                                                       domain='plone',
                                                       context=obj.REQUEST)
    elif obj.meta_type == 'MeetingItem':
        translationMapping['itemTitle'] = obj.Title().decode(enc)
        translationMapping['itemState'] = translate(obj.queryState(),
                                                    domain='plone',
                                                    context=obj.REQUEST)
        translationMapping['lastAnnexTitle'] = ''
        translationMapping['lastAnnexTypeTitle'] = ''
        lastAnnex = IAnnexable(obj).getLastInsertedAnnex()
        if lastAnnex:
            translationMapping['lastAnnexTitle'] = lastAnnex.Title().decode(enc)
            translationMapping['lastAnnexTypeTitle'] = \
                lastAnnex.getMeetingFileType(theData=True)['name'].decode(enc)
        meeting = obj.getMeeting(brain=True)
        if meeting:
            translationMapping['meetingTitle'] = meeting.Title().decode(enc)
            translationMapping['meetingLongTitle'] = tool.formatDate(meeting.getDate(), prefixed=True)
            translationMapping['itemNumber'] = obj.getItemNumber(
                relativeTo='meeting')
    # Update the translationMapping with a sub-product-specific
    # translationMapping, that may also define custom mail subject and body.
    customRes = obj.adapted().getSpecificMailContext(event, translationMapping)
    if customRes:
        subject = customRes[0].encode(enc)
        body = customRes[1].encode(enc)
    else:
        subjectLabel = u'%s_mail_subject' % event
        subject = translate(subjectLabel,
                            domain=d,
                            mapping=translationMapping,
                            context=obj.REQUEST)
        # special case for translations of event concerning state change
        # if we can not translate the specific translation msgid, we use a default msgid
        # so for example if meeting_state_changed_decide_mail_subject could not be translated
        # we will translate meeting_state_changed_default_mail_subject
        if subject is subjectLabel and (subjectLabel.startswith('meeting_state_changed_') or
                                        subjectLabel.startswith('item_state_changed_')):
            if subjectLabel.startswith('meeting_state_changed_'):
                subjectLabel = u'meeting_state_changed_default_mail_subject'
            else:
                subjectLabel = u'item_state_changed_default_mail_subject'
            subject = translate(subjectLabel,
                                domain=d,
                                mapping=translationMapping,
                                context=obj.REQUEST)
        subject = subject.encode(enc)
        bodyLabel = u'%s_mail_body' % event
        body = translate(bodyLabel,
                         domain=d,
                         mapping=translationMapping,
                         context=obj.REQUEST)
        # special case for translations of event concerning state change
        # if we can not translate the specific translation msgid, we use a default msgid
        # so for example if meeting_state_changed_decide_mail_body could not be translated
        # we will translate meeting_state_changed_default_mail_body
        if body is bodyLabel and (bodyLabel.startswith('meeting_state_changed_') or
                                  bodyLabel.startswith('item_state_changed_')):
            if bodyLabel.startswith('meeting_state_changed_'):
                bodyLabel = u'meeting_state_changed_default_mail_body'
            else:
                bodyLabel = u'item_state_changed_default_mail_body'
            body = translate(bodyLabel,
                             domain=d,
                             mapping=translationMapping,
                             context=obj.REQUEST)
        body = body.encode(enc)
    adminFromAddress = _getEmailAddress(
        portal.getProperty('email_from_name'),
        portal.getProperty('email_from_address'), enc)
    fromAddress = adminFromAddress
    if tool.getFunctionalAdminEmail():
        fromAddress = _getEmailAddress(tool.getFunctionalAdminName(),
                                       tool.getFunctionalAdminEmail(),
                                       enc)
    if not recipients:
        recipients = [adminFromAddress]
    if mailMode == 'test':
        # Instead of sending mail, in test mode, we log data about the mailing.
        logger.info('Test mode / we should send mail to %s' % str(recipients))
        logger.info('Subject is [%s]' % subject)
        logger.info('Body is [%s]' % body)
        return
    # Determine mail format (plain text or HTML)
    mailFormat = 'plain'
    if cfg.getUserParam('mailFormat', obj.REQUEST) == 'html':
        mailFormat = 'html'
    # Send the mail(s)
    try:
        if not attachments:
            # Send a personalized email for every user.
            for recipient in recipients:
                _sendMail(obj, body, recipient, fromAddress, subject, mailFormat)
        else:
            # Send a single mail with everybody in bcc, for performance reasons
            # (avoid to duplicate the attached file(s)).
            _sendMail(obj, body, recipients, fromAddress, subject, mailFormat,
                      attachments)
    except EmailError, ee:
        logger.warn(str(ee))


def sendMailIfRelevant(obj, event, permissionOrRole, isRole=False,
                       customEvent=False, mapping={}):
    '''An p_event just occurred on meeting or item p_obj. If the corresponding
       meeting config specifies that a mail needs to be sent, this function
       will send a mail. The mail subject and body are defined from i18n labels
       that derive from the event name. if p_isRole is True, p_permissionOrRole
       is a role, and the mail will be sent to every user having this role. If
       p_isRole is False, p_permissionOrRole is a permission and the mail will
       be sent to everyone having this permission.  Some mapping can be received
       and used afterward in mail subject and mail body translations.

       If mail sending is activated (or in test mode) and enabled for this
       event, this method returns True.

       A plug-in may use this method for sending custom events that are not
       defined in the MeetingConfig. In this case, you must specify
       p_customEvent = True.'''
    tool = obj.portal_plonemeeting
    # If p_isRole is True and the current user has this role, I will not send
    # mail: a MeetingManager is already notified!
    currentUser = obj.portal_membership.getAuthenticatedMember()
    if isRole and currentUser.has_role(permissionOrRole, obj):
        # In this case we don't know if mail is enabled or disabled; we just
        # decide to avoid sending the mail.
        return
    cfg = tool.getMeetingConfig(obj)
    # Do not send the mail if mail mode is "deactivated".
    if cfg.getMailMode() == 'deactivated':
        return
    # Do not send mail if the (not custom) event is unknown.
    if not customEvent and event not in cfg.getMailItemEvents() and \
       event not in cfg.getMailMeetingEvents():
        return
    # Ok, send a mail. Who are the recipients ?
    recipients = []
    adap = obj.adapted()
    if isRole and (permissionOrRole == 'Owner'):
        userIds = [obj.Creator()]
    else:
        userIds = obj.portal_membership.listMemberIds()
        # When using the LDAP plugin, this method does not return all
        # users, nor the cached users!
    for userId in userIds:
        user = obj.acl_users.getUser(userId)
        if not user:
            continue
        # May happen if someone deletes the user directly in the ZMI.
        userInfo = obj.portal_membership.getMemberById(userId)
        if not userInfo.getProperty('email'):
            continue
        # Does the user have the corresponding permission on p_obj ?
        if isRole:
            checkMethod = user.has_role
        else:
            checkMethod = user.has_permission
        if not checkMethod(permissionOrRole, obj):
            continue
        recipient = tool.getMailRecipient(userInfo)
        # Must we avoid sending mail to this recipient for some custom reason?
        if not adap.includeMailRecipient(event, userId):
            continue
        # Has the user unsubscribed to this event in his preferences ?
        itemEvents = cfg.getUserParam('mailItemEvents', request=obj.REQUEST, userId=userId)
        meetingEvents = cfg.getUserParam('mailMeetingEvents', request=obj.REQUEST, userId=userId)
        if (event not in itemEvents) and (event not in meetingEvents):
            continue
        # After all, we will add this guy to the list of recipients.
        recipients.append(recipient)
    sendMail(recipients, obj, event, mapping=mapping)
    return True


def sendAdviceToGiveMailIfRelevant(event):
    '''A transition was fired on an item (in p_event.object). Check here if,
       in the new item state, advices need to be given, that had not to be given
       in the previous item state.'''
    tool = event.object.portal_plonemeeting
    cfg = tool.getMeetingConfig(event.object)
    if 'adviceToGive' not in cfg.getMailItemEvents():
        return
    for groupId, adviceInfo in event.object.adviceIndex.iteritems():
        adviceStates = getattr(tool, groupId).getItemAdviceStates(cfg)
        # Ignore advices that must not be given in the current item state
        if event.new_state.id not in adviceStates:
            continue
        # Ignore advices that already needed to be given in the previous item state
        if event.old_state.id in adviceStates:
            continue
        # do not consider groups that already gave their advice
        if not adviceInfo['type'] == 'not_given':
            continue
        # Send a mail to every person from group _advisers.
        ploneGroup = event.object.acl_users.getGroup('%s_advisers' % groupId)
        for memberId in ploneGroup.getMemberIds():
            if 'adviceToGive' not in cfg.getUserParam('mailItemEvents',
                                                      request=event.object.REQUEST,
                                                      userId=memberId):
                continue
            # Send a mail to this guy
            recipient = tool.getMailRecipient(memberId)
            if recipient:
                labelType = adviceInfo['optional'] and 'advice_optional' or 'advice_mandatory'
                translated_type = translate(labelType, domain='PloneMeeting', context=event.object.REQUEST).lower()
                sendMail([recipient],
                         event.object,
                         'adviceToGive',
                         mapping={'type': translated_type})


def addRecurringItemsIfRelevant(meeting, transition):
    '''Sees in the meeting config linked to p_meeting if the triggering of
       p_transition must lead to the insertion of some recurring items in
       p_meeting.'''
    recItems = []
    meetingConfig = meeting.portal_plonemeeting.getMeetingConfig(meeting)
    for item in meetingConfig.getItems(recurring=True):
        if item.getMeetingTransitionInsertingMe() == transition:
            recItems.append(item)
    if recItems:
        meeting.addRecurringItems(recItems)


# I wanted to put permission "ReviewPortalContent" among defaultPermissions,
# but if I do this, it generates an error when calling "manage_permission" in
# method "clonePermissions" (see below). I've noticed that in several
# PloneMeeting standard workflows (meeting_workflow, meetingitem_workflow,
# meetingfile_workflow, etc), although this permission is declared as a
# managed permission, when you go in the ZMI to consult the actual
# permissions that are set on objects governed by those workflows, the
# permission "Review portal content" does not appear in the list at all.


def clonePermissions(srcObj, destObj, permissions=(View,
                                                   AccessContentsInformation,
                                                   ModifyPortalContent,
                                                   DeleteObjects)):
    '''This method applies on p_destObj the same values for p_permissions
       than those that apply for p_srcObj, according to workflow on
       p_srcObj. p_srcObj may be an item or a meeting.'''
    wfTool = srcObj.portal_workflow
    srcWorkflows = wfTool.getWorkflowsFor(srcObj)
    if not srcWorkflows:
        return
    srcWorkflow = srcWorkflows[0]
    for permission in permissions:
        if permission in srcWorkflow.permissions:
            # Get the roles this permission is given to for srcObj in its
            # current state.
            srcStateDef = getattr(srcWorkflow.states, srcObj.queryState())
            permissionInfo = srcStateDef.getPermissionInfo(permission)
            destObj.manage_permission(permission,
                                      permissionInfo['roles'],
                                      acquire=permissionInfo['acquired'])
    # Reindex object because permissions are catalogued.
    destObj.reindexObject(idxs=['allowedRolesAndUsers'])


def getCustomSchemaFields(baseSchema, completedSchema, cols):
    '''The Archetypes schema of any PloneMeeting content type can be extended
       through the "pm_updates.py mechanism". This function returns the list of
       fields that have been added by a sub-product by checking differences
       between the p_baseSchema and the p_completedSchema.'''
    coreFieldNames = ('id', 'title', 'description')
    baseFieldNames = baseSchema._fields
    res = []
    for field in completedSchema.fields():
        fieldName = field.getName()
        if fieldName.endswith('2'):
            continue
        if (fieldName not in coreFieldNames) and \
           (fieldName not in baseFieldNames) and \
           (field.schemata != 'metadata'):
            res.append(field)
    if cols and (cols > 1):
        # I need to group fields in sub-lists (cols is the number of fields by
        # sublist).
        newRes = []
        row = []
        for elem in res:
            if len(row) == cols:
                newRes.append(row)
                row = []
            row.append(elem)
        # Complete the last unfinished line if required.
        if row:
            while len(row) < cols:
                row.append(None)
            newRes.append(row)
        res = newRes
    return res


# ------------------------------------------------------------------------------
def getDateFromRequest(day, month, year, start):
    '''This method produces a DateTime instance from info coming from a request.
       p_hour and p_month may be ommitted. p_start is a bool indicating if the
       date will be used as start date or end date; this will allow us to know
       how to fill p_hour and p_month if they are ommitted. If _year is
       ommitted, we will return a date near the Big bang (if p_start is True)
       or near the Apocalypse (if p_start is False). p_day, p_month and p_year
       are required to be valid string representations of integers.'''
    # Determine day
    if not day.strip() or (day == '00'):
        if start:
            day = 1
        else:
            day = 30
    else:
        day = int(day)
    # Determine month
    if not month.strip() or (month == '00'):
        if start:
            month = 1
        else:
            month = 12
    else:
        month = int(month)
    if (month == 2) and (day == 30):
        day = 28
    # Determine year
    if not year.strip() or (year == '0000'):
        if start:
            year = 1980
        else:
            year = 3000
    else:
        year = int(year)
    try:
        res = DateTime('%d/%d/%d' % (month, day, year))
    except DateTime.DateError:
        # The date entered by the user is invalid. Take a default date.
        if start:
            res = DateTime('1980/01/01')
        else:
            res = DateTime('3000/12/31')
    return res


# ------------------------------------------------------------------------------
def getDateFromDelta(aDate, delta):
    '''This function returns a DateTime instance, which is computed from a
       reference DateTime instance p_aDate to which a p_delta is applied.
       A p_delta is a string having the form '<deltaDays>-<hour>:<minutes>,
       where:
        - 'deltaDays' is a positive or negative integer indicating the number of
          days to add/remove;
        - 'hour' and 'minutes' is the hour and minutes to set for the
          computed date. It means that the hour and minutes of p_aDate are
          ignored.
    '''
    days, hour = delta.split('.')
    return DateTime('%s %s' % ((aDate + int(days)).strftime('%Y/%m/%d'), hour))

# ------------------------------------------------------------------------------
from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass


class FakeMeetingUser:
    '''Used as a replacement for a MeetingUser, ie:
       * when the real MeetingUser has been deleted,
       * when we need to get replacement-related info concatenated from several
         MeetingUser instances.
    '''
    security = ClassSecurityInfo()
    def __init__(self, id, user=None, replacement=None):
        self.id = id
        if not user:
            return
        bilingual = user.getField('duty2')
        # MeetingUser instance p_user is replaced by a p_replacement user.
        self.title = user.Title()
        if bilingual:
            self.title2 = user.getTitle2()
        self.duty = replacement.getReplacementDuty()
        if bilingual:
            self.duty2 = replacement.getReplacementDuty2()
        # If this person replaces another one, self.duty above is the duty of
        # the person as replacement for the other one. We keep its original
        # duty in self.originalDuty below.
        self.originalDuty = user.getDuty()
        if bilingual:
            self.originalDuty2 = user.getDuty2()

    security.declarePublic('getId')
    def getId(self):
        return self.id

    security.declarePublic('Title')
    def Title(self):
        return getattr(self, 'title', '')

    security.declarePublic('getDuty')
    def getDuty(self, original=False):
        if not original:
            return getattr(self, 'duty', '')
        return getattr(self, 'originalDuty', '')

    security.declarePublic('getBilingual')
    def getBilingual(self, name, force=1, sep='-'):
        '''Gets the bilingual content of field named p_name (mimics
           MeetingUser.getBilingual).'''
        if force == 1:
            return getattr(self, name, '')
        elif force == 2:
            return getattr(self, name+'2', '')
        elif force == 'all':
            return '%s%s%s' % (getattr(self, name, ''), sep,
                               getattr(self, name+'2', ''))
InitializeClass(FakeMeetingUser)


def getMeetingUsers(obj, fieldName, theObjects=False, includeDeleted=True,
                    meetingForRepls=None):
    '''Gets the meeting users defined on a given p_obj (item or meeting) within
       a given p_fieldName. Here's the meaning of the remaining params:
       * theObjects  If True, the method will return MeetingUser instances
                     instead of MeetingUser IDs (False value is used for
                     Archetypes getters.
       * includeDeleted  (works only when p_theObjects is True)
                     If True, the method will return a FakeMeetingUser
                     instance for every MeetingUser that has been deleted.
       * meetingForRepls (works only when p_theObjects is True)
                     If given, it is a Meeting instance; it means that we
                     need to take care of user replacements as defined on
                     this meeting. In this case we will return
                     a FakeMeetingUser instance for every replaced user, whose
                     "duty" will be initialized with the replacement duty of
                     the original user.'''
    res = obj.getField(fieldName).get(obj)
    if not theObjects:
        return res
    cfg = obj.portal_plonemeeting.getMeetingConfig(obj)
    newRes = []
    for id in res:
        mUser = getattr(cfg.meetingusers, id, None)
        if not mUser:
            if includeDeleted:
                newRes.append(FakeMeetingUser(id))
        else:
            if not meetingForRepls:  # Simply add the MeetingUser to the result
                newRes.append(mUser)
            else:
                newRes.append(mUser.getForUseIn(meetingForRepls))
    return newRes

# ------------------------------------------------------------------------------
mainTypes = ('MeetingItem', 'Meeting', 'MeetingFile')


def getFieldContent(obj, name, force=None, sep='-', **kwargs):
    '''Returns the content of p_field on p_obj. If content if available in
       2 languages, return the one that corresponds to user language, excepted
       if p_force is integer 1 or 2: in this case it returns content in language
       1 or 2. If p_force is "all", it returns the content in both languages,
       separated with p_sep.'''
    global mainTypes
    if force:
        if force == 1:
            return obj.getField(name).get(obj, **kwargs)
        elif force == 2:
            return obj.getField(name+'2').get(obj, **kwargs)
        elif force == 'all':
            return '%s%s%s' % (obj.getField(name).get(obj, **kwargs), sep,
                               obj.getField(name+'2').get(obj, **kwargs))
    field = obj.getField(name)
    # Is content of this field bilingual?
    tool = obj.portal_plonemeeting
    adaptations = tool.getModelAdaptations()
    if obj.meta_type in mainTypes:
        bilingual = 'secondLanguage' in adaptations
    else:
        bilingual = 'secondLanguageCfg' in adaptations
    if not bilingual:
        return field.get(obj)
    else:
        # Get the name of the 2 languages
        firstLanguage = obj.portal_languages.getDefaultLanguage()[0:2]
        userLanguage = tool.getUserLanguage()
        if userLanguage == firstLanguage:
            return field.get(obj)
        else:
            return obj.getField(field.getName()+'2').get(obj, **kwargs)


def getFieldVersion(obj, name, changes):
    '''Returns the content of field p_name on p_obj. If p_changes is True,
       historical modifications of field content are highlighted.'''
    lastVersion = obj.getField(name).getAccessor(obj)()
    if not changes:
        return lastVersion
    # Return cumulative diff between successive versions of field
    res = None
    lastEvent = None
    for event in obj.workflow_history[obj.getWorkflowName()]:
        if (event['action'] == '_datachange_') and (name in event['changes']):
            if res is None:
                # We have found the first version of the field
                res = event['changes'][name]
            else:
                # We need to produce the difference between current result and
                # this version.
                iMsg, dMsg = getHistoryTexts(obj, lastEvent)
                comparator = HtmlDiff(res, event['changes'][name], iMsg, dMsg)
                res = comparator.get()
            lastEvent = event
    # Now we need to compare the result with the current version.
    iMsg, dMsg = getHistoryTexts(obj, lastEvent)
    comparator = HtmlDiff(res, lastVersion, iMsg, dMsg)
    return comparator.get()


# ------------------------------------------------------------------------------
def getLastEvent(obj, transition, notBefore='transfer'):
    '''Returns, from the workflow history of p_obj, the event that corresponds
       to the most recent triggering of p_transition (=its name). p_transition
       can be a list of names: in this case, it returns the event about the most
       recently triggered transition (ie, accept, refuse or delay). If
       p_notBefore is given, it corresponds to a kind of start transition for
       the search: we will not search in the history preceding the last
       triggering of this transition. This is useful when history of an item
       is the combined history of this item from several sites, and we want
       to search only within history of the "last" site, so we want to ignore
       everything that occurrred before the last "transfer" transition.'''
    wfTool = getToolByName(obj, 'portal_workflow')
    history = obj.workflow_history[wfTool.getWorkflowsFor(obj)[0].getId()]
    i = len(history)-1
    while i >= 0:
        event = history[i]
        if notBefore and (event['action'] == notBefore):
            return
        if isinstance(transition, basestring):
            condition = event['action'] == transition
        else:
            condition = event['action'] in transition
        if condition:
            return event
        i -= 1


# ------------------------------------------------------------------------------
# History-related functions
# ------------------------------------------------------------------------------
def rememberPreviousData(obj, name=None):
    '''This method is called before updating p_obj and remembers, for every
       historized field (or only for p_name if explicitly given), the previous
       value. Result is a dict ~{s_fieldName: previousFieldValue}~'''
    res = {}
    cfg = obj.portal_plonemeeting.getMeetingConfig(obj)
    isItem = obj.meta_type == 'MeetingItem'
    # Do nothing if the object is not in a state when historization is enabled.
    if isItem:
        meth = cfg.getRecordItemHistoryStates
    else:
        meth = cfg.getRecordMeetingHistoryStates
    if obj.queryState() not in meth():
        return res
    # Store in res the values currently stored on p_obj.
    if isItem:
        historized = cfg.getHistorizedItemAttributes()
    else:
        historized = cfg.getHistorizedMeetingAttributes()
    if name:
        if name in historized:
            res[name] = obj.getField(name).get(obj)
    else:
        for name in historized:
            res[name] = obj.getField(name).get(obj)
    return res


def addDataChange(obj, previousData=None):
    '''This method adds a "data change" event in the object history. If the
       previous data are not given in p_previousData, we look for it in
       obj._v_previousData.'''
    if previousData is None:
        previousData = getattr(obj, '_v_previousData', None)
    if not previousData:
        return
    # Remove from p_previousData values that were not changed or that were empty
    for name in previousData.keys():
        field = obj.getField(name)
        oldValue = previousData[name]
        if isinstance(oldValue, basestring):
            oldValue = oldValue.strip()
        newValue = field.get(obj)
        if isinstance(newValue, basestring):
            newValue = newValue.strip()
        if oldValue == newValue:
            del previousData[name]
    if not previousData:
        return
    # Add an event in the history
    userId = obj.portal_membership.getAuthenticatedMember().getId()
    event = {'action': '_datachange_', 'actor': userId, 'time': DateTime(),
             'comments': '', 'review_state': obj.queryState(),
             'changes': previousData}
    if hasattr(obj, '_v_previousData'):
        del obj._v_previousData
    # Add the event to the history
    obj.workflow_history[obj.getWorkflowName()] += (event,)


def hasHistory(obj, fieldName=None):
    '''Has p_obj an history? If p_fieldName is specified, the question is: has
       p_obj an history for field p_fieldName?'''
    wfName = obj.getWorkflowName()
    if hasattr(obj.aq_base, 'workflow_history') and obj.workflow_history and \
       (wfName in obj.workflow_history):
        for event in obj.workflow_history[wfName]:
            if not fieldName:
                condition = event['action']
            else:
                condition = (event['action'] == '_datachange_') and \
                            (fieldName in event['changes'])
            if condition:
                return True


def findNewValue(obj, name, history, stopIndex):
    '''This function tries to find a more recent version of value of field
       p_name on p_obj. It first tries to find it in history[:stopIndex+1]. If
       it does not find it there, it returns the current value on p_obj.'''
    i = stopIndex+1
    while (i-1) >= 0:
        i -= 1
        if history[i]['action'] != '_datachange_':
            continue
        if name not in history[i]['changes']:
            continue
        # We have found it!
        return history[i]['changes'][name]
    return obj.getField(name).get(obj)


def getHistoryTexts(obj, event):
    '''Returns a tuple (insertText, deleteText) containing texts to show on,
       respectively, inserted and deleted chunks of text.'''
    userName = obj.portal_plonemeeting.getUserName(event['actor'])
    mapping = {'userName': userName.decode('utf-8')}
    res = []
    for type in ('insert', 'delete'):
        msg = translate('history_%s' % type, mapping=mapping,
                        domain='PloneMeeting', context=obj.REQUEST)
        date = obj.portal_plonemeeting.formatDate(event['time'],
                                                  short=True, withHour=True)
        msg = '%s: %s' % (date, msg)
        res.append(msg.encode('utf-8'))
    return res


def getHistory(obj, startNumber=0, batchSize=5):
    '''Returns the history for this object, sorted in reverse order
       (most recent change first)'''
    res = []
    wfTool = getToolByName(obj, 'portal_workflow')
    wfName = wfTool.getWorkflowsFor(obj)[0].getId()
    history = list(obj.workflow_history[wfName])
    history.reverse()
    stopIndex = startNumber + batchSize - 1
    i = -1
    # if MeetingConfig.hideItemHistoryCommentsToUsersOutsideProposingGroup is True
    # we will have to hide the history comments if current user is not part of the proposing group
    userMayAccessComment = True
    tool = getToolByName(obj, 'portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    if cfg.getHideItemHistoryCommentsToUsersOutsideProposingGroup() and \
       obj.meta_type == 'MeetingItem' and \
       not tool.isManager():
        userMeetingGroupIds = [mGroup.getId() for mGroup in tool.getGroupsForUser()]
        if not obj.getProposingGroup() in userMeetingGroupIds:
            userMayAccessComment = False
    while (i+1) < len(history):
        i += 1
        # Keep only events in range startNumber:startNumber+batchSize
        if i < startNumber:
            continue
        if i > stopIndex:
            break
        event = history[i]
        if event['action'] == '_datachange_':
            # We take a copy, because we will modify it.
            event = history[i].copy()
            event['changes'] = {}
            for name, oldValue in history[i]['changes'].iteritems():
                widgetName = obj.getField(name).widget.getName()
                if widgetName == 'RichWidget':
                    if xhtmlContentIsEmpty(oldValue):
                        val = '-'
                    else:
                        newValue = findNewValue(obj, name, history, i-1)
                        # Compute the diff between oldValue and newValue
                        iMsg, dMsg = getHistoryTexts(obj, event)
                        comparator = HtmlDiff(oldValue, newValue, iMsg, dMsg)
                        val = comparator.get()
                    event['changes'][name] = val
                elif widgetName == 'BooleanWidget':
                    label = oldValue and 'Yes' or 'No'
                    event['changes'][name] = translate(label, domain="plone", context=obj.REQUEST)
                elif widgetName == 'TextAreaWidget':
                    val = oldValue.replace('\r', '').replace('\n', '<br/>')
                    event['changes'][name] = val
                elif widgetName == 'SelectionWidget':
                    allValues = getattr(obj, obj.getField(name).vocabulary)()
                    val = allValues.getValue(oldValue or '')
                    event['changes'][name] = val or '-'
                elif widgetName == 'MultiSelectionWidget':
                    allValues = getattr(obj, obj.getField(name).vocabulary)()
                    val = [allValues.getValue(v) for v in oldValue]
                    if not val:
                        val = '-'
                    else:
                        val = '<br/>'.join(val)
                    event['changes'][name] = val
                else:
                    event['changes'][name] = oldValue
        else:
            # workflow history event
            # hide comment if user may not access it
            if not userMayAccessComment:
                # We take a copy, because we will modify it.
                event = history[i].copy()
                event['comments'] = "<span class='discreet'>Only members of the proposing group may access history comments.</span>"
        res.append(event)
    return {'events': res, 'totalNumber': len(history)}


# ------------------------------------------------------------------------------
def setFieldFromAjax(obj, fieldName, newValue):
    '''Sets on p_obj the content of a field whose name is p_fieldName and whose
       new value is p_fieldValue. This method is called by Ajax pages.'''
    field = obj.getField(fieldName)
    # Keep old value, we might need to historize it.
    previousData = rememberPreviousData(obj, fieldName)
    field.getMutator(obj)(newValue, content_type='text/html')
    # Potentially store it in object history
    if previousData:
        addDataChange(obj, previousData)
    # Update the last modification date
    obj.modification_date = DateTime()
    # Apply XHTML transforms when relevant
    transformAllRichTextFields(obj, onlyField=fieldName)
    obj.reindexObject()


# ------------------------------------------------------------------------------
def transformAllRichTextFields(obj, onlyField=None):
    '''Potentially, all richtext fields defined on an item (description,
       decision, etc) or a meeting (observations, ...) may be transformed via the method
       transformRichTextField that may be overridden by an adapter. This
       method calls it for every rich text field defined on this obj (item or meeting), if
       the user has the permission to update the field.'''
    member = obj.portal_membership.getAuthenticatedMember()
    meetingConfig = obj.portal_plonemeeting.getMeetingConfig(obj)
    fieldsToTransform = meetingConfig.getXhtmlTransformFields()
    transformTypes = meetingConfig.getXhtmlTransformTypes()
    for field in obj.schema.fields():
        if field.widget.getName() != 'RichWidget':
            continue
        if onlyField and (field.getName() != onlyField):
            continue
        # What is the "write" permission for this field ?
        writePermission = 'Modify portal content'
        if hasattr(field, 'write_permission'):
            writePermission = field.write_permission
        if not member.has_permission(writePermission, obj):
            continue
        # Apply mandatory transforms
        fieldContent = formatXhtmlFieldForAppy(field.get(obj))
        # Apply standard transformations as defined in the config
        # fieldsToTransform is like ('MeetingItem.description', 'MeetingItem.budgetInfos', )
        if ("%s.%s" % (obj.meta_type, field.getName()) in fieldsToTransform) and \
           not xhtmlContentIsEmpty(fieldContent):
            if 'removeBlanks' in transformTypes:
                fieldContent = removeBlanks(fieldContent)
        # Apply custom transformations if defined
        field.set(obj, obj.adapted().transformRichTextField(
                  field.getName(), fieldContent))
        field.setContentType(obj, field.default_content_type)


# ------------------------------------------------------------------------------
def signatureNotAlone(xhtmlContent):
    '''This method will set, on the p_xhtmlContent's last paragraph, a
       specific CSS class that will prevent, in ODT documents, signatures
       to stand alone on their last page.'''
    # A paragraph may be a "p" or "li". If it is a "p", I will add style
    # (if not already done) "pmItemKeepWithNext"; if it is a "li" I will
    # add style "pmParaKeepWithNext" (if not already done).
    res = xhtmlContent
    lastParaIndex = res.rfind('<p')
    lastItemIndex = res.rfind('<li')
    if (lastParaIndex != -1) or (lastItemIndex != -1):
        # Is the last one an item or a para?
        styleKey = 'item'
        elemLenght = 3
        if lastParaIndex > lastItemIndex:
            styleKey = 'para'
            elemLenght = 2
        maxIndex = max(lastParaIndex, lastItemIndex)
        kwnStyle = KEEP_WITH_NEXT_STYLES[styleKey]
        # Does this element already have a "class" attribute?
        if res.find('class="%s"' % kwnStyle, maxIndex) == -1:
            # No: I add the style
            res = (res[:maxIndex+elemLenght] +
                   ' class="%s" ' % kwnStyle +
                   res[maxIndex+elemLenght:])
    return res


# ------------------------------------------------------------------------------
def spanifyLink(htmltag):
    '''Given p_htmltag is a string like <a ...</a> that will be converted to
       a <span>...</span>'''
    htmltag = re.sub('<a href="[^"]+"', '<span', htmltag)
    htmltag = re.sub('</a>', '</span>', htmltag)
    return htmltag


# ------------------------------------------------------------------------------
def forceHTMLContentTypeForEmptyRichFields(obj):
    '''
      Will saving a empty Rich field ('text/html'), the contentType is set back to 'text/plain'...
      Force it to 'text/html' if the field is empty
    '''
    for field in obj.Schema().filterFields(default_content_type='text/html'):
        if not field.getRaw(obj):
            field.setContentType(obj, 'text/html')


# ------------------------------------------------------------------------------
def prepareSearchValue(value):
    '''Prepare given p_value to execute a query in the portal_catalog
       with a ZCTextIndex by adding a '*' at the end of each word.'''
    # first remove nasty characters meaning something as a search string
    toRemove = '?-+*()'
    for char in toRemove:
        value.replace(char, ' ')

    words = value.split(' ')
    res = []
    # do not add a star at the end of some words
    noAddStartFor = ['OR', 'AND', ]
    for word in words:
        if not word:
            continue
        addAStar = True
        for elt in noAddStartFor:
            if word.endswith(elt):
                addAStar = False
                break
        if addAStar:
            word = word + '*'
        res.append(word)
    return ' '.join(res)


# ------------------------------------------------------------------------------
tokens = (('<li', -1), ('</li>', 5))
crlf = ('\r', '\n')


def formatXhtmlFieldForAppy(value):
    '''p_value is a string containing XHTML code. This code must follow some
       rules to be Appy-compliant (ie, for appy.shared.XhtmlDiff to work
       properly).'''
    global tokens
    global crlf
    for token, delta in tokens:
        res = []
        i = 0  # Where I am in p_value
        while i < len(value):
            j = value.find(token, i)
            if j == -1:
                # No more occurrences. Dump the end of p_value in the result.
                res.append(value[i:])
                break
            res.append(value[i:j])
            deltaj = j+delta
            if (delta < 0) and (j > 0) and (value[deltaj] not in crlf):
                res.append('\n')
            i = j + len(token)
            res.append(value[j:i])
            if (delta > 0) and (j > 0) and (value[deltaj] not in crlf):
                res.append('\n')
        value = ''.join(res)
    return value
# ------------------------------------------------------------------------------
# taken from http://mscerts.programming4.us/fr/639402.aspx
# adapted to fit our needs


def networkdays(start_date, end_date, holidays=[], weekends=(5, 6, )):
    delta_days = (end_date - start_date).days + 1
    full_weeks, extra_days = divmod(delta_days, 7)
    # num_workdays = how many days/week you work * total # of weeks
    num_workdays = (full_weeks + 1) * (7 - len(weekends))
    # subtract out any working days that fall in the 'shortened week'
    for d in range(1, 8 - extra_days):
        if (end_date + timedelta(d)).weekday() not in weekends:
            num_workdays -= 1
    # skip holidays that fall on weekends
    holidays = [x for x in holidays if x.weekday() not in weekends]
    # subtract out any holidays
    for d in holidays:
        if start_date <= d <= end_date:
            num_workdays -= 1
    return num_workdays


def _in_between(a, b, x):
    return a <= x <= b or b <= x <= a


def cmp(a, b):
    return (a > b) - (a < b)


def workday(start_date, days=0, holidays=[], weekends=[], unavailable_weekdays=[]):
    '''Given a p_startdate, calculate a new_date with given p_days delta.
       If some p_holidays are defined, it will increase the resulting new_date.
       Moreover, if found new_date weeknumber is p_unavailable_weekday, we will find next
       available day.'''
    if days == 0:
        return start_date
    if days > 0 and start_date.weekday() in weekends:
        while start_date.weekday() in weekends:
            start_date -= timedelta(days=1)
    elif days < 0:
        while start_date.weekday() in weekends:
            start_date += timedelta(days=1)
    full_weeks, extra_days = divmod(days, 7 - len(weekends))
    new_date = start_date + timedelta(weeks=full_weeks)
    for i in range(extra_days):
        new_date += timedelta(days=1)
        while new_date.weekday() in weekends:
            new_date += timedelta(days=1)
    # to account for days=0 case
    while new_date.weekday() in weekends:
        new_date += timedelta(days=1)

    # avoid this if no holidays
    if holidays:
        delta = timedelta(days=1 * cmp(days, 0))
        # skip holidays that fall on weekends
        holidays = [x for x in holidays if x.weekday() not in weekends]
        holidays = [x for x in holidays if x != start_date]
        for d in sorted(holidays, reverse=(days < 0)):
            # if d in between start and current push it out one working day
            if _in_between(start_date, new_date, d):
                new_date += delta
                while new_date.weekday() in weekends:
                    new_date += delta
    if new_date.weekday() in unavailable_weekdays:
        # we will relaunch the search if we do not want a date to be a particular
        # day number.  For example, we do not want the new_date to be on saterday,
        # so day number 5 (as beginning by 0), in this case, we add 1 to days and we relaunch
        # the workday search
        new_date = workday(start_date, days+1, holidays, weekends, unavailable_weekdays)

    return new_date


class AdvicesUpdatedEvent(ObjectEvent):
    implements(IAdvicesUpdatedEvent)

    def __init__(self, object):
        self.object = object


class ItemDuplicatedEvent(ObjectEvent):
    implements(IItemDuplicatedEvent)

    def __init__(self, object, newItem):
        self.object = object
        self.newItem = newItem


class ItemDuplicatedFromConfigEvent(ObjectEvent):
    implements(IItemDuplicatedFromConfigEvent)

    def __init__(self, object, usage):
        self.object = object
        self.usage = usage
