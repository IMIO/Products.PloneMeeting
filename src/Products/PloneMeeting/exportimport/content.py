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

__author__ = '''Gauthier BASTIEN <gbastien@commune.sambreville.be>'''
__docformat__ = 'plaintext'

'''PloneMeeting exportimport setup.
   This is the exportimport file for GenericSetup. See configure.zcml and
   profiles/default for more information.'''

# ------------------------------------------------------------------------------
from zExceptions import BadRequest
from Products.PloneMeeting.config import *
from Products.PloneMeeting.model.adaptations import performModelAdaptations
import logging
logger = logging.getLogger('PloneMeeting')

# PloneMeeting-Error related constants -----------------------------------------
MEETING_ID_EXISTS = 'The meeting config with id "%s" already exists.'

# ------------------------------------------------------------------------------
class ToolInitializer:
    '''Initializes the PloneMeeting tool based on information from a given
       PloneMeeting profile.'''
    successMessage = "The PloneMeeting tool has been successfully initialized."
    noDataMessage = "No data to import for this profile"

    def __init__(self, context, productname):
        self.profilePath = context._profile_path
        # productname is like Products.MyProfile or mypackage.specialprofile
        self.productname = productname
        self.site = context.getSite()
        self.tool = self.site.portal_plonemeeting
        self.profileData = self.getProfileData()
        # Initialize the tool if we have data
        if not self.profileData:
            return
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
        try:
            module_path = 'from %s.import_data import data' % profileModule
            exec module_path
            return data
        except ImportError:
            # This is the case if we reinstall PloneMeeting, no data is defined
            # in the default profile.
            logger.warn("Unable to import %s" % module_path)

    def run(self):
        # Import external applications
        d = self.profileData
        if not d:
            return self.noDataMessage
        performModelAdaptations(self.tool)
        # Register classes again, after model adaptations have been performed
        # (see comment in __init__.py)
        registerClasses()
        self.tool.updateLanguageSettings()
        self.tool.addExternalApplications(d.externalApplications)
        self.tool.addUsersAndGroups(d.groups, d.usersOutsideGroups)
        for mConfig in d.meetingConfigs:
            try:
                self.tool.createMeetingConfig(mConfig, source=self.profilePath)
            except BadRequest:
                # If we raise a BadRequest, it is that the id is already in use.
                logger.warn(MEETING_ID_EXISTS % mConfig.id)
        return self.successMessage

# Functions that correspond to the PloneMeeting profile import steps -----------
def isTestOrArchiveProfile(context):
    isTest = context.readDataFile("PloneMeeting_test_marker.txt")
    isArchive = context.readDataFile("PloneMeeting_archive_marker.txt")
    return isTest or isArchive

def initializeTool(context):
    '''Initialises the PloneMeeting tool based on information from the current
       profile.'''
    # This method is called by several profiles: test, archive. Because of a bug
    # in portal_setup, the method can be wrongly called by the default profile.
    if not isTestOrArchiveProfile(context): return
    # Installs HubSessions/PloneMeeting if not already done
    pqi = context.getSite().portal_quickinstaller
    # Now that we do not run this profile from elsewhere than portal_setup
    # We had to install PloneMeeting first...
    # pqi.listInstalledProducts()
    if not pqi.isProductInstalled('PloneMeeting'):
        profileId = u'profile-Products.PloneMeeting:default'
        context.getSite().portal_setup.runAllImportStepsFromProfile(profileId)
    # Initialises data from the profile.
    return ToolInitializer(context, PROJECTNAME).run()
# ------------------------------------------------------------------------------
