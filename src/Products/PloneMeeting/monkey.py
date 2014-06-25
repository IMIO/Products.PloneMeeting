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
            path_translated = self.REQUEST.get('PATH_TRANSLATED', '')
            # do not return items of tool if using application
            if 'livesearch_reply' in path_translated or \
               'updated_search' in path_translated or \
               'plonemeeting_topic_view' in path_translated or \
               'search_form' in path_translated:
                kw['isDefinedInTool'] = False
            # if show_inactive is True, it means that we are using a layout
            # like folder_listing or folder_contents, check if we are in the configuration
            elif kw.get('show_inactive', False):
                # only query elements of the config if we are in the config...
                kw['isDefinedInTool'] = False
                if hasattr(self.REQUEST, 'PUBLISHED'):
                    context = hasattr(self.REQUEST['PUBLISHED'], 'context') and self.REQUEST['PUBLISHED'].context or self.REQUEST['PUBLISHED']
                    if 'portal_plonemeeting' in context.absolute_url() or 'portal_plonemeeting' in repr(context):
                        kw['isDefinedInTool'] = True
            elif 'portal_plonemeeting' in repr(self) and 'topics' in repr(self):
                # if we are executing a topic of a MeetingConfig, we do not want items of the tool
                kw['isDefinedInTool'] = False

        # for other cases, the 'isDefinedInTool' index is not in the
        # query so elements defined in the tool and not defined in the tool are taken into account
        return self.__pm_old_searchResults(REQUEST, **kw)

    CatalogTool.__pm_old_searchResults = CatalogTool.searchResults
    CatalogTool.searchResults = searchResults
    logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (searchResults)")
    CatalogTool.__call__ = searchResults
    logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (__call__)")

DefinedInToolAwareCatalog()
