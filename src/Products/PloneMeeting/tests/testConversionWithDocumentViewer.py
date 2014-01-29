# -*- coding: utf-8 -*-
#
# File: testToolPloneMeeting.py
#
# Copyright (c) 2007-2012 by PloneGov
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
        self.failUnless(annex1.isConvertable())
        # now load a not convertable format
        self.annexFile = 'tests/file_unconvertableFormat.eml'
        annex2 = self.addAnnex(item)
        self.failIf(annex2.isConvertable())

    def test_pm_IsConvertedAtCreation(self):
        '''An annex is converted at creation if it is specified in the configuration...'''
        # by default, annex preview is enabled so annexes are converted
        self.assertTrue(self.tool.getEnableAnnexPreview())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        # the annex is converted
        self.assertTrue(annex1.conversionStatus() == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        # disable annex preview, the annex will not be converted upon creation
        self.tool.setEnableAnnexPreview(False)
        annex2 = self.addAnnex(item)
        self.assertFalse(annex2.conversionStatus() == 'successfully_converted')
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
        self.assertFalse(annex1.conversionFailed())
        self.assertTrue(annex1.conversionStatus() == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        # while adding a not convertable format, nothing is converted
        self.annexFile = 'tests/file_unconvertableFormat.eml'
        annex2 = self.addAnnex(item)
        self.assertFalse(annex2.conversionFailed())
        self.assertTrue(annex2.conversionStatus() == 'not_convertable')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'not_convertable')
        # a convertable format but an error during conversion, it adds a portal_message
        messages = IStatusMessage(self.request)
        self.assertEquals(len(messages.show()), 0)
        self.annexFile = 'tests/file_errorDuringConversion.pdf'
        annex3 = self.addAnnex(item)
        # the element is convertable
        self.failUnless(annex3.isConvertable())
        # but there was an error during conversion
        self.assertTrue(annex3.conversionStatus() == 'conversion_error')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'conversion_error')
        self.assertTrue(messages.show()[-1].message == CONVERSION_ERROR)
        self.assertTrue(annex3.conversionFailed())

    def test_pm_ForceConversion(self):
        '''
          Even if annex preview is disabled, we need the annex to be converted
          if we want to print it.  So check that, even if preview is disabled :
          - if we set MeetingFile.toPrint to True using the mutator MeetingFile.setToPrint,
            the annex  is correctly converted
          - if MeetingFile.toPrint is True by default, the annex  is correctly converted upon creation
        '''
        # first disable annex preview
        self.tool.setEnableAnnexPreview(False)
        # MeetingFile.toPrint is False by default
        self.assertFalse(self.meetingConfig.getAnnexToPrintDefault())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        # this is not converted
        self.assertFalse(annex1.conversionStatus() == 'successfully_converted')
        self.assertFalse(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        # if we specify that this annex needs to be printed, it will be converted
        annex1.setToPrint(True)
        self.assertTrue(annex1.conversionStatus() == 'successfully_converted')
        self.assertTrue(item.annexIndex[-1]['conversionStatus'] == 'successfully_converted')
        self.changeUser('admin')
        # specify that annexes are toPrint by default
        self.assertFalse(self.meetingConfig.setAnnexToPrintDefault(True))
        self.changeUser('pmManager')
        annex2 = self.addAnnex(item)
        # this is actually converted
        self.assertTrue(annex2.conversionStatus() == 'successfully_converted')
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
        self.failUnless(annex.conversionStatus() is 'successfully_converted')
        # now duplicate the item and check annexes
        clonedItem = item.clone()
        clonedAnnex = clonedItem.objectValues('MeetingFile')[0]
        self.failUnless(clonedAnnex.conversionStatus() is 'successfully_converted')
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
