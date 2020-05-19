# -*- coding: utf-8 -*-

from App.class_init import InitializeClass
from Products.CMFPlone.CatalogTool import CatalogTool


class LookupCatalogTool(CatalogTool):
    """ """
    id = 'lookup_catalog'
    meta_type = 'Lookup Catalog Tool'


InitializeClass(CatalogTool)
