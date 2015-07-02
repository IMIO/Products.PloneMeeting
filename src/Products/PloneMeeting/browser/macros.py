from Products.Five import BrowserView


class PloneMeetingMacros(BrowserView):
    """
      Manage macros used for PloneMeeting.
    """
    def callMacro(self, page, macro):
        """
          Call the given p_macro on given p_page (that is a BrowserView containing macros)
        """
        return self.context.unrestrictedTraverse(page)[macro]
