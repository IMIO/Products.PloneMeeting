# -*- coding: utf-8 -*-

from plone import api
from plone.app.textfield.widget import IRichTextWidget
from plone.app.textfield.widget import RichTextWidget
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from Products.CMFCore.permissions import ModifyPortalContent
from Products.Five import BrowserView
from Products.PloneMeeting.utils import checkMayQuickEdit
from Products.PloneMeeting.utils import get_dx_widget
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import INPUT_MODE
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
        """This field may sometimes be edited using specific write permissions."""
        portal_types = api.portal.get_tool('portal_types')
        fti = portal_types[self.context.portal_type]
        schema = fti.lookupSchema()
        write_permissions = schema.queryTaggedValue(WRITE_PERMISSIONS_KEY, {})
        write_perm = write_permissions.get(self.__name__, ModifyPortalContent)
        return checkMayQuickEdit(self.context, permission=write_perm)

    def need_to_refresh_page(self):
        """ """
        return False

    def js_on_load(self):
        """ """
        return self.need_to_refresh_page() and 'javascript:refreshPageIfNeeded()' or ''

    def js_on_click(self):
        return "tag=$('div#hook_{0}')[0];" \
            "loadContent(tag, load_view='@@richtext-edit?field_name={0}', " \
            "async=true, base_url='{1}', event_name='ckeditor_prepare_ajax_success');".format(
                self.__name__, self.context.absolute_url())


@implementer(IFieldWidget)
def PMRichTextFieldWidget(field, request):
    return FieldWidget(field, PMRichTextWidget(request))


class RichTextEdit(BrowserView):
    """ """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()
        self.context_url = context.absolute_url()

    def js_save(self):
        """ """
        return "CKEDITOR.instances['{0}'].execCommand('ajaxsave', 'saveCmd');".format(
            self.field_name)

    def js_save_and_exit(self):
        """ """
        return "exitCKeditor('{0}', base_url='{1}')".format(
            self.field_name, self.context_url)

    def js_cancel(self):
        """ """
        return "if (confirm(sure_to_cancel_edit)) {{tag=$('div#hook_{0}')[0];" \
            "loadContent(tag, load_view='@@render-single-widget?field_name={0}', " \
            "async=true, base_url='{1}', event_name=null);}}".format(
                self.field_name, self.context_url)

    def __call__(self, field_name):
        """ """
        self.field_name = field_name
        self.widget = get_dx_widget(self.context, field_name, mode=INPUT_MODE)
        return self.index()
