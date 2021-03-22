# -*- coding: utf-8 -*-

from z3c.form.browser.orderedselect import OrderedSelectWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import IOrderedSelectWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only


class IPMOrderedSelectWidget(IOrderedSelectWidget):
    """Marker interface for PM orderedselect widget"""


@implementer_only(IPMOrderedSelectWidget)
class PMOrderedSelectWidget(OrderedSelectWidget):
    """ """


@implementer(IFieldWidget)
def PMOrderedSelectFieldWidget(field, request):
    return FieldWidget(field, PMOrderedSelectWidget(request))
