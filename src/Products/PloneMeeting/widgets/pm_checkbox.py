# -*- coding: utf-8 -*-

from plone import api
from z3c.form.browser.checkbox import CheckBoxWidget
from z3c.form.interfaces import ICheckBoxWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only


class IPMCheckBoxWidget(ICheckBoxWidget):
    """Marker interface for PM checkbox widget"""


@implementer_only(IPMCheckBoxWidget)
class PMCheckBoxWidget(CheckBoxWidget):
    """ """

    @property
    def portal_url(self):
        """ """
        return api.portal.get().absolute_url()

    @property
    def items(self):
        """Manage disabled/readonly on some items."""
        items = super(PMCheckBoxWidget, self).items
        terms = self.terms
        for item in items:
            term = terms.getTermByToken(item['value'])
            item['disabled'] = getattr(term, 'disabled', False)
            item['readonly'] = getattr(term, 'readonly', False)
        return items


@implementer(IFieldWidget)
def PMCheckBoxFieldWidget(field, request):
    return FieldWidget(field, PMCheckBoxWidget(request))
