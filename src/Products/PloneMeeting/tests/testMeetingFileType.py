# -*- coding: utf-8 -*-
#
# File: testMeetingFileType.py
#
# Copyright (c) 2007-2013 by Imio.be
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

from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.PloneMeeting.interfaces import IAnnexable
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testMeetingFileType(PloneMeetingTestCase):
    '''Tests the MeetingFileType class methods.'''

    def test_pm_CanNotRemoveLinkedMeetingFileType(self):
        '''While removing a MeetingFileType, it should raise if it is used by a MeetingFile...'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        meetingFileType = annex.getMeetingFileType(theRealObject=True)
        self.changeUser('admin')
        # if we try to remove this meetingFileType, it raises an Exception
        meetingFileTypesFolder = meetingFileType.aq_inner.aq_parent
        self.assertRaises(BeforeDeleteException,
                          meetingFileTypesFolder.manage_delObjects,
                          [meetingFileType.getId(), ])
        # we can remove a MeetingFileType that is not linked to anything...
        meetingFileTypesFolder.manage_delObjects(['item-annex', ])
        # if we remove the MeetingFile linked to the MeetingFileType, we can remove it
        item.manage_delObjects([annex.getId(), ])
        meetingFileTypesFolder.manage_delObjects([meetingFileType.getId(), ])

    def test_pm_validate_subTypes(self):
        '''Test the MeetingFileType.subTypes validation.
           A subType can not be removed if in use.'''
        # get the first available MeetingFileType
        mftData = self.meetingConfig.getFileTypes('item')[0]
        mft = self.portal.uid_catalog(UID=mftData['id'])[0].getObject()
        mft.setSubTypes(({'row_id': 'unique_row_id_123',
                          'title': 'Annex sub type',
                          'predefinedTitle': 'Annex sub type predefined title',
                          'otherMCCorrespondences': (),
                          'isActive': '1', }, ))
        # create an annex using the sub type
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # modify annex fileType to use the defined subType
        annex.setMeetingFileType('%s__subtype__unique_row_id_123' % mft.UID())
        IAnnexable(item).updateAnnexIndex()
        self.assertTrue(item.annexIndex[0]['mftId'] == '%s__subtype__unique_row_id_123' % mft.UID())
        self.assertTrue(IAnnexable(item).getAnnexes()[0].getMeetingFileType() ==
                        '%s__subtype__unique_row_id_123' % mft.UID())
        # it is used, we can not remove it from the defined MeetingFileType.subTypes
        can_not_remove_msg = translate('sub_type_can_not_remove_used_row',
                                       domain='PloneMeeting',
                                       mapping={'sub_type_title': 'Annex sub type',
                                                'item_url': item.absolute_url()},
                                       context=self.portal.REQUEST)
        subTypes = ({'row_id': 'unique_row_id_123',
                     'title': 'Annex sub type',
                     'predefinedTitle': 'Annex sub type predefined title',
                     'otherMCCorrespondences': (),
                     'isActive': '1', }, )
        # if re-applying config, it works...
        # validate returns nothing if validation was successful
        self.failIf(mft.validate_subTypes(subTypes))
        # now remove the subType
        subTypes = tuple()
        # validation fails
        self.assertTrue(mft.validate_subTypes(subTypes) == can_not_remove_msg)
        # we will be able to remove the subType if not annex is using it
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        # validate returns nothing if validation was successful
        self.failIf(mft.validate_subTypes(subTypes))

    def test_pm_CanNotChangeRelatedToOfUsedMeetingFileType(self):
        '''If a MeetingFileType is in use, we can not change the 'relatedTo' anymore...'''
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        mft = annex.getMeetingFileType(theRealObject=True)
        # validate relatedTo
        self.assertEquals(mft.getRelatedTo(), 'item')
        # try to change the value to 'advice' or 'item_decision', it fails...
        error_msg = translate('cannot_change_inuse_item_relatedto',
                              domain='PloneMeeting',
                              mapping={'item_url': item.absolute_url()},
                              context=item.REQUEST)
        self.assertTrue(mft.validate_relatedTo('advice') == error_msg)
        self.assertTrue(mft.validate_relatedTo('item_decision') == error_msg)
        # but not changing value does validate correctly
        # validate returns nothing if validation was successful
        self.failIf(mft.validate_relatedTo('item'))

        # do the test for an annex added on an advice
        item.setOptionalAdvisers(('developers', ))
        self.proposeItem(item)
        advice = createContentInContainer(item,
                                          'meetingadvice',
                                          **{'advice_group': 'developers',
                                             'advice_type': u'positive',
                                             'advice_comment': RichTextValue(u'My comment')})
        # add an annex to the advice
        advice_annex = self.addAnnex(advice, relatedTo='advice')
        advice_mft = advice_annex.getMeetingFileType(theRealObject=True)
        self.assertTrue(advice_mft.getRelatedTo() == 'advice')
        # now changing related to of 'advice-annex' will fail
        error_advice_related_msg = translate('cannot_change_inuse_advice_relatedto',
                                             domain='PloneMeeting',
                                             mapping={'item_url': item.absolute_url()},
                                             context=item.REQUEST)
        self.assertTrue(advice_mft.validate_relatedTo('item') == error_advice_related_msg)
        self.assertTrue(advice_mft.validate_relatedTo('item_decision') == error_advice_related_msg)
        self.failIf(advice_mft.validate_relatedTo('advice'))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingFileType, prefix='test_pm_'))
    return suite
