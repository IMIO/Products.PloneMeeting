from DateTime import DateTime
from Products.Five import BrowserView


class AnnexesMacros(BrowserView):
    """
      Manage macros used for annexes
    """
    def now(self):
        return DateTime()
