# -*- coding: utf-8 -*-

from appy.gen import No
from natsort import humansorted
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.PloneMeeting.external.utils import send_vision_json_request
from Products.PloneMeeting.utils import is_proposing_group_editor
from zope.i18n import translate

import json
import requests


class ExternalView(BrowserView):
    """
      This manage functionnality around iA.Vision
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self):
        """ """
        if not self.context.isDefinedInTool():
            self.result = send_vision_json_request(
                "delib-links", extra_parameters={"delib_uid": self.context.UID()})
            if not isinstance(self.result, requests.Response):
                self.result = humansorted(self.result, key=lambda x: x['target']['name'])
        else:
            self.result = No(translate('Nothing to display.', domain='PloneMeeting', context=self.request))
        return super(ExternalView, self).__call__()

    def available(self):
        """ """
        if isinstance(self.result, requests.Response):
            # error
            try:
                error = json.loads(self.result.content)
            except ValueError:
                error = self.result.text
            self.result = No(
                u"%s (%s)" %
                (translate('Nothing to display.',
                           domain='PloneMeeting',
                           context=self.request),
                 safe_unicode(error)))
        return isinstance(self.result, list) and True or self.result

    def can_link(self):
        """Can link if:
           - can edit the item;
           - MeetingManager;
           - proposing group editor."""
        return _checkPermission(ModifyPortalContent, self.context) or \
            self.tool.isManager(self.cfg) or \
            is_proposing_group_editor(self.context.getProposingGroup(), self.cfg)

    def show_section(self):
        """Display the "External linked elements" on the item view?"""
        return self.cfg.getId() in self.tool.getShowExternalLinksSection()
