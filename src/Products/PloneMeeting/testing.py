# -*- coding: utf-8 -*-
#
# File: testing.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

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
        super(PMLayer, self).setUpPloneSite(portal)
        # Create some member areas
        for userId in ('pmManager',
                       'pmCreator1',
                       'pmCreator1b',
                       'pmCreator2',
                       'siteadmin',
                       'powerobserver1'):
            # this layer is used by imio.pm.wsclient
            if api.user.get(userId):
                _createMemberarea(portal, userId)


PM_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                          package=Products.PloneMeeting,
                          name='PM_ZCML')

PM_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, PM_ZCML),
                              name='PM_Z2')


PM_TESTING_PROFILE = PMLayer(
    zcml_filename="testing.zcml",
    zcml_package=Products.PloneMeeting,
    additional_z2_products=('collective.eeafaceted.collectionwidget',
                            'Products.PloneMeeting',
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
