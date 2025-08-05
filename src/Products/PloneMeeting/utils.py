# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from AccessControl.Permission import Permission
from Acquisition import aq_base
from appy.pod.xhtml2odt import XhtmlPreprocessor
from appy.shared.diff import HtmlDiff
from bs4 import BeautifulSoup
from collective.behavior.internalnumber.browser.settings import decrement_if_last_nb
from collective.behavior.internalnumber.browser.settings import increment_nb_for
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.core.utils import get_gender_and_number
from collective.contact.core.utils import get_position_type_name
from collective.contact.core.vocabulary import get_directory
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.plonegroup.utils import get_plone_group
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.excelexport.exportables.dexterityfields import get_exportable_for_fieldname
from collective.iconifiedcategory.interfaces import IIconifiedInfos
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from datetime import datetime
from datetime import timedelta
from DateTime import DateTime
from dexterity.localroles.utils import add_fti_configuration
from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import base_getattr
from imio.helpers.content import get_schema_fields
from imio.helpers.content import get_user_fullname
from imio.helpers.content import richtextval
from imio.helpers.security import fplog
from imio.helpers.workflow import get_final_states
from imio.helpers.workflow import get_state_infos
from imio.helpers.xhtml import addClassToContent
from imio.helpers.xhtml import addClassToLastChildren
from imio.helpers.xhtml import CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT
from imio.helpers.xhtml import imagesToData
from imio.helpers.xhtml import imagesToPath
from imio.helpers.xhtml import markEmptyTags
from imio.helpers.xhtml import removeBlanks
from imio.helpers.xhtml import replace_content
from imio.helpers.xhtml import separate_images
from imio.helpers.xhtml import storeImagesLocally
from imio.helpers.xhtml import xhtmlContentIsEmpty
from imio.history.interfaces import IImioHistory
from imio.history.utils import add_event_to_history
from imio.history.utils import getLastAction
from imio.history.utils import getLastWFAction
from imio.history.utils import getPreviousEvent
from imio.pyutils.utils import safe_encode
from plone import api
from plone.app.textfield import RichText
from plone.app.textfield.value import RichTextValue
from plone.app.uuid.utils import uuidToObject
from plone.autoform.interfaces import WIDGETS_KEY
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.utils import resolveDottedName
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.locking.events import unlockAfterModification
from plone.memoize import ram
from plone.supermodel.utils import mergedTaggedValueDict
from Products.Archetypes.atapi import DisplayList
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import ManageProperties
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.DCWorkflow.events import TransitionEvent
from Products.MailHost.MailHost import MailHostError
from Products.PageTemplates.Expressions import SecureModuleImporter
from Products.PloneMeeting.config import ADD_SUBCONTENT_PERMISSIONS
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import ADVICE_STATES_ENDED
from Products.PloneMeeting.config import ADVICE_STATES_MAPPING
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import REINDEX_NEEDED_MARKER
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
from Products.PloneMeeting.interfaces import IItemPollTypeChangedEvent
from Products.PloneMeeting.interfaces import IMeetingAfterTransitionEvent
from Products.PloneMeeting.interfaces import IMeetingConfigCustom
from Products.PloneMeeting.interfaces import IMeetingCustom
from Products.PloneMeeting.interfaces import IMeetingGroupCustom
from Products.PloneMeeting.interfaces import IMeetingItemCustom
from Products.PloneMeeting.interfaces import IMeetingLocalRolesUpdatedEvent
from Products.PloneMeeting.interfaces import IToolPloneMeetingCustom
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import IContextAware
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import NOVALUE
from zope.annotation import IAnnotations
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.component.interfaces import ObjectEvent
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import implements
from zope.lifecycleevent import ObjectModifiedEvent
from zope.location import locate
from zope.schema import getFieldsInOrder
from zope.security.interfaces import IPermission

import html
import itertools
import logging
import lxml
import os
import os.path
import re
import socket
import unicodedata
import unidecode
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
    interfaceMethod = adaptables[obj.getTagName()]['method']
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
    theInterface = adaptables[obj.getTagName()]['interface']
    try:
        res = theInterface(obj)
    except TypeError:
        pass
    return res


methodTypes = ('FSPythonScript', 'FSControllerPythonScript', 'instancemethod')


def _referer_to_path(request):
    """ """
    # We are changing the state of an element. We must then check the referer
    refererUrl = request.get('HTTP_REFERER')
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
    return referer


def get_referer_obj(request):
    """ """
    referer_path = _referer_to_path(request)
    portal = api.portal.get()
    obj = None
    try:
        obj = portal.unrestrictedTraverse(referer_path)
    except Exception:
        pass
    return obj


def getCurrentMeetingObject(context):
    '''What is the object currently published by Plone ?'''
    obj = context.REQUEST.get('PUBLISHED')
    className = obj.__class__.__name__
    if className == 'present-several-items':
        return obj.context
    elif obj and \
            hasattr(obj, 'context') and \
            obj.context.getTagName() == 'Meeting':
        return obj.context

    if not (className in ('Meeting', 'MeetingItem')):
        # check if we are on a Script or so or calling a BrowserView
        if className in methodTypes or \
           'SimpleViewClass' in className or \
           'facade_actions_panel' in className:  # async_actions panel
            obj = get_referer_obj(context.REQUEST)
        else:
            # Check the parent (if it has sense)
            if hasattr(obj, 'getParentNode'):
                obj = obj.getParentNode()
                if not (obj.getTagName() in ('Meeting', 'MeetingItem')):
                    obj = None
            else:
                # It can be a method with attribute im_class
                obj = None

    toReturn = None
    if obj and obj.__class__.__name__ == 'Meeting':
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
    groupTitle = u'%s (%s)' % (
        safe_unicode(groupTitle),
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


def get_datagridfield_column_value(value, column):
    """Returns every values of a datagridfield column."""
    if not value:
        return []
    value = [row[column] for row in value
             if row.get('orderindex_', None) != 'template_row_marker' and row[column]]
    # merge lists and remove duplicates
    if value and hasattr(value[0], "__iter__"):
        value = set(list(itertools.chain.from_iterable(value)))
    return value


def field_is_empty(widget, column=None):
    """ """
    if isinstance(widget.value, RichTextValue):
        value = widget.value.raw
    elif hasattr(widget, "columns"):
        # DataGridField
        value = get_datagridfield_column_value(widget.value, column)
    else:
        value = widget.value
    if isinstance(value, (str, unicode)):
        value = value.strip()
    is_empty = True
    if value:
        is_empty = False
    return is_empty


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
        # make sure recipients are utf-8 encoded
        recipients = [safe_encode(recipient) for recipient in recipients]
        if attachments:
            # Send a single mail to everybody, for performance reasons
            # (avoid to duplicate the attached file(s))
            # Hide the whole list of recipients if we must send the mail to many.
            # every emails in recipients not in 'To' will be bcc
            body['To'] = fromAddress
            obj.MailHost.send(
                body, recipients, fromAddress, subject, charset='utf-8', msg_type=format)
        else:
            # Send a personalized email for every user
            for recipient in recipients:
                obj.MailHost.send(
                    body, recipient, fromAddress, subject, charset='utf-8', msg_type=format)
    except socket.error as sg:
        raise EmailError(SENDMAIL_ERROR % str(sg))
    except UnicodeDecodeError as ue:
        raise EmailError(ENCODING_ERROR % str(ue))
    except MailHostError as mhe:
        raise EmailError(MAILHOST_ERROR % str(mhe))
    except Exception as e:
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


def several_mc_with_same_title(cfg_title=None):
    """Return True if we have several MeetingConfigs with same title."""
    tool = api.portal.get_tool("portal_plonemeeting")
    every_cfg_titles = [cfg.Title() for cfg in tool.getActiveConfigs(check_access=False)]
    if cfg_title:
        return every_cfg_titles.count(cfg_title) > 1
    else:
        return len(every_cfg_titles) != len(set(every_cfg_titles))


def sendMail(recipients, obj, event, attachments=None, mapping={}):
    '''Sends a mail related to p_event that occurred on p_obj to
       p_recipients. If p_recipients is None, the mail is sent to
       the system administrator.'''
    # Do not sent any mail if mail mode is "deactivated".
    tool = api.portal.get_tool("portal_plonemeeting")
    cfg = tool.getMeetingConfig(obj) or tool.getActiveConfigs()[0]
    mailMode = cfg.getMailMode()
    if mailMode == 'deactivated':
        return
    # Compute user name
    user = api.user.get_current()
    # Compute list of MeetingGroups for this user
    userGroups = ', '.join([g.Title() for g in tool.get_orgs_for_user(the_objects=True)])
    # Create the message parts
    d = 'PloneMeeting'
    portal = api.portal.get()
    portalUrl = get_public_url(portal)
    if mapping:
        # we need every mappings to be unicode
        for elt in mapping:
            if not isinstance(mapping[elt], unicode):
                mapping[elt] = safe_unicode(mapping[elt])
        translation_mapping = mapping
    else:
        translation_mapping = {}

    # get last WF action but specifically manage when an transition was
    # triggered automatilcally, the comments is in the previous transition
    wf_action = getLastWFAction(obj)
    comments = wf_action['comments']
    while comments == 'wf_transition_triggered_by_application':
        wf_action = getPreviousEvent(obj, wf_action)
        comments = wf_action['comments']

    # in case we use configGroups and we have several MeetingConfig with
    # same title, this means we use configGroups to group same kind of
    # MeetingConfig, we prepend configGroup "full_label" to the "meetingConfigTitle"
    if cfg.getConfigGroup() and several_mc_with_same_title():
        cfg_title = safe_unicode(cfg.Title(include_config_group="full_label"))
    else:
        # common case
        cfg_title = safe_unicode(cfg.Title())
    wf = api.portal.get_tool('portal_workflow').getWorkflowsFor(obj)[0]
    translation_mapping.update({
        'portalUrl': portalUrl,
        'portalTitle': safe_unicode(portal.Title()),
        'objectTitle': safe_unicode(obj.Title()),
        'objectUrl': get_public_url(obj),
        'meetingTitle': '',
        'meetingLongTitle': '',
        'itemTitle': '',
        'user': get_user_fullname(user.getId()),
        'groups': safe_unicode(userGroups),
        'meetingConfigTitle': cfg_title,
        'transitionActor': wf_action and
        get_user_fullname(wf_action['actor'], with_user_id=True) or u'-',
        'transitionTitle': translate(
            safe_unicode(wf.transitions[wf_action['action']].title),
            domain="plone",
            context=obj.REQUEST) if (
                wf_action and
                wf_action['type'] == 'workflow' and
                wf_action['action'] in wf.transitions) else u'-',
        'transitionComments': wf_action and safe_unicode(wf_action['comments']) or u'-',
    })
    if obj.getTagName() == 'Meeting':
        translation_mapping['meetingTitle'] = safe_unicode(obj.Title())
        translation_mapping['meetingLongTitle'] = tool.format_date(obj.date, prefixed=True)
        translation_mapping['meetingState'] = get_state_infos(obj)['state_title']
    elif obj.getTagName() == 'MeetingItem':
        translation_mapping['itemTitle'] = safe_unicode(obj.Title())
        translation_mapping['itemState'] = get_state_infos(obj)['state_title']
        meeting = obj.getMeeting()
        if meeting:
            translation_mapping['meetingUrl'] = get_public_url(meeting)
            translation_mapping['meetingTitle'] = safe_unicode(meeting.Title())
            translation_mapping['meetingLongTitle'] = tool.format_date(meeting.date, prefixed=True)
            translation_mapping['itemNumber'] = obj.getItemNumber(
                relativeTo='meeting')

    # some event end with "Owner", we use same event without the "Owner" suffix
    subjectLabel = u'%s_mail_subject' % event.replace("Owner", "")
    subject = translate(subjectLabel,
                        domain=d,
                        mapping=translation_mapping,
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
                            mapping=translation_mapping,
                            context=obj.REQUEST)
    subject = safe_unicode(subject)
    # some event end with "Owner", we use same event without the "Owner" suffix
    bodyLabel = u'%s_mail_body' % event.replace("Owner", "")
    body = translate(bodyLabel,
                     domain=d,
                     mapping=translation_mapping,
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
                         mapping=translation_mapping,
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

    # add a fingerpointing log message
    extras = u'event={0} subject="{1}" recipients=[{2}]'.format(
        event, subject, ", ".join(recipients))
    fplog('send_mail', extras=safe_encode(extras))

    if mailMode == 'test':
        # Instead of sending mail, in test mode, we log data about the mailing.
        logger.info('Test mode / we should send mail to %s' % str(recipients))
        logger.info('Subject is [%s]' % subject)
        logger.info('Body is [%s]' % body)
        api.portal.show_message(extras, request=obj.REQUEST)
    else:
        # Use 'plain' for mail format so the email client will turn links to clickable links
        mailFormat = 'text/plain'
        # Send the mail(s)
        try:
            _sendMail(obj, body, recipients, fromAddress, subject, mailFormat, attachments)
        except EmailError as ee:
            logger.warn(str(ee))
    return obj, body, recipients, fromAddress, subject, attachments, translation_mapping


def sendMailIfRelevant(obj,
                       event,
                       value,
                       customEvent=False,
                       mapping={},
                       isSuffix=False,
                       isRole=False,
                       isPermission=False,
                       isGroupIds=False,
                       isUserIds=False,
                       debug=False):
    '''An p_event just occurred on meeting or item p_obj. If the corresponding
       meeting config specifies that a mail needs to be sent, this function
       will send a mail. The mail subject and body are defined from i18n labels
       that derive from the event name.
       p_value may vary depending on other parameters:
       - when p_isSuffix, value is a group suffix;
       - when p_isRole, value is a permission role;
       - when p_isPermission, value is a permission;
       - when p_isGroupIds, value is a list of Plone group ids;
       - whhen p_isUserIds, value is a list of Plone user ids.

       Some mapping can be received and used afterward in mail subject and mail body translations.

       If mail sending is activated (or in test mode) and enabled for this
       event, this method returns True.

       A plug-in may use this method for sending custom events that are not
       defined in the MeetingConfig. In this case, you must specify
       p_customEvent = True.'''
    tool = api.portal.get_tool(TOOL_ID)
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
    userIds = []
    membershipTool = api.portal.get_tool('portal_membership')
    if isSuffix:
        org_uid = obj.adapted()._getGroupManagingItem(obj.query_state(), theObject=False)
        plone_group = get_plone_group(org_uid, value)
        if not plone_group:
            # maybe the suffix is a MeetingConfig related suffix, like _meetingmanagers
            plone_group = get_plone_group(cfg.getId(), value)
        if plone_group:
            userIds = plone_group.getGroupMemberIds()
    elif isRole:
        if value == 'Owner':
            userIds = [obj.Creator()]
        else:
            # Warning "_members" returns all users (even deleted users),
            # the filter must do this afterwards.
            userIds = api.portal.get_tool('portal_memberdata')._members
    elif isGroupIds:
        # isGroupIds
        for plone_group_id in value:
            plone_group = api.group.get(plone_group_id)
            if plone_group:
                userIds += plone_group.getMemberIds()
    elif isUserIds:
        # isUserIds
        userIds = value
    else:
        # isPermission
        userIds = api.portal.get_tool('portal_memberdata')._members

    # remove duplicate
    userIds = list(set(userIds))
    currentUser = membershipTool.getAuthenticatedMember()
    for userId in userIds:
        user = membershipTool.getMemberById(userId)
        # do not warn user doing the action
        if not user or userId == currentUser.getId():
            continue
        if not user.getProperty('email'):
            continue
        if isPermission:
            # then "isPermission"
            # Does the user have the corresponding permission on p_obj ?
            # we do this here for performance reason as we have the "user" object
            if not api.user.has_permission(
                    permission=value, obj=obj, user=user):
                continue
        elif isRole:
            if not user.has_role(value, obj):
                continue

        recipient = getMailRecipient(user)
        # After all, we will add this guy to the list of recipients.
        recipients.append(recipient)
    subject = body = None
    if recipients:
        # wipeout recipients to avoid sendind same email to several users
        unique_emails = []
        unique_email_recipients = []
        for recipient in recipients:
            username, email = recipient.split('<')
            if email in unique_emails:
                continue
            unique_emails.append(email)
            unique_email_recipients.append(recipient)
        obj, body, recipients, fromAddress, subject, attachments, translation_mapping = \
            sendMail(unique_email_recipients, obj, event, mapping=mapping)
    debug = debug or obj.REQUEST.get('debug_sendMailIfRelevant', False)
    if debug:
        obj.REQUEST.set('debug_sendMailIfRelevant_result', (recipients, subject, body))
        return recipients, subject, body
    return True


def getMailRecipient(userIdOrInfo):
    '''This method returns the mail recipient (=string based on email and
       fullname if present) from a user id or UserInfo retrieved from a
       call to portal_membership.getMemberById.'''
    if isinstance(userIdOrInfo, basestring):
        # It is a user ID. Get the corresponding UserInfo instance
        userInfo = api.user.get(userIdOrInfo)
    else:
        userInfo = userIdOrInfo
    # We return None if the user does not exist or has no defined email.
    if not userInfo or not userInfo.getProperty('email'):
        return None
    # Compute the mail recipient string: Firstname Lastname <email@email.org>
    res = u'{0} <{1}>'.format(
        get_user_fullname(userInfo.id), safe_unicode(userInfo.getProperty('email')))
    return res


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


def getDateFromDelta(aDate, delta):
    '''This function returns a datetime instance, which is computed from a
       reference datetime instance p_aDate to which a p_delta is applied.
       A p_delta is a string having the form '<deltaDays>-<hour>:<minutes>,
       where:
        - 'deltaDays' is a positive or negative integer indicating the number of
          days to add/remove;
        - 'hour' and 'minutes' is the hour and minutes to set for the
          computed date. It means that the hour and minutes of p_aDate are
          ignored.
    '''
    days, time_info = delta.split('.')
    hour, minute = time_info.split(':')
    new_date = aDate + timedelta(int(days))
    new_date = new_date.replace(hour=int(hour), minute=int(minute))
    return new_date


def is_transition_before_date(obj, transition, date):
    '''Returns True if this p_obj last p_transition was made before p_date.
       p_date is a python datetime.datetime.'''
    res = False
    last_action = getLastWFAction(obj, transition=transition)
    if last_action:
        last_action_date = DateTime(last_action["time"])
        last_action_date._timezone_naive = True
        last_action_date = last_action_date.asdatetime()
        if last_action_date < date:
            res = True
    return res


def mark_empty_tags(obj, value):
    """ """
    if _checkPermission(ModifyPortalContent, obj):
        value = markEmptyTags(
            value,
            tagTitle=translate('blank_line',
                               domain='PloneMeeting',
                               context=obj.REQUEST),
            onlyAtTheEnd=True)
    return value


def getFieldVersion(obj, name, changes):
    '''Returns the content of field p_name on p_obj. If p_changes is True,
       historical modifications of field content are highlighted.'''
    lastVersion = obj.getField(name).getAccessor(obj)()
    # highlight blank lines at the end of the text if current user may edit the obj
    lastVersion = mark_empty_tags(obj, lastVersion)
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
    tool = api.portal.get_tool(TOOL_ID)
    cfg = tool.getMeetingConfig(obj)
    # Do nothing if the object is not in a state when historization is enabled.
    if obj.query_state() not in cfg.getRecordItemHistoryStates():
        return res
    # Store in res the values currently stored on p_obj.
    historized = cfg.getHistorizedItemAttributes()
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
    userId = get_current_user_id()
    event = {'action': '_datachange_', 'actor': userId, 'time': DateTime(),
             'comments': '', 'review_state': obj.query_state(),
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
    toLocalizedTime = obj.restrictedTraverse('@@plone').toLocalizedTime
    mapping = {'userName': get_user_fullname(event['actor'])}
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


def get_dx_attrs(portal_type,
                 optional_only=False,
                 richtext_only=False,
                 prefixed_key=False,
                 as_display_list=True):
    """ """
    res = []
    request = getRequest()
    # schema fields
    schema = get_dx_schema(portal_type=portal_type)
    schema_fields = getFieldsInOrder(schema)
    # FIELD_INFOS
    portal_types = api.portal.get_tool('portal_types')
    fti = portal_types[portal_type]
    field_infos = getattr(resolveDottedName(fti.klass), "FIELD_INFOS", {})
    for field_name, field in schema_fields:
        if optional_only and \
           (field_name not in field_infos or not field_infos[field_name]['optional']):
            continue
        if richtext_only and \
           (field.__class__.__name__ != "RichText" or field.default_mime_type != 'text/html'):
            continue
        res.append(field_name)
    if as_display_list:
        display_list_tuples = []
        for field_name in res:
            key = field_name
            if prefixed_key:
                prefix = fti.klass.split(".")[-1]
                key = "{0}.{1}".format(prefix, key)
                display_list_tuples.append(
                    (key,
                     u'%s ➔ %s' % (
                         key,
                         translate("title_{0}".format(field_name),
                                   domain="PloneMeeting",
                                   context=request))
                     ))
            else:
                display_list_tuples.append(
                    (key,
                     '%s (%s)' % (translate("title_{0}".format(field_name),
                                            domain="PloneMeeting",
                                            context=request),
                                  field_name)
                     ))

        res = DisplayList(tuple(display_list_tuples))
    return res


def get_dx_schema(obj=None, portal_type=None):
    """ """
    portal_types = api.portal.get_tool('portal_types')
    fti = portal_types[portal_type or obj.portal_type]
    schema = fti.lookupSchema()
    return schema


def get_dx_field(obj, field_name):
    """ """
    for schema_field_name, schema_field in get_schema_fields(obj):
        if schema_field_name == field_name:
            return schema_field


def get_dx_widget(obj, field_name, mode=DISPLAY_MODE):
    """ """
    orig_field_name = field_name
    if '.' in field_name:
        field_name = field_name.split('.')[1]
    field = get_dx_field(obj, field_name)
    schema = get_dx_schema(obj)
    autoform_widgets = mergedTaggedValueDict(schema, WIDGETS_KEY)
    if field_name in autoform_widgets:
        widget = autoform_widgets[field_name](field, obj.REQUEST)
    elif '.' in orig_field_name:
        # XXX to be fixed
        from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
        widget = PMRichTextFieldWidget(field, obj.REQUEST)
    else:
        widget = getMultiAdapter((field, obj.REQUEST), IFieldWidget)
    widget.context = obj
    alsoProvides(widget, IContextAware)
    widget.mode = mode
    widget.update()
    if hasattr(widget.field, "allowed_mime_types"):
        widget.field.allowed_mime_types = ['text/html']
    # this will set widget.__name__
    locate(widget, None, orig_field_name)
    widget.name = orig_field_name
    return widget


def get_dx_data(obj):
    """ """
    data = []
    # use print_value available on the documentgenerator helper view
    view = obj.unrestrictedTraverse('@@document-generation')
    helper = view.get_generation_context_helper()
    for attr_name in get_dx_attrs(obj.portal_type):
        field_content = None
        try:
            field_content = helper.print_value(attr_name, raw_xhtml=True)
        except Exception:
            logger.warning(
                "In \"utils.get_dx_data\", could not print_value for attr_name "
                "\"%s\" with value \"%s\" for element at \"%s\"" %
                (attr_name, getattr(obj, attr_name), "/".join(obj.getPhysicalPath())))
        # do not store a RichTextValue, store the rendered value
        field_value = getattr(obj, attr_name)
        if isinstance(field_value, RichTextValue):
            field_value = field_content
        data.append(
            {'field_name': attr_name,
             'field_value': field_value,
             'field_content': field_content})
    return data


def set_dx_value(obj, field_name, value, raise_unauthorized=True):
    """Convenience method to be able to set an attribute on a DX content type."""
    field = get_dx_field(obj, field_name)
    if field is not None:
        # will raise in case an error occurs
        field.validate(value)
        schema = get_dx_schema(obj)
        write_permission = schema.queryTaggedValue(
            WRITE_PERMISSIONS_KEY, {}).get(field_name, ModifyPortalContent)
        if _checkPermission(write_permission, obj):
            field.set(obj, value)
        elif raise_unauthorized:
            raise Unauthorized


def set_field_from_ajax(
        obj,
        field_name,
        new_value,
        remember=True,
        tranform=True,
        reindex=True,
        unlock=True,
        modified=True):
    '''Sets on p_obj the content of a field whose name is p_fieldName and whose
       new value is p_fieldValue. This method is called by Ajax pages.'''

    notify_modified = True
    if IDexterityContent.providedBy(obj):
        widget = get_dx_widget(obj, field_name=field_name)
        if not widget.may_edit():
            raise Unauthorized
        setattr(obj, field_name, richtextval(new_value))
    else:
        # only used for AT MeetingItem
        if not obj.mayQuickEdit(field_name):
            raise Unauthorized

        # check if quick editing field_name will change modified of item
        notify_modified = not obj.adapted()._bypass_quick_edit_notify_modified_for(field_name)

        field = obj.getField(field_name)
        if remember:
            # Keep old value, we might need to historize it.
            previousData = rememberPreviousData(obj, field_name)
            field.getMutator(obj)(new_value, mimetype='text/html')
            # Potentially store it in object history
            if previousData:
                addDataChange(obj, previousData)
        else:
            field.getMutator(obj)(new_value, mimetype='text/html')

    if tranform:
        # Apply XHTML transforms when relevant
        transformAllRichTextFields(obj, onlyField=field_name)

    if reindex:
        # only reindex relevant indexes aka SearchableText + field specific index if exists
        index_names = api.portal.get_tool('portal_catalog').indexes()
        extra_idxs = ['SearchableText']
        if field_name == 'description':
            probable_index_name = 'Description'
        else:
            probable_index_name = 'get%s%s' % (field_name[0].upper(), field_name[1:])
        if field_name in index_names:
            extra_idxs.append(field_name)
        if probable_index_name in index_names:
            extra_idxs.append(probable_index_name)
        # unmark deferred SearchableText reindexing
        setattr(obj, REINDEX_NEEDED_MARKER, False)
        notifyModifiedAndReindex(obj, notify_modified=notify_modified, extra_idxs=extra_idxs)
    if unlock:
        # just unlock, do not call ObjectEditedEvent because it does too much
        unlockAfterModification(obj, event={})
    # add a fingerpointing log message
    extras = 'object={0} field_name={1}'.format(
        repr(obj), field_name)
    fplog('quickedit_field', extras=extras)


def notifyModifiedAndReindex(obj, notify_modified=True, extra_idxs=[], notify_event=False, update_metadata=1):
    """Ease notifyModified and reindex of a given p_obj.
       If p_extra_idxs contains '*', a full reindex is done, if not
       only 'modified' related indexes are updated.
       If p_notify_event is True, the ObjectModifiedEvent is notified."""

    idxs = []
    modified_idxs = []
    if notify_modified:
        obj.notifyModified()
        modified_idxs = ['modified', 'ModificationDate', 'Date']

    if '*' not in extra_idxs:
        idxs = modified_idxs + ['pm_technical_index'] + extra_idxs

    reindex_object(obj, idxs, update_metadata=update_metadata)

    if notify_event:
        notify(ObjectModifiedEvent(obj))


def reindex_object(obj, idxs=[], no_idxs=[], update_metadata=1, mark_to_reindex=False):
    """Reimplement self.reindexObject for AT as p_update_metadata is not available.
       p_idxs and p_no_idxs are mutually exclusive, passing indexes in p_no_idxs
       means every indexes excepted these indexes.
       If p_mark_to_reindex=True then we enable the REINDEX_NEEDED_MARKER."""
    catalog = api.portal.get_tool('portal_catalog')
    indexes = catalog.indexes()
    if no_idxs:
        idxs = [i for i in indexes if i not in no_idxs]
    else:
        idxs = [i for i in idxs if i in indexes]
    if mark_to_reindex:
        if 'pm_technical_index' not in idxs:
            idxs.append('pm_technical_index')
        setattr(obj, REINDEX_NEEDED_MARKER, True)
    catalog.catalog_object(obj, idxs=list(set(idxs)), update_metadata=update_metadata)


def transformAllRichTextFields(obj, onlyField=None):
    '''Potentially, all richtext fields defined on an item (description,
       decision, etc) or a meeting (observations, ...) may be transformed via the method
       transformRichTextField that may be overridden by an adapter. This
       method calls it for every rich text field defined on this obj (item or meeting), if
       the user has the permission to update the field.'''
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    fieldsToTransform = cfg.getXhtmlTransformFields()
    transformTypes = cfg.getXhtmlTransformTypes()
    fields = {}
    if IDexterityContent.providedBy(obj):
        if onlyField:
            field = get_dx_field(obj, onlyField)
            fields[field.__name__] = getattr(obj, field.__name__).raw
        else:
            schema = get_dx_schema(obj)
            write_permissions = schema.queryTaggedValue(WRITE_PERMISSIONS_KEY, {})
            fields = {field_name: getattr(obj, field_name, None) is not None and getattr(obj, field_name).raw
                      for field_name, field in getFieldsInOrder(schema)
                      if field.__class__.__name__ == "RichText" and
                      (write_permissions.get(field.__name__) and
                       _checkPermission(write_permissions[field_name], obj) or True)}
    else:
        if onlyField:
            field = obj.schema[onlyField]
            fields[field.getName()] = field.getRaw(obj)
        else:
            fields = {field.getName(): field.getRaw(obj).strip() for field in obj.schema.fields()
                      if field.widget.getName() == 'RichWidget' and
                      _checkPermission(field.write_permission, obj)}

    for field_name, field_raw_value in fields.items():
        if not field_raw_value:
            continue
        # Apply mandatory transforms
        fieldContent = storeImagesLocally(obj, field_raw_value)
        # Apply standard transformations as defined in the config
        # fieldsToTransform is like ('MeetingItem.description', 'MeetingItem.budgetInfos', )
        if ("%s.%s" % (obj.getTagName(), field_name) in fieldsToTransform):
            if 'removeBlanks' in transformTypes:
                fieldContent = removeBlanks(fieldContent)
        if IDexterityContent.providedBy(obj):
            new_value = richtextval(fieldContent)
            setattr(obj, field_name, new_value)
        else:
            field = obj.getField(field_name)
            field.set(obj, fieldContent)
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
def forceHTMLContentTypeForEmptyRichFields(obj, field_name=None):
    '''
      While saving an empty Rich field ('text/html'),
      the contentType is set back to 'text/plain'...
      Force it to 'text/html' if the field is empty.
    '''
    if field_name:
        fields = obj.Schema().filterFields(default_content_type='text/html', __name__=field_name)
    else:
        fields = obj.Schema().filterFields(default_content_type='text/html')
    for field in fields:
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
        # transform a field or execute the TAL expression
        if tal_expr and transform['transition'] == transitionId and \
           ('.' not in transform['field_name'] or
                transform['field_name'].split('.')[0] == obj.getTagName()):
            try:
                extra_expr_ctx.update({'item': obj, })
                res = _evaluateExpression(
                    obj,
                    expression=tal_expr,
                    roles_bypassing_expression=[],
                    extra_expr_ctx=extra_expr_ctx,
                    empty_expr_is_true=False,
                    raise_on_error=True)
                # transform a field
                if '.' in transform['field_name']:
                    field = obj.getField(transform['field_name'].split('.')[1])
                    field.set(obj, res, mimetype='text/html')
                    idxs.append(field.accessor)
            except Exception as e:
                plone_utils = api.portal.get_tool('plone_utils')
                plone_utils.addPortalMessage(
                    ON_TRANSITION_TRANSFORM_TAL_EXPR_ERROR % (
                        transform['field_name'], str(e)),
                    type='warning')
                break
    # if something changed, pass supposed indexes + SearchableText
    if idxs:
        idxs.append('SearchableText')
    return idxs


# ------------------------------------------------------------------------------
def meetingExecuteActionOnLinkedItems(meeting, transitionId, items=[]):
    '''
      When the given p_transitionId is triggered on the given p_meeting,
      check if we need to trigger an action on linked items
      defined in MeetingConfig.meetingExecuteActionOnLinkedItems.
    '''
    extra_expr_ctx = _base_extra_expr_ctx(meeting)
    cfg = extra_expr_ctx['cfg']
    wfTool = api.portal.get_tool('portal_workflow')
    wf_comment = _('wf_transition_triggered_by_application')
    if not items:
        items = meeting.get_items()
    for action in cfg.getOnMeetingTransitionItemActionToExecute():
        if action['meeting_transition'] == transitionId:
            is_transition = not action['tal_expression']
            for item in items:
                if is_transition:
                    # do not fail if a transition could not be triggered, just add an
                    # info message to the log so configuration can be adapted to avoid this
                    try:
                        wfTool.doActionFor(item, action['item_action'], comment=wf_comment)
                    except WorkflowException:
                        pass
                else:
                    # execute the TAL expression, will not fail but log if an error occurs
                    # do this as Manager to avoid permission problems, the configuration
                    # is supposed to be applied
                    with api.env.adopt_roles(['Manager']):
                        extra_expr_ctx.update({'item': item, 'meeting': meeting})
                        _evaluateExpression(
                            item,
                            expression=action['tal_expression'].strip(),
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


def split_gender_and_number(value):
    """ """
    res = {}
    values = value and value.split('|') or [u'', u'', u'', u'']
    if len(values) > 1:
        res = {'MS': values[0],
               'MP': values[1],
               'FS': values[2],
               'FP': values[3]}
    else:
        res = {'MS': values[0],
               'MP': values[0],
               'FS': values[0],
               'FP': values[0]}
    return res


def _prefixed_gn_position_name(gn,
                               position_type_value,
                               include_value=False,
                               uncapitalize_position=False):
    """ """
    value_starting_vowel = {'MS': u'L\'',
                            'MP': u'Les ',
                            'FS': u'L\'',
                            'FP': u'Les ',

                            # by male singular
                            'BMS': u'de l\'',
                            # by male plural
                            'BMP': u'des ',
                            # by female singular
                            'BFS': u'de l\'',
                            # by female plural
                            'BFP': u'des ',

                            # to male singular
                            'TMS': u'à l\'',
                            # from male plural
                            'TMP': u'aux ',
                            # from female singular
                            'TFS': u'à l\'',
                            # from female plural
                            'TFP': u'aux ',
                            }
    value_starting_consonant = {'MS': u'Le ',
                                'MP': u'Les ',
                                'FS': u'La ',
                                'FP': u'Les ',

                                # by male singular
                                'BMS': u'du ',
                                # by male plural
                                'BMP': u'des ',
                                # by female singular
                                'BFS': u'de la ',
                                # by female plural
                                'BFP': u'des ',

                                # to male singular
                                'TMS': u'au ',
                                # from male plural
                                'TMP': u'aux ',
                                # from female singular
                                'TFS': u'à la ',
                                # from female plural
                                'TFP': u'aux ',
                                }
    # startswith vowel or consonant?
    first_letter = safe_unicode(position_type_value[0])
    # turn "é" to "e"
    first_letter = unidecode.unidecode(first_letter)
    if first_letter.lower() in ['a', 'e', 'i', 'o', 'u']:
        mappings = value_starting_vowel
    else:
        mappings = value_starting_consonant
    res = mappings.get(gn, u'')
    if include_value:
        # we lowerize first letter of position_type_value
        position_type_value = uncapitalize_position and \
            uncapitalize(position_type_value) or position_type_value
        res = u'{0}{1}'.format(res, position_type_value)
    return res


def get_prefixed_gn_position_name(contacts,
                                  position_type,
                                  include_value=True,
                                  uncapitalize_position=False,
                                  use_by=False,
                                  use_to=False):
    """This will generate an arbitraty prefixed gendered/numbered position_type."""
    gn = get_gender_and_number(contacts, use_by=use_by, use_to=use_to)
    position_type_value = get_gn_position_name(contacts, position_type)
    return _prefixed_gn_position_name(
        gn,
        position_type_value,
        include_value=include_value,
        uncapitalize_position=uncapitalize_position)


def get_gn_position_name(contacts, position_type):
    """Get a gendered/numbered position_name from given list
       of p_contacts and directory p_position_type."""
    gn = get_gender_and_number(contacts)
    position_name = get_position_type_name(get_directory(contacts[0]), position_type)
    return split_gender_and_number(position_name)[gn]


def get_attendee_short_title(hp, cfg, item=None, meeting=None, **kwargs):
    '''Helper that return short title for given p_hp,
       taking into account that p_hp position may be redefined for self.'''
    position_type = None
    if item is not None:
        position_type = meeting.get_attendee_position_for(
            item.UID(), hp.UID())
    include_voting_group = cfg.getDisplayVotingGroup()
    return hp.get_short_title(
        forced_position_type_value=position_type,
        include_voting_group=include_voting_group,
        **kwargs)


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


def toHTMLStrikedContent(html_content):
    """
      p_content is HTML having elements to strike between [[]].
      We will replace these [[]] by <strike> tags.
    """
    html_content = html_content.replace('[[', '<strike>').replace(']]', '</strike>')
    return html_content


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


def display_as_html(plain_content, obj, mark_empty_tags=False, striked=False):
    """Display p_plain_content as HTML, especially ending lines
       that are not displayed if empty."""
    # when used in a datagrid field, sometimes we get strange content...
    plain_content = plain_content if plain_content and not isinstance(plain_content, NOVALUE.__class__) else ''
    portal_transforms = api.portal.get_tool('portal_transforms')
    html_content = portal_transforms.convertTo('text/html', plain_content).getData()
    html_content = html_content.replace('\r', '')
    if striked:
        html_content = toHTMLStrikedContent(html_content)
    if mark_empty_tags and _checkPermission(ModifyPortalContent, obj):
        # replace ending <p> by empty tags
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
        if base_hasattr(published, "getTagName"):
            context = published
        else:
            context = base_hasattr(published, 'context') and published.context or None
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
    """Check if given p_obj was modified since last version (history)."""
    adapter = getAdapter(obj, IImioHistory, 'advice_given')
    last_event = getLastAction(adapter)
    modified = True
    if last_event:
        # keep >= for backward compatibility as before, modified was set to timestamp, now it is older...
        if last_event['time'] >= obj.modified():
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


def historize_object_data(obj, comment):
    """Historize p_obj data and parent's data.
       An optionnal p_comment may be defined and will be usedappear in the versions history."""
    # compute advice data and item data
    item_data = main_item_data(obj.aq_parent)
    advice_data = get_dx_data(obj)
    add_event_to_history(
        obj,
        'advice_given_history',
        action='advice_given_or_modified',
        comments=comment,
        extra_infos={'item_data': item_data,
                     'advice_data': advice_data})


def get_event_field_data(event_data, field_name, data_type="field_value"):
    """ """
    data = [field[data_type] for field in event_data
            if field["field_name"] == field_name]
    return data[0] if data else None


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
            schema = get_dx_schema(obj)
            write_permissions = schema.queryTaggedValue(WRITE_PERMISSIONS_KEY, {})
            for field_id, write_permission in write_permissions.items():
                # only consider enabled fields
                if isinstance(schema.get(field_id), RichText) and \
                        obj.attribute_is_used(field_id):
                    write_perms.append(write_permission)
        else:
            # Archetypes
            for field in obj.Schema().filterFields(default_content_type='text/html'):
                # only consider enabled fields, for example as MeetingItem.internalNotes
                # is editable in every states, that will give the permission in every
                # states, but only when field used
                if field.write_permission and obj.attribute_is_used(field.getName()):
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
        # give it to roles having 'PloneMeeting: add annex' or
        # 'PloneMeeting: add annexDecision' permission
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


def getAdvicePortalTypeIds_cachekey(method):
    '''cachekey method for getAdvicePortalTypes.'''
    return True


@ram.cache(getAdvicePortalTypeIds_cachekey)
def getAdvicePortalTypeIds():
    """We may have several 'meetingadvice' portal_types,
       return it as ids."""
    return getAdvicePortalTypes(as_ids=True)


def getAdvicePortalTypes(as_ids=False):
    """We may have several 'meetingadvice' portal_types."""
    typesTool = api.portal.get_tool('portal_types')
    res = []
    for portal_type in typesTool.listTypeInfo():
        if portal_type.id.startswith('meetingadvice'):
            res.append(portal_type)
    if as_ids:
        res = [p.id for p in res]
    return res


def findMeetingAdvicePortalType(context):
    """ """
    advicePortalTypeIds = getAdvicePortalTypeIds()
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


def get_advice_alive_states():
    """Return every WF states considered as alive states (WF not ended)."""
    res = []
    wf_tool = api.portal.get_tool('portal_workflow')
    for adv_pt in getAdvicePortalTypeIds():
        res += wf_tool.getWorkflowsFor(adv_pt)[0].states.keys()
    # remove the ADVICE_STATES_ENDED and duplicates
    return tuple(set([state_id for state_id in res
                      if state_id not in ADVICE_STATES_ENDED]))


def getAvailableMailingLists(obj, pod_template, include_recipients=False):
    '''Gets the names of the (currently active) mailing lists defined for
       this template.'''
    res = []
    mailing_lists = pod_template.mailing_lists and pod_template.mailing_lists.strip()
    if not mailing_lists:
        return res
    try:
        extra_expr_ctx = _base_extra_expr_ctx(obj)
        extra_expr_ctx.update({'obj': obj, })
        for line in mailing_lists.split('\n'):
            name, expression, userIds = line.split(';')
            if not expression or _evaluateExpression(
                    obj,
                    expression,
                    roles_bypassing_expression=[],
                    extra_expr_ctx=extra_expr_ctx,
                    raise_on_error=True):
                # escape as name in JS is escaped to manage name with "'"
                name = html.escape(name.strip())
                if include_recipients:
                    res.append((name, extract_recipients(obj, userIds)))
                else:
                    res.append(name)
    except Exception as exc:
        msg = translate(
            'Mailing lists are not correctly defined, original error is \"${error}\"',
            domain='PloneMeeting',
            mapping={'error': str(exc)},
            context=obj.REQUEST)
        if include_recipients:
            res.append((msg, []))
        else:
            res.append(msg)
    return res


def extract_recipients(obj, values):
    """ """
    # compile userIds in case we have a TAL expression
    recipients = []
    userIdsOrEmailAddresses = []
    extra_expr_ctx = _base_extra_expr_ctx(obj)
    extra_expr_ctx.update({'obj': obj, })
    for value in values.strip().split(','):
        # value may be a TAL expression returning a list of userIds or email addresses
        # or a group (of users)
        # or a userId
        # or an e-mail address
        if value.startswith('python:') or '/' in value:
            evaluatedExpr = _evaluateExpression(
                obj,
                expression=value.strip(),
                extra_expr_ctx=extra_expr_ctx)
            userIdsOrEmailAddresses += list(evaluatedExpr)
        elif value.startswith('group:'):
            group = api.group.get(value[6:])
            userIdsOrEmailAddresses += list(group.getMemberIds())
        else:
            userIdsOrEmailAddresses.append(value)
    # now we have userIds or email address, we want email addresses
    for userIdOrEmailAddress in userIdsOrEmailAddresses:
        recipient = '@' in userIdOrEmailAddress and userIdOrEmailAddress or \
            getMailRecipient(userIdOrEmailAddress.strip())
        if not recipient:
            continue
        if recipient not in recipients:
            recipients.append(recipient)
    return recipients


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
    for k, v in base_getattr(container, 'categorized_elements', {}).items():
        # do not fail on 'Members', use unrestrictedTraverse
        try:
            annex = portal.unrestrictedTraverse(v['relative_url'])
        except Exception:
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
        v['last_updated'] = datetime.now()
    container._p_changed = True


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


def checkMayQuickEdit(obj,
                      bypassWritePermissionCheck=False,
                      permission=ModifyPortalContent,
                      expression='',
                      onlyForManagers=False,
                      bypassMeetingClosedCheck=False):
    """ """
    from Products.PloneMeeting.content.meeting import Meeting
    tool = api.portal.get_tool('portal_plonemeeting')
    res = False
    meeting = obj.getTagName() == "Meeting" and obj or (obj.hasMeeting() and obj.getMeeting())
    if (not onlyForManagers or (onlyForManagers and tool.isManager(tool.getMeetingConfig(obj)))) and \
       (bypassWritePermissionCheck or _checkPermission(permission, obj)) and \
       (_evaluateExpression(obj, expression)) and \
       (not (not bypassMeetingClosedCheck and
        meeting and
        meeting.query_state() in Meeting.MEETINGCLOSEDSTATES) or
            tool.isManager(realManagers=True)):
        res = True
    return res


def may_view_field(obj, field_name):
    """Check if current user has permission and condition to see the given p_field_name."""
    field = obj.getField(field_name)
    return _checkPermission(field.read_permission, obj) and \
        _evaluateExpression(obj, field.widget.condition)


def get_states_before_cachekey(method, obj, review_state):
    '''cachekey method for get_states_before.'''
    # do only re-compute if cfg changed or params changed
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    return (cfg.getId(), cfg._p_mtime, review_state)


@ram.cache(get_states_before_cachekey)
def get_states_before(obj, review_state_id):
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


def get_item_validation_wf_suffixes(cfg, org_uid=None, only_enabled=True):
    """Returns suffixes related to MeetingItem validation WF,
       so the 'creators', 'observers' and suffixes managed by
       MeetingConfig.itemWFValidationLevels.
       If p_org is given, we only return available suffixes."""
    base_suffixes = [u'creators', u'observers']
    # we get the principal suffix from level['suffix'] then level['extra_suffixes']
    # is containing suffixes that will also get Editor access in relevant state
    config_suffixes = cfg.getItemWFValidationLevels(
        data='suffix', only_enabled=only_enabled)
    # special case when using no item WF validation at all, so items are created "validated"
    # we use the extra_suffixes to give access to the item as by default for example
    # as "reviewers" not in the workflow, they do not get access to the "validated" item
    if not config_suffixes:
        config_extra_suffixes = cfg.getItemWFValidationLevels(
            states=['itemcreated'],
            data='extra_suffixes',
            only_enabled=False,
            return_state_singleton=False)
    else:
        config_extra_suffixes = cfg.getItemWFValidationLevels(
            data='extra_suffixes', only_enabled=only_enabled)
    # flatten, config_extra_suffixes is a list of lists
    config_extra_suffixes = list(itertools.chain.from_iterable(config_extra_suffixes))
    suffixes = list(set(base_suffixes + config_suffixes + config_extra_suffixes))
    if org_uid:
        # only return suffixes that are available for p_org
        available_suffixes = set(get_all_suffixes(org_uid))
        suffixes = list(available_suffixes.intersection(set(suffixes)))
    return suffixes


def compute_item_roles_to_assign_to_suffixes_cachekey(method, cfg, item, item_state, org_uid=None):
    '''cachekey method for compute_item_roles_to_assign_to_suffixes.'''
    # we do not use item in the key, cfg and item_state is sufficient
    return cfg.getId(), cfg.modified(), item_state, org_uid


@ram.cache(compute_item_roles_to_assign_to_suffixes_cachekey)
def compute_item_roles_to_assign_to_suffixes(cfg, item, item_state, org_uid=None):
    """ """
    apply_meetingmanagers_access = True
    suffix_roles = {}

    # roles given to item_state are managed automatically
    # it is possible to manage it manually for extra states (coming from wfAdaptations for example)
    # try to find corresponding item state
    corresponding_auto_item_state = cfg.adapted().get_item_corresponding_state_to_assign_local_roles(
        item_state)
    if corresponding_auto_item_state:
        item_state = corresponding_auto_item_state
    else:
        # if no corresponding item state, check if we manage state suffix roles manually
        apply_meetingmanagers_access, suffix_roles = cfg.adapted().get_item_custom_suffix_roles(
            item, item_state)

    # find suffix_roles if it was not managed manually
    if suffix_roles:
        return apply_meetingmanagers_access, suffix_roles

    # we get every states, including disabled ones so for example we may use
    # "itemcreated" even if it is disabled
    item_val_levels_states = cfg.getItemWFValidationLevels(
        data='state', only_enabled=False)

    # by default, observers may View in every states as well as creators
    # for observers, this also depends on MeetingConfig.itemObserversStates if defined
    suffix_roles = {'creators': ['Reader'], }
    if not cfg.getItemObserversStates() or item_state in cfg.getItemObserversStates():
        suffix_roles['observers'] = ['Reader']

    # MeetingConfig.itemWFValidationLevels
    # states before validated
    if item_state in item_val_levels_states:
        # find Editor suffixes
        # walk every defined validation levels so we give 'Reader'
        # to levels already behind us
        for level in cfg.getItemWFValidationLevels(only_enabled=False):
            suffixes = [level['suffix']] + list(level['extra_suffixes'])
            for suffix in suffixes:
                if suffix not in suffix_roles:
                    suffix_roles[suffix] = []
                # 'Contributor' will allow add annex decision
                given_roles = ['Reader', 'Contributor']
                # we are on the current state
                if level['state'] == item_state:
                    given_roles.append('Editor')
                    given_roles.append('Reviewer')
                for role in given_roles:
                    if role not in suffix_roles[suffix]:
                        suffix_roles[suffix].append(role)
            if level['state'] == item_state:
                break

    # states out of item validation (validated and following states)
    else:
        # every item validation suffixes get View access
        # we also give the Contributor except to 'observers'
        # so every editors roles get the "PloneMeeting: Add decision annex"
        # permission that let add decision annex
        for suffix in get_item_validation_wf_suffixes(cfg, org_uid):
            given_roles = ['Reader']
            if item.may_add_annex_decision(cfg, item_state) and suffix != 'observers':
                given_roles.append('Contributor')
            suffix_roles[suffix] = given_roles

    return apply_meetingmanagers_access, suffix_roles


def is_proposing_group_editor(org_uid, cfg):
    """ """
    suffixes = cfg.getItemWFValidationLevels(data='suffix', only_enabled=True)
    return cfg.aq_parent.user_is_in_org(org_uid=org_uid, suffixes=suffixes)


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
        # use get or unrestrictedTraverse depending on fact that
        # org_path is a path or a single str
        getter = "/" in org_info and own_org.unrestrictedTraverse or own_org.get
        if '_' in org_info and not ignore_underscore:
            org_path, suffix = org_info.split('_')
            org = getter(org_path.encode('utf-8'))
            return get_plone_group_id(org.UID(), suffix)
        else:
            org = getter(org_info.encode('utf-8'))
            if org:
                return org.UID()
    except Exception as exc:
        if raise_on_error:
            raise(exc)
        else:
            return None


def decodeDelayAwareId(delayAwareId):
    """Decode a 'delay-aware' id, we receive something like
       'orgauid__rowid__myuniquerowid.20141215'.
       We return the org_uid and the row_id."""
    infos = delayAwareId.split('__rowid__')
    if '__userid__' in infos[0]:
        infos[0] = infos[0].split('__userid__')[0]
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


def _clear_local_roles(obj):
    """ """
    # remove every localRoles then recompute
    old_local_roles = obj.__ac_local_roles__.copy()
    obj.__ac_local_roles__.clear()
    # add 'Owner' local role
    obj.manage_addLocalRoles(obj.owner_info()['id'], ('Owner',))
    return old_local_roles


def is_editing(cfg):
    """Return True if currently editing something."""
    request = getRequest()
    url = request.get('URL', '')
    edit_ends = ['/edit', '/base_edit', '/@@edit']
    edit_ends.append('/++add++{0}'.format(cfg.getItemTypeName()))
    edit_ends.append('/++add++{0}'.format(cfg.getMeetingTypeName()))
    res = False
    for edit_end in edit_ends:
        if url.endswith(edit_end):
            res = True
            break
    return res


def get_next_meeting(meeting_date, cfg, date_gap=0):
    '''Gets the next meeting based on meetingDate DateTime.
       p_cfg is used to know in which MeetingConfig to query next meeting.
       p_dateGap is the number of 'dead days' following the date of
       the current meeting in which we do not look for next meeting'''
    meetingTypeName = cfg.getMeetingTypeName()
    catalog = api.portal.get_tool('portal_catalog')
    # find every meetings after meetingDate
    meeting_date += timedelta(days=date_gap)
    brains = catalog(
        portal_type=meetingTypeName,
        meeting_date={'query': meeting_date,
                      'range': 'min'},
        sort_on='meeting_date')
    res = None
    for brain in brains:
        meeting = brain.getObject()
        if meeting.date > meeting_date:
            res = meeting
            break
    return res


def _base_extra_expr_ctx(obj):
    """ """
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    # member, context and portal are managed by
    # collective.behavior.talcondition or collective.documentgenerator
    data = {'tool': tool,
            'cfg': cfg,
            # backward compatibility
            'meetingConfig': cfg,
            'meeting': obj.getMeeting() if obj.__class__.__name__ == 'MeetingItem' else None,
            # backward compatibility, "member" will be available by default
            'user': api.user.get_current(),
            'catalog': api.portal.get_tool('portal_catalog'),
            # give ability to access annexes some package safe utils
            'collective_iconifiedcategory_utils': SecureModuleImporter['collective.iconifiedcategory.safe_utils'],
            'contact_core_utils': SecureModuleImporter['collective.contact.core.safe_utils'],
            'contact_plonegroup_utils': SecureModuleImporter['collective.contact.plonegroup.safe_utils'],
            'imio_annex_utils': SecureModuleImporter['imio.annex.safe_utils'],
            'imio_history_utils': SecureModuleImporter['imio.history.safe_utils'],
            'utils': SecureModuleImporter['Products.PloneMeeting.safe_utils'],
            'pm_utils': SecureModuleImporter['Products.PloneMeeting.safe_utils'], }
    return data


def down_or_up_wf(obj):
    """Return "", "down", or "up" depending on workflow history."""
    # down the workflow, the last transition was a backTo... transition
    wfTool = api.portal.get_tool('portal_workflow')
    wf = wfTool.getWorkflowsFor(obj)[0]
    backTransitionIds = [tr for tr in wf.transitions if tr.startswith('back')]
    transitionIds = [tr for tr in wf.transitions if not tr.startswith('back')]
    # get the last event that is a real workflow transition event
    lastEvent = getLastWFAction(obj, transition=backTransitionIds + transitionIds)
    res = ""
    if lastEvent and lastEvent['action']:
        if lastEvent['action'].startswith('back'):
            res = "down"
        # make sure it is a transition because we save other actions too in workflow_history
        else:
            # up the workflow for at least second times and not linked to a meeting
            # check if last event was already made in item workflow_history
            history = obj.workflow_history[wf.getId()]
            i = 0
            for event in history:
                if event['action'] == lastEvent['action']:
                    i = i + 1
                    if i > 1:
                        res = "up"
                        break
    return res


def redirect(request, url):
    """Manage when view is called by an ajax request and
       must not return anything but reload the page or faceted (in JS)."""
    # ajax request or overlay
    if "_" in request or "ajax_load" in request:
        request.RESPONSE.setStatus(204)
        return ""
    else:
        return request.RESPONSE.redirect(url)


def number_word(number):
    """ """
    request = getRequest()
    suppl_word_msgid = number == 1 and "num_part_st" or "num_part_th"
    suppl_word = translate(msgid=suppl_word_msgid,
                           domain="PloneMeeting",
                           mapping={'number': number},
                           context=request,
                           default=u"${number}st/th")
    return suppl_word


def escape(text):
    return html.escape(safe_unicode(text), quote=True)


def convert2xhtml(obj,
                  xhtmlContents,
                  image_src_to_paths=False,
                  image_src_to_data=False,
                  separatorValue='',
                  keepWithNext=False,
                  keepWithNextNumberOfChars=CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT,
                  checkNeedSeparator=False,
                  addCSSClass=None,
                  anonymize=False,
                  use_safe_html=False,
                  use_appy_pod_preprocessor=False,
                  clean=False):
    """Helper method to format a p_xhtmlContents.  The xhtmlContents is a list or a string containing
       either XHTML content or some specific recognized words like :
       - 'separator', in this case, it is replaced with the p_separatorValue;
       Given xhtmlContents are all merged together to be printed in the document.
       If p_keepWithNext is True, signatureNotAlone is applied on the resulting XHTML.
       If p_image_src_to_paths is True, if some <img> are contained in the XHTML, the link to the image
       is replaced with a path to the .blob of the image of the server so LibreOffice may access it.
       Indeed, private images not accessible by anonymous may not be reached by LibreOffice.
       If p_checkNeedSeparator is True, it will only add the separator if previous
       xhtmlContent did not contain empty lines at the end.
       If addCSSClass is given, a CSS class will be added to every tags of p_chtmlContents.
       Finally, the separatorValue is used when word 'separator' is encountered in xhtmlContents.
       A call to printXHTML in a POD template with an item as context could be :
       view.printXHTML(self.getMotivation(), 'separator', '<p>DECIDE :</p>', 'separator', self.getDecision())
       BY DEFAULT, THIS WILL DO NOTHING!
    """
    xhtmlFinal = ''
    # xhtmlContents may be a single string value or a list
    if not hasattr(xhtmlContents, '__iter__'):
        xhtmlContents = [xhtmlContents]
    for xhtmlContent in xhtmlContents:
        if isinstance(xhtmlContent, RichTextValue):
            xhtmlContent = xhtmlContent.output
        if xhtmlContent is None:
            xhtmlContent = ''
        if xhtmlContent == 'separator':
            hasSeparation = False
            if checkNeedSeparator:
                preparedXhtmlContent = "<special_tag>%s</special_tag>" % xhtmlContent
                tree = lxml.html.fromstring(safe_unicode(preparedXhtmlContent))
                children = tree.getchildren()
                if children and not children[-1].text:
                    hasSeparation = True
            if not hasSeparation:
                xhtmlFinal += separatorValue
        else:
            xhtmlFinal += xhtmlContent

    # manage image_src_to_paths/image_src_to_data, exclusive parameters
    # turning http link to image to blob path will avoid unauthorized by appy.pod
    if image_src_to_paths:
        xhtmlFinal = imagesToPath(obj, xhtmlFinal)
    elif image_src_to_data:
        # turning http link to image to data base64 value will make html "self-supporting"
        xhtmlFinal = imagesToData(obj, xhtmlFinal)

    # manage keepWithNext
    if keepWithNext:
        xhtmlFinal = signatureNotAlone(xhtmlFinal, numberOfChars=keepWithNextNumberOfChars)

    # manage addCSSClass
    if addCSSClass:
        xhtmlFinal = addClassToContent(xhtmlFinal, addCSSClass)

    # manage anonymize_css_class
    if anonymize:
        if anonymize is True:
            css_class = "pm-anonymize"
            new_content = u""
            new_content_link = {}
        else:
            css_class = anonymize["css_class"]
            new_content = anonymize.get("new_content", u"")
            new_content_link = anonymize.get("new_content_link", u"")

        xhtmlFinal = replace_content(
            xhtmlFinal,
            css_class=css_class,
            new_content=new_content,
            new_content_link=new_content_link)

    if clean:
        xhtmlFinal = separate_images(xhtmlFinal)

    # use_safe_html to clean the HTML
    # originally it was used to make xhtmlContents XHTML compliant
    # by replacing <br> with <br /> for example, but now it is done
    # by appy.pod calling the Rendered with html=True parameter
    # so use_safe_html=False by default
    if use_safe_html:
        pt = api.portal.get_tool('portal_transforms')
        xhtmlFinal = pt.convert('safe_html', xhtmlFinal).getData()

    if use_appy_pod_preprocessor:
        xhtmlFinal = XhtmlPreprocessor.html2xhtml(xhtmlFinal)

    return xhtmlFinal


def isPowerObserverForCfg_cachekey(method, cfg, power_observer_types=[]):
    '''cachekey method for isPowerObserverForCfg.'''
    return (get_plone_groups_for_user(),
            repr(cfg),
            power_observer_types)


# not ramcached perf tests says it does not change anything
# and this avoid useless entry in cache
# @ram.cache(isPowerObserverForCfg_cachekey)
def isPowerObserverForCfg(cfg, power_observer_types=[]):
    """
      Returns True if the current user is a power observer
      for the given p_itemOrMeeting.
      It is a power observer if member of the corresponding
      p_power_observer_types suffixed groups.
      If no p_power_observer_types we check every existing power_observers groups.
    """
    user_plone_groups = get_plone_groups_for_user()
    for po_infos in cfg.getPowerObservers():
        if not power_observer_types or po_infos['row_id'] in power_observer_types:
            groupId = "{0}_{1}".format(cfg.getId(), po_infos['row_id'])
            if groupId in user_plone_groups:
                return True
    return False


def get_annexes_config(context, portal_type="annex", annex_group=False):
    """ """
    if portal_type == 'annexDecision':
        context.REQUEST.set('force_use_item_decision_annexes_group', True)
        config = get_config_root(context)
        if annex_group:
            group = get_group(config, context)
        context.REQUEST.set('force_use_item_decision_annexes_group', False)
    else:
        config = get_config_root(context)
        if annex_group:
            group = get_group(config, context)
    if annex_group:
        return group
    return config


def get_enabled_ordered_wfas(tool):
    """Return a list of ordered WFAdaptations currently enabled in every MeetingConfigs."""
    from Products.PloneMeeting.MeetingConfig import MeetingConfig
    return tuple(
        [wfa for wfa in MeetingConfig.wfAdaptations
         if wfa in itertools.chain.from_iterable(
             [cfg.getWorkflowAdaptations() for cfg in tool.objectValues('MeetingConfig')])])


def get_internal_number(obj, init=False):
    """Return an item internalnumber.
       If p_init=True, itemnumber is initialized if relevant."""
    internal_number = base_getattr(obj, "internal_number", None)
    if init and internal_number is None and not obj.isDefinedInTool():
        # internalnumber is a DX behavior and default value is the next available
        # we init and increment here, decrement is managed upon edit cancel
        next_nb = increment_nb_for(obj, bypass_attr_check=True)
        # if not enabled for portal_type, then next_nb is None
        if next_nb:
            # we get next_nb but current nb is next - 1
            internal_number = next_nb - 1
            setattr(obj, "internal_number", internal_number)
    return internal_number


def set_internal_number(obj, value, update_ref=False, reindex=True, decrement=False):
    """Set the internal_number for a given p_obj. If p_update_ref is True we also
    update the item reference. If reindex is True, we reindex the internal_number index.
    If decrement is True, we decrement global counter if it was last value."""
    # manage decrement before setting value
    if decrement:
        decrement_if_last_nb(obj)
    setattr(obj, "internal_number", value)
    if update_ref:
        obj.update_item_reference()
    if reindex:
        # there is only an index, no metadata related to "internal_number"
        reindex_object(obj, idxs=['internal_number'], update_metadata=False)


def _get_category(obj, cat_id, the_object=False, cat_type='categories'):
    """Get the cat_type "category" on an item or meeting.
       p_cat_type may be "categories", "classifiers" or "meetingcategories"."""
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    if the_object:
        # return '' if category does not exist or is None
        res = ''
        # avoid problems with acquisition or if cat_id is None
        if cat_id in cfg.get(cat_type).objectIds():
            res = cfg.get(cat_type).get(cat_id)
    else:
        res = cat_id
    return res


def configure_advice_dx_localroles_for(portal_type, org_uids=[]):
    """Configure the DX localroles for an advice portal_type:
       - initial_state receives no role;
       - final state receives "Reviewer" role;
       - other states receive "Editor/Reviewer/Contributor" roles."""
    wf_tool = api.portal.get_tool('portal_workflow')
    wf = wf_tool.getWorkflowsFor(portal_type)[0]
    roles_config = {
        'advice_group': {}
    }
    final_state_ids = get_final_states(wf, ignored_transition_ids=['giveAdvice'])
    # compute suffixes
    suffixes = []
    if org_uids:
        for org_uid in org_uids:
            suffixes += get_all_suffixes(org_uid=org_uid)
        # remove duplicates
        suffixes = list(set(suffixes))
    else:
        suffixes = get_all_suffixes()
    for state in wf.states.values():
        if state.id == 'advice_given':
            # special case, 'advice_given' is a state always existing in any
            # advice related workflow and is the technical final state
            roles_config['advice_group'][state.id] = {
                'advisers': {'roles': [], 'rel': ''}}
        else:
            # get suffix from ADVICE_STATES_MAPPING, if suffix does not exist
            # in plonegroup, we will use "advisers"
            suffix = ADVICE_STATES_MAPPING.get(state.id, u'advisers')
            # make sure suffix is used or we use u'advisers'
            # this let's have a common ADVICE_STATES_MAPPING with some exceptions
            suffix = suffix if suffix in suffixes else u'advisers'
            if state.id in final_state_ids:
                roles_config['advice_group'][state.id] = {
                    suffix: {'roles': [u'Reviewer'], 'rel': ''}}
            else:
                # any other states, most of states actually
                roles_config['advice_group'][state.id] = {
                    suffix: {'roles': [u'Editor', u'Reviewer', u'Contributor'],
                             'rel': ''}}
    msg = add_fti_configuration(portal_type=portal_type,
                                configuration=roles_config['advice_group'],
                                keyname='advice_group',
                                force=True)
    if msg:
        logger.warn(msg)


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


class ItemPollTypeChangedEvent(ObjectEvent):
    implements(IItemPollTypeChangedEvent)

    def __init__(self, object, old_pollType):
        self.object = object
        self.old_pollType = old_pollType


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
