# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.helpers.content import get_vocab
from io import BytesIO
from plone.directives import form
from Products.CMFPlone import PloneMessageFactory as PMF
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from PyPDF2 import PdfFileReader
from PyPDF2 import PdfFileWriter
from z3c.form import button
from z3c.form import field
from z3c.form import form as z3c_form
from zope import schema
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


@provider(IContextAwareDefaultFactory)
def annex_ids_default(context):
    """Select every annexes by default."""
    vocab = get_vocab(
        context,
        u"Products.PloneMeeting.vocabularies.item_export_pdf_contained_annexes_vocabulary")
    return vocab.by_token.keys()


class IItemExportPDF(form.Schema):
    """ """

    pod_template_uids = schema.List(
        title=_(u"Documents to generate"),
        description=_(u""),
        required=False,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.generable_pdf_documents_vocabulary"),
    )

    annex_ids = schema.List(
        title=_(u"Annexes to keep"),
        description=_(u""),
        required=False,
        defaultFactory=annex_ids_default,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.item_export_pdf_contained_annexes_vocabulary"),
    )

    annex_decision_ids = schema.List(
        title=_(u"Decision annexes to keep"),
        description=_(u""),
        required=False,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.item_export_pdf_contained_decision_annexes_vocabulary"),
    )


class ItemExportPDFForm(z3c_form.Form):
    """ """
    fields = field.Fields(IItemExportPDF)
    fields["pod_template_uids"].widgetFactory = PMCheckBoxFieldWidget
    fields["annex_ids"].widgetFactory = PMCheckBoxFieldWidget
    fields["annex_decision_ids"].widgetFactory = PMCheckBoxFieldWidget

    ignoreContext = True  # don't use context to get widget data

    label = PMF(u"Export PDF")
    description = _('export_pdf_descr')
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @button.buttonAndHandler(_('Apply'), name='apply_export_pdf')
    def handleApply(self, action):
        self._check_auth()
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self._check_data(data)
        return self._do_export_pdf(data)

    def _check_data(self, data):
        """Make sure annex_ids/annex_decision_ids are correct.
           As some values are disabled in the UI, a user could try
           to surround this, raise Unauthorized in this case."""
        annex_terms = self.widgets['annex_ids'].terms
        annex_term_ids = [term.token for term in annex_terms
                          if not term.disabled]
        for annex_id in data['annex_ids']:
            if annex_id not in annex_term_ids:
                raise Unauthorized
        decision_annex_terms = self.widgets['annex_decision_ids'].terms
        decision_annex_term_ids = [term.token for term in decision_annex_terms
                                   if not term.disabled]
        for decision_annex_id in data['annex_decision_ids']:
            if decision_annex_id not in decision_annex_term_ids:
                raise Unauthorized

    def updateWidgets(self):
        super(ItemExportPDFForm, self).updateWidgets()
        self.widgets['pod_template_uids'].sortable = True
        self.widgets['annex_ids'].sortable = True
        self.widgets['annex_decision_ids'].sortable = True

    def _do_export_pdf(self, data):
        # pod templates
        view = self.context.restrictedTraverse('@@document-generation')
        generated_pod_templates = [view(template_uid=template_uid, output_format='pdf')
                                   for template_uid in data['pod_template_uids']]
        # annexes
        kept_annexes_ids = data['annex_ids'] + data['annex_decision_ids']
        # get annexes in kept_annexes_ids order
        annexes = [self.context.get(annex_id).file.data for annex_id in kept_annexes_ids]
        # create unique PDF file
        output_writer = PdfFileWriter()
        for pdf_content in generated_pod_templates + annexes:
            output_writer.appendPagesFromReader(
                PdfFileReader(BytesIO(pdf_content)))
        pdf_file_content = BytesIO()
        output_writer.write(pdf_file_content)
        self.request.set('pdf_file_content', pdf_file_content)
        return pdf_file_content

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def update(self):
        self._check_auth()
        super(ItemExportPDFForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def _check_auth(self):
        """Raise Unauthorized if current user may not export to PDF."""
        if not self.context.show_export_pdf_action():
            raise Unauthorized

    def render(self):
        if 'pdf_file_content' in self.request:
            filename = "export_pdf_%s" % self.context.getId()
            self.request.response.setHeader('Content-Type', 'application/pdf')
            self.request.response.setHeader('Content-disposition', 'attachment;filename=%s.pdf' % filename)
            pdf_file_content = self.request['pdf_file_content']
            pdf_file_content.seek(0)
            return pdf_file_content.read()

        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ItemExportPDFForm, self).render()
