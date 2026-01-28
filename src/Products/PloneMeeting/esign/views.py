# -*- coding: utf-8 -*-

from imio.esign.browser.views import SessionsListingView
from plone import api


class PMSessionsListingView(SessionsListingView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def get_dashboard_link(self, session):
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

    def get_sessions_url(self):
        return api.portal.get()["sessions"].absolute_url()
