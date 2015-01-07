# -*- coding: utf-8 -*-
#
# File: MeetingFile.py
#
# Copyright (c) 2014 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from plone.app.blob.content import ATBlob
from plone.app.blob.content import ATBlobSchema
from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
import os
import os.path
from Acquisition import aq_base
from AccessControl import Unauthorized
from zope.annotation import IAnnotations
from zope.i18n import translate
from plone.memoize.instance import memoize
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import getObjSize
from Products.MimetypesRegistry.common import MimeTypeException
from collective.documentviewer.async import asyncInstalled
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.utils import getCustomAdapter, sendMailIfRelevant

import logging
logger = logging.getLogger('PloneMeeting')

# Error-related constants ------------------------------------------------------
UNSUPPORTED_FORMAT_FOR_OCR = 'File "%s" could not be OCR-ized because mime ' \
    'type "%s" is not a supported input format. Supported input formats ' \
    'are: %s; %s.'
DUMP_FILE_ERROR = 'Error occurred while dumping or removing file "%s" on ' \
    'disk. %s'
GS_ERROR = 'An error occurred when using Ghostscript to convert "%s". Note ' \
    'that program "gs" must be in path.'
TESSERACT_ERROR = 'An error occurred when using Tesseract to OCR-ize file ' \
    '"%s". Note that program "tesseract" must be in path.'

GS_TIFF_COMMAND = 'gs -q -dNOPAUSE -dBATCH -sDEVICE=tiffg4 ' \
    '-sOutputFile=%s/%%04d.tif %s -c quit'
GS_INFO_COMMAND = 'Launching Ghoscript: %s'
TESSERACT_COMMAND = 'tesseract %s %s -l %s'
TESSERACT_INFO_COMMAND = 'Launching Tesseract: %s'
PDFTOTEXT_COMMAND = 'pdftotext %s %s'
PDFTOTEXT_INFO_COMMAND = 'Launching pdftotext: %s'
PDFTOTEXT_ERROR = 'An error occurred while converting a PDF file with ' \
                  'pdftotext.'
WVTEXT_COMMAND = 'wvText %s %s'
WVTEXT_INFO_COMMAND = 'Launching wvText: %s'
WVTEXT_ERROR = 'An error occurred while converting a Word document with wvText.'
CONTENT_TYPE_NOT_FOUND = 'The content_type for MeetingFile at %s was not found in mimetypes_registry!'
FILE_EXTENSION_NOT_FOUND = 'The extension used by MeetingFile at %s does not correspond to ' \
    'an extension available in the mimetype %s found in mimetypes_registry!'
CONVERSION_ERROR = u'There was an error during annex conversion, please contact system administrator.'
CONVERSION_ERROR_MANAGER = u'There was an error during annex conversion at %s.'

##/code-section module-header

schema = Schema((

    StringField(
        name='meetingFileType',
        widget=StringField._properties['widget'](
            visible=False,
            label='Meetingfiletype',
            label_msgid='PloneMeeting_label_meetingFileType',
            i18n_domain='PloneMeeting',
        ),
        required=True,
    ),
    BooleanField(
        name='toPrint',
        default=False,
        widget=BooleanField._properties['widget'](
            label='Toprint',
            label_msgid='PloneMeeting_label_toPrint',
            i18n_domain='PloneMeeting',
        ),
    ),
    BooleanField(
        name='isConfidential',
        default=False,
        widget=BooleanField._properties['widget'](
            description="IsConfidential",
            description_msgid="is_confidential_descr",
            label='Isconfidential',
            label_msgid='PloneMeeting_label_isConfidential',
            i18n_domain='PloneMeeting',
        ),
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingFile_schema = ATBlobSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
##/code-section after-schema

class MeetingFile(ATBlob, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingFile)

    meta_type = 'MeetingFile'
    _at_rename_after_creation = True

    schema = MeetingFile_schema

    ##code-section class-header #fill in your manual code here
    aliases = {
        '(Default)': '(dynamic view)',
        'view': 'file_view',
        'index.html': '(dynamic view)',
        'edit': 'atct_edit',
        'properties': 'base_metadata',
        'sharing': 'folder_localrole_form',
        'gethtml': '',
        'mkdir': '',
    }
    ocrFormatsOk = ('image/tiff',)
    ocrFormatsOkButConvertNeeded = ('application/pdf',)
    ocrAllFormatsOk = ocrFormatsOk + ocrFormatsOkButConvertNeeded
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getName')
    def getName(self):
        '''Returns the annex title.'''
        return self.Title()

    security.declarePublic('getIcon')
    def getIcon(self, relative_to_portal=0):
        '''Calculate the icon using the meetingFileType icon.'''
        field = self.getField('file')
        if not field:
            # field is empty
            return BaseContent.getIcon(self, relative_to_portal)
        mft = self.getMeetingFileType(theRealObject=True)
        if mft:
            return self.portal_url.getRelativeContentURL(mft) + '/theIcon'
        else:
            return None

    security.declarePublic('getMeetingFileType')
    def getMeetingFileType(self, theData=False, theRealObject=False, **kwargs):
        '''Override Archetypes accessor to be able to manage subTypes that are not real
           objects but dict of data.  If p_theData is True, we return a dict containing
           data of linked meetingFileType that can be the real MFT object of one of the subTypes.
           If p_theRealObject is True, we will return the real MFT object, even if we are on
           one of its subTypes.'''
        res = self.getField('meetingFileType').get(self, **kwargs)  # = mft id
        if res and (theData or theRealObject):
            # MeetingFileTypes are not in the portal_catalog
            # but it is indexed in the uid_catalog...
            uid_catalog = getToolByName(self, 'uid_catalog')
            # if the meetingFileType is a subType, find the MeetingFileType
            # object than _dataFor corresponding subType
            mftUID = res
            row_id = None
            if '__subtype__' in res:
                mftUID, row_id = res.split('__subtype__')
            mft = uid_catalog(UID=mftUID)[0].getObject()
            if theRealObject:
                res = mft
            else:
                # res will contain data of the MFT object if row_id is None
                # and will contain data of the subtype otherwise
                res = mft._dataFor(row_id=row_id)
        return res

    security.declarePublic('getBestIcon')
    def getBestIcon(self):
        '''Calculates the icon for the AT default view'''
        self.getIcon()

    security.declarePublic('findRelatedTo')
    def findRelatedTo(self):
        '''
          Check what the corresponding MeetingFileType is relatedTo...
        '''
        mft = self.getMeetingFileType(theData=True)
        if mft:
            return mft['relatedTo']
        return ''

    security.declarePublic('getParent')
    def getParent(self):
        '''Returns the parent, aka the element managing MeetingFiles.
           Annexes are located in an item or in an advice...'''
        return self.getParentNode()

    security.declareProtected(View, 'index_html')
    def index_html(self, REQUEST=None, RESPONSE=None):
        '''Download the file'''
        if not self.isViewableForCurrentUser():
            raise Unauthorized
        self.portal_plonemeeting.rememberAccess(self.UID())
        return ATBlob.index_html(self, REQUEST, RESPONSE)

    security.declareProtected(View, 'download')
    def download(self, REQUEST=None, RESPONSE=None):
        """Download the file"""
        if not self.isViewableForCurrentUser():
            raise Unauthorized
        self.portal_plonemeeting.rememberAccess(self.UID())
        return ATBlob.download(self, REQUEST, RESPONSE)

    security.declarePublic('isViewableForCurrentUser')
    def isViewableForCurrentUser(self):
        '''
          MeetingFile is viewable if :
          - parent is an item and is privacyViewable;
          - annex is not confidential;
          - annex is confidential and current user may view it.
          This is used to protect MeetingFile download in case current user knows the url
          of an annex he may not access...
        '''
        parent = self.getParent()
        # is parent an item and privacy viewable?
        if parent.meta_type == 'MeetingItem' and not parent.adapted().isPrivacyViewable():
            return False
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(parent)
        if not cfg.getEnableAnnexConfidentiality():
            return True
        isPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=False)
        isRestrictedPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=True)
        return IAnnexable(parent)._isViewableForCurrentUser(cfg,
                                                            isPowerObserver,
                                                            isRestrictedPowerObserver,
                                                            self.getAnnexInfo())

    security.declarePublic('at_post_create_script')
    def at_post_create_script(self):
        # We define here a PloneMeeting-specific modification date for this
        # annex. Indeed, we can't use the standard Plone modification_date for
        # the PloneMeeting color system because some events like parent state
        # changes update security settings on annexes and modification_date is
        # updated.
        tool = getToolByName(self, 'portal_plonemeeting')
        self.pm_modification_date = self.modification_date
        tool.rememberAccess(self.UID(), commitNeeded=False)
        parent = self.getParent()
        if parent:
            # update parent.annexIndex if it was not already set
            # by the conversion process for example
            annexIndexUids = [annex['UID'] for annex in parent.annexIndex]
            if not self.UID() in annexIndexUids:
                IAnnexable(parent).updateAnnexIndex()
            parent.alreadyUsedAnnexNames.append(self.id)
        # at the end of creation, we know now self.relatedTo
        # and we can manage the self.toPrint default value
        cfg = tool.getMeetingConfig(self)
        if self.findRelatedTo() == 'item_decision':
            self.setToPrint(cfg.getAnnexDecisionToPrintDefault())
        elif self.findRelatedTo() == 'item':
            self.setToPrint(cfg.getAnnexToPrintDefault())
        else:
            # relatedTo == 'advice'
            self.setToPrint(cfg.getAnnexAdviceToPrintDefault())
        # at the end of creation, we know now self.meetingFileType
        # and we can manage the self.isConfidential default value
        mft = self.getMeetingFileType(theData=True)
        self.setIsConfidential(mft['isConfidentialDefault'])
        # Call sub-product code if any
        self.adapted().onEdit(isCreated=True)
        # Add text-extraction-related attributes
        rq = self.REQUEST
        self.needsOcr = rq.get('needs_ocr', None) is not None
        self.ocrLanguage = rq.get('ocr_language', None)
        # Reindexing the annex may have the effect of extracting text from the
        # binary content, if tool.extractTextFromFiles is True (see method
        # MeetingFile.indexExtractedText).
        self.reindexObject()

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        self.adapted().onEdit(isCreated=False)

    security.declarePublic('getAnnexInfo')
    def getAnnexInfo(self):
        '''Produces a dict with some useful info about this annex. This is
           used for indexing purposes (see method updateAnnexIndex in
           browser/annexes.py).'''
        fileTypeData = self.getMeetingFileType(theData=True)
        portal_url = getToolByName(self, 'portal_url')
        res = {'Title': self.Title(),
               'absolute_url': portal_url.getRelativeContentURL(self),
               'UID': self.UID(),
               'meetingFileTypeObjectUID': fileTypeData['meetingFileTypeObjectUID'],
               'mftId': fileTypeData['id'],
               'id': self.getId(),
               'iconUrl': self.getIcon(),
               # if the parent also has a pm_modification_date,
               # make sure we use the real MeetingFile's one
               'modification_date': aq_base(self).pm_modification_date,
               'relatedTo': self.findRelatedTo(),
               'conversionStatus': self.conversionStatus(),
               'isConfidential': self.getIsConfidential(),
               'warnSize': self.warnSize(),
               'friendlySize': getObjSize(self)()
               }
        return res

    def warnSize(self):
        '''Need to warn user because of huge size of the annex?'''
        return bool(self.get_size() > MAX_FILE_SIZE_WARNING)

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingFile':
            return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    security.declarePublic('indexExtractedText')
    def indexExtractedText(self):
        '''This method extracts text from the binary content of this object
           and puts it in the index that corresponds to this method. It does so
           only if tool.extractTextFromFiles is True.

           If self.needsOcr is True, it does OCR recognition
           by calling command-line programs Ghostscript (gs) and Tesseract
           (tesseract). Ghostscript is used for converting a file into
           images and Tesseract is the OCR engine that converts those images
           into text. Tesseract needs to know in what p_ocrLanguage the file
           is written'''
        if not hasattr(self.aq_base, 'needsOcr'):
            return ''
        tool = self.portal_plonemeeting
        if not tool.getExtractTextFromFiles():
            return ''
        # Extracts the text from the binary content.
        extractedText = ''
        mimeType = self.content_type
        if self.needsOcr:
            if mimeType in self.ocrAllFormatsOk:
                try:
                    fileName = self.dump()  # Dumps me on disk first
                    tifFolder = None
                    if mimeType in self.ocrFormatsOkButConvertNeeded:
                        # I will first use Ghostscript to convert the file to
                        # "tiff" format. I will create a folder where
                        # Ghostscript will generate one tiff file per PDF page.
                        tifFolder = os.path.splitext(fileName)[0] + '.folder'
                        os.mkdir(tifFolder)
                        cmd = GS_TIFF_COMMAND % (tifFolder, fileName)
                        logger.info(GS_INFO_COMMAND % cmd)
                        os.system(cmd)
                        tifFiles = ['%s/%s' % (tifFolder, f) for f in os.listdir(tifFolder)]
                        if not tifFiles:
                            logger.warn(GS_ERROR % (fileName))
                    else:
                        tifFiles = [fileName]
                    tifFiles.sort()
                    # Launch the OCR engine
                    for tifFile in tifFiles:
                        resFile = os.path.splitext(tifFile)[0]
                        resFilePlusExt = resFile + '.txt'
                        cmd = TESSERACT_COMMAND % (tifFile, resFile,
                                                   self.ocrLanguage)
                        logger.info(TESSERACT_INFO_COMMAND % cmd)
                        os.system(cmd)
                        if not os.path.exists(resFilePlusExt):
                            logger.warn(TESSERACT_ERROR % tifFile)
                        else:
                            f = file(resFilePlusExt)
                            extractedText += f.read()
                            f.close()
                            os.remove(resFilePlusExt)
                        os.remove(tifFile)
                    if tifFolder:
                        os.removedirs(tifFolder)
                    os.remove(fileName)
                except OSError, oe:
                    logger.warn(DUMP_FILE_ERROR % (self.getFilename(), str(oe)))
                except IOError, ie:
                    logger.warn(DUMP_FILE_ERROR % (self.getFilename(), str(ie)))
            else:
                logger.warn(UNSUPPORTED_FORMAT_FOR_OCR % (self.getFilename(),
                            mimeType, self.ocrFormatsOk,
                            self.ocrFormatsOkButConvertNeeded))
        else:
            fileName = self.dump()  # Dumps me on disk first
            # Import the content of a not-to-ocr PDF file.
            resultFileName = os.path.splitext(fileName)[0] + '.txt'
            decodeNeeded = None
            if mimeType == 'application/pdf':
                cmd = PDFTOTEXT_COMMAND % (fileName, resultFileName)
                logger.info(PDFTOTEXT_INFO_COMMAND % cmd)
                os.system(cmd)
                if not os.path.exists(resultFileName):
                    logger.warn(PDFTOTEXT_ERROR)
            elif mimeType == 'application/msword':
                cmd = WVTEXT_COMMAND % (fileName, resultFileName)
                logger.info(WVTEXT_INFO_COMMAND % cmd)
                os.system(cmd)
                decodeNeeded = 'latin-1'
                if not os.path.exists(resultFileName):
                    logger.warn(WVTEXT_ERROR)
            else:
                logger.info('Unable to index content of "%s"' % self.id)
            # Return temporary files written on disk and return the result.
            os.remove(fileName)
            if os.path.exists(resultFileName):
                f = file(resultFileName)
                if decodeNeeded:
                    extractedText += f.read().decode(decodeNeeded)
                else:
                    extractedText += f.read()
                f.close()
                os.remove(resultFileName)
        return extractedText

    security.declareProtected(ModifyPortalContent, 'setToPrint')
    def setToPrint(self, value):
        """
          Override the setToPrint mutator so we can handle conversion to images process
          If the annex is to print (setToPrint(True)), generates relevant images to insert in
          the document that will be generated.  If the annex is not to print (setToPrint(False)),
          remove generated images...
        """
        if value is True:
            # check if we need to generate relevant images using collective.documentviewer converter
            # if we want the annex to be printable, force the conversion to images (not 'redone' if already done...)
            convertToImages(self, None, force=True)
        # finally set the given value
        self.getField('toPrint').set(self, value)

    security.declarePublic('conversionStatus')
    def conversionStatus(self):
        """
          Returns the conversion status of current MeetingFile.
          Status can be :
          - not_convertable : the MeetingFile is not convertable by collective.documentviewer
          - under_conversion : or awaiting conversion, the MeetingFile is convertable but is not yet converted
          - conversion_error : there was an error during MeetingFile conversion.  Manager have access in the UI to more infos
          - successfully_converted : the MeetingFile is converted correctly
        """
        annotations = IAnnotations(self)
        # not_convertable or awaiting conversion?
        if not 'collective.documentviewer' in annotations.keys() or not self.isConvertable():
            return 'not_convertable'
        # under conversion?
        if not 'successfully_converted' in annotations['collective.documentviewer']:
            return 'under_conversion'

        if not annotations['collective.documentviewer']['successfully_converted'] is True:
            return 'conversion_error'

        return 'successfully_converted'

    security.declarePublic('conversionFailed')
    def conversionFailed(self):
        """
          Check if conversion failed
        """
        annotations = IAnnotations(self)
        if 'collective.documentviewer' in annotations and \
           'successfully_converted' in annotations['collective.documentviewer'] and \
           annotations['collective.documentviewer']['successfully_converted'] is False:
            return True
        return False

    security.declarePublic('isConvertable')
    def isConvertable(self):
        """
          Check if the annex is convertable (hopefully).  If the annex mimetype is one taken into
          account by collective.documentviewer CONVERTABLE_TYPES, then it should be convertable...
        """
        mr = self.mimetypes_registry
        try:
            content_type = mr.lookup(self.content_type)
        except MimeTypeException:
            content_type = None
        if not content_type:
            logger.warning(CONTENT_TYPE_NOT_FOUND % self.absolute_url_path())
            return False
        # get printable extensions from collective.documentviewer
        printableExtensions = self._documentViewerPrintableExtensions()

        # mr.lookup returns a list
        extensions = content_type[0].extensions
        # now that we have the extensions, find the one we are using
        currentExtension = ''
        # in case we have myimage.JPG, make sure extension is lowercase as
        # extentions on mimetypes_registry are lowercase...
        try:
            filename = self.getFilename()
        except AttributeError:
            filename = self.getFile().filename
        file_extension = filename.split('.')[-1].lower()
        for extension in extensions:
            if file_extension == extension:
                currentExtension = extension
                break

        # if we found the exact extension we are using, we can see if it is in the list
        # of printable extensions provided by collective.documentviewer
        # most of times, this is True...
        if currentExtension in printableExtensions:
            return True
        if not currentExtension:
            logger.warning(FILE_EXTENSION_NOT_FOUND % (self.absolute_url_path(),
                                                       content_type[0]))

        # if we did not find the currentExtension in the mimetype's extensions,
        # for example an uploaded element without extension, check nevertheless
        # if the mimetype seems to be managed by collective.documentviewer
        if set(extensions).intersection(set(printableExtensions)):
            return True

        return False

    @memoize
    def _documentViewerPrintableExtensions(self):
        """
          Compute file extensions that will be considered as printable.
        """
        from collective.documentviewer.config import CONVERTABLE_TYPES
        printableExtensions = []
        for convertable_type in CONVERTABLE_TYPES.iteritems():
            printableExtensions.extend(convertable_type[1].extensions)
        return printableExtensions



registerType(MeetingFile, PROJECTNAME)
# end of class MeetingFile

##code-section module-footer #fill in your manual code here


def convertToImages(object, event, force=False):
    """
      Convert the MeetingFile to images so it can be printed or previewed.
    """
    if (not object.portal_plonemeeting.getEnableAnnexPreview() and not force) or  \
       not object.isConvertable():
        return
    # if the annex will be converted to images by plone.app.async
    # save some elements from the REQUEST that will be used after...
    if asyncInstalled():
        saved_req = dict(object.REQUEST)
        # remove useless keys
        keys_to_remove = []
        for key in saved_req:
            if not isinstance(saved_req[key], str):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del saved_req[key]
        # save it as string to avoid pickling error
        object.saved_request = str(saved_req)
    # queueJob use plone.app.async if installed or current instance if not
    from collective.documentviewer.async import queueJob
    queueJob(object)


def prepareClonedAnnexForConversion(obj, event):
    """
      While cloning a MeetingFile (it is the case when the item is duplicated),
      we eventually want to convert it but we need to prepare it to
      be convertable...
    """
    # remove every annotations regarding 'collective.documentviewer'
    # this way, 'collective.documentviewer' will be able to convert
    # the annex because it checks if the object has already been converted
    # and if we keep existing annotations, I think it is, but is is not...
    annotations = IAnnotations(obj)
    if 'collective.documentviewer' in annotations:
        del annotations['collective.documentviewer']
    # now call convertToImages because IObjectInitializedEvent is not called
    # while copy/pasting an object (case in the duplication process)
    # but check if a copyAnnexes is not set to False in the REQUEST meaning
    # that we are duplicating an item but that we do not copyAnnexes
    if obj.REQUEST.get('copyAnnexes', True):
        convertToImages(obj, event)


def checkAfterConversion(obj, event):
    """
      After conversion, check that there was no error, if an error occured,
      make sure the annex is set to not toPrint and send an email if relevant.
    """
    parent = obj.getParent()
    if event.status == 'failure':
        # make sure the annex is not printed in documents
        obj.setToPrint(False)
        # special behavior for real Managers
        isRealManager = obj.portal_plonemeeting.isManager(realManagers=True)
        # send an email to relevant users to warn them if relevant
        # plone.app.async does not have a REQUEST... so make one...
        if asyncInstalled():
            from Testing.makerequest import makerequest
            parent = makerequest(parent)
            import ast
            # initialize the REQUEST with saved values on the annex...
            saved_request = ast.literal_eval(obj.saved_request)
            for key in saved_request:
                parent.REQUEST[key] = saved_request[key]
        else:
            # if we are not using plone.app.async, add a portal_message
            msg = isRealManager and (CONVERSION_ERROR_MANAGER % obj.absolute_url_path()) or \
                CONVERSION_ERROR
            obj.plone_utils.addPortalMessage(
                translate(msgid=msg,
                          domain='PloneMeeting',
                          context=obj.REQUEST),
                'error')

        # email notification, check if the Manager is not 'playing' with conversion
        if isRealManager:
            sendMailIfRelevant(parent, 'annexConversionError', 'Manager', isRole=True)
        else:
            sendMailIfRelevant(parent, 'annexConversionError', 'PloneMeeting: Add annex', isRole=False)

    # update the conversionStatus value in the annexIndex
    # if this is triggered before at_post_create_script,
    # a pm_modification_date is not available
    # this is tested in testConversionWithDocumentViewer.testConvert
    if not hasattr(aq_base(obj), 'pm_modification_date'):
        obj.pm_modification_date = obj.modification_date
    IAnnexable(parent).updateAnnexIndex()

    # remove saved_request on annex
    try:
        del obj.saved_request
    except:
        pass
##/code-section module-footer
