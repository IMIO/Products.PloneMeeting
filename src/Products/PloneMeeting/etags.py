# -*- coding: utf-8 -*-

from collective.iconifiedcategory.utils import _modified
from collective.messagesviewlet.utils import get_messages_to_show
from DateTime import DateTime
from imio.helpers.cache import get_cachekey_volatile
from plone import api
from plone.app.caching.interfaces import IETagValue
from plone.app.caching.operations.utils import getContext
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface

import zlib


class UserGroups(object):
    """The ``usergroups`` etag component, returning the current user's groups
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        tool = api.portal.get_tool('portal_plonemeeting')
        res = '_'.join(tool.get_plone_groups_for_user())
        # as this list can be very long, we only returns it's crc32
        # indeed, if we return a too long value, it crashes the browser etags...
        # moreover, short etag save bandwidth
        res = zlib.crc32(res)
        return 'ug_' + str(res)


class ContextModified(object):
    """The ``contextmodified`` etag component, returning the most recent
       between modified date or _p_mtime of context
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        return 'cm_' + str(_modified(context, asdatetime=False))


class ParentModified(object):
    """The ``parentmodified`` etag component, returning the most recent
       between modified date or _p_mtime of context's parent
       Usefull to reload advice view if item modified.
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        tool = api.portal.get_tool('portal_plonemeeting')
        res = 'pm_0'
        if context.portal_type in tool.getAdvicePortalTypeIds():
            parent = context.aq_inner.aq_parent
            res = 'pm_' + str(_modified(parent, asdatetime=False))
        return res


class LinkedMeetingModified(object):
    """The ``linkedmeetingmodified`` etag component, returning the modified
       date of linked meeting for MeetingItem
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        res = 'lm_0'
        if context.meta_type == 'MeetingItem':
            meeting = context.getMeeting()
            if meeting:
                res = 'lm_' + str(_modified(meeting, asdatetime=False))
        elif context.portal_type == 'Folder':
            # in case this is a meeting folder
            # we return last Meeting modified when using MeetingConfig.redirectToNextMeeting
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            if cfg and cfg.getRedirectToNextMeeting():
                # this changes when meeting added/removed/date changed
                meeting_date_last_modified = get_cachekey_volatile(
                    'Products.PloneMeeting.Meeting.date')
                res = 'lm_' + str(int(DateTime(meeting_date_last_modified)))
        return res


class ConfigModified(object):
    """The ``configmodified`` etag component, returning the modified
       date of linked MeetingConfig
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = 'cfgm_0'
        if cfg:
            res = 'cfgm_' + str(_modified(cfg, asdatetime=False))
        return res


class ToolModified(object):
    """The ``toolmodified`` etag component, returning the modified
       date of portal_plonemeeting
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        tool = api.portal.get_tool('portal_plonemeeting')
        return 'toolm_' + str(_modified(tool, asdatetime=False))


class MessagesViewlet(object):
    """The ``messagesviewlet`` etag component, returning the modified
       date of every messages from collective.messagesviewlet to display.
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        messages = get_messages_to_show(context)
        return 'msgviewlet_' + '_'.join([str(_modified(msg, asdatetime=False))
                                         for msg in messages])
