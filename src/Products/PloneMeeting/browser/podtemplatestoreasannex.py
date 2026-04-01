# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from collective.eeafaceted.batchactions import _ as _CEBA
from imio.helpers.content import get_vocab_values
from imio.helpers.content import uuidToObject
from plone import api
from plone.formwidget.masterselect import MasterSelectBoolField
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.batchactions import compute_signers
from Products.PloneMeeting.browser.batchactions import DisplaySignersProvider
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.contentprovider import ContentProviders
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from zope import schema
from zope.globalrequest import getRequest
from zope.interface import implements
from zope.interface import Interface
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


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


@provider(IContextAwareDefaultFactory)
def annex_ids_default(context):
    """Select every annexes by default."""
    return get_vocab_values(
        context,
        u"Products.PloneMeeting.vocabularies.contained_annexes_to_sign_vocabulary")


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

    add_to_sign_session = MasterSelectBoolField(
        title=_(u'title_add_to_sign_session'),
        description=_("descr_add_to_sign_session"),
        required=True,
        slave_fields=(
            {'masterID': 'form-widgets-add_to_sign_session-0',
             'slaveID': '#formfield-form-widgets-annex_ids',
             'name': 'annex_ids',
             'action': 'show',
             'hide_values': 1,
             },
        ),
        default=True)

    annex_ids = schema.List(
        title=_(u"title_annex_ids_to_add_to_sign_session"),
        description=_(u"descr_annex_ids_to_add_to_sign_session"),
        required=False,
        defaultFactory=annex_ids_default,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.contained_annexes_to_sign_vocabulary"),
    )

    store_generated_document = schema.Bool(
        title=_(u'title_store_generated_document'),
        description=_("descr_store_generated_document"),
        required=False,
        default=True)


class PodTemplateStoreAsAnnexForm(form.Form):
    """ """
    implements(IFieldsAndContentProvidersForm)
    schema = IPodTemplateStoreAsAnnex
    fields = field.Fields(IPodTemplateStoreAsAnnex)
    fields["annex_ids"].widgetFactory = PMCheckBoxFieldWidget
    ignoreContext = True  # don't use context to get widget data

    contentProviders = ContentProviders()
    contentProviders['signers'] = DisplaySignersProvider
    contentProviders['signers'].position = 2

    label = _CEBA(u"Store POD template as annex")
    description = _('store_pod_template_as_annex_descr')
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

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
        generation_view = self.context.restrictedTraverse('@@document-generation')
        # res is a string (error msg) or an annex
        self.request.set('store_as_annex', '1')
        generation_view(
            template_uid=data['template_uid'],
            output_format=data['output_format'],
            store_generated_document=data['store_generated_document'],
            add_to_sign_session=data['add_to_sign_session'],
            annex_ids_to_add_to_session=data['annex_ids'])
        self.request.set('store_as_annex', '0')
        self._finished = True

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def update(self):
        super(PodTemplateStoreAsAnnexForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')
        self.pod_template = uuidToObject(self.widgets['template_uid'].value)
        self.signers, self.raw_signers, self.signers_error_msg, self.esign_enabled, self.annex_type = \
            compute_signers(self.context, self.pod_template)
        self.output_format = self.widgets['output_format'].value
        self.show_esign = self.esign_enabled and \
            not self.signers_error_msg and \
            self.output_format == u'pdf' and \
            self.annex_type.to_sign
        # hide esign related fields if not available
        if not self.show_esign:
            self.widgets['add_to_sign_session'].mode = HIDDEN_MODE
            self.widgets['add_to_sign_session'].value = ['false']
            self.widgets['annex_ids'].mode = HIDDEN_MODE
            self.widgets['annex_ids'].terms = []
            self.widgets['annex_ids'].value = []
            self.widgets['store_generated_document'].mode = HIDDEN_MODE

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(PodTemplateStoreAsAnnexForm, self).render()


PodTemplateStoreAsAnnexFormWrapper = wrap_form(PodTemplateStoreAsAnnexForm)
