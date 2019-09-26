# -*- coding: utf-8 -*-
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

from collections import OrderedDict
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from plone import api
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.events import _is_held_pos_uid_used_by
from Products.PloneMeeting.utils import displaying_available_items
from zope.component import getMultiAdapter


class ForceInsertNormal(ViewletBase):
    '''This viewlet displays the forceInsertNormal button under the available
       items to present in a meeting on the meeting view.'''

    def available(self):
        """ """
        return displaying_available_items(self.context) and self.view.brains

    def enabled(self):
        """Is the checkbox enabled?  Only necessary if meeting is in a late state."""
        late_state = self.context.adapted().getLateState()
        return self.context.queryState() not in self.context.getStatesBefore(late_state)

    def render(self):
        if self.available():
            return self.index()
        else:
            return ''

    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')

    index = ViewPageTemplateFile("templates/viewlet_force_insert_normal.pt")


class PMMeetingBatchActionsViewlet(BatchActionsViewlet):
    """ """
    def available(self):
        """Not available on the 'available items' when displayed on a meeting."""
        if displaying_available_items(self.context):
            return False
        return True


class HeldPositionBackRefs(ViewletBase):
    """Display elements using held_position."""

    def available(self):
        """ """
        return True

    def using_configs(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        hp_uid = self.context.UID()
        res = []
        for cfg in tool.objectValues('MeetingConfig'):
            if _is_held_pos_uid_used_by(hp_uid, cfg):
                res.append(cfg)
        return res

    def using_meetings(self, limit=10):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        catalog = api.portal.get_tool('portal_catalog')
        hp_uid = self.context.UID()
        res = OrderedDict()
        for cfg in tool.objectValues('MeetingConfig'):
            meeting_type_name = cfg.getMeetingTypeName()
            brains = catalog(portal_type=meeting_type_name, sort_on='getDate')
            for brain in brains:
                meeting = brain.getObject()
                if _is_held_pos_uid_used_by(hp_uid, meeting):
                    if cfg not in res:
                        res[cfg] = []
                    res[cfg].append(meeting)
                    if len(res[cfg]) >= limit:
                        break
        return res

    index = ViewPageTemplateFile("templates/viewlet_held_position_back_refs.pt")
