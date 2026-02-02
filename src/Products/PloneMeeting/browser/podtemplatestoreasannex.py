# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from plone.autoform.directives import widget
from plone.z3cform.layout import wrap_form
from Products.CMFPlone import PloneMessageFactory as PMF
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.globalrequest import getRequest
from zope.interface import Interface


def template_uid_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?template_uid=uid.
    """
    return getRequest().get('template_uid', u'')


def output_format_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?output_format=output_format.
    """
    return getRequest().get('output_format', u'')


class IPodTemplateStoreAsAnnex(Interface):
    """ """

    template_uid = schema.TextLine(
        title=_(u"Template uid"),
        description=_(u""),
        defaultFactory=template_uid_default,
        required=False)

    output_format = schema.TextLine(
        title=_(u"Output format"),
        description=_(u""),
        defaultFactory=output_format_default,
        required=False)

    widget('add_to_sign_session', RadioFieldWidget)
    add_to_sign_session = schema.Bool(
        title=_(u'title_add_to_sign_session'),
        description=_(
            "This will add stored annexes to a e-signing session."),
        required=False,
        default=True)


class PodTemplateStoreAsAnnexForm(form.Form):
    """ """
    schema = IPodTemplateStoreAsAnnex
    fields = field.Fields(IPodTemplateStoreAsAnnex)

    ignoreContext = True  # don't use context to get widget data

    label = PMF(u"Store pod template as annex")
    description = _('store_pod_template_as_annex_descr')
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @button.buttonAndHandler(_('Apply'), name='apply_store_as_annex')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        return self._do_store_as_annex(data)

    def updateWidgets(self):
        self.fields['template_uid'].mode = HIDDEN_MODE
        self.fields['output_format'].mode = HIDDEN_MODE
        super(PodTemplateStoreAsAnnexForm, self).updateWidgets()

    def _do_store_as_annex(self, data):
        import ipdb; ipdb.set_trace()
        self._finished = True

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def update(self):
        super(PodTemplateStoreAsAnnexForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(PodTemplateStoreAsAnnexForm, self).render()

PodTemplateStoreAsAnnexFormWrapper = wrap_form(PodTemplateStoreAsAnnexForm)
