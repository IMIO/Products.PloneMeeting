# -*- coding: utf-8 -*-

from imio.esign.browser.views import SessionFilesView
from imio.esign.browser.views import SessionsListingView
from imio.esign.utils import get_session_info
from imio.prettylink.interfaces import IPrettyLink
from plone import api


class PMSessionsListingView(SessionsListingView):

    def __init__(self, context, request):
        super(PMSessionsListingView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

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


class PMSessionFilesView(SessionFilesView):

    def get_file_link(self, ctx, obj):
        return ctx.getPrettyLink(
            contentValue=ctx.Title(withItemNumber=True, withMeetingDate=True)) + \
            u" ➔ " + IPrettyLink(obj).getLink()
