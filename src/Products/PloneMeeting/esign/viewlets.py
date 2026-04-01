# -*- coding: utf-8 -*-

from imio.esign.browser.views import FacetedSessionInfoViewlet
from imio.esign.browser.views import ItemSessionInfoViewlet
from plone import api
from Products.PloneMeeting.esign.utils import esign_access_groups
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
        url = self.request.getURL()
        if 'searches_items' in url:
            return self.cfg.get('searches').get('searches_items').get(
                'searchitemsinesignsessions').UID() if self.cfg else None
        elif 'searches_decisions' in url:
            return self.cfg.get('searches').get('searches_decisions').get(
                'searchmeetingsinesignsessions').UID() if self.cfg else None
        # important, do not return None
        return ""

    def collapsible_css_default(self):
        """Default CSS class to apply on the collapsible."""
        return "collapsible discreet active"

    def collapsible_content_css_default(self):
        """Default CSS class to apply on the collapsible."""
        return "collapsible-content discreet"


class PMItemSessionInfoViewlet(ItemSessionInfoViewlet, PMFacetedSessionInfoViewlet):
    """ """

    def available(self):
        """Can be displayed on:
           - MeetingItem to proposingGroup and esign access groups;
           - Meeting the esign access groups;
           - MeetingAdvice to proposingGroup, advisers and esign_access_groups."""
        if bool(esign_access_groups()) or self.tool.isManager(realManagers=True):
            return True
        tag_name = self.context.getTagName()
        if tag_name == "MeetingItem":
            return self.context.getProposingGroup() in self.tool.get_orgs_for_user()
        elif tag_name == "MeetingAdvice":
            return self.context.getProposingGroup() in self.tool.get_orgs_for_user() or \
                self.context.advice_group in self.tool.get_orgs_for_user(suffixes=['advisers'])
        else:
            return False
