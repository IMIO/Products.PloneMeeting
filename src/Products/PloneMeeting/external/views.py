# -*- coding: utf-8 -*-

from Products.Five import BrowserView
from Products.PloneMeeting.external.config import API_DELIB_UID
from Products.PloneMeeting.external.utils import send_json_request


class ExternalView(BrowserView):
    """
      This manage functionnality around iA.Vision
    """

    def available(self):
        """ """
        return bool(self.content)

    def __call__(self):
        """ """
        self.content = send_json_request(
            "delib-links", extra_parameters={"delib_uid": API_DELIB_UID})
        return super(ExternalView, self).__call__()
