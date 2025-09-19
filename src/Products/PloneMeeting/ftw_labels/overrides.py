# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from ftw.labels.browser.labeling import Labeling
from ftw.labels.browser.labelsjar import LabelsJar
from ftw.labels.interfaces import ILabeling
from ftw.labels.interfaces import ILabelSupport
from ftw.labels.jar import LabelJar
from ftw.labels.portlets.labeljar import Renderer as FTWLabelsRenderer
from ftw.labels.viewlets.labeling import LabelingViewlet
from plone import api
from Products.PloneMeeting.config import PMMessageFactory as _
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

    def available_labels(self, modes=('view', 'edit')):
        # cache in request
        cache_key = "ftw-labeling-cache-{0}-{1}".format(self.context.UID(), "-".join(modes))
        cache = IAnnotations(self.request)
        value = cache.get(cache_key, None)
        if value is None:
            labeling = ILabeling(self.context)
            value = labeling.filter_manageable_labels(
                labeling.available_labels(), modes=modes)
            cache[cache_key] = value
        return value

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
        return bool(self.available_labels(modes=('edit', ))[1])

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
