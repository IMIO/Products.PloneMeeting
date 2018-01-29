# -*- coding: utf-8 -*-
#
# File: adapters.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from plone import api
from ftw.labels.interfaces import ILabelJar


def ftw_labels_jar_discovery(context):
    """Return the root where fwt.labels are defined, here the MeetingConfig."""
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(context)
    return ILabelJar(cfg)
