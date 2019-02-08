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


class LinkedObjsModified(object):
    """The ``linkedelementsmodified`` etag component, returning the modified
       date of every linked elements including MeetingConfig
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        context = getContext(self.published)
        brefs = context.getBRefs()
        brefs_key = '_'.join(['{0}_{1}'.format(bref.UID(), int(bref.modified())) for bref in brefs])
        # add MeetingConfig modified if any
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        cfg_key = ''
        if cfg:
            cfg_key = '{0}_{1}'.format(cfg.UID(), int(cfg.modified()))
        return brefs_key + cfg_key
