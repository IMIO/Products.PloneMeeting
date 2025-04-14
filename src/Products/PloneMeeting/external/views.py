# -*- coding: utf-8 -*-

from appy.gen import No
from natsort import humansorted
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from Products.PloneMeeting.external.config import API_DELIB_UID
from Products.PloneMeeting.external.utils import send_json_request
from Products.PloneMeeting.utils import is_proposing_group_editor
from Products.PloneMeeting.config import PMMessageFactory as _

class ExternalView(BrowserView):
    """
      This manage functionnality around iA.Vision
    """

    def available(self):
        """ """
        return isinstance(self.content, list) and True or self.content

    def can_link(self):
        """Can link if:
           - can edit the item;
           - MeetingManager;
           - proposing group editor."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return _checkPermission(ModifyPortalContent, self.context) or \
            tool.isManager(cfg) or \
            is_proposing_group_editor(self.context.getProposingGroup(), cfg)

    def __call__(self):
        """ """
        if not self.context.isDefinedInTool():
            self.content = send_json_request(
                "delib-links", extra_parameters={"delib_uid": API_DELIB_UID})
            if self.content:
                self.content = humansorted(self.content, key=lambda x: x['target']['name'])
        else:
            self.content = No(_('Nothing to display.'))
        return super(ExternalView, self).__call__()
