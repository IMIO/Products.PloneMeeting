# -*- coding: utf-8 -*-
#
# File: etags.py
#
# Copyright (c) 2019 by Imio.be
#
# GNU General Public License (GPL)
#

from collective.messagesviewlet.utils import get_messages_to_show
from plone import api
from plone.app.caching.interfaces import IETagValue
from plone.app.caching.operations.utils import getContext
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface


def _modified(obj):
    """Returns max value between obj.modified() and obj._p_mtime,
       in case an annotation is changed on obj, obj._p_mtime is changed,
       not obj.modified()."""
    return str(max(int(obj.modified()), obj._p_mtime))


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
        return 'ug_' + '_'.join(tool.get_plone_groups_for_user())


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
        return 'cm_' + _modified(context)


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
                res = 'lm_' + _modified(meeting)
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
            res = 'cfgm_' + _modified(cfg)
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
        return 'toolm_' + _modified(tool)


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
        return 'msgviewlet_' + '_'.join([_modified(msg) for msg in messages])
