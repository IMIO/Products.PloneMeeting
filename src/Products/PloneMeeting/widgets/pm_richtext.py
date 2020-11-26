# -*- coding: utf-8 -*-

from Products.CMFCore.permissions import ModifyPortalContent
from plone import api
from plone.app.textfield.widget import IRichTextWidget
from plone.app.textfield.widget import RichTextWidget
from Products.PloneMeeting.utils import checkMayQuickEdit
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.interface import implementer
from zope.interface import implementer_only
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY


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
               "loadContent(tag, tag, load_view='@@richtext-edit?field_name={0}', " \
            "async=true, base_url=null, event_name='ckeditor_prepare_ajax_success');".format(self.__name__)


@implementer(IFieldWidget)
def PMRichTextFieldWidget(field, request):
    return FieldWidget(field, PMRichTextWidget(request))
