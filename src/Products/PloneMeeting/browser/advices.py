# -*- coding: utf-8 -*-
#
# File: annexes.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from AccessControl import Unauthorized
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView


class AdvicesIcons(BrowserView):
    """
      Advices displayed as icons.
    """
    def __init__(self, context, request):
        """ """
        super(AdvicesIcons, self).__init__(context, request)
        self.tool = getToolByName(self, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self):
        if not self.context.adapted().isPrivacyViewable():
            return '-'
        return super(AdvicesIcons, self).__call__()


class ChangeAdviceHiddenDuringRedactionView(BrowserView):
    """View that toggle the advice.advice_hide_during_redaction attribute."""

    def __call__(self):
        # user must be able to edit the advice
        if not _checkPermission('Modify portal content', self.context):
            raise Unauthorized
        else:
            # toggle the value
            self.context.advice_hide_during_redaction = not bool(self.context.advice_hide_during_redaction)
            notify(ObjectModifiedEvent(self.context))
