# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_own_organization
from collective.contact.widget.source import ContactSource
from collective.contact.widget.source import ContactSourceBinder


#############################################
#
#      NOT USED ANYMORE TO BE REMOVED
#
#############################################

class PMContactSource(ContactSource):
    """Returns organizations, except ones stored in PLONEGROUP_ORG."""

    def search(self, query, relations=None, limit=50):
        """Base selectable_filter do the job but do not query own_org,
           we append it at the beginning of the vocabulary."""
        results = [term for term in super(PMContactSource, self).search(query, relations, limit)]
        brains = self.catalog(UID=get_own_organization().UID())
        results.insert(0, self.getTermByBrain(brains[0], real_value=False))
        return results


class PMContactSourceBinder(ContactSourceBinder):
    """Returns organizations, except ones stored in PLONEGROUP_ORG."""
    path_source = PMContactSource

    def __init__(self, navigation_tree_query=None, default=None, defaultFactory=None, **kw):
        super(PMContactSourceBinder, self).__init__(navigation_tree_query, default, defaultFactory, **kw)
        self.selectable_filter.criteria = {
            'portal_type': ('organization', ),
            'object_provides': ['collective.contact.plonegroup.interfaces.INotPloneGroupContact']}
