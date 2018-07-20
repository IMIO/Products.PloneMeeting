# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from ftw.labels.portlets.labeljar import Renderer as ftw_labels_renderer
from ftw.labels.viewlets.labeling import LabelingViewlet
from imio.helpers.cache import cleanRamCacheFor
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission


class PMFTWLabelsRenderer(ftw_labels_renderer):
    """ """
    @property
    def available(self):
        """ """
        available = super(PMFTWLabelsRenderer, self).available
        return available and \
            self.context.getEnableLabels() and \
            self.request.get('pageName', None) == 'data'

    @property
    def labels(self):
        """This is overrided to invalidate the
           "Products.PloneMeeting.vocabularies.ftwlabelsvocabulary" vocabulary.
           This is a workaround, each time we see the portlet, it means we are
           in the configuration and maybe we just added/removed/edited a label."""
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.ftwlabelsvocabulary')
        return super(PMFTWLabelsRenderer, self).labels


class PMFTWLabelsLabelingViewlet(LabelingViewlet):
    """ """
    @property
    def available(self):
        """ """
        available = super(PMFTWLabelsLabelingViewlet, self).available
        if available:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            available = cfg.getEnableLabels()
        return available

    @property
    def can_edit(self):
        return _checkPermission(ModifyPortalContent, self.context)
