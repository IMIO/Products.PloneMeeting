# -*- coding: utf-8 -*-

from imio.helpers.xhtml import removeCssClasses
from imio.helpers.xhtml import replace_content
from plone import api
from plone.outputfilters.interfaces import IFilter
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.utils import isPowerObserverForCfg
from zope.interface import implements


class CssTransformer(object):
    """Transform that will remove some defined css classes and anonymize some others."""

    implements(IFilter)
    order = 1000

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def is_enabled(self):
        """Hide if enabled when current user may not edit."""
        return self.cfg and \
            self.cfg.getCssTransforms() and \
            not _checkPermission(ModifyPortalContent, self.context)

    def _remove_css_classes(self, data):
        """Remove CSS classes the user is powerobserver for."""
        css_classes = []
        for row in self.cfg.getCssTransforms():
            if row['powerobservers'] and \
               row['action'] == 'remove' and \
               isPowerObserverForCfg(self.cfg, power_observer_types=row['powerobservers']):
                css_classes.append(row['css_class'].strip())
        if css_classes:
            data = removeCssClasses(data, css_classes=css_classes)
        return data

    def _replace_content(self, data):
        """Replace content using defined CSS classes the user is powerobserver for."""
        replacements = []
        for row in self.cfg.getCssTransforms():
            if row['powerobservers'] and \
               row['action'] == 'replace' and \
               isPowerObserverForCfg(self.cfg, power_observer_types=row['powerobservers']):
                replacements.append({'css_class': row['css_class'].strip(),
                                     'new_content': row['replace_new_content'].strip(),
                                     'new_css_class': row['replace_new_css_class'].strip()})
        for replacement in replacements:
            data = replace_content(
                data,
                css_class=replacement['css_class'],
                new_content=replacement['new_content'],
                new_css_class=replacement['new_css_class'])
        return data

    def __call__(self, data):
        data = self._remove_css_classes(data)
        data = self._replace_content(data)
        return data
