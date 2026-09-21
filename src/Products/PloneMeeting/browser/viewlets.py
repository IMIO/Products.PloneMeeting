# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from cgi import escape
from collections import OrderedDict
from eea.facetednavigation.interfaces import IFacetedNavigable
from plone import api
from plone.app.layout.viewlets import ViewletBase
from plone.app.layout.viewlets.common import TitleViewlet
from plone.memoize.view import memoize
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.config import ITEM_INITIATOR_INDEX_PATTERN
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.events import _is_held_pos_uid_used_by
from Products.PloneMeeting.utils import displaying_available_items
from zope.component import getMultiAdapter


class ForceInsertNormal(ViewletBase):
    '''This viewlet displays the forceInsertNormal button under the available
       items to present in a meeting on the meeting view.'''

    def available(self):
        """Always available on available items because we have there JS
           computing number of available items, we rely on the show method."""
        return displaying_available_items(self.context)

    def show(self):
        """ """
        return self.view.brains

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


class HeldPositionBackRefs(ViewletBase):
    """Display elements using held_position."""

    index = ViewPageTemplateFile("templates/viewlet_held_position_back_refs.pt")

    def __init__(self, context, request, view, manager=None):
        super(HeldPositionBackRefs, self).__init__(context, request, manager)
        self.context_url = self.context.absolute_url()

    def available(self):
        """ """
        return True


class HeldPositionBackRefsView(BrowserView):
    """The asynch view that displays elements using held_position."""

    def using_configs(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        hp_uid = self.context.UID()
        res = []
        for cfg in tool.objectValues('MeetingConfig'):
            if _is_held_pos_uid_used_by(hp_uid, cfg):
                res.append(cfg)
        return res

    def using_meetings(self, limit=50):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        catalog = api.portal.get_tool('portal_catalog')
        hp_uid = self.context.UID()
        res = OrderedDict()
        for cfg in tool.objectValues('MeetingConfig'):
            meeting_type_name = cfg.getMeetingTypeName()
            brains = catalog.unrestrictedSearchResults(
                portal_type=meeting_type_name,
                sort_on='meeting_date',
                sort_order='reverse')
            for brain in brains:
                meeting = brain.getObject()
                if _is_held_pos_uid_used_by(hp_uid, meeting):
                    if cfg not in res:
                        res[cfg] = {'meetings': [], 'overlimit': False}
                    res[cfg]['meetings'].append(meeting)
                    if not limit or len(res[cfg]['meetings']) >= limit:
                        res[cfg]['overlimit'] = True
                        break
        return res

    def using_items(self, limit=50):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        catalog = api.portal.get_tool('portal_catalog')
        hp_uid = self.context.UID()
        res = OrderedDict()
        for cfg in tool.objectValues('MeetingConfig'):
            item_type_name = cfg.getItemTypeName()
            brains = catalog.unrestrictedSearchResults(
                portal_type=item_type_name,
                pm_technical_index=[
                    ITEM_INITIATOR_INDEX_PATTERN.format(hp_uid)],
                sort_on='meeting_date',
                sort_order='reverse')
            for brain in brains:
                if cfg not in res:
                    res[cfg] = {'items': [], 'overlimit': False}
                res[cfg]['items'].append(brain)
                if not limit or len(res[cfg]['items']) >= limit:
                    res[cfg]['overlimit'] = True
                    break
        return res


class PMTitleViewlet(TitleViewlet):

    @property
    @memoize
    def page_title(self):
        '''Include MeetingConfig title when on a faceted context (dashboards).'''
        title = super(PMTitleViewlet, self).page_title
        if IFacetedNavigable.providedBy(self.context) and \
           not IMeeting.providedBy(self.context):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            if cfg:
                title = u"%s - %s" % (escape(safe_unicode(cfg.Title())), title)
        return title
