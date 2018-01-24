# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from plone import api
from ftw.labels.portlets.labeljar import Renderer as ftw_labels_renderer
from ftw.labels.viewlets.labeling import LabelingViewlet


class PMFTWLabelsRenderer(ftw_labels_renderer):
    """ """
    @property
    def available(self):
        """ """
        available = super(PMFTWLabelsRenderer, self).available
        return available and \
            self.context.getEnableLabels() and \
            self.request.get('pageName', None) == 'data'


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
