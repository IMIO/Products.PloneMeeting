# -*- coding: utf-8 -*-
#
# File: testConversionWithDocumentViewer.py
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

import os
import shutil
from tempfile import mkdtemp

from zope.annotation import IAnnotations
from zope.i18n import translate

from collective.documentviewer.settings import GlobalSettings

from Products.statusmessages.interfaces import IStatusMessage
from Products.PloneMeeting.MeetingFile import CONVERSION_ERROR
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testConversionWithDocumentViewer(PloneMeetingTestCase):
    '''Tests the MeetingFile and MeetingItem methods related to conversion using collective.documentviewer.'''

    def setUp(self):
        PloneMeetingTestCase.setUp(self)
        # set storage to Blob for collective.documentviewer so everything is correctly
        # removed while the test finished
        _dir = mkdtemp()
        viewer_settings = GlobalSettings(self.portal)._metadata
        viewer_settings['storage_type'] = 'Blob'
        viewer_settings['storage_location'] = _dir
        # annex preview is disabled by default in 'test' profile
        self.tool.setEnableAnnexPreview(True)

    def test_pm_IsConvertable(self):
        '''Test that the MeetingFile is convertable to images so it can be printed.'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # default's file is a .txt
        annex1 = self.addAnnex(item)
        # first ensure that the annex is convertable
        self.failUnless(IAnnexable(item).isConvertable(annex1))
        # now load a not convertable format
        self.annexFile = 'tests/file_unconvertableFormat.eml'
        annex2 = self.addAnnex(item)
        self.failIf(IAnnexable(item).isConvertable(annex2))

    def test_pm_IsConvertedAtCreation(self):
        '''An annex is converted at creation if it is specified in the configuration...'''
        # by default, annex preview is enabled so annexes are converted
        self.assertTrue(self.tool.getEnableAnnexPreview())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        # the annex is converted
        self.assertTrue(IAnnexable(item).conversionStatus(annex1) == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        # disable annex preview, the annex will not be converted upon creation
        self.tool.setEnableAnnexPreview(False)
        annex2 = self.addAnnex(item)
        self.assertFalse(IAnnexable(item).conversionStatus(annex2) == 'successfully_converted')
        self.assertFalse(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')

    def test_pm_Convert(self):
        '''If an annex is converted it can be :
           - successfully_converted
           - under_conversion or waiting conversion if conversion is disabled
           - '''
        # by default, annex preview is enabled so annexes are converted
        self.assertTrue(self.tool.getEnableAnnexPreview())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        # the annex is converted
        self.assertFalse(IAnnexable(item).conversionFailed(annex1))
        self.assertTrue(IAnnexable(item).conversionStatus(annex1) == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        # while adding a not convertable format, nothing is converted
        self.annexFile = 'tests/file_unconvertableFormat.eml'
        annex2 = self.addAnnex(item)
        self.assertFalse(IAnnexable(item).conversionFailed(annex2))
        self.assertTrue(IAnnexable(item).conversionStatus(annex2) == 'not_convertable')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'not_convertable')
        # a convertable format but an error during conversion, it adds a portal_message
        messages = IStatusMessage(self.request)
        self.annexFile = 'tests/file_errorDuringConversion.pdf'
        annex3 = self.addAnnex(item)
        # the element is convertable
        self.failUnless(IAnnexable(item).isConvertable(annex3))
        # but there was an error during conversion
        self.assertTrue(IAnnexable(item).conversionStatus(annex3) == 'conversion_error')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'conversion_error')
        self.assertTrue(messages.show()[-1].message == translate(CONVERSION_ERROR, context=self.request))
        self.assertTrue(IAnnexable(item).conversionFailed(annex3))

    def test_pm_ForceConversion(self):
        '''
          Even if annex preview is disabled, we need the annex to be converted
          if we want to print it.  So check that, even if preview is disabled :
          - if we set MeetingFile.toPrint to True using the mutator MeetingFile.setToPrint,
            the annex  is correctly converted
          - if MeetingFile.toPrint is True by default, the annex  is correctly converted upon creation
        '''
        cfg = self.meetingConfig
        # first disable annex preview
        self.tool.setEnableAnnexPreview(False)
        # MeetingFile.toPrint is False by default
        self.assertFalse(cfg.getAnnexToPrintDefault())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        # this is not converted
        self.assertFalse(IAnnexable(item).conversionStatus(annex1) == 'successfully_converted')
        self.assertFalse(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        # if we specify that this annex needs to be printed, it will not be converted because
        # we use "for information" annex toPrint
        cfg.setEnableAnnexToPrint('enabled_for_info')
        annex1.setToPrint(True)
        self.assertFalse(IAnnexable(item).conversionStatus(annex1) == 'successfully_converted')
        self.assertFalse(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        cfg.setEnableAnnexToPrint('enabled_for_printing')
        annex1.setToPrint(True)
        # this time the annex is converted
        self.assertTrue(IAnnexable(item).conversionStatus(annex1) == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')

        self.changeUser('admin')
        # specify that annexes are toPrint by default
        self.assertFalse(cfg.setAnnexToPrintDefault(True))
        self.changeUser('pmManager')
        annex2 = self.addAnnex(item)
        # this is actually converted
        self.assertTrue(IAnnexable(item).conversionStatus(annex2) == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')

    def test_pm_AnnexesOfClonedItemAreConverted(self):
        """
          While cloning an item (duplicate), check that annexes are
          converted if necessary...
        """
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # annex1 has been converted successfully
        self.failUnless(IAnnexable(item).conversionStatus(annex) is 'successfully_converted')
        # now duplicate the item and check annexes
        clonedItem = item.clone()
        clonedAnnex = clonedItem.objectValues('MeetingFile')[0]
        self.failUnless(IAnnexable(item).conversionStatus(clonedAnnex) is 'successfully_converted')
        # make sure also it has really been converted, aka the last_updated
        # value in c.documentviewer annotations is differents from original annex one
        annexAnnotations = IAnnotations(annex)['collective.documentviewer']
        clonedAnnexAnnotations = IAnnotations(clonedAnnex)['collective.documentviewer']
        self.failUnless(annexAnnotations['last_updated'] != clonedAnnexAnnotations['last_updated'])

    def test_pm_GetAnnexesToPrintUsingBlob(self):
        """
          Test the IAnnexable.getAnnexesToPrint method.  It is a helper method that
          returns a dict containing usefull informations about annexes to print in a POD template.
          This test when the global settings storage_type is 'Blob'.
        """
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex.setToPrint(True)
        # add a second annex but not set as toPrint
        annex2 = self.addAnnex(item)
        self.assertTrue(not annex2.getToPrint())

        annexAnnotations = IAnnotations(annex)['collective.documentviewer']
        # we have to call 'readers' on the blob the make sure it is really committed...
        # or _p_blob_committed could not be set
        annexAnnotations['blob_files']['large/dump_1.png'].readers
        largeFileDumpImage1Path = annexAnnotations['blob_files']['large/dump_1.png']._p_blob_committed
        expected = [{'images': [{'path': largeFileDumpImage1Path,
                                 'number': 1}],
                     'number_of_images': 1,
                     'number': 1,
                     'UID': annex.UID(),
                     'title': annex.Title()}]
        self.assertEquals(IAnnexable(item).getAnnexesToPrint(), expected)

    def test_pm_GetAnnexesToPrintUsingFile(self):
        """
          Test the IAnnexable.getAnnexesToPrint method.  It is a helper method that
          returns a dict containing usefull informations about annexes to print in a POD template.
          This test when the global settings storage_type is 'File'.
        """
        viewer_settings = GlobalSettings(self.portal)._metadata
        viewer_settings['storage_type'] = 'File'
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex.setToPrint(True)
        annexUID = annex.UID()
        # add a second annex but not set as toPrint
        annex2 = self.addAnnex(item)
        self.assertTrue(not annex2.getToPrint())
        dvpdffiles = self.portal.unrestrictedTraverse('@@dvpdffiles')
        filetraverser = dvpdffiles.publishTraverse(self.request, annexUID[0])
        filetraverser = dvpdffiles.publishTraverse(self.request, annexUID[1])
        filetraverser = dvpdffiles.publishTraverse(self.request, annexUID)
        large = filetraverser.publishTraverse(self.request, 'large')
        largeFileDumpImage1Path = large.context.path
        expected = [{'images': [{'path': largeFileDumpImage1Path + '/dump_1.png',
                                 'number': 1}],
                     'number_of_images': 1,
                     'number': 1,
                     'UID': annex.UID(),
                     'title': annex.Title()}]
        self.assertEquals(IAnnexable(item).getAnnexesToPrint(), expected)

    def tearDown(self):
        """
          While using 'File' as storage_type, annexes are converted in a temporary
          folder that is not removed automatically, so remove it manually...
        """
        PloneMeetingTestCase.tearDown(self)
        viewer_settings = GlobalSettings(self.portal)._metadata
        if viewer_settings['storage_type'] == 'Blob':
            return

        storage_location = GlobalSettings(self.portal).storage_location
        # removed the temporary folder created during tests
        if os.path.exists(storage_location):
            shutil.rmtree(storage_location)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testConversionWithDocumentViewer, prefix='test_pm_'))
    return suite
