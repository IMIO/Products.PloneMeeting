# -*- coding: utf-8 -*-

from plone import api
from collective.contact.core.browser.organization import SubOrganizations
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY


class PMSubOrganizations(SubOrganizations):

    def __call__(self, level=0):
        self.level = level
        self.portal_url = api.portal.get().absolute_url()
        return self.index()

    def get_sub_organizations(self, organization):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        path = '/'.join(organization.getPhysicalPath())
        sub_organizations = catalog.searchResults(
            portal_type="organization",
            path={'query': path,
                  'depth': 1},
            sort_on='sortable_title')
        return [sub_org.getObject() for sub_org in sub_organizations]

    def is_active(self, organization):
        """ """
        return api.content.get_state(organization) == 'active'

    def may_add_organization(self, orga):
        """ """
        return orga.getTypeInfo() in orga.allowedContentTypes()

    def display_warnings(self, orga):
        """ """
        plonegroup_organizations = api.portal.get_registry_record(ORGANIZATIONS_REGISTRY)
        orga_uid = orga.UID()
        res = []
        if not orga.selectable_for_plonegroup:
            res.append(0)
        if orga.selectable_for_plonegroup and orga_uid not in plonegroup_organizations:
            res.append(1)
        return res
