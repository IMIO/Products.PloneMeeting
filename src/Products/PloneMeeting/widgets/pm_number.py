# -*- coding: utf-8 -*-

from z3c.form.browser.text import TextWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import ITextWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only


class IPMNumberWidget(ITextWidget):
    """Marker interface for PM number widget"""


@implementer_only(IPMNumberWidget)
class PMNumberWidget(TextWidget):
    """Input type number widget implementation."""

    def max(self):
        """ """
        form = self.request['PUBLISHED']
        # depending on fact that form is wrapped, we get it immediately or not
        form = form.form_instance if hasattr(form, "form_instance") else form
        max = form.max(self)
        return max

    def min(self):
        """ """
        form = self.request['PUBLISHED']
        form = form.form_instance if hasattr(form, "form_instance") else form
        min = form.min(self)
        return min


@implementer(IFieldWidget)
def PMNumberFieldWidget(field, request):
    return FieldWidget(field, PMNumberWidget(request))
