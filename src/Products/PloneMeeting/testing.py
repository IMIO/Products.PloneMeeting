# -*- coding: utf-8 -*-
from plone.testing import z2, zca
from plone.app.testing import PloneWithPackageLayer
from plone.app.testing import FunctionalTesting
import Products.PloneMeeting


PM_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                          package=Products.PloneMeeting,
                          name='PM_ZCML')

PM_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, PM_ZCML),
                              name='PM_Z2')

PM_TESTING_PROFILE = PloneWithPackageLayer(
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('Products.PloneMeeting',
                            'Products.CMFPlacefulWorkflow'),
    gs_profile_id='Products.PloneMeeting:testing',
    name="PM_TESTING_PROFILE")

PM_TESTING_PROFILE_FUNCTIONAL = FunctionalTesting(
    bases=(PM_TESTING_PROFILE,), name="PM_TESTING_PROFILE_FUNCTIONAL")
