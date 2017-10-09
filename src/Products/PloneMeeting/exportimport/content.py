# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Copyright (c) 2007 PloneGov
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

from zope.i18n import translate
from plone import api
from collective.iconifiedcategory import CAT_SEPARATOR
from Products.CMFPlone.interfaces.constrains import IConstrainTypes
from imio.dashboard.utils import _updateDefaultCollectionFor
from Products.PloneMeeting.config import PloneMeetingError
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import registerClasses
from Products.PloneMeeting.model.adaptations import performModelAdaptations
from Products.PloneMeeting.ToolPloneMeeting import MEETING_CONFIG_ERROR
from Products.PloneMeeting.utils import updateCollectionCriterion


# PloneMeeting-Error related constants -----------------------------------------
MEETINGCONFIG_BADREQUEST_ERROR = 'There was an error during creation of MeetingConfig with id "%s". ' \
                                 'Original error : "%s"'


class ToolInitializer:
    '''Initializes the PloneMeeting tool based on information from a given
       PloneMeeting profile.'''
    successMessage = "The PloneMeeting tool has been successfully initialized."
    noDataMessage = "No data to import for this profile"

    def __init__(self, context, productname):
        self.profilePath = context._profile_path
        # productname default's name space is 'Products'.
        # If a name space is found, then Products namespace is not used
        self.productname = '.' in productname and productname or 'Products.%s' % productname
        self.site = context.getSite()
        self.tool = self.site.portal_plonemeeting
        # set correct title
        self.tool.setTitle(translate('pm_configuration',
                           domain='PloneMeeting',
                           context=self.site.REQUEST))
        self.profileData = self.getProfileData()
        # Initialize the tool if we have data
        if not self.profileData:
            return
        # initialize the tool only if it was not already done before
        # by another profile, it is the case if some MeetingConfigs or MeetingGroups exist
        if not self.tool.objectIds('MeetingConfig') and \
           not self.tool.objectIds('MeetingGroup'):
            for k, v in self.profileData.getData().iteritems():
                exec 'self.tool.set%s%s(v)' % (k[0].upper(), k[1:])

    def getProfileData(self):
        '''Loads, from the current profile, the data to import into the tool:
           meeting config(s), categories, etc.'''
        pp = self.profilePath
        if not pp:
            return
        profileModule = pp[pp.rfind(self.productname.replace('.', '/')):].replace('/', '.')
        profileModule = profileModule.replace('\\', '.')
        data = ''
        module_path = 'from %s.import_data import data' % profileModule
        exec module_path
        return data

    def run(self):
        d = self.profileData
        if not d:
            return self.noDataMessage
        performModelAdaptations(self.tool)
        # Register classes again, after model adaptations have been performed
        # (see comment in __init__.py)
        registerClasses()
        # if we already have existing MeetingGroups, we do not add additional ones
        alreadyHaveGroups = bool(self.tool.objectValues('MeetingGroup'))
        if not alreadyHaveGroups:
            self.tool.addUsersAndGroups(d.groups)
        savedMeetingConfigsToCloneTo = {}

        created_cfgs = []
        for mConfig in d.meetingConfigs:
            # XXX we need to defer the management of the 'meetingConfigsToCloneTo'
            # defined on the mConfig after the creation of every mConfigs because
            # if we defined in mConfig1.meetingConfigsToCloneTo the mConfig2 id,
            # it will try to getattr this meetingConfig2 id that does not exist yet...
            # so save defined values, removed them from mConfig and manage that after
            savedMeetingConfigsToCloneTo[mConfig.id] = mConfig.meetingConfigsToCloneTo
            mConfig.meetingConfigsToCloneTo = []
            cfg = self.tool.createMeetingConfig(mConfig, source=self.profilePath)
            if cfg:
                created_cfgs.append(cfg)
                self._finishConfigFor(cfg, data=mConfig)

        # manage other_mc_correspondences
        for created_cfg in created_cfgs:
            self._manageOtherMCCorrespondences(created_cfg)

        # now that every meetingConfigs have been created, we can manage the meetingConfigsToCloneTo
        for mConfigId in savedMeetingConfigsToCloneTo:
            if not savedMeetingConfigsToCloneTo[mConfigId]:
                continue
            # initialize the attribute on the meetingConfig and call _updateCloneToOtherMCActions
            cfg = getattr(self.tool, mConfigId)
            # validate the MeetingConfig.meetingConfigsToCloneTo data that we are about to set
            error = cfg.validate_meetingConfigsToCloneTo(savedMeetingConfigsToCloneTo[mConfigId])
            if error:
                raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), error))
            cfg.setMeetingConfigsToCloneTo(savedMeetingConfigsToCloneTo[mConfigId])
            cfg._updateCloneToOtherMCActions()
        # finally, create the current user (admin) member area
        self.site.portal_membership.createMemberArea()
        # at the end, add users outside PloneMeeting groups because
        # they could have to be added in groups created by the MeetingConfig
        if not alreadyHaveGroups:
            self.tool.addUsersOutsideGroups(d.usersOutsideGroups)
        # finally update MeetingUsers created if each MeetingConfig because
        # title rely on Plone user that is often created in the usersOutsideGroups
        for created_cfg in created_cfgs:
            for mUser in created_cfg.meetingusers.objectValues('MeetingUser'):
                mUser.at_post_edit_script()
        return self.successMessage

    def _finishConfigFor(self, cfg, data):
        """When the MeetingConfig has been created, some parameters still need to be applied
           because they need the MeetingConfig to exist."""
        # apply the meetingTopicStates to the 'searchallmeetings' DashboardCollection
        updateCollectionCriterion(cfg.searches.searches_meetings.searchallmeetings,
                                  'review_state',
                                  data.meetingTopicStates)
        # apply the maxDaysDecisions to the 'searchlastdecisions' DashboardCollection
        updateCollectionCriterion(cfg.searches.searches_decisions.searchlastdecisions,
                                  'getDate',
                                  data.maxDaysDecisions)
        # apply the decisionTopicStates to the 'searchlastdecisions'
        # and 'searchalldecision' DashboardCollections
        updateCollectionCriterion(cfg.searches.searches_decisions.searchlastdecisions,
                                  'review_state',
                                  data.decisionTopicStates)
        updateCollectionCriterion(cfg.searches.searches_decisions.searchalldecisions,
                                  'review_state',
                                  data.decisionTopicStates)
        # select correct default view
        meetingAppDefaultView = data.meetingAppDefaultView
        if meetingAppDefaultView in cfg.searches.searches_items.objectIds():
            default_uid = getattr(cfg.searches.searches_items,
                                  meetingAppDefaultView).UID()
            # update the criterion default value in searches and searches_items folders
            _updateDefaultCollectionFor(cfg.searches, default_uid)
            _updateDefaultCollectionFor(cfg.searches.searches_items, default_uid)
        else:
            error = 'meetingAppDefaultView : No DashboardCollection with id %s' % meetingAppDefaultView
            raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), error))

        # now we can set values for dashboard...Filters fields as the 'searches' folder has been created
        for fieldName in ('dashboardItemsListingsFilters',
                          'dashboardMeetingAvailableItemsFilters',
                          'dashboardMeetingLinkedItemsFilters'):
            field = cfg.getField(fieldName)
            # we want to validate the vocabulay, as if enforceVocabulary was True
            error = field.validate_vocabulary(cfg, cfg.getField(field.getName()).get(cfg), {})
            if error:
                raise PloneMeetingError(MEETING_CONFIG_ERROR % (cfg.getId(), error))

    def _manageOtherMCCorrespondences(self, cfg):
        def _convert_to_real_other_mc_correspondences(annex_type):
            """ """
            tool = api.portal.get_tool('portal_plonemeeting')
            real_other_mc_correspondences = []
            # we have a content_category id prefixed with cfg id
            # like meeting-config-test_-_annexes_types_-_item_annexes_-_annex
            # but we need the UID of the corresponding annexType
            for other_mc_correspondence in annex_type.other_mc_correspondences:
                steps = other_mc_correspondence.split(CAT_SEPARATOR)
                other_cfg = tool.get(steps[0])
                corresponding_annex_type = other_cfg
                for step in steps[1:]:
                    corresponding_annex_type = corresponding_annex_type[step]
                real_other_mc_correspondences.append(corresponding_annex_type.UID())
            annex_type.other_mc_correspondences = set(real_other_mc_correspondences)

        # finish configuration of annexType.other_mc_correspondences
        # for ItemAnnexContentCategory and ItemAnnexContentSubcategory
        for annex_group in cfg.annexes_types.objectValues():
            if 'ItemAnnexContentCategory' in IConstrainTypes(annex_group).getLocallyAllowedTypes():
                for annex_type in annex_group.objectValues():
                    if annex_type.other_mc_correspondences:
                        _convert_to_real_other_mc_correspondences(annex_type)
                        for subType in annex_type.objectValues():
                            _convert_to_real_other_mc_correspondences(subType)


def isTestOrArchiveProfile(context):
    isTest = context.readDataFile("PloneMeeting_testing_marker.txt")
    isArchive = context.readDataFile("PloneMeeting_archive_marker.txt")
    return isTest or isArchive


def initializeTool(context):
    '''Initialises the PloneMeeting tool based on information from the current
       profile.'''
    # This method is called by several profiles: testing, archive. Because of a bug
    # in portal_setup, the method can be wrongly called by the default profile.
    if not isTestOrArchiveProfile(context):
        return
    # Installs PloneMeeting if not already done
    pqi = context.getSite().portal_quickinstaller
    # Now that we do not run this profile from elsewhere than portal_setup
    # We had to install PloneMeeting first...
    # pqi.listInstalledProducts()
    if not pqi.isProductInstalled('PloneMeeting'):
        profileId = u'profile-Products.PloneMeeting:default'
        context.getSite().portal_setup.runAllImportStepsFromProfile(profileId)
    # Initialises data from the profile.
    return ToolInitializer(context, PROJECTNAME).run()
