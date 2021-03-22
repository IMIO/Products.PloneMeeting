# -*- coding: utf-8 -*-

from z3c.form.browser.select import SelectWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import ISelectWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only


class IPMSelectReadonlyWidget(ISelectWidget):
    """Marker interface for PM select readonly widget"""


@implementer_only(IPMSelectReadonlyWidget)
class PMSelectReadonlyWidget(SelectWidget):
    """Select readonly widget implementation."""


@implementer(IFieldWidget)
def PMSelectReadonlyFieldWidget(field, request):
    return FieldWidget(field, PMSelectReadonlyWidget(request))
