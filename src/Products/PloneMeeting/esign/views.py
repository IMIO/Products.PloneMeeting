# -*- coding: utf-8 -*-

from imio.esign import manage_session_perm
from imio.esign.browser.views import ExternalSessionCreateView
from imio.esign.browser.views import SessionDeleteView
from imio.esign.browser.views import SessionFilesView
from imio.esign.browser.views import SessionsListingView
from imio.esign.utils import get_session_info
from imio.prettylink.interfaces import IPrettyLink
from plone import api
from Products.PloneMeeting.config import ESIGNWATCHERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX


class PMSessionsListingView(SessionsListingView):

    def __init__(self, context, request):
        super(PMSessionsListingView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def available(self):
        return self.tool.isManager(realManagers=True) or bool(self._get_access_groups())

    def get_dashboard_link(self, session):
        # if a cfg could not be initialized, we get it from the session first element
        if self.cfg is None:
            session_info = get_session_info(session['id'])
            self.cfg = self.tool.get(session_info['cfg_id'])
        # compute url
        url = ""
        if self.cfg:
            pm_folder = self.tool.getPloneMeetingFolder(self.cfg.getId())
            collection_uid = self.cfg.get('searches').get('searches_items').get('searchitemsinesignsessions').UID()
            url = "{pm_folder_url}/searches_items#c3=20&b_start=0&c1={collection_uid}" \
                "&esign_session_id={session_id}".format(
                    pm_folder_url=pm_folder.absolute_url(),
                    collection_uid=collection_uid,
                    session_id=session["id"],
                )
        return url

    def _get_access_groups(self):
        """Return groups of the user giving access to sessions.
           MeetingManagers and eSign watchers have access."""
        return self.tool.get_filtered_plone_groups_for_user(
            suffixes=[MEETINGMANAGERS_GROUP_SUFFIX, ESIGNWATCHERS_GROUP_SUFFIX])

    def get_sessions(self):
        """Filter sessions by MeetingConfig.
           Only keep sessions user is MeetingManager for."""
        sessions = super(PMSessionsListingView, self).get_sessions()
        if not self.tool.isManager(realManagers=True):
            manager_user_groups = self._get_access_groups()
            manager_cfg_ids = [
                group.replace("_%s" % MEETINGMANAGERS_GROUP_SUFFIX, "").replace(ESIGNWATCHERS_GROUP_SUFFIX, "")
                for group in manager_user_groups]
            sessions = [session for session in sessions if session['cfg_id'] in manager_cfg_ids]
        return sessions


class PMSessionFilesView(SessionFilesView):

    def get_file_link(self, ctx, obj):
        if ctx.getTagName() == 'MeetingItem':
            return ctx.getPrettyLink(
                contentValue=ctx.Title(withItemNumber=True, withMeetingDate=True)) + \
                u" ➔ " + IPrettyLink(obj).getLink()
        elif ctx.getTagName() == 'Meeting':
            return ctx.get_pretty_link(prefixed=True, short=False, showContentIcon=True) + \
                u" ➔ " + IPrettyLink(obj).getLink()


class PMSessionDeleteView(SessionDeleteView):
    """ """

    def __init__(self, context, request):
        super(PMSessionDeleteView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def may_delete_session(self):
        """Check if the user may delete sessions, check on self.tool as MeetingManagers are MeetingManagers on the tool."""
        return api.user.has_permission(manage_session_perm, obj=self.tool)


class PMExternalSessionCreateView(ExternalSessionCreateView):
    """ """

    def __init__(self, context, request):
        super(PMExternalSessionCreateView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def may_create_external_sessions(self):
        """Check if the user may create external sessions"""
        return api.user.has_permission(manage_session_perm, obj=self.tool)
