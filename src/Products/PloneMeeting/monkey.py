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
        show_inactive = kw.get('show_inactive', False)
        if show_inactive or \
           self.REQUEST.get('PATH_TRANSLATED', '').endswith('livesearch_reply') or \
           self.REQUEST.get('PATH_TRANSLATED', '').endswith('updated_search'):
            # only query elements of the config if we are in the config...
            kw['isDefinedInTool'] = False
            if hasattr(self.REQUEST, 'PUBLISHED'):
                context = hasattr(self.REQUEST['PUBLISHED'], 'context') and self.REQUEST['PUBLISHED'].context or self.REQUEST['PUBLISHED']
                if 'portal_plonemeeting' in context.absolute_url() or 'portal_plonemeeting' in repr(context):
                    kw['isDefinedInTool'] = True
        return self.__pm_old_searchResults(REQUEST, **kw)

    CatalogTool.__pm_old_searchResults = CatalogTool.searchResults
    CatalogTool.searchResults = searchResults
    logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (searchResults)")
    CatalogTool.__call__ = searchResults
    logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (__call__)")

DefinedInToolAwareCatalog()
