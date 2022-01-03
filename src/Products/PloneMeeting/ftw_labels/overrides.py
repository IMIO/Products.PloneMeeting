# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from ftw.labels.browser.labeling import Labeling
from ftw.labels.browser.labelsjar import LabelsJar
from ftw.labels.jar import LabelJar
from ftw.labels.portlets.labeljar import Renderer as ftw_labels_renderer
from ftw.labels.viewlets.labeling import LabelingViewlet
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import is_proposing_group_editor
from Products.PloneMeeting.utils import notifyModifiedAndReindex


class PMFTWLabelsRenderer(ftw_labels_renderer):
    """ """
    @property
    def available(self):
        """ """
        available = super(PMFTWLabelsRenderer, self).available
        return available and \
            self.context.getEnableLabels() and \
            self.request.get('pageName', None) == 'data'


class PMLabelJar(LabelJar):

    def add(self, title, color, by_user):
        """Override to invalidate relevant cache."""
        notifyModifiedAndReindex(self.context)
        return super(PMLabelJar, self).add(title, color, by_user)

    def remove(self, label_id):
        """Protect against removal of used labels."""
        cfg = self.context
        brains = api.content.find(portal_type=cfg.getItemTypeName(), labels=label_id)
        if brains:
            api.portal.show_message(
                _('This label can not be removed as it is used by some items, for example ${item_url}',
                  mapping={'item_url': brains[0].getURL()}),
                type='error',
                request=self.context.REQUEST)
            return self.context.REQUEST.RESPONSE.redirect(self.context.REQUEST['HTTP_REFERER'])
        notifyModifiedAndReindex(self.context)
        return super(PMLabelJar, self).remove(label_id)

    def update(self, label_id, title, color, by_user):
        """ """
        notifyModifiedAndReindex(self.context)
        return super(PMLabelJar, self).update(label_id, title, color, by_user)


class PMLabelsJar(LabelsJar):
    """ """

    def remove(self):
        """Redirect to HTTP_REFERER."""
        super(PMLabelsJar, self).remove()
        return self._redirect()


class PMLabeling(Labeling):
    """ """

    def update(self):
        """ """
        if not self.can_edit:
            raise Unauthorized
        return super(PMLabeling, self).update()

    def pers_update(self):
        """ """
        if not self.can_personal_edit:
            raise Unauthorized
        return super(PMLabeling, self).pers_update()

    @property
    def can_edit(self):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return _checkPermission(ModifyPortalContent, self.context) or \
            tool.isManager(cfg) or \
            (cfg.getItemLabelsEditableByProposingGroupForever() and
             is_proposing_group_editor(self.context.getProposingGroup(), cfg))

    @property
    def can_personal_edit(self):
        return 1


class PMFTWLabelsLabelingViewlet(LabelingViewlet):
    """ """

    def __init__(self, context, request, view, manager=None):
        super(PMFTWLabelsLabelingViewlet, self).__init__(context, request, view, manager=None)
        self.tool = api.portal.get_tool('portal_plonemeeting')

    @property
    def available(self):
        """ """
        available = super(PMFTWLabelsLabelingViewlet, self).available
        if available:
            cfg = self.tool.getMeetingConfig(self.context)
            available = cfg.getEnableLabels()
        return available

    @property
    def can_edit(self):
        return self.context.restrictedTraverse('@@labeling').can_edit

    @property
    def can_personal_edit(self):
        return self.context.restrictedTraverse('@@pers-labeling').can_personal_edit
