# -*- coding: utf-8 -*-

from Products.PloneMeeting.utils import display_as_html
from z3c.form.browser.textarea import TextAreaWidget
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import ITextAreaWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only


class IPMTextAreaWidget(ITextAreaWidget):
    """Marker interface for PM textarea widget"""


def get_textarea_value(value, obj, for_display=True, striked=True, mark_empty_tags=False, raw=True):
    """ """
    res = u''
    if value is not None:
        if raw:
            res = value.raw
        else:
            res = value.output
    if res and for_display:
        res = render_textarea(res, obj, striked=striked, mark_empty_tags=mark_empty_tags)
    return res


def render_textarea(value, obj, striked=True, mark_empty_tags=True):
    """ """
    # turn to HTML, turn [[]] values to <strike></strike> and mark empty ending paragraphs
    value = display_as_html(value, obj, mark_empty_tags=mark_empty_tags, striked=striked)
    return value


@implementer_only(IPMTextAreaWidget)
class PMTextAreaWidget(TextAreaWidget):
    """ """

    def render(self):
        """Patch the value before displaying :
           - turn [[]] into <striked>;
           - mark empty ending paragraphs."""
        value = self.value
        if self.mode == DISPLAY_MODE and value is not None:
            self.value = render_textarea(value, self.context)
        return super(PMTextAreaWidget, self).render()


@implementer(IFieldWidget)
def PMTextAreaFieldWidget(field, request):
    return FieldWidget(field, PMTextAreaWidget(request))
