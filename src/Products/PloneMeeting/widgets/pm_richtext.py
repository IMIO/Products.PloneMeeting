# -*- coding: utf-8 -*-

from plone import api
from plone.app.textfield.widget import IRichTextWidget
from plone.app.textfield.widget import RichTextWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only


class IPMRichTextWidget(IRichTextWidget):
    """Marker interface for PM RichText Widget"""


@implementer_only(IPMRichTextWidget)
class PMRichTextWidget(RichTextWidget):
    """ """

    @property
    def portal_url(self):
        """ """
        return api.portal.get().absolute_url()

    def may_edit(self):
        """ """
        return True

    def need_to_refresh_page(self):
        """ """
        return False


@implementer(IFieldWidget)
def PMRichTextFieldWidget(field, request):
    return FieldWidget(field, PMRichTextWidget(request))
