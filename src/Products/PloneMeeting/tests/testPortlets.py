# -*- coding: utf-8 -*-
#
# File: testPortlets.py
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

from zope.component import getUtility, getMultiAdapter
from plone.portlets.interfaces import IPortletManager, IPortletRenderer
from plone.app.testing import login
from Products.PloneMeeting.browser import portlet_plonemeeting as pm
from Products.PloneMeeting.config import *
from Products.PloneMeeting.tests.PloneMeetingTestCase import \
    PloneMeetingTestCase


class testPortlets(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def testPortletPMAvailableTemplates(self):
        '''Test the portlet_plonemeeting.getTemplateItems method
           returning available item templates for current user.
           template1 is available to everyone but template2 is restricted to group 'vendors'.'''
        # pmCreator1 is member of 'developers'
        login(self.portal, 'pmCreator1')
        self.getMeetingFolder()
        context = getattr(self.portal.Members.pmCreator1.mymeetings, self.meetingConfig.getId())
        request = self.portal.REQUEST
        view = self.portal.restrictedTraverse('@@plone')
        manager = getUtility(IPortletManager, name='plone.leftcolumn', context=self.portal)
        assignment = pm.Assignment()
        renderer = getMultiAdapter((context, request, view, manager, assignment), IPortletRenderer)
        self.assertEquals(['template1',], [template.getId() for template in renderer.templateItems()])
        # pmCreator2 is member of 'vendors' and can so access template2 that is restricted to 'vendors'
        login(self.portal, 'pmCreator2')
        self.getMeetingFolder()
        context = getattr(self.portal.Members.pmCreator2.mymeetings, self.meetingConfig.getId())
        request = self.portal.REQUEST
        view = self.portal.restrictedTraverse('@@plone')
        manager = getUtility(IPortletManager, name='plone.leftcolumn', context=self.portal)
        assignment = pm.Assignment()
        renderer = getMultiAdapter((context, request, view, manager, assignment), IPortletRenderer)
        self.assertEquals(['template1', 'template2', ], [template.getId() for template in renderer.templateItems()])



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPortlets))
    return suite
