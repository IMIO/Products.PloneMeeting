# -*- coding: utf-8 -*-
#
# File: testSetup.py
#
# Copyright (c) 2016 by Imio.be
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

from Products.CMFPlone.factory import addPloneSite
from plone.app.testing import login
from plone.app.testing.interfaces import DEFAULT_LANGUAGE
from Products.PloneMeeting.testing import NakedIntegrationTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import cleanMemoize


class testSetup(NakedIntegrationTestCase):
    '''Tests the setup, especially registered profiles.'''

    def test_pm_InstallAvailableProfiles(self):
        """This is made for subpackages to test that defined profiles
           containing an import_data works as expected."""
        login(self.app, 'admin')
        # self current package name based on testing layer
        package_name = self.layer.__module__.replace('.testing', '')
        profile_names = [info['id'] for info in self.portal.portal_setup.listProfileInfo()
                         if info['product'] == package_name and
                         not info['id'].endswith(':default') and
                         not info['id'].endswith(':testing')]
        i = 1
        for profile_name in profile_names:
            pm_logger.info("Applying import_data of profile '%s'" % profile_name)
            addPloneSite(self.app,
                         str(i),
                         title='Site title',
                         setup_content=False,
                         default_language=DEFAULT_LANGUAGE,
                         extension_ids=('plonetheme.sunburst:default',
                                        profile_name, ))
            # clean memoize between each site because the same REQUEST especially
            # is used for every sites and this can lead to problems...
            cleanMemoize(self.portal)
            i = i + 1


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSetup, prefix='test_pm_'))
    return suite
