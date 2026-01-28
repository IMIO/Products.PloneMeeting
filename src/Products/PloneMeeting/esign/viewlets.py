# -*- coding: utf-8 -*-

from imio.esign.browser.views import FacetedSessionInfoViewlet
from plone import api
from Products.PloneMeeting.esign.views import PMSessionsListingView


class PMFacetedSessionInfoViewlet(FacetedSessionInfoViewlet):

    sessions_listing_view = PMSessionsListingView

    def __init__(self, context, request, view, manager=None):
        """ """
        super(PMFacetedSessionInfoViewlet, self).__init__(
            context, request, view, manager=manager)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def sessions_collection_uid(self):
        return self.cfg.get('searches').get('searches_items').get('searchitemsinesignsessions').UID()
