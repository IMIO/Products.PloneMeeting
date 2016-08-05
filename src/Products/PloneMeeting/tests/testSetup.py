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
from plone import api

from Products.GenericSetup.context import DirectoryImportContext
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_REAPPLY
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import cleanMemoize


class testSetup(PloneMeetingTestCase):
    '''Tests the setup, especially registered profiles.'''

    def _currentSetupProfileNames(self, excluded=[]):
        """ """
        package_name = self.layer.__module__.replace('.testing', '')
        profile_names = [info['id'] for info in self.portal.portal_setup.listProfileInfo()
                         if info['product'] == package_name and
                         not info['id'].endswith(tuple(excluded))]
        return profile_names

    def test_pm_InstallAvailableProfiles(self):
        """This is made for subpackages to test that defined profiles
           containing an import_data works as expected."""
        login(self.app, 'admin')
        # get current package name based on testing layer
        profile_names = self._currentSetupProfileNames(excluded=(':default', ':testing'))
        i = 1
        for profile_name in profile_names:
            pm_logger.info("Applying import_data of profile '%s'" % profile_name)
            addPloneSite(
                self.app,
                str(i),
                title='Site title',
                setup_content=False,
                default_language=DEFAULT_LANGUAGE,
                extension_ids=('plonetheme.sunburst:default', profile_name, ))
            # check that configured Pod templates are correctly rendered
            # there should be no message of type
            tool = api.portal.get_tool('portal_plonemeeting')
            for cfg in tool.objectValues('MeetingConfig'):
                view = cfg.restrictedTraverse('@@check-pod-templates')
                messages = view.manageMessages()
                self.assertEquals(messages['error'], [])
                self.assertEquals(messages['no_pod_portal_types'], [])
                # check that there are no new keys in messages
                self.assertEquals(messages.keys(),
                                  ['error', 'no_obj_found',
                                   'no_pod_portal_types', 'not_enabled',
                                   'dashboard_templates_not_managed', 'clean'])
            # clean memoize between each site because the same REQUEST especially
            # is used for every sites and this can lead to problems...
            cleanMemoize(self.portal)
            i = i + 1

    def test_pm_WorkflowsRemovedOnReinstall(self):
        '''This will test that remove=True is used in the workflows.xml, indeed
           if it is not the case, the workflows are updated instead of being removed/re-added
           and that can lead to some weird behaviors because WFAdaptations add some
           transitions/states and these are left in the workflows.'''
        DUMMY_STATE = 'dummy_state'
        # add a state to the workflows then reinstall it
        wfTool = api.portal.get_tool('portal_workflow')
        for cfg in self.tool.objectValues('MeetingConfig'):
            # warning, here we get the real WF added by workflows.xml
            itemBaseWF = wfTool.getWorkflowById(cfg.getItemWorkflow())
            # this is necessary in case we use same WF for several MeetingConfigs
            if not DUMMY_STATE in itemBaseWF.states:
                itemBaseWF.states.addState(DUMMY_STATE)
            self.assertTrue(DUMMY_STATE in itemBaseWF.states)
            # same for Meeting workflow
            meetingBaseWF = wfTool.getWorkflowById(cfg.getMeetingWorkflow())
            if not DUMMY_STATE in meetingBaseWF.states:
                meetingBaseWF.states.addState(DUMMY_STATE)
            self.assertTrue(DUMMY_STATE in meetingBaseWF.states)
        # re-apply the workflows step, reinstall the :default profile
        profile_name = [pn for pn in self._currentSetupProfileNames() if pn.endswith(':default')][0]
        if not profile_name.startswith(u'profile-'):
            profile_name = u'profile-' + profile_name
        self.portal.portal_setup.runAllImportStepsFromProfile(profile_name,
                                                              dependency_strategy=DEPENDENCY_STRATEGY_REAPPLY)
        # now make sure WFs are clean
        for cfg in self.tool.objectValues('MeetingConfig'):
            itemBaseWF = wfTool.getWorkflowById(cfg.getItemWorkflow())
            self.assertFalse(DUMMY_STATE in itemBaseWF.states)
            meetingBaseWF = wfTool.getWorkflowById(cfg.getMeetingWorkflow())
            self.assertFalse(DUMMY_STATE in meetingBaseWF.states)

    def test_pm_ToolAttributesAreOnlySetOnFirstImportData(self):
        '''The tool attributes are set the first time it is imported, if some
           import_data are imported after, it does not change the tool attributes.'''
        # testing import_data has been imported, change a parameter in the tool
        # and import_data again to check
        self.changeUser('admin')
        self.assertFalse(self.tool.restrictUsers)
        self.tool.setRestrictUsers(True)
        # make sure restrictUsers is set in the 'testing' profile import_data
        profile_names = self._currentSetupProfileNames()
        profile_name = [p_name for p_name in profile_names if p_name.endswith(':testing')][0]
        profile_infos = [profile for profile in self.portal.portal_setup.listProfileInfo()
                         if profile['id'] == profile_name][0]
        path = profile_infos['path']
        import_context = DirectoryImportContext(self.portal.portal_setup, path)
        self.assertTrue('data.restrictUsers = False' in import_context.readDataFile('import_data.py'))
        self.portal.portal_setup.runAllImportStepsFromProfile(u'profile-' + profile_name)
        # restrictUsers is still True
        self.assertTrue(self.tool.restrictUsers)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSetup, prefix='test_pm_'))
    return suite
