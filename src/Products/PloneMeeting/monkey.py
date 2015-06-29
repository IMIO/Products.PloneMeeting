# -*- coding: utf-8 -*-
#
# File: monkey.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

import logging
logger = logging.getLogger('Products.PloneMeeting')


def DefinedInToolAwareCatalog():
    """
      Patches the catalog tool to filter elements defined in portal_plonemeeting.
      This was inspired by code in collective.hiddencontent.
    """

    from Products.CMFPlone.CatalogTool import CatalogTool

    def searchResults(self, REQUEST=None, **kw):
        """ Calls ZCatalog.searchResults with extra arguments that
            limit the results to what the user is allowed to see.

            This version only returns the results for non-hidden
            content, unless you explicitly ask for all results by
            providing the hidden=true/all keyword.
        """
        if not 'isDefinedInTool' in kw:
            kw['isDefinedInTool'] = False
            # if show_inactive is True, it means that we are using a layout
            # like folder_listing or folder_contents, check if we are in the configuration
            if 'portal_plonemeeting' in repr(self) or \
               'portal_plonemeeting' in repr(self.REQUEST):
                kw['isDefinedInTool'] = True

        # for other cases, the 'isDefinedInTool' index is not in the
        # query so elements defined in the tool and not defined in the tool are taken into account
        return self.__pm_old_searchResults(REQUEST, **kw)

    CatalogTool.__pm_old_searchResults = CatalogTool.searchResults
    CatalogTool.searchResults = searchResults
    logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (searchResults)")
    CatalogTool.__call__ = searchResults
    logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (__call__)")

DefinedInToolAwareCatalog()
