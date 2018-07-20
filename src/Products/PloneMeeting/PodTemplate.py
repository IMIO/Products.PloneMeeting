# -*- coding: utf-8 -*-
#
# File: PodTemplate.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from appy.pod.renderer import Renderer
from appy.shared.utils import normalizeString
from Products.Archetypes.atapi import *
from Products.CMFCore.Expression import createExprContext
from Products.CMFCore.Expression import Expression
from Products.CMFCore.utils import getToolByName
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.PageTemplates.Expressions import getEngine
from Products.PloneMeeting.config import *
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.utils import clonePermissions
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldContent
from Products.PloneMeeting.utils import sendMail
from StringIO import StringIO
from zope.interface import implements

import appy.pod
import interfaces
import logging
##code-section module-header #fill in your manual code here
import os
import tempfile
import time


logger = logging.getLogger('PloneMeeting')

MAILINGLIST_CONDITION_ERROR = 'There was an error in the TAL expression ' \
    'defining if the mailinglist with title \'%s\' should be available. ' \
    'Returned error is : \'%s\''
UNABLE_TO_DETECT_MIMETYPE_ERROR = 'There was an error while trying to detect ' \
                                  'the mimetype of the document to generate. ' \
                                  'Please contact system administrator.'
##/code-section module-header

schema = Schema((

    FileField(
        name='podTemplate',
        widget=FileField._properties['widget'](
            description="PodTemplate",
            description_msgid="pod_template_descr",
            label='Podtemplate',
            label_msgid='PloneMeeting_label_podTemplate',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        storage=AttributeStorage(),
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='podFormat',
        widget=SelectionWidget(
            description="PodFormat",
            description_msgid="pod_format_doc",
            label='Podformat',
            label_msgid='PloneMeeting_label_podFormat',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        vocabulary='listPodFormats',
        default="odt",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='podCondition',
        widget=StringField._properties['widget'](
            size=100,
            description="PodCondition",
            description_msgid="pod_condition_descr",
            label='Podcondition',
            label_msgid='PloneMeeting_label_podCondition',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='podPermission',
        widget=MultiSelectionWidget(
            description="PodPermission",
            description_msgid="pod_permission_descr",
            size=10,
            label='Podpermission',
            label_msgid='PloneMeeting_label_podPermission',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listPodPermissions',
        default="View",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='freezeEvent',
        widget=SelectionWidget(
            description="FreezeEvent",
            description_msgid="freeze_event_descr",
            label='Freezeevent',
            label_msgid='PloneMeeting_label_freezeEvent',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listFreezeEvents',
    ),
    TextField(
        name='mailingLists',
        allowable_content_types=('text/plain',),
        widget=TextAreaWidget(
            description="PTMailingLists",
            description_msgid="pt_mailing_lists_descr",
            label='Mailinglists',
            label_msgid='PloneMeeting_label_mailingLists',
            i18n_domain='PloneMeeting',
        ),
        default_output_type='text/plain',
        default_content_type='text/plain',
        write_permission="PloneMeeting: Write risky config",
    ),

),
)

##code-section after-local-schema #fill in your manual code here
# Error-related constants ------------------------------------------------------
POD_ERROR = 'An error occurred while generating the document. Please check ' \
            'the following things if you wanted to generate the document in ' \
            'PDF, DOC or RTF: (1) OpenOffice is started in server mode on ' \
            'the port you should have specified in the PloneMeeting ' \
            'configuration (go to Site setup-> PloneMeeting configuration); ' \
            '(2) if the Python interpreter running Zope and ' \
            'Plone is not able to discuss with OpenOffice (it does not have ' \
            '"uno" installed - check it by typing "import uno" at the Python ' \
            'prompt) please specify, in the PloneMeeting configuration, ' \
            'the path to a UNO-enabled Python interpreter (ie, the Python ' \
            'interpreter included in the OpenOffice distribution, or, if ' \
            'your server runs Ubuntu, the standard Python interpreter ' \
            'installed in /usr/bin/python). Here is the error as reported ' \
            'by the appy.pod library:\n\n %s'
DELETE_TEMP_DOC_ERROR = 'A temporary document could not be removed. %s.'
##/code-section after-local-schema

PodTemplate_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
PodTemplate_schema['id'].write_permission = "PloneMeeting: Write risky config"
PodTemplate_schema['title'].write_permission = "PloneMeeting: Write risky config"
PodTemplate_schema.changeSchemataForField('description', 'default')
PodTemplate_schema.moveField('description', after='title')
PodTemplate_schema['description'].storage = AttributeStorage()
PodTemplate_schema['description'].write_permission = "PloneMeeting: Write risky config"
PodTemplate_schema['description'].widget.description = " "
PodTemplate_schema['description'].widget.description_msgid = "empty_description"
# hide metadata fields and even protect it with the WriteRiskyConfig permission
for field in PodTemplate_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig
##/code-section after-schema

class PodTemplate(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IPodTemplate)

    meta_type = 'PodTemplate'
    _at_rename_after_creation = True

    schema = PodTemplate_schema

    ##code-section class-header #fill in your manual code here
    podFormats = (("doc", "Microsoft Word"),
                  ("odt", "Open Document Format (text)"),
                  ("rtf", "Rich Text Format (RTF)"),
                  ("pdf", "Adobe PDF"))
    BAD_CONDITION = 'POD template "%s" (%s): wrong condition "%s" (%s).'
    BAD_MAILINGLIST = "This document can't be sent."
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self, force=None):
        '''Returns the possibly translated title.'''
        return getFieldContent(self, 'title', force)

    security.declarePrivate('listPodFormats')
    def listPodFormats(self):
        return DisplayList(self.podFormats)

    security.declarePrivate('listPodPermissions')
    def listPodPermissions(self):
        res = []
        for permission in self.portal_controlpanel.possible_permissions():
            res.append((permission, permission))
        return DisplayList(tuple(res))

    security.declarePublic('isApplicable')
    def isApplicable(self, obj):
        '''May the current user use this template for generating documents ?'''
        user = self.portal_membership.getAuthenticatedMember()
        res = False
        # Check permissions
        isAllowed = True
        for podPermission in self.getPodPermission():
            if not user.has_permission(podPermission, obj):
                isAllowed = False
                break
        if isAllowed:
            res = True  # At least for now
            # Check condition
            if self.getPodCondition().strip():
                portal = getToolByName(self, 'portal_url').getPortalObject()
                ctx = createExprContext(obj.aq_inner.aq_parent, portal, obj)
                try:
                    res = Expression(self.getPodCondition())(ctx)
                except Exception, e:
                    logger.warn(self.BAD_CONDITION % (self.Title(),
                                self.getPodFormat(), self.getPodCondition(),
                                str(e)))
                    res = False
        return res

    security.declarePublic('getDocumentId')
    def getDocumentId(self, obj):
        '''Returns the id of the document that may be produced in the
           database from p_self and p_obj.'''
        return '%s_%s.%s' % (obj.id, self.id, self.getPodFormat())

    security.declarePrivate('meetingIsDecided')
    def meetingIsDecided(self, obj):
        '''Is the meeting decided ?'''
        res = False
        if obj.meta_type == 'Meeting':
            res = obj.adapted().isDecided()
        else:  # It is a meeting item
            if obj.hasMeeting() and obj.getMeeting().adapted().isDecided():
                res = True
        return res

    def _getFileName(self, obj):
        '''Returns a valid, clean fileName for the document generated from
           p_self for p_obj.'''
        # to avoid long filename problems, only take 120 first characters
        res = u'%s-%s' % (obj.Title().decode('utf-8')[0:100],
                          self.getName().decode('utf-8')[0:20])
        return normalizeString(res)

    security.declarePublic('generateDocument')
    def generateDocument(self, obj, itemUids=[], forBrowser=True):
        '''Generates a document from this template, for object p_obj. If p_obj
           is a meeting, p_itemUids contains the UIDs of the items to dump
           into the document (which is a subset of all items linked to this
           meeting).

           If p_forBrowser is True, this method produces a valid output for
           browsers (setting HTTP headers, etc). Else, it returns the raw
           document content.'''
        tool = self.portal_plonemeeting
        meetingConfig = tool.getMeetingConfig(obj)
        # Temporary file where to generate the result
        tempFileName = '%s/%s_%f.%s' % (
            tempfile.gettempdir(), obj.UID(), time.time(), self.getPodFormat())
        # Define parameters to pass to the appy.pod renderer
        currentUser = self.portal_membership.getAuthenticatedMember()
        from Products.PloneMeeting import utils as pod_utils
        podContext = {'self': obj,
                      'adap': obj.adapted(),
                      'tool': self.portal_plonemeeting,
                      'meetingConfig': meetingConfig,
                      'meetingIsDecided': self.meetingIsDecided(obj),
                      'itemUids': itemUids,
                      'user': currentUser,
                      'podTemplate': self,
                      # give ability to access annexes related methods
                      'IAnnexable': IAnnexable,
                      # make methods defined in utils available
                      'utils': pod_utils,
                      }
        podContext.update(obj.adapted().getSpecificDocumentContext())
        rendererParams = {'template': StringIO(self.getPodTemplate()),
                          'context': podContext,
                          'result': tempFileName}
        if tool.getUnoEnabledPython():
            rendererParams['pythonWithUnoPath'] = tool.getUnoEnabledPython()
        if tool.getOpenOfficePort():
            rendererParams['ooPort'] = tool.getOpenOfficePort()
        # Launch the renderer
        try:
            renderer = Renderer(**rendererParams)
            renderer.run()
        except appy.pod.PodError, pe:
            if not os.path.exists(tempFileName):
                # In some (most?) cases, when OO returns an error, the result is
                # nevertheless generated.
                raise PloneMeetingError(POD_ERROR % str(pe))
        # Open the temp file on the filesystem
        f = file(tempFileName, 'rb')
        res = f.read()
        if forBrowser:
            fileName = self._getFileName(obj)
            response = obj.REQUEST.RESPONSE
            mr = getToolByName(self, 'mimetypes_registry')
            mimetype = mr.lookupExtension(self.getPodFormat())
            if not mimetype:
                self.plone_utils.addPortalMessage(translate(UNABLE_TO_DETECT_MIMETYPE_ERROR,
                                                            domain='PloneMeeting',
                                                            context=self.REQUEST), 'error')
                self.REQUEST.RESPONSE.redirect(obj.absolute_url())
            response.setHeader('Content-Type', mimetype.normalized())
            response.setHeader('Content-Disposition', 'inline;filename="%s.%s"'
                               % (fileName, self.getPodFormat()))
        f.close()
        # Returns the doc and removes the temp file
        try:
            os.remove(tempFileName)
        except OSError, oe:
            logger.warn(DELETE_TEMP_DOC_ERROR % str(oe))
        return res

    security.declarePrivate('listFreezeEvents')
    def listFreezeEvents(self):
        meetingConfig = self.getParentNode()
        res = [('', self.translate('no_freeze_event', domain='PloneMeeting'))]
        for id, text in meetingConfig.listTransitions('Meeting'):
            res.append(('pod_meeting_%s' % id, 'Meeting->%s' % text))
        for id, text in meetingConfig.listTransitions('Item'):
            res.append(('pod_item_%s' % id, 'Item->%s' % text))
        return DisplayList(tuple(res))

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        self.adapted().onEdit(isCreated=False)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'PodTemplate':
            return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePrivate('validate_mailingLists')
    def validate_mailingLists(self, value):
        '''Validates the content of field "mailingList".'''
        if not value or not value.strip():
            return
        for line in value.strip().split('\n'):
            if line.count(';') != 2:
                return ' '  # Not empty, so the field is highlighted as erroneous

    security.declarePublic('getAvailableMailingLists')
    def getAvailableMailingLists(self, obj, member):
        '''Gets the names of the (currently active) mailing lists defined for
           this template.'''
        res = []
        mailingInfo = self.getMailingLists().strip()
        if not mailingInfo:
            return res
        for line in mailingInfo.split('\n'):
            name, condition, userIds = line.split(';')
            data = {'obj': obj,
                    'member': member, }
            ctx = getEngine().getContext(data)
            try:
                condition = Expression(condition)(ctx)
                if condition:
                    res.append(name.strip())
            except Exception, e:
                logger.warning(MAILINGLIST_CONDITION_ERROR % (name, str(e)))
        return res



registerType(PodTemplate, PROJECTNAME)
# end of class PodTemplate

##code-section module-footer #fill in your manual code here
CANT_WRITE_DOC = 'User "%s" was not authorized to create file "%s" ' \
                 'in folder "%s" from template "%s".'


def freezePodDocumentsIfRelevant(obj, transition):
    '''p_transitions just occurred on p_obj. Is there any document that needs
       to be generated in the database from a POD template?'''
    tool = getToolByName(obj, 'portal_plonemeeting')
    membershipTool = getToolByName(obj, 'portal_membership')
    meetingConfig = tool.getMeetingConfig(obj)
    user = membershipTool.getAuthenticatedMember()
    podTemplatesFolder = getattr(meetingConfig, TOOL_FOLDER_POD_TEMPLATES)
    for podTemplate in podTemplatesFolder.objectValues():
        if transition == podTemplate.getFreezeEvent() and podTemplate.isApplicable(obj):
            # I must dump a document in the DB based on this template and
            # object.
            fileId = podTemplate.getDocumentId(obj)
            folder = obj.aq_inner.aq_parent
            existingDoc = getattr(folder, fileId, None)
            # If the doc was already generated, we do not rewrite it.
            # This way, if some doc generations crash, when retrying them
            # the already generated docs are not generated again.
            if not existingDoc:
                try:
                    docContent = podTemplate.generateDocument(obj,
                                                              forBrowser=False)
                    folder.invokeFactory('File', id=fileId, file=docContent)
                    doc = getattr(folder, fileId)
                    mr = getToolByName(obj, 'mimetypes_registry')
                    mimetype = mr.lookupExtension(podTemplate.getPodFormat())
                    doc.setFormat(mimetype.normalized())
                    doc.setTitle('%s (%s)' % (obj.Title(), podTemplate.Title()))
                    clonePermissions(obj, doc)
                except PloneMeetingError, pme:
                    # Probably some problem while contacting OpenOffice.
                    logger.warn(str(pme))
                    portal = getToolByName(obj, 'portal_url').getPortalObject()
                    sendMail([portal.getProperty('email_from_address')],
                             obj, "documentGenerationFailed")
                except Unauthorized:
                    logger.warn(CANT_WRITE_DOC % (
                        user.getId(), fileId, obj.absolute_url(), podTemplate.getId()))
##/code-section module-footer
