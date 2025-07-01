# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.helpers.cache import get_plone_groups_for_user
from ftw.labels.browser.labeling import Labeling
from ftw.labels.browser.labelsjar import LabelsJar
from ftw.labels.interfaces import ILabelSupport
from ftw.labels.jar import LabelJar
from ftw.labels.portlets.labeljar import Renderer as FTWLabelsRenderer
from ftw.labels.viewlets.labeling import LabelingViewlet
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import ITEM_LABELS_ACCESS_CACHE_ATTR
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import is_proposing_group_editor
from Products.PloneMeeting.utils import notifyModifiedAndReindex


class PMFTWLabelsRenderer(FTWLabelsRenderer):
    """ """
    @property
    def available(self):
        """ """
        available = super(PMFTWLabelsRenderer, self).available
        return available and \
            'labels' in self.context.getUsedItemAttributes() and \
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
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def available(self):
        """ """
        # for PloneMeeting
        if 'labels' not in self.cfg.getUsedItemAttributes():
            return False

        # override to avoid several calls to self.available_labels
        available_labels = self.available_labels
        if not available_labels:
            return False
        if 'portal_factory' in self.context.absolute_url():
            return False
        if not ILabelSupport.providedBy(self.context):
            return False
        if not available_labels[0] and not available_labels[1]:
            return False
        return True

    @property
    def available_labels(self):
        # local cache as called several times (at least 2 times) by the viewlet
        labels = getattr(self, "_available_labels_cache", None)
        if labels is None:
            labels = super(PMFTWLabelsLabelingViewlet, self).available_labels
            # filter depending on self._labels_cache
            cache = getattr(self.context, ITEM_LABELS_ACCESS_CACHE_ATTR)
            # do not filter for Managers
            if not self.tool.isManager(realManagers=True):
                personal_labels = []
                global_labels = []
                user_groups = set(get_plone_groups_for_user())
                item_state = self.context.query_state()
                default_config_already_checked = False
                for label in labels[0] + labels[1]:
                    # manage _labels_cache, if not in cache, use the config for
                    # 'default_for_all_labels'
                    cached = cache.get(label['label_id'])
                    is_using_default_config = False
                    if cached is None:
                        is_using_default_config = True
                        cached = cache["*"]
                    # when using default config, only filter if it was not already
                    # tested and passed
                    if not is_using_default_config or default_config_already_checked is False:
                        # view
                        if label['active']:
                            if cached['view_groups'] and \
                               not user_groups.intersection(cached['view_groups']):
                                continue
                            view_states = self.cfg.getLabelsConfig(
                                label_id=label['label_id']).get('view_states')
                            if view_states and item_state not in view_states:
                                continue
                            # mark default config as working
                            if is_using_default_config:
                                default_config_already_checked = True
                        # edit
                        else:
                            if cached['edit_groups'] and \
                               not user_groups.intersection(cached['edit_groups']):
                                continue
                            edit_states = self.cfg.getLabelsConfig(
                                label_id=label['label_id']).get('edit_states')
                            if edit_states and item_state not in edit_states:
                                continue
                            # mark default config as working
                            if is_using_default_config:
                                default_config_already_checked = True
                    # OK label may be kept
                    if label['by_user']:
                        personal_labels.append(label)
                    else:
                        global_labels.append(label)
                labels = [personal_labels, global_labels]
            self._available_labels_cache = labels
        return labels

    @property
    def can_edit(self):
        return self.context.restrictedTraverse('@@labeling').can_edit

    @property
    def can_personal_edit(self):
        return self.context.restrictedTraverse('@@pers-labeling').can_personal_edit
