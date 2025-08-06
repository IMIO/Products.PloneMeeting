# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2018 by Imio.be
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.behavior.talcondition.utils import _evaluateExpression
from ftw.labels.browser.labeling import Labeling
from ftw.labels.browser.labelsjar import LabelsJar
from ftw.labels.interfaces import ILabeling
from ftw.labels.interfaces import ILabelSupport
from ftw.labels.jar import LabelJar
from ftw.labels.labeling import ANNOTATION_KEY as FTW_LABELS_ANNOTATION_KEY
from ftw.labels.portlets.labeljar import Renderer as FTWLabelsRenderer
from ftw.labels.viewlets.labeling import LabelingViewlet
from imio.helpers.cache import get_plone_groups_for_user
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import ITEM_LABELS_ACCESS_CACHE_ATTR
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from zope.annotation import IAnnotations


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
            return self.context.REQUEST.RESPONSE.redirect(
                self.context.REQUEST['HTTP_REFERER'])
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
    def __init__(self, context, request):
        super(PMLabeling, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def filter_manageable_labels(self, labels, modes=("view", "edit", )):
        """Give p_labels is like [[], []]."""
        # do not filter for Managers
        if not self.tool.isManager(realManagers=True):
            # filter depending on self._labels_cache
            cache = getattr(self.context, ITEM_LABELS_ACCESS_CACHE_ATTR)
            personal_labels = []
            global_labels = []
            user_groups = set(get_plone_groups_for_user())
            default_view_config_already_checked = default_edit_config_already_checked = False
            extra_expr_ctx = None
            for label in labels[0]+labels[1]:
                # by_user labels are always editable
                if not label['by_user']:
                    # manage _labels_cache, if not in cache, use the config for
                    # 'default_for_all_labels'
                    cached = cache.get(label['label_id'])
                    is_using_default_config = False
                    if cached is None:
                        is_using_default_config = True
                        cached = cache["*"]
                    config = self.cfg.getLabelsConfig(["*"]) if \
                        is_using_default_config else \
                        self.cfg.getLabelsConfig([label['label_id']])
                    # view
                    if "view" in modes and \
                       label['active'] and \
                       (not is_using_default_config or
                            default_view_config_already_checked is False):
                        if cached['view_groups'] and \
                           not user_groups.intersection(cached['view_groups']):
                            continue
                        # manage view_access, already computed, "False" or "True"
                        # "None" means needs to be computed on the fly
                        if cached['view_access'] is False:
                            continue
                        elif config['view_access_on_cache'] == '0' and \
                                config['view_access_on'].strip():
                            # will be done only on first use
                            if extra_expr_ctx is None:
                                extra_expr_ctx = _base_extra_expr_ctx(
                                    self.context, {'item': self.context, })
                            if not _evaluateExpression(
                                    self.context,
                                    expression=config['view_access_on'],
                                    extra_expr_ctx=extra_expr_ctx,
                                    raise_on_error=True):
                                continue
                        # mark view default config as working
                        if is_using_default_config:
                            default_view_config_already_checked = True
                    # edit
                    elif "edit" in modes and \
                         not label['active'] and \
                         (not is_using_default_config or
                          default_edit_config_already_checked is False):
                        if cached['edit_groups'] and \
                           not user_groups.intersection(cached['edit_groups']):
                            continue
                        # manage edit_access_on, already computed, "False" or "True"
                        # "None" means needs to be computed on the fly
                        if cached['edit_access'] is False:
                            continue
                        elif config['edit_access_on_cache'] == '0' and \
                                config['edit_access_on'].strip():
                            # will be done only on first use
                            if extra_expr_ctx is None:
                                extra_expr_ctx = _base_extra_expr_ctx(
                                    self.context, {'item': self.context, })
                            if not _evaluateExpression(
                                    self.context,
                                    expression=config['edit_access_on'],
                                    extra_expr_ctx=extra_expr_ctx,
                                    raise_on_error=True):
                                continue
                        # mark edit default config as working
                        if is_using_default_config:
                            default_edit_config_already_checked = True
                    # if we are here, label may be kept, otherwise we would have
                    # encountered a "continue" here above
                    global_labels.append(label)
                else:
                    personal_labels.append(label)
            labels = [personal_labels, global_labels]
        return labels

    def available_labels(self, modes=('view', 'edit')):
        # cache in request
        cache_key = "fwt_labeling_cache_{0}-{1}".format(self.context.UID(), "_".join(modes))
        if cache_key not in self.request:
            self.request.set(
                cache_key,
                self.filter_manageable_labels(
                    ILabeling(self.context).available_labels(), modes=modes))
        return self.request.get(cache_key)

    def update(self):
        """ """
        if not self.can_edit:
            raise Unauthorized
        # avoid labels not manageable to be removed
        # add it back to activate_labels in the request
        activate_labels = self.request.form.get('activate_labels', [])
        active_labels = ILabeling(self.context).active_labels()
        if active_labels:
            for active_label in active_labels:
                # this will make check for edit
                active_label['active'] = False
            # need a full label to filter it, returns pers and global labels
            editable_labels = self.filter_manageable_labels(
                [[], active_labels], modes=('edit, '))[1]
            active_label_ids = [label['label_id'] for label in active_labels
                                if not label['by_user']]
            editable_label_ids = [label['label_id'] for label in editable_labels]
            not_mangeable_label_ids = set(active_label_ids).difference(
                editable_label_ids + activate_labels)
            if not_mangeable_label_ids:
                not_editable_label_titles = [
                    label['title'] for label in active_labels
                    if label['label_id'] in not_mangeable_label_ids]
                api.portal.show_message(
                    _("You can not manage labels \"${not_manageable_label_titles}\"!",
                      mapping={'not_manageable_label_titles': safe_unicode(
                        ', '.join(not_editable_label_titles))}),
                    type='warning',
                    request=self.request)
            activate_labels += list(not_mangeable_label_ids)
            self.request.form.update({'activate_labels': activate_labels})
        # check if need to update_local_roles, a relevant label has been (un)selected
        # check if one added or removed
        stored_label_ids = IAnnotations(self.context).get(FTW_LABELS_ANNOTATION_KEY, {}).keys()
        added_or_removed = tuple(set(activate_labels).symmetric_difference(stored_label_ids))
        # this will add/remove relevant labels before eventual update_local_roles
        res = super(PMLabeling, self).update()
        # first element of config is related to "*",
        config = self.cfg.getLabelsConfig(('*', ) + added_or_removed, data="update_local_roles")
        # we have:
        # a config other than the default specifying to update local roles
        # or we do not have "0" for every selected elements and
        # default config specify to update local roles
        if ("1" in config[1:]) or \
           (len(config)-1 != len(added_or_removed) and config[0] == "1"):
            self.context.update_local_roles(avoid_reindex=True)
        return res

    def pers_update(self):
        """ """
        if not self.can_personal_edit:
            raise Unauthorized
        return super(PMLabeling, self).pers_update()

    @property
    def can_edit(self):
        return self.available_labels()

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
        return self.context.restrictedTraverse('@@labeling').available_labels()

    @property
    def can_edit(self):
        return self.context.restrictedTraverse('@@labeling').can_edit

    @property
    def can_personal_edit(self):
        return self.context.restrictedTraverse('@@pers-labeling').can_personal_edit
