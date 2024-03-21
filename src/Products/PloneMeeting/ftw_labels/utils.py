# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from ftw.labels.interfaces import ILabeling


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
