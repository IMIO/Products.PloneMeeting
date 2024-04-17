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


class IItemExportPDF(form.Schema):
    """ """

    elements = schema.List(
        title=_(u"Elements to export in PDF"),
        description=_(u""),
        required=False,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.item_export_pdf_elements_vocabulary"),
    )


class ItemExportPDFForm(z3c_form.Form):
    """ """
    fields = field.Fields(IItemExportPDF)
    fields["elements"].widgetFactory = PMCheckBoxFieldWidget

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

    def updateWidgets(self):
        super(ItemExportPDFForm, self).updateWidgets()
        self.widgets['elements'].sortable = True

    def _check_data(self, data):
        """Make sure elements are selectable.
           As some values are disabled in the UI, a user could try
           to surround this, raise Unauthorized in this case."""
        selectable = [term.token for term in self.widgets['elements'].terms
                      if not getattr(term, 'disabled', False)]
        for elt_id in data['elements']:
            if elt_id not in selectable:
                raise Unauthorized

    def _do_export_pdf(self, data):
        # pod templates
        view = self.context.restrictedTraverse('@@document-generation')
        pod_template_uids = [
            term.token for term in get_vocab(
                self.context,
                'Products.PloneMeeting.vocabularies.'
                'generable_pdf_documents_vocabulary')._terms
            if term.token in data['elements']]
        content = {template_uid: view(template_uid=template_uid, output_format='pdf')
                   for template_uid in pod_template_uids}
        # annexes
        content.update({annex_id: self.context.get(annex_id).file.data
                        for annex_id in data['elements'] if annex_id not in pod_template_uids})
        # create unique PDF file
        output_writer = PdfFileWriter()
        for element_id in data['elements']:
            output_writer.appendPagesFromReader(
                PdfFileReader(BytesIO(content[element_id]), strict=False))
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
