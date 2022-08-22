# -*- coding: utf-8 -*-
#
# File: testing.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

import monkey  # flake8: noqa
from plone import api
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneWithPackageLayer
from plone.app.testing.bbb import _createMemberarea
from plone.testing import z2
from plone.testing import zca
from Products.CMFPlone.utils import base_hasattr
from zope.globalrequest.local import setLocal

import Products.PloneMeeting


class PMLayer(PloneWithPackageLayer):

    def setUpZope(self, app, configurationContext):
        from App.config import _config
        if not base_hasattr(_config, 'product_config'):
            _config.product_config = {
                'imio.zamqp.core':
                {'ws_url': 'http://localhost:6543', 'ws_password': 'test',
                 'ws_login': 'testuser', 'routing_key': '019999',
                 'client_id': '019999'}}
        super(PMLayer, self).setUpZope(app, configurationContext)

    def setUpPloneSite(self, portal):
        setLocal('request', portal.REQUEST)
        # configure default workflows so Folder has a workflow
        # make sure we have a default workflow
        portal.portal_workflow.setDefaultChain('simple_publication_workflow')
        super(PMLayer, self).setUpPloneSite(portal)
        # Create member area of existing users
        for user in api.user.get_users():
            # this layer is used by imio.pm.wsclient
            _createMemberarea(portal, user.getId())


PM_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                          package=Products.PloneMeeting,
                          name='PM_ZCML')

PM_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, PM_ZCML),
                              name='PM_Z2')


PM_TESTING_PROFILE = PMLayer(
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('Products.PloneMeeting',
                            'collective.eeafaceted.collectionwidget',
                            'Products.CMFPlacefulWorkflow',
                            'Products.PasswordStrength'),
    gs_profile_id='Products.PloneMeeting:testing',
    name="PM_TESTING_PROFILE")

PM_TESTING_PROFILE_INTEGRATION = IntegrationTesting(
    bases=(PM_TESTING_PROFILE,),
    name="PM_TESTING_PROFILE_INTEGRATION")

PM_TESTING_PROFILE_FUNCTIONAL = FunctionalTesting(
    bases=(PM_TESTING_PROFILE,),
    name="PM_TESTING_PROFILE_FUNCTIONAL")

PM_TESTING_ROBOT = FunctionalTesting(
    bases=(
        PM_TESTING_PROFILE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="PM_TESTING_ROBOT",
)
