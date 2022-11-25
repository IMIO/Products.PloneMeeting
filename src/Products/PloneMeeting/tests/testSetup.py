# -*- coding: utf-8 -*-
#
# File: testSetup.py
#
# GNU General Public License (GPL)
#

from imio.helpers.content import object_values
from pkgutil import iter_importers
from plone import api
from Products.GenericSetup.context import DirectoryImportContext
from Products.PloneMeeting.config import HAS_SOLR
from Products.PloneMeeting.exportimport.content import ToolInitializer
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import cleanMemoize

import os
import random


old__getProfileData = ToolInitializer.getProfileData


def getProfileData(self):
    """Patch getProfileData so we are sure we have only one
       MeetingConfig created with same id, this is necessary
       to test successive MC creations because it fails when creating
       successively"""
    data = old__getProfileData(self)
    for mc in data.meetingConfigs:
        # save original if so we may use it when necessary
        mc.__real_id__ = mc.id
        # shuffle MC id
        mc_id = list(mc.id)
        random.shuffle(mc_id)
        mc.id = ''.join(mc_id)
    return data


class testSetup(PloneMeetingTestCase):
    '''Tests the setup, especially registered profiles.'''

    def _currentSetupProfileNames(self, excluded=[]):
        """ """
        package_name = self.layer.__module__.replace('.testing', '')
        profile_names = [info['id'] for info in self.portal.portal_setup.listProfileInfo()
                         if info['product'] == package_name and
                         not info['id'].endswith(tuple(excluded))]
        return profile_names

    def _deleteItemAndMeetings(self):
        """Find and delete items and meetings without using portal_catalog."""
        meetings = []
        items = []
        for user_folder in self.portal.Members.objectValues():
            mymeetings = user_folder.get('mymeetings')
            if mymeetings:
                for cfg_folder in mymeetings.objectValues():
                    meetings = meetings + list(object_values(cfg_folder, 'Meeting'))
                    items = items + list(object_values(cfg_folder, 'MeetingItem'))
        # delete items first because deleting a meeting delete included items...
        for obj in items + meetings:
            parent = obj.aq_inner.aq_parent
            parent.manage_delObjects(ids=[obj.getId()])

    def test_pm_InstallAvailableProfiles(self):
        """This is made for subpackages to test that defined profiles
           containing an import_data works as expected."""
        ToolInitializer.getProfileData = getProfileData
        self.changeUser('admin')

        api.portal.set_registry_record(
            'collective.documentgenerator.browser.controlpanel.'
            'IDocumentGeneratorControlPanelSchema.raiseOnError_for_non_managers',
            True)

        # get current package name based on testing layer
        profile_names = self._currentSetupProfileNames(excluded=(':default', ':testing'))
        for profile_name in profile_names:
            pm_logger.info("Applying import_data of profile '%s'" % profile_name)
            # delete existing organizations and MeetingConfigs
            for cfg in self.tool.objectValues('MeetingConfig'):
                self._deleteItemAndMeetings()
                self._removeConfigObjectsFor(cfg)
                self.tool.manage_delObjects(ids=cfg.getId())
            self._removeOrganizations()
            # remove every DashboardPODTemplates stored in contacts
            to_remove = [obj.getId() for obj in self.portal.contacts.objectValues()
                         if obj.portal_type in ('person', 'DashboardPODTemplate')]
            self.portal.contacts.manage_delObjects(ids=to_remove)

            self.portal.portal_setup.runAllImportStepsFromProfile(u'profile-' + profile_name)
            # check that configured Pod templates are correctly rendered
            # there should be no message of type 'error' or 'no_pod_portal_types'
            tool = api.portal.get_tool('portal_plonemeeting')
            for cfg in tool.objectValues('MeetingConfig'):
                view = cfg.restrictedTraverse('@@check-pod-templates')
                view()
                self.assertEqual(view.messages['check_pod_template_error'], {})
                # ignore DashboardPODTemplate, it has a pod_portal_types attribute
                # but it is omitted in the form
                no_pod_portal_types = view.no_pod_portal_types.copy()
                if no_pod_portal_types:
                    no_pod_portal_types = [
                        pod_template for pod_template, dummy, dummy in
                        view.no_pod_portal_types.values()[0]
                        if pod_template.portal_type != 'DashboardPODTemplate']
                self.assertFalse(no_pod_portal_types)
                # check that there are no new keys in messages
                self.assertEqual(view.messages.keys(),
                                 ['check_pod_template_error',
                                  'check_pod_template_no_obj_found',
                                  'check_pod_template_no_pod_portal_types',
                                  'check_pod_template_not_enabled',
                                  'check_pod_template_not_managed',
                                  'check_pod_template_clean'])
                # access application to check that not errors are raised,
                # especially regarding the searches displayed in the collection portlet
                # make sure extra searches are added
                cfg.createSearches(cfg._searchesInfo())
                self.changeUser('pmCreator1')
                searches_items = self.getMeetingFolder(cfg).searches_items
                self.assertFalse('There was an error while rendering the portlet.' in searches_items())
                self.changeUser('admin')
                # call test_pm_VersionableTypes for every profiles
                self.test_pm_VersionableTypes()
            # clean memoize between each site because the same REQUEST especially
            # is used for every sites and this can lead to problems...
            cleanMemoize(self.portal)
        ToolInitializer.getProfileData = old__getProfileData

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
            if DUMMY_STATE not in itemBaseWF.states:
                itemBaseWF.states.addState(DUMMY_STATE)
            self.assertTrue(DUMMY_STATE in itemBaseWF.states)
            # same for Meeting workflow
            meetingBaseWF = wfTool.getWorkflowById(cfg.getMeetingWorkflow())
            if DUMMY_STATE not in meetingBaseWF.states:
                meetingBaseWF.states.addState(DUMMY_STATE)
            self.assertTrue(DUMMY_STATE in meetingBaseWF.states)
        # re-apply the workflows step from the :default profile
        item_wf_time = float(itemBaseWF._p_mtime)
        meeting_wf_time = float(meetingBaseWF._p_mtime)
        profile_name = [pn for pn in self._currentSetupProfileNames() if pn.endswith(':default')][0]
        if not profile_name.startswith(u'profile-'):
            profile_name = u'profile-' + profile_name
        self.portal.portal_setup.runImportStepFromProfile(
            profile_name, 'workflow')
        # now make sure WFs are clean
        for cfg in self.tool.objectValues('MeetingConfig'):
            itemBaseWF = wfTool.getWorkflowById(cfg.getItemWorkflow())
            if itemBaseWF._p_mtime != item_wf_time:
                self.assertFalse(DUMMY_STATE in itemBaseWF.states)
            else:
                pm_logger.info('test_pm_WorkflowsRemovedOnReinstall: item workflow not updated using '
                               'profile_name {0} for MeetingConfig {1}?'.format(profile_name, cfg.getId()))
            meetingBaseWF = wfTool.getWorkflowById(cfg.getMeetingWorkflow())
            if meetingBaseWF._p_mtime != meeting_wf_time:
                self.assertFalse(DUMMY_STATE in meetingBaseWF.states)
            else:
                pm_logger.info('test_pm_WorkflowsRemovedOnReinstall: meeting workflow not updated using '
                               'profile_name {0} for MeetingConfig {1}?'.format(profile_name, cfg.getId()))

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
        import imp
        import_data = imp.load_source('', import_context._profile_path + '/import_data.py')
        self.assertFalse(import_data.data.restrictUsers)
        self.portal.portal_setup.runAllImportStepsFromProfile(u'profile-' + profile_name)
        # restrictUsers is still True
        self.assertTrue(self.tool.restrictUsers)

    def test_pm_TypesNotSearched(self):
        """Searchable types are only items and meetings of existing MeetingConfigs."""
        plone_utils = api.portal.get_tool('plone_utils')
        expected = []
        for cfg in self.tool.objectValues('MeetingConfig'):
            expected.append(cfg.getItemTypeName())
            expected.append(cfg.getMeetingTypeName())
        self.assertEqual(set(plone_utils.getUserFriendlyTypes()),
                         set(expected))

        # if a new MeetingConfig is created, types_not_searched are updated accordingly
        self.changeUser('admin')
        newCfg = self.create('MeetingConfig', shortName='New')
        expected.append(newCfg.getItemTypeName())
        expected.append(newCfg.getMeetingTypeName())
        self.assertEqual(set(plone_utils.getUserFriendlyTypes()),
                         set(expected))

    def test_pm_FactoryTypes(self):
        """Every MeetingItem portal_types are using portal_factory.
           Every MeetingItem* portal_types should be registered."""
        portal_factory = api.portal.get_tool('portal_factory')
        factory_types = portal_factory.getFactoryTypes().keys()
        portal_types = api.portal.get_tool('portal_types')
        # every portal_types starting with MeetingItem/MeetingConfig
        meeting_types = [pt for pt in portal_types if pt.startswith(('MeetingConfig', 'MeetingItem'))]
        for meeting_type in meeting_types:
            self.failIf(set(meeting_types).difference(factory_types))

    def test_pm_VersionableTypes(self):
        """Make sure every Plone default types are not more versionable."""
        portal_repository = api.portal.get_tool('portal_repository')
        versioned = [u'annex', u'annexDecision']
        self.assertEqual(sorted(portal_repository.getVersionableContentTypes()), versioned)
        self.assertEqual(sorted(portal_repository._version_policy_mapping.keys()), versioned)

    def test_pm_EnsureSolrActivated(self):
        """ """
        pm_logger.info("HAS_SOLR %s" % HAS_SOLR)
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.create('MeetingItem')
        brains = self.catalog(portal_type=cfg.getItemTypeName())
        if HAS_SOLR:
            self.assertTrue(self.portal.portal_quickinstaller.isProductInstalled('collective.solr'),
                            msg="collective.solr is not installed")
            self.assertTrue(api.portal.get_registry_record('collective.solr.active'),
                            msg="collective.solr is not active")
            self.assertEqual(api.portal.get_registry_record('collective.solr.port'), int(os.environ['SOLR_PORT']))
            self.assertEqual(api.portal.get_registry_record('collective.solr.required'), [u''])
            self.assertEqual(brains[0].__class__.__name__, 'PloneFlare')
        else:
            self.assertEqual(brains[0].__class__.__name__, 'mybrains')
            pm_logger.info("HAS_SOLR is False so there is nothing more to check")

    def test_pm_DevPackages(self):
        """Display a log message with packages found in dev.
           This is useful for the bin/testprod that should have 0 dev packages."""
        dev_package_paths = [package.path for package in iter_importers()
                             if hasattr(package, "path") and
                             package.path and
                             "/src/" in package.path]
        pm_logger.info("Number of dev packages: %d" % len(dev_package_paths))
        for dev_package_path in dev_package_paths:
            pm_logger.info("Dev package: %s" % dev_package_path)


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testSetup, prefix='test_pm_'))
    return suite
