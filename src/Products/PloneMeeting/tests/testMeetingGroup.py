# -*- coding: utf-8 -*-
#
# File: testMeetingGroup.py
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
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testMeetingGroup(PloneMeetingTestCase):
    '''Tests the MeetingCategory class methods.'''

    def test_pm_CanNotRemoveUsedMeetingGroup(self):
        '''While removing a MeetingGroup, it should raise if it is used...'''
        self.changeUser('pmManager')
        # create an item
        item = self.create('MeetingItem')
        # default used proposingGroup is 'developers'
        self.assertEquals(item.getProposingGroup(), 'developers')
        # now try to remove corresponding group
        self.changeUser('admin')
        # it first fails because the corresponding Plone groups are not empty
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_plonegroup')
        # so remove every users of these groups
        developers = self.tool.developers
        for ploneGroup in developers.getPloneGroups():
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # this time it complains about a linked meetingitem
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['developers', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_meetingitem')
        # remove the item, then it works...
        item.aq_inner.aq_parent.manage_delObjects([item.getId(), ])
        self.tool.manage_delObjects(['developers', ])
        # the group is actually removed
        self.failIf(hasattr(self.tool, 'developers'))

        # removing a used group in the configuration fails too
        self.assertEquals(self.meetingConfig.recurringitems.template2.getProposingGroup(), 'vendors')
        # first fails because corresponding Plone groups are not empty...
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['vendors', ])
        self.assertEquals(cm.exception.message, 'can_not_delete_meetinggroup_plonegroup')
        # so remove them...
        vendors = self.tool.vendors
        for ploneGroup in vendors.getPloneGroups():
            for memberId in ploneGroup.getGroupMemberIds():
                ploneGroup.removeMember(memberId)
        # then fails because used in the configuration
        with self.assertRaises(BeforeDeleteException) as cm:
            self.tool.manage_delObjects(['vendors', ])
        self.assertEquals(cm.exception.message,
                          translate('can_not_delete_meetinggroup_config_meetingitem',
                                    domain='plone',
                                    mapping={'url': self.meetingConfig.recurringitems.template2.absolute_url()},
                                    context=self.portal.REQUEST))
        # so remove the item in the config (it could work by changing the proposingGroup too...)
        self.meetingConfig.recurringitems.manage_delObjects(['template2', ])
        # now it works...
        self.tool.manage_delObjects(['vendors', ])
        # the group is actually removed
        self.failIf(hasattr(self.tool, 'vendors'))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testMeetingGroup, prefix='test_pm_'))
    return suite
