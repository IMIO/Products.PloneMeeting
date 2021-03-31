# -*- coding: utf-8 -*-

from Acquisition import aq_base
from AccessControl.Permission import Permission
from appy.shared.diff import HtmlDiff
from bs4 import BeautifulSoup
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.excelexport.exportables.dexterityfields import get_exportable_for_fieldname
from collective.fingerpointing.config import AUDIT_MESSAGE
from collective.fingerpointing.logger import log_info
from collective.fingerpointing.utils import get_request_information
from collective.iconifiedcategory.interfaces import IIconifiedInfos
from DateTime import DateTime
from datetime import datetime
from datetime import timedelta
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from imio.helpers.xhtml import addClassToLastChildren
from imio.helpers.xhtml import CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT
from imio.helpers.xhtml import markEmptyTags
from imio.helpers.xhtml import removeBlanks
from imio.helpers.xhtml import storeImagesLocally
from imio.helpers.xhtml import xhtmlContentIsEmpty
from plone import api
from plone.app.textfield import RichText
from plone.app.uuid.utils import uuidToObject
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from plone.dexterity.interfaces import IDexterityContent
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.locking.events import unlockAfterModification
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import AccessContentsInformation
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ManageProperties
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import safe_unicode
from Products.DCWorkflow.events import TransitionEvent
from Products.MailHost.MailHost import MailHostError
from Products.PageTemplates.Expressions import SecureModuleImporter
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import ADD_SUBCONTENT_PERMISSIONS
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import TOOL_ID
from Products.PloneMeeting.interfaces import IAdviceAfterAddEvent
from Products.PloneMeeting.interfaces import IAdviceAfterModifyEvent
from Products.PloneMeeting.interfaces import IAdviceAfterTransitionEvent
from Products.PloneMeeting.interfaces import IAdvicesUpdatedEvent
from Products.PloneMeeting.interfaces import IItemAfterTransitionEvent
from Products.PloneMeeting.interfaces import IItemDuplicatedEvent
from Products.PloneMeeting.interfaces import IItemDuplicatedFromConfigEvent
from Products.PloneMeeting.interfaces import IItemDuplicatedToOtherMCEvent
from Products.PloneMeeting.interfaces import IItemListTypeChangedEvent
from Products.PloneMeeting.interfaces import IItemLocalRolesUpdatedEvent
from Products.PloneMeeting.interfaces import IMeetingAfterTransitionEvent
from Products.PloneMeeting.interfaces import IMeetingConfigCustom
from Products.PloneMeeting.interfaces import IMeetingCustom
from Products.PloneMeeting.interfaces import IMeetingGroupCustom
from Products.PloneMeeting.interfaces import IMeetingItemCustom
from Products.PloneMeeting.interfaces import IMeetingLocalRolesUpdatedEvent
from Products.PloneMeeting.interfaces import IToolPloneMeetingCustom
from zope.annotation import IAnnotations
from zope.component import getAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.component.interfaces import ObjectEvent
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import implements
from zope.security.interfaces import IPermission

import logging
import os
import os.path
import re
import socket
import unicodedata
import urlparse


logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants ------------------------------------------
WRONG_INTERFACE_NAME = 'Wrong interface name "%s". You must specify the full ' \
                       'interface package name.'
WRONG_INTERFACE_PACKAGE = 'Could not find package "%s".'
WRONG_INTERFACE = 'Interface "%s" not found in package "%s".'
ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR = 'There was an error during transform of field \'%s\' of this item. ' \
    'Please check TAL expression defined in the configuration.  Original exception: %s'
ITEM_EXECUTE_ACTION_ERROR = "There was an error in the TAL expression '{0}' " \
    "defined in field MeetingConfig.onMeetingTransitionItemActionToExecute executed on item at '{1}'. " \
    "Original exception : {2}"

# ------------------------------------------------------------------------------
monthsIds = {1: 'month_jan', 2: 'month_feb', 3: 'month_mar', 4: 'month_apr',
             5: 'month_may', 6: 'month_jun', 7: 'month_jul', 8: 'month_aug',
             9: 'month_sep', 10: 'month_oct', 11: 'month_nov', 12: 'month_dec'}

weekdaysIds = {0: 'weekday_sun', 1: 'weekday_mon', 2: 'weekday_tue',
               3: 'weekday_wed', 4: 'weekday_thu', 5: 'weekday_fri',
               6: 'weekday_sat'}

adaptables = {
    'MeetingItem': {'method': 'getItem', 'interface': IMeetingItemCustom},
    'Meeting': {'method': 'getMeeting', 'interface': IMeetingCustom},
    # No (condition or action) workflow-related adapters are defined for the
    # following content types; only a Custom adapter.
    'MeetingAdvice': {'method': 'getAdvice', 'interface': None},
    'MeetingConfig': {'method': None, 'interface': IMeetingConfigCustom},
    'MeetingGroup': {'method': None, 'interface': IMeetingGroupCustom},
    'ToolPloneMeeting': {'method': None, 'interface': IToolPloneMeetingCustom},
}


def getInterface(interfaceName):
    '''Gets the interface named p_interfaceName.'''
    elems = interfaceName.split('.')
    if len(elems) < 2:
        raise PloneMeetingError(WRONG_INTERFACE_NAME % interfaceName)
    interfaceName = elems[len(elems) - 1]
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
    tool = api.portal.get_tool(TOOL_ID)
    cfg = tool.getMeetingConfig(obj)
    interfaceMethod = adaptables[obj.__class__.__name__]['method']
    if conditions:
        interfaceMethod += 'Conditions'
    else:
        interfaceMethod += 'Actions'
    interfaceLongName = getattr(cfg, '%sInterface' % interfaceMethod)(**{'obj': obj})
    adapter = getInterface(interfaceLongName)(obj)
    # set some attributes so it is reusable in the adapter
    adapter.tool = tool
    adapter.cfg = cfg
    return adapter


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
    if className == 'present-several-items':
        return obj.context
    elif obj and \
            hasattr(obj, 'context') and \
            hasattr(obj.context, 'meta_type') and \
            obj.context.meta_type == 'Meeting':
        return obj.context

    if not (className in ('Meeting', 'MeetingItem')):
        # check if we are on a Script or so or calling a BrowserView
        if className in methodTypes or 'SimpleViewClass' in className:
            # We are changing the state of an element. We must then check the referer
            refererUrl = context.REQUEST.get('HTTP_REFERER')
            referer = urlparse.urlparse(refererUrl)[2]
            if referer.endswith('/view') or \
               referer.endswith('/@@meeting_available_items_view') or \
               referer.endswith('/edit') or \
               referer.endswith('/search_form') or \
               referer.endswith('/plonemeeting_topic_view'):
                referer = os.path.dirname(referer)
            # We add the portal path if necessary
            # (in case Apache rewrites the uri for example)
            portal_url = api.portal.get_tool('portal_url')
            portal_path = portal_url.getPortalPath()
            if not referer.startswith(portal_path):
                # The rewrite rule has modified the URL. First, remove any
                # added URL prefix.
                if referer.find('/Members/') != -1:
                    referer = referer[referer.index('/Members/'):]
                # Then, add the real portal as URL prefix.
                referer = portal_path + referer
            # take care that the Meeting may contains annexes
            catalog = api.portal.get_tool('portal_catalog')
            res = catalog(path=referer, meta_type='Meeting')
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

    toReturn = None
    if obj and hasattr(obj, 'meta_type') and obj.meta_type == 'Meeting':
        toReturn = obj
    return toReturn


def cleanMemoize(portal, prefixes=[]):
    '''This will remove some memoized values from request.
       This is necessary for example as borg localroles are memoized and if we check
       roles, then change and check again in the same request, we get wrong results...'''
    annotations = IAnnotations(portal.REQUEST)
    annotations_to_delete = []
    for annotation in annotations.keys():
        if not prefixes:
            annotations_to_delete.append(annotation)
        else:
            for prefix in prefixes:
                if annotation.startswith(prefix):
                    annotations_to_delete.append(annotation)
    for annotation_to_delete in annotations_to_delete:
        del annotations[annotation_to_delete]

    if 'plone.memoize' in annotations:
        annotations['plone.memoize'].clear()


def createOrUpdatePloneGroup(groupId, groupTitle, groupSuffix):
    '''This will create the PloneGroup that corresponds to me
       and p_groupSuffix, if group already exists, it will just update it's title.'''
    properties = api.portal.get_tool('portal_properties')
    enc = properties.site_properties.getProperty('default_charset')
    groupTitle = '%s (%s)' % (
        groupTitle.decode(enc),
        translate(groupSuffix, domain='PloneMeeting', context=getRequest()))
    # a default Plone group title is NOT unicode.  If a Plone group title is
    # edited TTW, his title is no more unicode if it was previously...
    # make sure we behave like Plone...
    groupTitle = groupTitle.encode(enc)
    portal_groups = api.portal.get_tool('portal_groups')
    wasCreated = portal_groups.addGroup(groupId, title=groupTitle)
    if not wasCreated:
        # update the title so Plone groups title are coherent
        # with MeetingGroup title in case it is updated thereafter
        portal_groups.editGroup(groupId, title=groupTitle)
    return wasCreated


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


def cropHTML(html, length=400, ellipsis='...'):
    '''Crop given HTML and return valid HTML.'''
    html = safe_unicode(html)
    cropped_content = BeautifulSoup(html[:length], 'html.parser').renderContents()
    return cropped_content


# Mail sending machinery -------------------------------------------------------
class EmailError(Exception):
    pass


SENDMAIL_ERROR = 'Error while sending mail: %s.'
ENCODING_ERROR = 'Encoding error while sending mail: %s.'
MAILHOST_ERROR = 'Error with the MailServer while sending mail: %s.'


def _getEmailAddress(name, email):
    '''Creates a full email address from a p_name and p_email.'''
    res = email
    if name:
        res = safe_unicode(name) + ' <%s>' % email
    return safe_unicode(res)


def _sendMail(obj, body, recipients, fromAddress, subject, format,
              attachments=None):
    '''Sends a mail. p_mto can be a single email or a list of emails.'''
    bcc = None
    # Hide the whole list of recipients if we must send the mail to many.
    if not isinstance(recipients, basestring):
        # mbcc passed parameter must be utf-8 encoded
        bcc = [rec.encode('utf-8') for rec in recipients]
        recipients = fromAddress
    # Construct the data structures for the attachments if relevant
    if attachments:
        msg = MIMEMultipart()
        if isinstance(body, unicode):
            body = body.encode('utf-8')
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


def get_public_url(obj):
    """Returns the public URL of an element, especially when no REQUEST
       is available."""
    public_url = os.getenv('PUBLIC_URL', None)
    if public_url:
        portal_url = api.portal.get_tool('portal_url')
        url = os.path.join(public_url, portal_url.getRelativeContentURL(obj))
    else:
        url = obj.absolute_url()
    return url


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
    # Compute user name
    pms = api.portal.get_tool('portal_membership')
    userName = pms.getAuthenticatedMember().getId()
    userInfo = pms.getMemberById(userName)
    if userInfo and userInfo.getProperty('fullname'):
        userName = safe_unicode(userInfo.getProperty('fullname'))
    # Compute list of MeetingGroups for this user
    userGroups = ', '.join([g.Title() for g in tool.get_orgs_for_user()])
    # Create the message parts
    d = 'PloneMeeting'
    portal = api.portal.get()
    portalUrl = get_public_url(portal)
    if mapping:
        # we need every mappings to be unicode
        for elt in mapping:
            if not isinstance(mapping[elt], unicode):
                mapping[elt] = safe_unicode(mapping[elt])
        translationMapping = mapping
    else:
        translationMapping = {}
    translationMapping.update({
        'portalUrl': portalUrl, 'portalTitle': safe_unicode(portal.Title()),
        'objectTitle': safe_unicode(obj.Title()), 'objectUrl': get_public_url(obj),
        'meetingTitle': '', 'meetingLongTitle': '', 'itemTitle': '', 'user': userName,
        'groups': userGroups, 'meetingConfigTitle': safe_unicode(cfg.Title()),
    })
    if obj.meta_type == 'Meeting':
        translationMapping['meetingTitle'] = safe_unicode(obj.Title())
        translationMapping['meetingLongTitle'] = tool.formatMeetingDate(obj, prefixed=True)
        translationMapping['meetingState'] = translate(obj.queryState(),
                                                       domain='plone',
                                                       context=obj.REQUEST)
    elif obj.meta_type == 'MeetingItem':
        translationMapping['itemTitle'] = safe_unicode(obj.Title())
        translationMapping['itemState'] = translate(obj.queryState(),
                                                    domain='plone',
                                                    context=obj.REQUEST)
        meeting = obj.getMeeting()
        if meeting:
            translationMapping['meetingTitle'] = safe_unicode(meeting.Title())
            translationMapping['meetingLongTitle'] = tool.formatMeetingDate(meeting, prefixed=True)
            translationMapping['itemNumber'] = obj.getItemNumber(
                relativeTo='meeting')
    # Update the translationMapping with a sub-product-specific
    # translationMapping, that may also define custom mail subject and body.
    customRes = obj.adapted().getSpecificMailContext(event, translationMapping)
    if customRes:
        subject = safe_unicode(customRes[0])
        body = safe_unicode(customRes[1])
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
        subject = safe_unicode(subject)
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
        body = safe_unicode(body)
    adminFromAddress = _getEmailAddress(
        portal.getProperty('email_from_name'),
        safe_unicode(portal.getProperty('email_from_address')))
    fromAddress = adminFromAddress
    if tool.getFunctionalAdminEmail():
        fromAddress = _getEmailAddress(tool.getFunctionalAdminName(),
                                       tool.getFunctionalAdminEmail())
    if not recipients:
        recipients = [adminFromAddress]
    if mailMode == 'test':
        # Instead of sending mail, in test mode, we log data about the mailing.
        logger.info('Test mode / we should send mail to %s' % str(recipients))
        logger.info('Subject is [%s]' % subject)
        logger.info('Body is [%s]' % body)
        return
    # Use 'plain' for mail format so the email client will turn links to clickable links
    mailFormat = 'plain'
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
    tool = api.portal.get_tool(TOOL_ID)
    membershipTool = api.portal.get_tool('portal_membership')
    currentUser = membershipTool.getAuthenticatedMember()
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
        # Warning "_members" returns all users (even deleted users), the filter must do this afterwards.
        userIds = api.portal.get_tool('portal_memberdata')._members
    for userId in userIds:
        user = membershipTool.getMemberById(userId)
        # do not warn user doing the action
        if not user or userId == currentUser.getId():
            continue
        if not user.getProperty('email'):
            continue
        # Does the user have the corresponding permission on p_obj ?
        if isRole:
            if not user.has_role(permissionOrRole, obj):
                continue
        else:
            if not api.user.has_permission(permission=permissionOrRole, obj=obj, user=user):
                continue

        recipient = tool.getMailRecipient(user)
        # Must we avoid sending mail to this recipient for some custom reason?
        if not adap.includeMailRecipient(event, userId):
            continue
        # Has the user unsubscribed to this event in his preferences ?
        itemEvents = cfg.getMailItemEvents()
        meetingEvents = cfg.getMailMeetingEvents()
        if (event not in itemEvents) and (event not in meetingEvents):
            continue
        # After all, we will add this guy to the list of recipients.
        recipients.append(recipient)
    if recipients:
        sendMail(recipients, obj, event, mapping=mapping)
    return True


def addRecurringItemsIfRelevant(meeting, transition):
    '''Sees in the meeting config linked to p_meeting if the triggering of
       p_transition must lead to the insertion of some recurring items in
       p_meeting.'''
    recItems = []
    meetingConfig = meeting.portal_plonemeeting.getMeetingConfig(meeting)
    for item in meetingConfig.getRecurringItems():
        if item.getMeetingTransitionInsertingMe() == transition:
            recItems.append(item)
    if recItems:
        meeting.addRecurringItems(recItems)


# I wanted to put permission "ReviewPortalContent" among defaultPermissions,
# but if I do this, it generates an error when calling "manage_permission" in
# method "clonePermissions" (see below). I've noticed that in several
# PloneMeeting standard workflows (meeting_workflow, meetingitem_workflow, etc),
# although this permission is declared as a
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
    wfTool = api.portal.get_tool('portal_workflow')
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


def getFieldVersion(obj, name, changes):
    '''Returns the content of field p_name on p_obj. If p_changes is True,
       historical modifications of field content are highlighted.'''
    lastVersion = obj.getField(name).getAccessor(obj)()
    # highlight blank lines at the end of the text if current user may edit the obj
    if _checkPermission(ModifyPortalContent, obj):
        lastVersion = markEmptyTags(lastVersion,
                                    tagTitle=translate('blank_line',
                                                       domain='PloneMeeting',
                                                       context=obj.REQUEST),
                                    onlyAtTheEnd=True)

    if not changes:
        return lastVersion
    # Return cumulative diff between successive versions of field
    res = None
    lastEvent = None
    wfTool = api.portal.get_tool('portal_workflow')
    workflow_name = wfTool.getWorkflowsFor(obj)[0].getId()
    for event in obj.workflow_history[workflow_name]:
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
    wfTool = api.portal.get_tool('portal_workflow')
    workflow_name = wfTool.getWorkflowsFor(obj)[0].getId()
    obj.workflow_history[workflow_name] += (event,)


def hasHistory(obj, fieldName=None):
    '''Has p_obj an history? If p_fieldName is specified, the question is: has
       p_obj an history for field p_fieldName?'''
    wfTool = api.portal.get_tool('portal_workflow')
    workflow_name = wfTool.getWorkflowsFor(obj)[0].getId()
    if hasattr(obj.aq_base, 'workflow_history') and obj.workflow_history and \
       (workflow_name in obj.workflow_history):
        for event in obj.workflow_history[workflow_name]:
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
    i = stopIndex + 1
    while (i - 1) >= 0:
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
    tool = api.portal.get_tool(TOOL_ID)
    toLocalizedTime = obj.restrictedTraverse('@@plone').toLocalizedTime
    userName = tool.getUserName(event['actor'])
    mapping = {'userName': userName.decode('utf-8')}
    res = []
    for type in ('insert', 'delete'):
        msg = translate('history_%s' % type,
                        mapping=mapping,
                        domain='PloneMeeting',
                        context=obj.REQUEST)
        date = toLocalizedTime(event['time'], long_format=True)
        msg = '%s: %s' % (date, msg)
        res.append(msg.encode('utf-8'))
    return res


def setFieldFromAjax(obj, fieldName, newValue, remember=True, tranform=True, reindex=True, unlock=True):
    '''Sets on p_obj the content of a field whose name is p_fieldName and whose
       new value is p_fieldValue. This method is called by Ajax pages.'''
    field = obj.getField(fieldName)
    if remember:
        # Keep old value, we might need to historize it.
        previousData = rememberPreviousData(obj, fieldName)
        field.getMutator(obj)(newValue, mimetype='text/html')
        # Potentially store it in object history
        if previousData:
            addDataChange(obj, previousData)
    else:
        field.getMutator(obj)(newValue, mimetype='text/html')

    if tranform:
        # Apply XHTML transforms when relevant
        transformAllRichTextFields(obj, onlyField=fieldName)
    if reindex:
        # only reindex relevant indexes aka SearchableText + field specific index if exists
        index_names = api.portal.get_tool('portal_catalog').indexes()
        extra_idxs = ['SearchableText']
        if fieldName in index_names:
            extra_idxs.append(fieldName)
        if field.accessor in index_names:
            extra_idxs.append(field.accessor)
        notifyModifiedAndReindex(obj, extra_idxs=extra_idxs)
    if unlock:
        # just unlock, do not call ObjectEditedEvent because it does too much
        unlockAfterModification(obj, event={})
    # add a fingerpointing log message
    extras = 'object={0} field_name={1}'.format(
        repr(obj), fieldName)
    fplog('quickedit_field', extras=extras)


def notifyModifiedAndReindex(obj, extra_idxs=[], notify_event=False):
    """Ease notifyModified and reindex of a given p_obj.
       If p_extra_idxs contains '*', a full reindex is done, if not
       only 'modified' related indexes are updated.
       If p_notify_event is True, the ObjectEditedEvent is notified."""

    obj.notifyModified()

    idxs = []
    if '*' not in extra_idxs:
        idxs = ['modified', 'ModificationDate', 'Date'] + extra_idxs
    obj.reindexObject(idxs=idxs)

    if notify_event:
        notify(ObjectEditedEvent(obj))


def fplog(action, extras):
    """collective.fingerpointing add log message."""
    # add logging message to fingerpointing log
    user, ip = get_request_information()
    log_info(AUDIT_MESSAGE.format(user, ip, action, extras))


def transformAllRichTextFields(obj, onlyField=None):
    '''Potentially, all richtext fields defined on an item (description,
       decision, etc) or a meeting (observations, ...) may be transformed via the method
       transformRichTextField that may be overridden by an adapter. This
       method calls it for every rich text field defined on this obj (item or meeting), if
       the user has the permission to update the field.'''
    member = api.user.get_current()
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    fieldsToTransform = cfg.getXhtmlTransformFields()
    transformTypes = cfg.getXhtmlTransformTypes()
    for field in obj.schema.fields():
        if field.widget.getName() != 'RichWidget':
            continue
        if onlyField and (field.getName() != onlyField):
            continue
        # What is the "write" permission for this field ?
        writePermission = ModifyPortalContent
        if hasattr(field, 'write_permission'):
            writePermission = field.write_permission
        if not member.has_permission(writePermission, obj):
            continue
        # make sure we do not loose resolveuid to images, use getRaw
        raw_value = field.getRaw(obj).strip()
        # Apply mandatory transforms
        fieldContent = storeImagesLocally(obj, raw_value)
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
def signatureNotAlone(xhtmlContent, numberOfChars=CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT):
    '''This method will set, on the p_xhtmlContent's last paragraph, a
       specific CSS class that will prevent, in ODT documents, signatures
       to stand alone on their last page.'''
    # A paragraph may be a "p" or "li". If it is a "p", I will add style
    # (if not already done) "podItemKeepWithNext"; if it is a "li" I will
    # add style "ParaKWN" (if not already done).
    return addClassToLastChildren(xhtmlContent, numberOfChars=numberOfChars)


# ------------------------------------------------------------------------------
def forceHTMLContentTypeForEmptyRichFields(obj):
    '''
      While saving an empty Rich field ('text/html'),
      the contentType is set back to 'text/plain'...
      Force it to 'text/html' if the field is empty.
    '''
    for field in obj.Schema().filterFields(default_content_type='text/html'):
        if not field.getRaw(obj):
            field.setContentType(obj, 'text/html')


def applyOnTransitionFieldTransform(obj, transitionId):
    '''
      Apply onTransitionFieldTransforms defined in the corresponding obj MeetingConfig.
    '''
    idxs = []
    extra_expr_ctx = _base_extra_expr_ctx(obj)
    cfg = extra_expr_ctx['cfg']
    for transform in cfg.getOnTransitionFieldTransforms():
        tal_expr = transform['tal_expression'].strip()
        if transform['transition'] == transitionId and \
           transform['field_name'].split('.')[0] == obj.meta_type and \
           tal_expr:
            try:
                extra_expr_ctx.update({'item': obj, })
                res = _evaluateExpression(
                    obj,
                    expression=tal_expr,
                    roles_bypassing_expression=[],
                    extra_expr_ctx=extra_expr_ctx,
                    empty_expr_is_true=False,
                    raise_on_error=True)
            except Exception, e:
                plone_utils = api.portal.get_tool('plone_utils')
                plone_utils.addPortalMessage(
                    PloneMeetingError(ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR %
                                      (transform['field_name'].split('.')[1], str(e))),
                    type='warning')
                return
            field = obj.getField(transform['field_name'].split('.')[1])
            field.set(obj, res, mimetype='text/html')
            idxs.append(field.accessor)
    # XXX do not reindex for now as full reindex is done after
    # when moving to dexerity, will be able to reindex more efficiently
    if False and idxs:
        obj.reindexObject(idxs=idxs)


# ------------------------------------------------------------------------------
def meetingExecuteActionOnLinkedItems(meeting, transitionId):
    '''
      When the given p_transitionId is triggered on the given p_meeting,
      check if we need to trigger an action on linked items
      defined in MeetingConfig.meetingExecuteActionOnLinkedItems.
    '''
    extra_expr_ctx = _base_extra_expr_ctx(meeting)
    cfg = extra_expr_ctx['cfg']
    wfTool = api.portal.get_tool('portal_workflow')
    wf_comment = _('wf_transition_triggered_by_application')
    for config in cfg.getOnMeetingTransitionItemActionToExecute():
        if config['meeting_transition'] == transitionId:
            is_transition = not config['tal_expression']
            for item in meeting.getItems():
                if is_transition:
                    # do not fail if a transition could not be triggered, just add an
                    # info message to the log so configuration can be adapted to avoid this
                    try:
                        wfTool.doActionFor(item, config['item_action'], comment=wf_comment)
                    except WorkflowException:
                        pass
                else:
                    # execute the TAL expression, will not fail but log if an error occurs
                    # do this as Manager to avoid permission problems, the configuration is supposed to be applied
                    with api.env.adopt_roles(['Manager']):
                        extra_expr_ctx.update({'item': item, 'meeting': meeting})
                        _evaluateExpression(
                            item,
                            expression=config['tal_expression'].strip(),
                            roles_bypassing_expression=[],
                            extra_expr_ctx=extra_expr_ctx,
                            error_pattern=ITEM_EXECUTE_ACTION_ERROR)


def computeCertifiedSignatures(signatures):

    computedSignatures = {}
    now = datetime.now()
    validSignatureNumber = None
    for signature in signatures:
        # MeetingConfig use signatureNumber and organization use signature_number...
        if signature.get('signature_number'):
            signature_number = signature.get('signature_number')
            from_cfg = False
        else:
            signature_number = signature.get('signatureNumber')
            from_cfg = True

        # first check if we still did not found a valid signature for this signatureNumber
        if signature_number == validSignatureNumber:
            continue
        # walk thru every signatures and select available one
        # the first found active signature is kept
        if from_cfg:
            # if we have a date_from, we append hours 0h01 to take entire day into account
            date_from = signature['date_from'] or None
            if date_from:
                year, month, day = date_from.split('/')
                date_from = datetime(int(year), int(month), int(day), 0, 0) or None
            # if we have a date_to, we append hours 23h59 to take entire day into account
            date_to = signature['date_to'] or None
            if date_to:
                year, month, day = date_to.split('/')
                date_to = datetime(int(year), int(month), int(day), 23, 59) or None
        else:
            date_from = signature['date_from']
            date_from = date_from and datetime(date_from.year, date_from.month, date_from.day, 0, 0) or None
            date_to = signature['date_to']
            date_to = date_to and datetime(date_to.year, date_to.month, date_to.day, 23, 59) or None
        # if dates are defined and not current, continue
        if (date_from and date_to) and not _in_between(date_from, date_to, now):
            continue
        validSignatureNumber = signature_number
        computedSignatures[validSignatureNumber] = {}
        # manage held_position, if we have a held_position, we use it for 'name' and 'function'
        # although this can be overrided if something defined in 'name' or 'function' columns
        held_position = None
        # held_position
        if signature['held_position'] is not None and signature['held_position'] != '_none_':
            held_position = uuidToObject(signature['held_position'])
        computedSignatures[validSignatureNumber]['held_position'] = held_position
        # name
        if held_position and not signature['name']:
            computedSignatures[validSignatureNumber]['name'] = \
                held_position.get_person_title(include_person_title=False)
        else:
            computedSignatures[validSignatureNumber]['name'] = signature['name']
        # function
        if held_position and not signature['function']:
            computedSignatures[validSignatureNumber]['function'] = \
                held_position.get_prefix_for_gender_and_number(include_value=True)
        else:
            computedSignatures[validSignatureNumber]['function'] = signature['function']

    return computedSignatures


def listifySignatures(signatures):
    res = []
    for singNumber, signInfos in sorted(signatures.items()):
        res.append(signInfos['function'])
        res.append(signInfos['name'])
    return res


def updateCollectionCriterion(collection, i, v):
    """Update a collection criterion."""
    for criterion in collection.query:
        if criterion['i'] == i:
            if isinstance(criterion, dict):
                criterion['v'] = v
            else:
                criterion.v = v
            # make saved value persistent
            collection.query = collection.query
            break


def toHTMLStrikedContent(plain_content):
    """
      p_content is HTML having elements to strike between [[]].
      We will replace these [[]] by <strike> tags.
    """
    plain_content = plain_content.replace('[[', '<strike>').replace(']]', '</strike>')
    return plain_content


def translate_list(elements, domain="plone", as_list=False, separator=u', '):
    """Translate the received elements."""
    translated = []
    request = getRequest()
    for elt in elements:
        translated.append(
            translate(elt, domain=domain, context=request)
        )
    if not as_list:
        translated = u', '.join(translated)
    return translated


def display_as_html(plain_content, obj):
    """Display p_plain_content as HTML, especially ending lines
       that are not displayed if empty."""
    html_content = plain_content.replace('\n', '<br />')
    if _checkPermission(ModifyPortalContent, obj):
        # replace ending <br /> by empty tags
        splitted = html_content.split('<br />')
        res = []
        for elt in splitted:
            if not elt.strip():
                res.append('<p>&nbsp;</p>')
            else:
                res.append('<p>' + elt + '</p>')
        html_content = ''.join(res)
        html_content = markEmptyTags(
            html_content,
            tagTitle=translate('blank_line',
                               domain='PloneMeeting',
                               context=obj.REQUEST),
            onlyAtTheEnd=True)
    return html_content


def _itemNumber_to_storedItemNumber(number):
    """This will transform a displayed itemNumber to a real form the itemNumber is stored :
       - 1 -> 100;
       - 2 --> 200;
       - 2.1 --> 201;
       - 2.9 --> 209;
       - 2.10 --> 210;
       - 2.22 --> 222;
       """
    if '.' in number:
        newInteger, newDecimal = number.split('.')
        newInteger = newInteger
        newDecimal = newDecimal.zfill(2)
        realMoveNumber = int('{0}{1}'.format(newInteger, newDecimal))
    else:
        realMoveNumber = int(number) * 100
    return realMoveNumber
# ------------------------------------------------------------------------------


def _storedItemNumber_to_itemNumber(number, forceShowDecimal=True):
    """This will transform a stored itemNumber to a dispayable itemNumber :
       - 100 -> 1;
       - 200 --> 2;
       - 201 --> 2.1;
       - 209 --> 2.9;
       - 210 --> 2.10;
       - 222 --> 2.22;
       If p_forceShowDecimal is True, we will return a decimal, no matter it is '0'.
       """
    firstPart = int(number / 100)
    secondPart = number % 100
    if secondPart or forceShowDecimal:
        return '{0}.{1}'.format(firstPart, secondPart)
    else:
        return str(firstPart)


def get_context_with_request(context):
    # in case we have no REQUEST, it means that we are editing a DashboardCollection
    # for which when this vocabulary is used for the 'indexAdvisers' queryField used
    # on a DashboardCollection (when editing the DashboardCollection), the context
    # is portal_registry without a REQUEST...
    if not hasattr(context, 'REQUEST'):
        # sometimes, the DashboardCollection is the first parent in the REQUEST.PARENTS...
        portal = getSite()
        published = portal.REQUEST.get('PUBLISHED', None)
        context = hasattr(published, 'context') and published.context or None
        if not context or context == portal:
            # if not first parent, try to get it from HTTP_REFERER
            referer = portal.REQUEST['HTTP_REFERER'].replace(portal.absolute_url() + '/', '')
            referer = referer.replace('/edit', '')
            referer = referer.replace('?pageName=gui', '')
            referer = referer.split('?_authenticator=')[0]
            try:
                context = portal.unrestrictedTraverse(referer)
            except (KeyError, AttributeError):
                return None
            if not hasattr(context, 'portal_type') or \
                    not (context.portal_type == 'DashboardCollection' or context.portal_type.startswith('Meeting')):
                return None
    return context


def isModifiedSinceLastVersion(obj):
    """Check if given p_obj was modified since last version (versioning)."""
    pr = api.portal.get_tool('portal_repository')
    history_metadata = pr.getHistoryMetadata(obj)
    modified = True
    if history_metadata and history_metadata._available:
        # date it was versionned
        timestamp = history_metadata._full[history_metadata.nextVersionId - 1]['metadata']['sys_metadata']['timestamp']
        # we do not use _retrieve because it does a transaction savepoint and it
        # breaks collective.zamqp...  So we use timestamp
        # advice.modified will be older than timestamp as it is managed in see content.advice.versionate_if_relevant
        # keep >= for backward compatibility as before, modified was set to timestamp, now it is older...
        if DateTime(timestamp) >= obj.modified():
            modified = False
    return modified


def version_object(obj, keep_modified=True, only_once=False, comment=''):
    """Versionate p_obj, make sure modification_date is not changed if p_keep_modified is True.
       p_only_once will take care that p_obj is only versioned one time.
       An optionnal p_comment may be defined and will appear in the versions history."""
    pr = api.portal.get_tool('portal_repository')
    # if only_once, return if we already have versions
    if only_once and pr.getHistoryMetadata(obj):
        return

    # make sure obj modification date is not changed
    obj_modified = obj.modified()
    pr.save(obj=obj, comment=comment)
    # set back modified on obj so version timestamp is > obj modified
    obj.setModificationDate(obj_modified)


# taken from http://mscerts.programming4.us/fr/639402.aspx
# adapted to fit our needs
def networkdays(start_date, end_date, holidays=[], weekends=(5, 6, )):
    delta_days = (end_date - start_date).days
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
        new_date = workday(start_date, days + 1, holidays, weekends, unavailable_weekdays)

    return new_date


def _addManagedPermissions(obj):
    """Manage the 'ATContentTypes: Add Image' and 'Add portal content' permission :
       - first compute permission to Add Image, give to users able to edit at least one
         XHTML field, this means every roles having the 'Modify portal content' or a RichText
         field.write_permission must be able to add images;
       - then compute the 'Add portal content' permission,
         give it to people having a "Add something" permission.
       Other 'Add' permissions are managed in other places :
       - Add advice in MeetingItem._updateAdvices;
       - Add annex and Add annexDecision in the WF.
       We also need to manage the 'Manage properties' permission automatically, this
       let user change annexes position, give it to roles able having the 'PloneMeeting: Add annex'
       or 'PloneMeeting: add annexDecision' permissions.
       """
    def _addImagePermission():
        write_perms = []
        # get every RichText fields using a write_permission
        if IDexterityContent.providedBy(obj):
            # dexterity
            portal_types = api.portal.get_tool('portal_types')
            fti = portal_types[obj.portal_type]
            schema = fti.lookupSchema()
            write_permissions = schema.queryTaggedValue(WRITE_PERMISSIONS_KEY, {})
            for field_id, write_permission in write_permissions.items():
                if isinstance(schema.get(field_id), RichText):
                    write_perms.append(write_permission)
        else:
            # Archetypes
            for field in obj.Schema().filterFields(default_content_type='text/html'):
                if field.write_permission:
                    write_perms.append(field.write_permission)

        roles = []
        for write_perm in write_perms:
            try:
                write_perm_roles = Permission(write_perm, {}, obj).getRoles()
            except ValueError:
                # we have the id of a Zope3 style permission, get the title
                write_perm = queryUtility(IPermission, write_perm)
                write_perm_roles = Permission(write_perm, {}, obj).getRoles()
            roles += write_perm_roles

        # check the 'Modify portal content' permission
        modify_perm = Permission(ModifyPortalContent, {}, obj)
        modify_perm_roles = modify_perm.getRoles()
        roles += modify_perm_roles
        # remove duplicates
        roles = tuple(set(roles))
        obj.manage_permission("ATContentTypes: Add Image", roles, acquire=False)

    def _addPortalContentPermission():
        # now manage the AddPortalContent permission
        # the AddPortalContent is given on the portal to 'Contributor', keep this and add local ones
        # if a role is able to add something, it also needs the AddPortalContent permission
        roles = []
        for add_subcontent_permission in ADD_SUBCONTENT_PERMISSIONS:
            permission = Permission(add_subcontent_permission, {}, obj)
            roles += permission.getRoles()
        # remove duplicates
        roles = list(set(roles))
        obj.manage_permission(AddPortalContent, roles, acquire=True)

    def _addManagePropertiesPermission():
        # give it to roles having 'PloneMeeting: add annex' or 'PloneMeeting: add annexDecision' permission
        roles = []
        add_annex_permission = Permission(AddAnnex, {}, obj)
        roles += add_annex_permission.getRoles()
        add_annex_decision_permission = Permission(AddAnnexDecision, {}, obj)
        roles += add_annex_decision_permission.getRoles()
        obj.manage_permission(ManageProperties, roles, acquire=True)

    _addImagePermission()
    _addPortalContentPermission()
    _addManagePropertiesPermission()


def getTransitionToReachState(obj, state):
    '''Given a state, return a transition that will set the obj in this state.'''
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowsFor(obj)[0]
    res = ''
    availableTransitions = [t['id'] for t in wfTool.getTransitionsFor(obj)]
    for transition in wf.transitions.values():
        if transition.id not in availableTransitions:
            continue
        if transition.new_state_id == state:
            res = transition.id
            break
    return res


def findMeetingAdvicePortalType(context):
    """ """
    tool = api.portal.get_tool('portal_plonemeeting')
    advicePortalTypeIds = tool.getAdvicePortalTypes(as_ids=True)
    if context.portal_type in advicePortalTypeIds:
        return context.portal_type

    # try to find the used portal_type from the published object, it is the case
    # when adding an advice, the published is the form
    published = context.REQUEST.get('PUBLISHED')
    if not published:
        # try to get it from context
        if context.portal_type in advicePortalTypeIds:
            return context.portal_type
        return 'meetingadvice'

    # portal_type stored on published
    if getattr(published, 'portal_type', None) and published.portal_type in advicePortalTypeIds:
        return published.portal_type

    if not getattr(published, 'ti', None):
        published = published.context
        if not hasattr(published, 'ti') and hasattr(published, 'context'):
            published = published.context

    # adding the meetingadvice
    if hasattr(published, 'ti'):
        current_portal_type = published.ti.id
    else:
        current_portal_type = published.portal_type
    return current_portal_type


def displaying_available_items(context):
    """Is the meeting view displaying available items?"""
    return bool("@@meeting_available_items_view" in context.REQUEST['HTTP_REFERER'] or
                "@@meeting_available_items_view" in context.REQUEST['URL'])


def get_annexes(obj, portal_types=['annex', 'annexDecision']):
    return [annex for annex in obj.objectValues()
            if annex.portal_type in portal_types]


def updateAnnexesAccess(container):
    """ """
    portal = api.portal.get()
    adapter = None
    for k, v in getattr(container, 'categorized_elements', {}).items():
        # do not fail on 'Members', use unrestrictedTraverse
        try:
            annex = portal.unrestrictedTraverse(v['relative_url'])
        except:
            # in case we are removing an annex, this could be called
            # before categorized_elements dict is updated
            v['visible_for_groups'] = []
            continue
        # visible_for_groups is the same for every annexes
        if not adapter:
            adapter = getAdapter(annex, IIconifiedInfos)
        else:
            adapter.context = annex
            adapter.obj = aq_base(annex)
        v['visible_for_groups'] = adapter._visible_for_groups()
        v['allowedRolesAndUsers'] = adapter._allowedRolesAndUsers


def validate_item_assembly_value(value):
    '''This method does validate the 'item_assembly' field.
       It will check that [[]] are correct.'''
    # do not validate if we are calling the form, this way
    # if some old value is wrong, the form can be shown and the validation
    # is done when saving the form
    req = getRequest()
    if req.get('initial_edit', None) == u'1':
        return True
    # check that every opening [[ has a closing ]] and that it matches
    # correctly regarding position, we do not want "Text [[Text [[Text]] Text]] Text"
    opening_pos = []
    closing_pos = []
    for m in re.finditer('\[\[', value):
        opening_pos.append(m.start())
    for m in re.finditer('\]\]', value):
        closing_pos.append(m.start())

    if not opening_pos and not closing_pos:
        return True

    # create one single list and check number of elements and that elements
    # are succedding each other in right order
    if len(opening_pos) != len(closing_pos):
        return False
    # check succession
    res = zip(opening_pos, closing_pos)
    # zip() will return a list of tuple and sum() will turn this into a list
    res = sum(res, ())
    if not sorted(res) == list(res):
        return False
    # check number of elements, dividable by 2
    if not len(res) % 2 == 0:
        return False

    return True


def main_item_data(item):
    """Build a dict with main infos data."""
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(item)
    # compute data, save 'title' and every active RichText fields
    usedItemAttrs = cfg.getUsedItemAttributes()
    data = []
    data.append({'field_name': 'title',
                 'field_content': item.Title()})
    for field in item.Schema().fields():
        fieldName = field.getName()
        if field.widget.getName() == 'RichWidget' and \
           (fieldName in usedItemAttrs or not field.optional):
            data.append({'field_name': fieldName,
                         'field_content': field.get(item)})
    return data


def reviewersFor(workflow_id=None):
    # import MEETINGREVIEWERS as it is often monkeypatched...
    from Products.PloneMeeting.config import MEETINGREVIEWERS
    if workflow_id and workflow_id in MEETINGREVIEWERS:
        return MEETINGREVIEWERS.get(workflow_id)
    return MEETINGREVIEWERS.get('*')


def get_every_back_references(obj, relationship):
    '''Loop recursievely thru every back reference of type p_relationship
       for p_obj and return it.'''
    def get_back_references(back_refs, res=[]):
        for back_obj in back_refs:
            res.append(back_obj)
            get_back_references(back_obj.getBRefs(relationship), res)
        return res
    return get_back_references(obj.getBRefs(relationship))


def getStatesBefore(obj, review_state_id):
    """
      Returns states before the p_review_state_id state.
    """
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowsFor(obj)[0]
    # get the review_state state
    if review_state_id not in wf.states:
        # return every states
        return wf.states.keys()
    # get back to the meeting WF initial state
    res = []
    initial_state = wf.initial_state
    new_state_id = ''
    new_state = wf.states[review_state_id]
    while not new_state_id == initial_state:
        for transition in new_state.transitions:
            if transition.startswith('backTo'):
                new_state_id = wf.transitions[transition].new_state_id
                res.append(new_state_id)
                new_state = wf.states[new_state_id]
    return res


def plain_render(obj, fieldname):
    """ """
    request = getRequest()
    exportable = get_exportable_for_fieldname(obj, fieldname, request)
    return exportable.render_value(obj)


def duplicate_workflow(workflowName, duplicatedWFId, portalTypeNames=[]):
    """Duplicate p_workflowName and use p_duplicatedWFId for new workflow.
       If p_portalTypeName is given, associate new workflow to given portalTypeNames."""
    # do that as a Manager because it is needed to copy/paste workflows
    with api.env.adopt_roles(['Manager', ]):
        wfTool = api.portal.get_tool('portal_workflow')
        copyInfos = wfTool.manage_copyObjects(workflowName)
        newWFId = wfTool.manage_pasteObjects(copyInfos)[0]['new_id']
        # if already exists, delete it, so we are on a clean copy
        # before applying workflow_adaptations
        if duplicatedWFId in wfTool:
            wfTool.manage_delObjects(ids=[duplicatedWFId])
        wfTool.manage_renameObject(newWFId, duplicatedWFId)
        duplicatedWF = wfTool.get(duplicatedWFId)
        duplicatedWF.title = duplicatedWFId
        wfTool.setChainForPortalTypes(portalTypeNames, duplicatedWFId)
        return duplicatedWF


def duplicate_portal_type(portalTypeName, duplicatedPortalTypeId):
    """Duplicate p_portalTypeName and use duplicatedPortalTypeId for new portal_type."""
    portal_types = api.portal.get_tool('portal_types')
    copyInfos = portal_types.manage_copyObjects(portalTypeName)
    newPortalTypeId = portal_types.manage_pasteObjects(copyInfos)[0]['new_id']
    # if already exists, delete it, so we are up to date with original portal_type
    if duplicatedPortalTypeId in portal_types:
        portal_types.manage_delObjects(ids=[duplicatedPortalTypeId])
    portal_types.manage_renameObject(newPortalTypeId, duplicatedPortalTypeId)
    duplicatedPortalType = portal_types.get(duplicatedPortalTypeId)
    duplicatedPortalType.title = duplicatedPortalTypeId
    duplicatedPortalType.add_view_expr = duplicatedPortalType.add_view_expr.replace(
        portalTypeName, duplicatedPortalTypeId)
    return duplicatedPortalType


def org_id_to_uid(org_info, raise_on_error=True, ignore_underscore=False):
    """Returns the corresponding org based value for given org_info based value.
       'developers', will return 'orguid'.
       'developers_creators' will return 'orguid_creators'.
       If p_ignore_underscore=True, we specifically do not want to manage
       something like 'developers_creators' but we have an organization with
       a '_' in it's id which is not possible by default except when
       organizations were imported."""
    own_org = get_own_organization()
    try:
        if '_' in org_info and not ignore_underscore:
            org_path, suffix = org_info.split('_')
            org = own_org.restrictedTraverse(org_path.encode('utf-8'))
            return get_plone_group_id(org.UID(), suffix)
        else:
            org = own_org.restrictedTraverse(org_info.encode('utf-8'))
            return org.UID()
    except Exception, exc:
        if raise_on_error:
            raise(exc)
        else:
            return None


def get_person_from_userid(userid, only_active=True):
    """Return the person having given p_userid."""
    catalog = api.portal.get_tool('portal_catalog')
    query = {'portal_type': 'person'}
    if only_active:
        query['review_state'] = 'active'
    brains = catalog(**query)
    for brain in brains:
        person = brain.getObject()
        if person.userid == userid:
            return person


def decodeDelayAwareId(delayAwareId):
    """Decode a 'delay-aware' id, we receive something like
       'orgauid__rowid__myuniquerowid.20141215'.
       We return the org_uid and the row_id."""
    infos = delayAwareId.split('__rowid__')
    return infos[0], infos[1]


def uncapitalize(string):
    """Lowerize first letter of given p_string."""
    return string[0].lower() + string[1:]


def normalize(string, acceptable=[]):
    """Normalize given string :
       - turn é to e;
       - only keep lower letters, numbers and punctuation;
       - lowerized."""
    return ''.join(x for x in unicodedata.normalize('NFKD', string)
                   if unicodedata.category(x) != 'Mn').lower().strip()


def normalize_id(id):
    """ """
    idnormalizer = getUtility(IIDNormalizer)
    id = idnormalizer.normalize(id)
    return id


def add_wf_history_action(obj, action_name, action_label, user_id=None, insert_index=None):
    wfTool = api.portal.get_tool('portal_workflow')
    wfs = wfTool.getWorkflowsFor(obj)
    if not wfs:
        return
    wf = wfs[0]
    wfName = wf.id
    # get review_state from last event if any
    events = list(obj.workflow_history[wfName]) or []
    if events:
        previousEvent = events[-1]
        review_state_id = previousEvent['review_state']
    else:
        # use initial_state
        review_state_id = wf.initial_state
    # action comments must be translated in the imio.history domain
    newEvent = {}
    newEvent['comments'] = action_label or ''
    # action_name must be translated in the plone domain
    newEvent['action'] = action_name
    newEvent['actor'] = user_id or api.user.get_current().id
    # if an insert_index is defined, use same 'time' as previous as
    # events are sorted on 'time' and just add 1 millisecond
    if insert_index is not None:
        newEvent['time'] = events[insert_index]['time'] + 0.000000001
        newEvent['review_state'] = events[insert_index]['review_state']
        events.insert(insert_index, newEvent)
    else:
        newEvent['time'] = DateTime()
        newEvent['review_state'] = review_state_id
        events.insert(len(events), newEvent)
    obj.workflow_history[wfName] = events


def is_editing():
    """Return True if currently editing something."""
    request = getRequest()
    url = request.get('URL', '')
    edit_ends = ['/edit', '/base_edit', '/@@edit']
    res = False
    for edit_end in edit_ends:
        if url.endswith(edit_end):
            res = True
            break
    return res


def get_next_meeting(meetingDate, cfg, dateGap=0):
    '''Gets the next meeting based on meetingDate DateTime.
       p_cfg is used to know in which MeetingConfig to query next meeting.
       p_dateGap is the number of 'dead days' following the date of
       the current meeting in which we do not look for next meeting'''
    meetingTypeName = cfg.getMeetingTypeName()
    catalog = api.portal.get_tool('portal_catalog')
    # find every meetings after self.getDate
    meetingDate += dateGap
    brains = catalog(portal_type=meetingTypeName,
                     getDate={'query': meetingDate, 'range': 'min'},
                     sort_on='getDate')
    res = None
    for brain in brains:
        if brain.getDate > meetingDate:
            res = brain
            break
    if res:
        res = res.getObject()
    return res


def _base_extra_expr_ctx(obj):
    """ """
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    data = {'tool': tool,
            'cfg': cfg,
            'pm_utils': SecureModuleImporter['Products.PloneMeeting.utils'],
            'imio_history_utils': SecureModuleImporter['imio.history.utils'], }
    return data


class AdvicesUpdatedEvent(ObjectEvent):
    implements(IAdvicesUpdatedEvent)

    def __init__(self, object, triggered_by_transition=None, old_adviceIndex={}):
        self.object = object
        self.triggered_by_transition = triggered_by_transition
        self.old_adviceIndex = old_adviceIndex


class MeetingLocalRolesUpdatedEvent(ObjectEvent):
    implements(IMeetingLocalRolesUpdatedEvent)

    def __init__(self, object, old_local_roles):
        self.object = object
        self.old_local_roles = old_local_roles


class MeetingAfterTransitionEvent(TransitionEvent):
    '''
      Event triggered at the end of the onMeetingTransition,
      so we are sure that subplugins registering to this event
      will be called after.
    '''
    implements(IMeetingAfterTransitionEvent)


class ItemAfterTransitionEvent(TransitionEvent):
    '''
      Event triggered at the end of the onItemTransition,
      so we are sure that subplugins registering to this event
      will be called after.
    '''
    implements(IItemAfterTransitionEvent)


class AdviceAfterTransitionEvent(TransitionEvent):
    '''
      Event triggered at the end of the onAdviceTransition,
      so we are sure that subplugins registering to this event
      will be called after.
    '''
    implements(IAdviceAfterTransitionEvent)


class ItemDuplicatedEvent(ObjectEvent):
    implements(IItemDuplicatedEvent)

    def __init__(self, object, newItem):
        self.object = object
        self.newItem = newItem


class ItemDuplicatedToOtherMCEvent(ObjectEvent):
    implements(IItemDuplicatedToOtherMCEvent)

    def __init__(self, object, newItem):
        self.object = object
        self.newItem = newItem


class ItemDuplicatedFromConfigEvent(ObjectEvent):
    implements(IItemDuplicatedFromConfigEvent)

    def __init__(self, object, usage):
        self.object = object
        self.usage = usage


class ItemListTypeChangedEvent(ObjectEvent):
    implements(IItemListTypeChangedEvent)

    def __init__(self, object, old_listType):
        self.object = object
        self.old_listType = old_listType


class ItemLocalRolesUpdatedEvent(ObjectEvent):
    implements(IItemLocalRolesUpdatedEvent)

    def __init__(self, object, old_local_roles):
        self.object = object
        self.old_local_roles = old_local_roles


class AdviceAfterAddEvent(ObjectEvent):
    '''
      Event triggered at the end of the onAdviceAdded,
      so we are sure that subplugins registering to this event
      will be called after.
    '''
    implements(IAdviceAfterAddEvent)

    def __init__(self, object):
        self.object = object


class AdviceAfterModifyEvent(ObjectEvent):
    '''
      Event triggered at the end of the onAdviceModified,
      so we are sure that subplugins registering to this event
      will be called after onItemTransition.
    '''
    implements(IAdviceAfterModifyEvent)

    def __init__(self, object):
        self.object = object
