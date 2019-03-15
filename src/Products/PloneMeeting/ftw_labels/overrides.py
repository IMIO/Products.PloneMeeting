# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from ftw.labels.jar import LabelJar
from ftw.labels.browser.labeling import Labeling
from ftw.labels.portlets.labeljar import Renderer as ftw_labels_renderer
from ftw.labels.viewlets.labeling import LabelingViewlet
from imio.helpers.cache import cleanRamCacheFor
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import PMMessageFactory as _


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


class PMLabelJar(LabelJar):

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
        return super(PMLabelJar, self).remove(label_id)


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
        return _checkPermission(ModifyPortalContent, self.context) or tool.isManager(self.context)

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
    def can_pers_edit(self):
        return self.context.restrictedTraverse('@@pers-labeling').can_pers_edit
