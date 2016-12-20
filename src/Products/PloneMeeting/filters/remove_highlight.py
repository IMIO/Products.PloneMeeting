from zope.interface import implements
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

    def is_enabled(self):
        return True

    def __call__(self, data):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        hideCssClassesTo = cfg.getHideCssClassesTo()
        if hideCssClassesTo and \
           (('power_observers' in hideCssClassesTo and
             tool.isPowerObserverForCfg(cfg)) or
                ('restricted_power_observers' in hideCssClassesTo and
                 tool.isPowerObserverForCfg(cfg, isRestricted=True))):
            return removeCssClasses(data, css_classes=cfg.getCssClassesToHide())
        return data
