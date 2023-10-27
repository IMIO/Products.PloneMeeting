# -*- coding: utf-8 -*-

from collective.ckeditor.browser.ckeditorview import Z3CFormWidgetSettings
from plone import api
from plone.app.textfield.widget import IRichTextWidget
from plone.app.textfield.widget import RichTextWidget
from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
from plone.dexterity.events import EditBegunEvent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone.utils import base_hasattr
from Products.Five import BrowserView
from Products.PloneMeeting.utils import checkMayQuickEdit
from Products.PloneMeeting.utils import get_dx_widget
from Products.PloneMeeting.utils import mark_empty_tags
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import INPUT_MODE
from z3c.form.widget import FieldWidget
from zope.event import notify
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
        res = False
        # when used in a datagrid field, sometimes we get strange content...
        if 'ajax_load' not in self.request.form and not isinstance(self.context, dict):
            portal_types = api.portal.get_tool('portal_types')
            fti = portal_types[self.context.portal_type]
            schema = fti.lookupSchema()
            write_permissions = schema.queryTaggedValue(WRITE_PERMISSIONS_KEY, {})
            write_perm = write_permissions.get(self.__name__, ModifyPortalContent)
            if checkMayQuickEdit(self.context, permission=write_perm):
                # check that context is not locked
                res = not self.context.restrictedTraverse(
                    '@@plone_lock_info').is_locked_for_current_user()
        return res

    def need_to_refresh_page(self):
        """ """
        return False

    def js_on_load(self):
        """ """
        return self.need_to_refresh_page() and 'javascript:refreshPageIfNeeded()' or ''

    def js_on_click(self):
        return "if (reloadIfLocked()) {{tag=$('div#hook_{0}')[0];" \
            "loadContent(tag, load_view='@@richtext-edit?field_name={1}', " \
            "async=true, base_url='{2}', event_name='ckeditor_prepare_ajax_success');}}".format(
                self.__name__.replace('.', '\\\.'),
                self.__name__,
                self.context.absolute_url())

    def display_value(self, value):
        """ """
        value = mark_empty_tags(self.context, value)
        return value


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
        return "saveCKeditor('{0}', base_url='{1}')".format(
            self.field_name, self.context_url)

    def js_save_and_exit(self):
        """ """
        return "saveAndExitCKeditor('{0}', base_url='{1}')".format(
            self.field_name, self.context_url)

    def js_cancel(self):
        """ """
        return "cancelCKeditor('{0}', base_url='{1}')".format(
            self.field_name, self.context_url)

    def __call__(self, field_name):
        """ """
        # notify that edit begun, will especially lock content
        notify(EditBegunEvent(self.context))
        self.field_name = field_name
        self.widget = get_dx_widget(self.context, field_name, mode=INPUT_MODE)
        return self.index()


class PMZ3CFormWidgetSettings(Z3CFormWidgetSettings):

    def setupAjaxSave(self, widget_settings):
        """Override to remove the restrictedTraverse to check if save_url available."""
        portal = self.ckview.portal
        # when used in a datagridfield, the target is sometimes a dict...
        if not base_hasattr(self.ckview.context, "portal_type"):
            return
        target = self.getSaveTarget()
        widget_settings['ajaxsave_enabled'] = 'true'
        save_url = str(portal.portal_url.getRelativeUrl(target) + '/cke-save')
        widget_settings['ajaxsave_url'] = save_url
        widget_settings['ajaxsave_fieldname'] = self.getFieldName()
