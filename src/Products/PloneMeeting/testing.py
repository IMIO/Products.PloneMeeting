# -*- coding: utf-8 -*-
from plone.testing import z2, zca
from plone.app.testing import PloneWithPackageLayer
from plone.app.testing import IntegrationTesting, FunctionalTesting
import Products.PloneMeeting


PM_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                             package=Products.PloneMeeting,
                             name='PM_ZCML')

PM_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, PM_ZCML),
                                 name='PM_Z2')

PM = PloneWithPackageLayer(
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('Products.PloneMeeting','Products.CMFPlacefulWorkflow'),
    gs_profile_id='Products.PloneMeeting:default',
    name="PM")

PM_TESTS_PROFILE = PloneWithPackageLayer(
    bases=(PM, ),
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('Products.PloneMeeting',),
    gs_profile_id='Products.PloneMeeting:test',
    name="PM_TESTS_PROFILE")

PM_INTEGRATION = IntegrationTesting(
    bases=(PM,), name="PM_INTEGRATION")

PM_TESTS_PROFILE_INTEGRATION = IntegrationTesting(
    bases=(PM_TESTS_PROFILE,), name="PM_TESTS_PROFILE_INTEGRATION")

PM_TESTS_PROFILE_FUNCTIONAL = FunctionalTesting(
    bases=(PM_TESTS_PROFILE,), name="PM_TESTS_PROFILE_FUNCTIONAL")
