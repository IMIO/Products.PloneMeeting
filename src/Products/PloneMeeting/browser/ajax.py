import logging
logger = logging.getLogger('PloneMeeting')
from Products.Five import BrowserView


class PloneMeetingAjaxView(BrowserView):
    """
      Manage ajax PloneMeeting functionnalities.
    """
