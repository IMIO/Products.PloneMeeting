# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# Copyright (c) 2013 by Imio.be
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

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.interfaces import IAnnexable


class testAnnexes(PloneMeetingTestCase):
    '''Tests various aspects of annexes management.
       Advices are enabled for PloneGov Assembly, not for PloneMeeting Assembly.'''

    def _setupAnnexes(self):
        ''' '''
        self.changeUser('pmManager')
        # add an item with several annexes of different types
        item = self.create('MeetingItem')
        # create annexes of first relatedTo 'item'
        itemRelatedMFTs = self.meetingConfig.getFileTypes(relatedTo='item')
        # 3 annexes of first MFT
        mft1 = self.portal.uid_catalog(UID=itemRelatedMFTs[0]['id'])[0].getObject()
        self.addAnnex(item, annexType=mft1.getId())
        self.addAnnex(item, annexType=mft1.getId())
        self.addAnnex(item, annexType=mft1.getId())
        # 1 annexe of second MFT
        mft2 = self.portal.uid_catalog(UID=itemRelatedMFTs[1]['id'])[0].getObject()
        self.addAnnex(item, annexType=mft2.getId())
        # 2 annexes of third MFT
        mft3 = self.portal.uid_catalog(UID=itemRelatedMFTs[2]['id'])[0].getObject()
        self.addAnnex(item, annexType=mft3.getId())
        self.addAnnex(item, annexType=mft3.getId())
        return item, mft1, mft2, mft3

    def test_pm_getAnnexesByType(self):
        '''Test the getAnnexesByType method that returns
           annexes grouped by MeetingFileType.'''
        item, mft1, mft2, mft3 = self._setupAnnexes()
        # we have 3 groups of annexes
        annexesByType = IAnnexable(item).getAnnexesByType('item')
        self.assertTrue(len(annexesByType) == 3)
        # first group of annexes concern first MFT
        self.assertTrue(annexesByType[0][0]['meetingFileTypeObjectUID'] == mft1.UID())
        self.assertTrue(annexesByType[0][1]['meetingFileTypeObjectUID'] == mft1.UID())
        self.assertTrue(annexesByType[0][2]['meetingFileTypeObjectUID'] == mft1.UID())
        self.assertTrue(len(annexesByType[0]) == 3)
        # second group of annexes concern second MFT
        self.assertTrue(annexesByType[1][0]['meetingFileTypeObjectUID'] == mft2.UID())
        self.assertTrue(len(annexesByType[1]) == 1)
        # third group of annexes concern third MFT
        self.assertTrue(annexesByType[2][0]['meetingFileTypeObjectUID'] == mft3.UID())
        self.assertTrue(annexesByType[2][1]['meetingFileTypeObjectUID'] == mft3.UID())
        self.assertTrue(len(annexesByType[2]) == 2)

    def test_pm_getAnnexesByTypeAnnexConfidentiality(self):
        '''Test the getAnnexesByType method when annex confidentiality is enabled.
           A confidential annex is not visible by restricted power observers.'''
        item, mft1, mft2, mft3 = self._setupAnnexes()
        # a MeetingManager can access everything, as nothing is confidential for now...
        annexesByType = IAnnexable(item).getAnnexesByType('item')
        self.assertTrue(len(annexesByType) == 3)
        self.assertTrue(len(annexesByType[0]) == 3)
        self.assertTrue(len(annexesByType[1]) == 1)
        self.assertTrue(len(annexesByType[2]) == 2)
        # as nothing is confidential, a restricted power observer
        # can access every annexes too
        self.changeUser('restrictedpowerobserver1')
        annexesByType = IAnnexable(item).getAnnexesByType('item')
        self.assertTrue(len(annexesByType) == 3)
        self.assertTrue(len(annexesByType[0]) == 3)
        self.assertTrue(len(annexesByType[1]) == 1)
        self.assertTrue(len(annexesByType[2]) == 2)
        # now enable annex confidentiality and test again
        self.changeUser('admin')
        self.meetingConfig.setEnableAnnexConfidentiality(True)
        # make first annex of group1 and second annex of group3 confidential
        getattr(item, annexesByType[0][2]['id']).setIsConfidential(True)
        getattr(item, annexesByType[2][1]['id']).setIsConfidential(True)
        # update annex index as isConfidential is in MeetingItem.annexIndex
        IAnnexable(item).updateAnnexIndex()
        # it does not change anything for other users than restricted power observers
        self.changeUser('pmManager')
        annexesByType = IAnnexable(item).getAnnexesByType('item')
        self.assertTrue(len(annexesByType) == 3)
        self.assertTrue(len(annexesByType[0]) == 3)
        self.assertTrue(len(annexesByType[1]) == 1)
        self.assertTrue(len(annexesByType[2]) == 2)
        # but restricted power observers will not see confidential annexes
        self.changeUser('restrictedpowerobserver1')
        annexesByType = IAnnexable(item).getAnnexesByType('item')
        self.assertTrue(len(annexesByType) == 3)
        self.assertTrue(len(annexesByType[0]) == 2)
        self.assertTrue(len(annexesByType[1]) == 1)
        self.assertTrue(len(annexesByType[2]) == 1)
        # if every annexes of a group are confidential, the group
        # is not returned anymore, hide the unique annex of second group
        self.changeUser('pmManager')
        getattr(item, annexesByType[1][0]['id']).setIsConfidential(True)
        IAnnexable(item).updateAnnexIndex()
        self.changeUser('restrictedpowerobserver1')
        annexesByType = IAnnexable(item).getAnnexesByType('item')
        self.assertTrue(len(annexesByType) == 2)
        self.assertTrue(len(annexesByType[0]) == 2)
        self.assertTrue(len(annexesByType[1]) == 1)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAnnexes, prefix='test_pm_'))
    return suite
