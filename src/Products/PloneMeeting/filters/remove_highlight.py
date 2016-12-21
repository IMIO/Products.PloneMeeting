from zope.interface import implements
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from plone import api
from plone.outputfilters.interfaces import IFilter
from imio.helpers.xhtml import removeCssClasses


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
        return bool(self.cfg.getCssClassesToHide() and self.cfg.getHideCssClassesTo()) and \
            not _checkPermission(ModifyPortalContent, self.context)

    def _hideCssClasses(self, hideCssClassesTo):
        """Hide if current user may not edit current self.context
           and regarding MeetingConfig.hideCssClassesTo."""
        if (('power_observers' in hideCssClassesTo and
             self.tool.isPowerObserverForCfg(self.cfg)) or
                ('restricted_power_observers' in hideCssClassesTo and
                 self.tool.isPowerObserverForCfg(self.cfg, isRestricted=True))):
            return True
        return False

    def __call__(self, data):
        hideCssClassesTo = self.cfg.getHideCssClassesTo()
        if hideCssClassesTo and self._hideCssClasses(hideCssClassesTo):
            return removeCssClasses(data, css_classes=self.cfg.getCssClassesToHide())
        return data
