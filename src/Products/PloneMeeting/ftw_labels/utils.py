# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from collective.behavior.talcondition.utils import _evaluateExpression
from collective.iconifiedcategory.interfaces import IIconifiedInfos
from ftw.labels.interfaces import ILabeling
from imio.helpers.cache import get_plone_groups_for_user
from plone.restapi.deserializer import boolean_value
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from zope.component import getAdapter


def get_labels(obj, include_personal_labels=True):
    """Return active labels for p_obj.
       p_include_personal_labels may be:
       - True: returns every labels, personal or not;
       - False: personal labels not returned;
       - "only": only personal labels returned."""
    res = {}
    labeling = ILabeling(obj)
    labels = labeling.active_labels()
    for label in labels:
        if (include_personal_labels == "only" and not label['by_user']) or \
           (include_personal_labels is False and label['by_user']):
            continue
        res[label['label_id']] = label['title']
    return res


def compute_labels_access(adapter,
                          cfg,
                          item=None,
                          item_state=None,
                          force_compute_tal_expr=False,
                          modes=['view', 'edit']):
    """ """
    data = {}
    extra_expr_ctx = None
    for config in cfg.getLabelsConfig():
        data[config['label_id']] = {}
        # view
        if "view" in modes:
            data[config['label_id']]['view_groups'] = \
                adapter._item_visible_for_groups(config['view_groups'], item=item)
            # view_access will take into account view_states and view_access_on
            # None will mean in correct review state but TAL expr to be computed on the fly
            data[config['label_id']]['view_access'] = None
            if config['view_states'] and item_state and item_state not in config['view_states']:
                # no need to compute "view_access" if not in correct review state
                data[config['label_id']]['view_access'] = False
            elif force_compute_tal_expr or config['view_access_on_cache'] == '1':
                # compute view_access if allowed to cache
                data[config['label_id']]['view_access'] = True
                if config['view_access_on'].strip():
                    # will be done only on first use
                    if extra_expr_ctx is None:
                        extra_expr_ctx = _base_extra_expr_ctx(
                            item or cfg, {'item': item, })
                    data[config['label_id']]['view_access'] = \
                        _evaluateExpression(
                            item or cfg,
                            expression=config['view_access_on'],
                            extra_expr_ctx=extra_expr_ctx,
                            raise_on_error=True)
        if "edit" in modes:
            # edit
            data[config['label_id']]['edit_groups'] = \
                adapter._item_visible_for_groups(config['edit_groups'], item=item)
            # edit_access will take into account edit_states and edit_access_on
            # None will mean in correct review state but TAL expr to be computed on the fly
            data[config['label_id']]['edit_access'] = None
            if config['edit_states'] and item_state and item_state not in config['edit_states']:
                # no need to compute "edit_access" if not in correct review state
                data[config['label_id']]['edit_access'] = False
            elif force_compute_tal_expr or config['edit_access_on_cache'] == '1':
                # compute edit_access if allowed to cache
                data[config['label_id']]['edit_access'] = True
                if config['edit_access_on'].strip():
                    # will be done only on first use
                    if extra_expr_ctx is None:
                        extra_expr_ctx = _base_extra_expr_ctx(
                            item, {'item': item, })
                    data[config['label_id']]['edit_access'] = \
                        _evaluateExpression(
                            item or cfg,
                            expression=config['edit_access_on'],
                            extra_expr_ctx=extra_expr_ctx,
                            raise_on_error=True)
    return data


def filter_access_global_labels(jar, mode='view'):
    """Filter labels that are viewable or editable by current user."""
    cfg = jar.context
    # first compute global labels access
    if not cfg.isManager(realManagers=True):
        adapter = getAdapter(cfg, IIconifiedInfos)
        user_groups = set(get_plone_groups_for_user())
        # labels access computation is "static" for current user
        # - "view_access" is True or False
        # - "view_groups" are every groups having access
        labels_access = compute_labels_access(
            adapter, cfg, force_compute_tal_expr=True, modes=[mode])
        # add "view_groups_excluding" from config that is not in labels_access
        # turn "0" to False and "1" to True
        for config in cfg.getLabelsConfig():
            labels_access[config['label_id']]['%s_groups_excluding' % mode] = \
                boolean_value(config['%s_groups_excluding' % mode])
    else:
        # Manager can view every labels
        labels_access = {'*': {'%s_access' % mode: True, '%s_groups' % mode: ()}}
    labels = []
    for label in jar.list():
        if label['by_user']:
            labels.append(label)
        else:
            # check if user can view the label
            label_access = labels_access.get(
                label['label_id'], labels_access.get('*'))
            if label_access['%s_access' % mode] is False or (
               label_access['%s_groups' % mode] and (
               (label_access['%s_groups_excluding' % mode] is False and
                not user_groups.intersection(label_access['%s_groups' % mode])) or
               (label_access['%s_groups_excluding' % mode] is True and
                    user_groups.intersection(label_access['%s_groups' % mode])))):
                continue
            labels.append(label)
    return labels
