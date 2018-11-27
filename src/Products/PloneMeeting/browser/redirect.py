# -*- coding: utf-8 -*-

from Products.Five import BrowserView
from Products.PloneMeeting.interfaces import IRedirect
from zope.component.hooks import getSite
from zope.interface import implements


class RedirectView(BrowserView):
    """
    """
    DEFAULT = """<html><head><base href="{0}" /></head></html>"""

    def __call__(self):
        """ """
        url = self.request.form.get('url', '')
        if 'ajax_load' in self.request.form:
            return self.DEFAULT.format(url)
        else:
            self.request.RESPONSE.redirect(url)


class Redirect(object):
    """
      Redirect to the right place, this is necessary for overlays to work correctly with z3c.form...
    """
    implements(IRedirect)

    def __init__(self, request):
        self.request = request
        self.ajax_load = self.request.form.get('ajax_load', '')

    def redirect(self, url):
        """
          See docstring in interfaces.IRedirect
        """
        portal = getSite()
        result = []
        result.append(portal.absolute_url())
        result.append("/@@redirect_view?")
        if self.ajax_load:
            result.append("ajax_load=%s&" % self.ajax_load)
        result.append("url=%s" % url)
        self.request.RESPONSE.redirect(''.join(result))
