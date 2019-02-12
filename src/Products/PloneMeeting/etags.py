# -*- coding: utf-8 -*-
#
# File: etags.py
#
# Copyright (c) 2019 by Imio.be
#
# GNU General Public License (GPL)
#

from plone import api
from plone.app.caching.interfaces import IETagValue
from plone.app.caching.operations.utils import getContext
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface


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
        return '_'.join(tool.get_plone_groups_for_user())


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
        return str(max(int(context.modifie()), context._p_mtime))


class MeetingModified(object):
    """The ``meetingmodified`` etag component, returning the modified
       date of linked meeting for MeetingItem
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        res = ''
        if context.meta_type == 'MeetingItem':
            meeting = context.getMeeting()
            if meeting:
                res = str(int(meeting.modified()))
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
        res = ''
        if cfg:
            res = str(int(cfg.modified()))
        return res
