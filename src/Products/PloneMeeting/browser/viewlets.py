# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from collections import OrderedDict
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from plone import api
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.config import ITEM_INITIATOR_INDEX_PATTERN
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
        return self.context.is_late()

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


class AnnexesBatchActionsViewlet(BatchActionsViewlet):
    """ """

    section = "annexes"

    def available(self):
        """ """
        return True

    @property
    def select_item_name(self):
        """Manage fact that in the annexes, there are 2 tables
          (annexes and decision annexes) that use a different name
          for the checkbox column."""
        value = None
        if self.request.get('categorized_tab').portal_type == 'annexDecision':
            value = "select_item_annex_decision"
        else:
            value = super(AnnexesBatchActionsViewlet, self).select_item_name
        return value


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
            brains = catalog(portal_type=meeting_type_name,
                             sort_on='meeting_date',
                             sort_order='reverse')
            for brain in brains:
                meeting = brain.getObject()
                if _is_held_pos_uid_used_by(hp_uid, meeting):
                    if cfg not in res:
                        res[cfg] = []
                    res[cfg].append(meeting)
                    if len(res[cfg]) >= limit:
                        break
        return res

    def using_items(self, limit=10):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        catalog = api.portal.get_tool('portal_catalog')
        hp_uid = self.context.UID()
        res = OrderedDict()
        for cfg in tool.objectValues('MeetingConfig'):
            item_type_name = cfg.getItemTypeName()
            brains = catalog(
                portal_type=item_type_name,
                pm_technical_index=[
                    ITEM_INITIATOR_INDEX_PATTERN.format(hp_uid)],
                sort_on='meeting_date',
                sort_order='reverse')
            for brain in brains:
                if cfg not in res:
                    res[cfg] = []
                res[cfg].append(brain)
                if len(res[cfg]) >= limit:
                    break
        return res

    index = ViewPageTemplateFile("templates/viewlet_held_position_back_refs.pt")
