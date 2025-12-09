# -*- coding: utf-8 -*-
#
# File: adapters.py
#
# GNU General Public License (GPL)
#

from collective.behavior.talcondition.utils import _evaluateExpression
from ftw.labels.interfaces import ILabelJar
from ftw.labels.labeling import ANNOTATION_KEY as FTW_LABELS_ANNOTATION_KEY
from ftw.labels.labeling import Labeling
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.cache import invalidate_cachekey_volatile_for
from plone import api
from plone.app.querystring.queryparser import parseFormquery
from plone.memoize import ram
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import ITEM_LABELS_ACCESS_CACHE_ATTR
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from zope.annotation import IAnnotations


def ftw_labels_jar_discovery(context):
    """Return the root where ftw.labels are defined, here the MeetingConfig."""
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(context)
    return ILabelJar(cfg)


class PMLabeling(Labeling):
    """ """

    def __init__(self, context):
        super(PMLabeling, self).__init__(context)
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
            view_expr_result_cache = {}
            edit_expr_result_cache = {}
            for label in labels[0]+labels[1]:
                # by_user labels are always editable
                if not label['by_user']:
                    # optimization if modes == ('view', ) and label not 'active'
                    # this is the case when displayed in faceted dashboard
                    if modes == ('view',) and not label['active']:
                        continue
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
                    # first check for "view"
                    view_was_checked = False
                    if "view" in modes and \
                       label['active']:
                        if not is_using_default_config or \
                           default_view_config_already_checked is False:
                            # check "view_groups", in or not in depending on "view_groups_excluding"
                            if cached['view_groups'] and \
                               (
                                (config['view_groups_excluding'] == '0' and
                                 not user_groups.intersection(cached['view_groups'])) or
                                (config['view_groups_excluding'] == '1' and
                                 user_groups.intersection(cached['view_groups']))):
                                continue
                            # manage view_access, already computed, "False" or "True"
                            # "None" means needs to be computed on the fly
                            if cached['view_access'] is False:
                                continue
                            view_access_on = config['view_access_on'].strip()
                            if config['view_access_on_cache'] == '0' and view_access_on:
                                # will be done only on first use
                                if extra_expr_ctx is None:
                                    extra_expr_ctx = _base_extra_expr_ctx(
                                        self.context, {'item': self.context, })
                                # cache TAL expr result in case same TAL expr used for several configs
                                if view_access_on in view_expr_result_cache:
                                    if view_expr_result_cache[view_access_on] is False:
                                        continue
                                elif not _evaluateExpression(
                                        self.context,
                                        expression=view_access_on,
                                        extra_expr_ctx=extra_expr_ctx,
                                        raise_on_error=True):
                                    view_expr_result_cache[view_access_on] = False
                                    continue
                                view_expr_result_cache[view_access_on] = True
                            # mark view default config as working
                            if is_using_default_config:
                                default_view_config_already_checked = True
                            # mark "view" as checked, means "view" is in modes
                            # and check passed so we do not need to check "edit"
                            view_was_checked = True
                        else:
                            view_was_checked = True

                    # "edit" not having passed the "view" check
                    if "edit" in modes and not view_was_checked and \
                       (not is_using_default_config or
                            default_edit_config_already_checked is False):
                        # check "edit_groups", in or not in depending on "edit_groups_excluding"
                        if cached['edit_groups'] and \
                           (
                            (config['edit_groups_excluding'] == '0' and
                             not user_groups.intersection(cached['edit_groups'])) or
                            (config['edit_groups_excluding'] == '1' and
                             user_groups.intersection(cached['edit_groups']))):
                            continue
                        # manage edit_access_on, already computed, "False" or "True"
                        # "None" means needs to be computed on the fly
                        if cached['edit_access'] is False:
                            continue
                        edit_access_on = config['edit_access_on'].strip()
                        if config['edit_access_on_cache'] == '0' and edit_access_on:
                            # will be done only on first use
                            if extra_expr_ctx is None:
                                extra_expr_ctx = _base_extra_expr_ctx(
                                    self.context, {'item': self.context, })
                            # cache TAL expr result in case same TAL expr used for several configs
                            if edit_access_on in edit_expr_result_cache:
                                if edit_expr_result_cache[edit_access_on] is False:
                                    continue
                            elif not _evaluateExpression(
                                    self.context,
                                    expression=edit_access_on,
                                    extra_expr_ctx=extra_expr_ctx,
                                    raise_on_error=True):
                                edit_expr_result_cache[edit_access_on] = False
                                continue
                            edit_expr_result_cache[edit_access_on] = True
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

    def get_searches_labels_cachekey(method, self):
        """Cachekey for self.get_searches_labels.
           When a DashboardCollection is added/modified/removed,
           the MeetingConfig modification date is updated."""
        return self.cfg.modified()

    @ram.cache(get_searches_labels_cachekey)
    def get_searches_labels(self):
        """Return list of labels used in searches of current MeetingConfig
           so searches using the "labels" index and for which showNumberOfItems
           is True. This is used to invalidate searches counter cache when
           changing a label but only when relevant."""
        res = []
        for collection in self.cfg.searches.searches_items.objectValues():
            if collection.showNumberOfItems is True and collection.enabled is True:
                parsed_query = parseFormquery(collection, collection.query)
                if "labels" in parsed_query:
                    # most queries use "query", except for "not" queries
                    res += parsed_query['labels'].get(
                        'query', parsed_query['labels'].get('not'))
        return res

    def pers_update(self, label_ids, activate):
        # invalidate collections counter cache and portlet_todo if any
        user_id = get_current_user_id(self.context.REQUEST)
        if set(['%s:%s' % (user_id, label_id) for label_id in label_ids]). \
                intersection(self.get_searches_labels()):
            invalidate_cachekey_volatile_for(
                'Products.PloneMeeting.MeetingItem.modified', get_again=True)
        return super(PMLabeling, self).pers_update(label_ids, activate)

    def update(self, label_ids):
        """Avoid labels not manageable to be removed, add it back to label_ids."""
        active_labels = self.active_labels()
        stored_label_ids = IAnnotations(self.context).get(FTW_LABELS_ANNOTATION_KEY, {}).keys()
        for active_label in active_labels:
            active_label['active'] = True
        # need a full label to filter it, returns pers and global labels
        active_label_ids = [label['label_id'] for label in active_labels
                            if not label['by_user']]
        # build a filter_manageable_labels compliant list of dicts
        new_labels = [
            {'label_id': label_id, 'active': True, 'by_user': False}
            for label_id in label_ids]
        editable_labels = self.filter_manageable_labels(
            [[], active_labels + new_labels], modes=('edit', ))[1]
        editable_label_ids = [label['label_id'] for label in editable_labels]
        # wipeout label_ids if not stored and not editable, this could mean
        # a label manipulated in the UI as this should not be possible
        label_ids = [label_id for label_id in label_ids
                     if label_id in stored_label_ids or label_id in editable_label_ids]
        viewable_labels = self.filter_manageable_labels(
            [[], active_labels], modes=('view', ))[1]
        viewable_label_ids = [label['label_id'] for label in viewable_labels]
        not_manageable_label_ids = set(active_label_ids).difference(
            editable_label_ids + label_ids)
        # ignore not viewable label ids
        viewable_not_manageable_label_ids = [
            not_mangeable_label_id for not_mangeable_label_id in not_manageable_label_ids
            if not_mangeable_label_id in viewable_label_ids]
        if viewable_not_manageable_label_ids:
            not_manageable_label_titles = [
                '"{0}"'.format(label['title']) for label in active_labels
                if label['label_id'] in viewable_not_manageable_label_ids]
            api.portal.show_message(
                _("You can not manage labels ${not_manageable_label_titles}!",
                  mapping={'not_manageable_label_titles': safe_unicode(
                    ', '.join(not_manageable_label_titles))}),
                type='warning',
                request=self.context.REQUEST)
        label_ids += list(not_manageable_label_ids)
        # check if need to update_local_roles, a relevant label has been (un)selected
        # check if one added or removed
        added_or_removed = tuple(set(label_ids).symmetric_difference(stored_label_ids))
        # this will add/remove relevant labels before eventual update_local_roles
        super(PMLabeling, self).update(label_ids)
        # first element of config is related to "*"
        config = self.cfg.getLabelsConfig(('*', ) + added_or_removed, data="update_local_roles")
        # we have:
        # a config other than the default specifying to update local roles
        # or we do not have "0" for every selected elements and
        # default config specify to update local roles
        if ("1" in config[1:]) or \
           (len(config)-1 != len(added_or_removed) and config[0] == "1"):
            self.context.update_local_roles(avoid_reindex=True)
        # invalidate collections counter cache and portlet_todo
        if set(active_label_ids).symmetric_difference(label_ids). \
                intersection(self.get_searches_labels()):
            invalidate_cachekey_volatile_for(
                'Products.PloneMeeting.MeetingItem.modified', get_again=True)
