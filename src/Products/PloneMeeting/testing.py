# -*- coding: utf-8 -*-
#
# File: testing.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

import unittest

from plone.testing import z2, zca
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneWithPackageLayer

from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
import Products.PloneMeeting


PM_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                          package=Products.PloneMeeting,
                          name='PM_ZCML')

PM_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, PM_ZCML),
                              name='PM_Z2')


PM_TESTING_PROFILE = PloneWithPackageLayer(
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('imio.dashboard',
                            'Products.PloneMeeting',
                            'Products.CMFPlacefulWorkflow',
                            'Products.PasswordStrength'),
    gs_profile_id='Products.PloneMeeting:testing',
    name="PM_TESTING_PROFILE")

PM_TESTING_PROFILE_INTEGRATION = IntegrationTesting(
    bases=(PM_TESTING_PROFILE,), name="PM_TESTING_PROFILE_INTEGRATION")

PM_TESTING_PROFILE_FUNCTIONAL = FunctionalTesting(
    bases=(PM_TESTING_PROFILE,), name="PM_TESTING_PROFILE_FUNCTIONAL")

PM_TESTING_ROBOT = FunctionalTesting(
    bases=(
        PM_TESTING_PROFILE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="PM_TESTING_ROBOT",
)

# simple layer used for testSetup
PM_PLONE_FIXTURE = PloneWithPackageLayer(
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('imio.dashboard',
                            'Products.PloneMeeting',
                            'Products.CMFPlacefulWorkflow',
                            'Products.PasswordStrength'),
    gs_profile_id='Products.PloneMeeting:default',
    name="PLONE_FIXTURE")

PM_PLONE_INTEGRATION = IntegrationTesting(
    bases=(PM_PLONE_FIXTURE,),
    name="PLONE_INTEGRATION"
)


class NakedIntegrationTestCase(unittest.TestCase):
    """Base class for integration tests."""

    layer = PM_PLONE_INTEGRATION

    def setUp(self):
        super(NakedIntegrationTestCase, self).setUp()
        self.app = self.layer['app']
        self.portal = self.layer['portal']
