# -*- coding: utf-8 -*-

from imio.esign.browser.views import FacetedSessionInfoViewlet
from imio.esign.browser.views import ItemSessionInfoViewlet
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
        return self.cfg.get('searches').get('searches_items').get(
            'searchitemsinesignsessions').UID() if self.cfg else None

    def collapsible_css_default(self):
        """Default CSS class to apply on the collapsible."""
        return "collapsible discreet active"

    def collapsible_content_css_default(self):
        """Default CSS class to apply on the collapsible."""
        return "collapsible-content discreet"

    def available(self):
        """Can be displayed on MeetingItem, Meeting or MeetingAdvice."""
        # if can see the collection, can see the viewlet
        return True


class PMItemSessionInfoViewlet(ItemSessionInfoViewlet, PMFacetedSessionInfoViewlet):
    """ """

    def available(self):
        """Can be displayed on:
           - MeetingItem to proposingGroup and MeetingManagers;
           - Meeting the MeetingManagers;
           - MeetingAdvice to proposingGroup, advisers and MeetingManagers."""
        isManager = self.tool.isManager(self.cfg)
        if self.context.getTagName() == "MeetingItem":
            return isManager or self.context.getProposingGroup() in self.tool.get_orgs_for_user()
        elif self.context.getTagName() == "Meeting":
            return isManager
        elif self.context.getTagName() == "MeetingAdvice":
            return isManager or self.context.advice_group in self.tool.get_orgs_for_user(suffixes=['advisers'])
        return True
