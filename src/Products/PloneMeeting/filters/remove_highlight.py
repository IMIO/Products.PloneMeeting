from imio.helpers.xhtml import removeCssClasses
from plone import api
from plone.outputfilters.interfaces import IFilter
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from zope.interface import implements


class HighlightRemover(object):
    """Transform that will remove 'highlight' related CSS classes,
       depending on MeetingConfig.hideCSSClassesTo."""

    implements(IFilter)
    order = 1000

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def is_enabled(self):
        return bool(self.cfg) and \
            bool(self.cfg.getCssClassesToHide() and self.cfg.getHideCssClassesTo()) and \
            not _checkPermission(ModifyPortalContent, self.context)

    def _hideCssClasses(self, hideCssClassesTo):
        """Hide if current user may not edit current self.context
           and regarding MeetingConfig.hideCssClassesTo."""
        po_infos = self.cfg.getPowerObservers()
        if po_infos and \
           self.tool.isPowerObserverForCfg(self.cfg, power_observer_types=po_infos):
            return True
        return False

    def __call__(self, data):
        hideCssClassesTo = self.cfg.getHideCssClassesTo()
        if hideCssClassesTo and self._hideCssClasses(hideCssClassesTo):
            return removeCssClasses(data, css_classes=self.cfg.getCssClassesToHide())
        return data
