# -*- coding: utf-8 -*-
#
# File: MeetingFile.py
#
# Copyright (c) 2013 by PloneGov
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
import os, os.path, time, unicodedata
from App.class_init import InitializeClass
from Acquisition import aq_base
from zope.annotation import IAnnotations
from zope.i18n import translate
from plone.memoize.instance import memoize
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from Products.PloneMeeting.utils import getCustomAdapter, getOsTempFolder, \
     HubSessionsMarshaller
import logging
logger = logging.getLogger('PloneMeeting')

# Marshaller -------------------------------------------------------------------
class MeetingFileMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a meetin file into a XML file.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all_with_metadata'
    rootElementName = 'meetingFile'

    def marshallSpecificElements(self, mf, res):
        HubSessionsMarshaller.marshallSpecificElements(self, mf, res)
        self.dumpField(res, 'pm_modification_date', mf.pm_modification_date)
        self.dumpField(res, 'needsOcr', mf.needsOcr)
        self.dumpField(res, 'ocrLanguage', mf.ocrLanguage)

InitializeClass(MeetingFileMarshaller)

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
##/code-section module-header

schema = Schema((

    ReferenceField(
        name='meetingFileType',
        keepReferencesOnCopy=True,
        widget=ReferenceBrowserWidget(
            label='Meetingfiletype',
            label_msgid='PloneMeeting_label_meetingFileType',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        relationship="MeetingFileType",
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

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingFile_schema = ATBlobSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingFile_schema.registerLayer('marshall', MeetingFileMarshaller())
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
        '(Default)'  : '(dynamic view)',
        'view'       : 'file_view',
        'index.html' : '(dynamic view)',
        'edit'       : 'atct_edit',
        'properties' : 'base_metadata',
        'sharing'    : 'folder_localrole_form',
        'gethtml'    : '',
        'mkdir'      : '',
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
        mtf = self.getMeetingFileType()
        if mtf:
            return mtf.absolute_url(relative=1) + "/theIcon"
        else:
            return None

    security.declarePublic('getBestIcon')
    def getBestIcon(self):
        '''Calculates the icon for the AT default view'''
        self.getIcon()

    security.declarePublic('getItem')
    def getItem(self):
        '''Returns the linked item.  Annexes are located in the item...'''
        return self.aq_inner.aq_parent

    security.declareProtected(View, 'index_html')
    def index_html(self, REQUEST=None, RESPONSE=None):
        '''Download the file'''
        # Prevent downloading the annex if the related item is not # privacy-viewable.
        item = self.getItem()
        if not item.adapted().isPrivacyViewable():
            raise Unauthorized
        self.portal_plonemeeting.rememberAccess(self.UID())
        return ATBlob.index_html(self, REQUEST, RESPONSE)

    security.declarePublic('at_post_create_script')
    def at_post_create_script(self):
        # We define here a PloneMeeting-specific modification date for this
        # annex. Indeed, we can't use the standard Plone modification_date for
        # the PloneMeeting color system because some events like item state
        # changes update security settings on annexes and modification_date is
        # updated.
        self.pm_modification_date = self.modification_date
        self.portal_plonemeeting.rememberAccess(self.UID(), commitNeeded=False)
        item = self.getItem()
        if item:
            # update item.annexIndex if it was not already set
            # by the conversion process for example
            annexIndexUids = [annex['uid'] for annex in item.annexIndex]
            if not self.UID() in annexIndexUids:
                item.updateAnnexIndex()
            item.alreadyUsedAnnexNames.append(self.id)
        self.adapted().onEdit(isCreated=True) # Call sub-product code if any
        # Add text-extraction-related attributes
        rq = self.REQUEST
        self.needsOcr = rq.get('needs_ocr', None) != None
        self.ocrLanguage = rq.get('ocr_language', None)
        # Reindexing the annex may have the effect of extracting text from the
        # binary content, if tool.extractTextFromFiles is True (see method
        # MeetingFile.indexExtractedText).
        self.reindexObject()

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self): self.adapted().onEdit(isCreated=False)

    security.declarePublic('isDecisionRelated')
    def isDecisionRelated(self):
        '''
          Check that the corresponding MeetingFileType is decision related or not...
        '''
        mft = self.getMeetingFileType()
        if mft and mft.getDecisionRelated() == True:
            return True
        else: return False

    security.declarePublic('getAnnexInfo')
    def getAnnexInfo(self):
        '''Produces a dict with some useful info about this annex. This is
           used for indexing purposes (see method updateAnnexIndex in
           MeetingItem.py).'''
        fileType = self.getMeetingFileType()
        portal_url = getToolByName(self, 'portal_url')
        res = {'Title': self.Title(),
               'url': portal_url.getRelativeContentURL(self),
               'uid': self.UID(),
               'fileTypeId': fileType.id,
               'iconUrl': portal_url.getRelativeContentURL(fileType) + '/theIcon',
               # the item (parent) also has a pm_modification_date,
               # make sure we use the real MeetingFile's one
               'modification_date': aq_base(self).pm_modification_date,
               'decisionRelated': self.isDecisionRelated()
               }
        return res

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingFile': return self.context
        return self

    security.declarePublic('adapted')
    def adapted(self): return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

    security.declarePrivate('dump')
    def dump(self):
        '''Dumps me on disk, in a temp folder, with some unique name
           including time.time(). This method returns the absolute filename
           of the dumped file.'''
        tempFolder = getOsTempFolder()
        fileName = unicodedata.normalize(
            'NFKD', self.getFilename().decode('utf-8'))
        fileName = fileName.encode("ascii", "ignore").replace(' ', '')
        tempFileName = '%s/f%f.%s' % (tempFolder, time.time(), fileName)
        f = file(tempFileName, 'w'); f.write(self.data); f.close()
        return tempFileName

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
        if not hasattr(self.aq_base, 'needsOcr'): return ''
        tool = self.portal_plonemeeting
        if not tool.getExtractTextFromFiles(): return ''
        # Extracts the text from the binary content.
        extractedText = ''
        mimeType = self.content_type
        if self.needsOcr:
            if mimeType in self.ocrAllFormatsOk:
                try:
                    fileName = self.dump() # Dumps me on disk first
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
                        tifFiles = ['%s/%s' % (tifFolder, f) for f in \
                                    os.listdir(tifFolder)]
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
            fileName = self.dump() # Dumps me on disk first
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

    def _updateMeetingFileType(self, meetingConfig):
        '''
          Update the linked MeetingFileType of the annex while an item is sent from
          a MeetingConfig to another : find a corresponding MeetingFileType in the new MeetingConfig :
          - either we have a corresponding MeetingFileType (same id)
          - or if we can not get a corresponding MeetingFileType, we use the default one (the first found).
          Returns True if the meetingFileType was actually updated
        '''
        decisionRelated = self.isDecisionRelated()
        existingFileTypesUids = [ft.UID() for ft in meetingConfig.meetingfiletypes.getFileTypes(decisionRelated=decisionRelated, onlyActive=False)]
        existingFileTypesIds = [ft.getId() for ft in meetingConfig.meetingfiletypes.getFileTypes(decisionRelated=decisionRelated)]
        mft = self.getMeetingFileType()
        if not mft or not mft.UID() in existingFileTypesUids:
            # get the corresponding meetingFileType in the current meetingConfig
            # or use the default meetingFileType
            if mft and mft.id in existingFileTypesIds:
                # a corresponding meetingFileType has been found, use it
                correspondingFileType = getattr(meetingConfig.meetingfiletypes, mft.id)
            else:
                correspondingFileType = getattr(meetingConfig.meetingfiletypes, existingFileTypesIds[0])
            self.setMeetingFileType(correspondingFileType)
            return True



registerType(MeetingFile, PROJECTNAME)
# end of class MeetingFile

##code-section module-footer #fill in your manual code here
##/code-section module-footer
