# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from imio.annex.browser.views import ExportPDFForm
from imio.helpers.content import get_vocab
from Products.PloneMeeting.config import POD_TEMPLATE_TOKEN_SEPARATOR
from Products.PloneMeeting.interfaces import IRedirect


class ItemExportPDFForm(ExportPDFForm):
    """Export selected POD templates (generated as PDF), annexes and
       decision annexes of an item into a single PDF file."""

    vocabulary = u"Products.PloneMeeting.vocabularies.item_export_pdf_elements_vocabulary"

    def _may_export(self):
        """ """
        return self.context.show_export_pdf_action()

    def _redirect(self, url):
        """ """
        IRedirect(self.request).redirect(url)

    def _elements_content(self, data):
        """Selected elements are POD templates to generate as PDF or annexes,
           POD template token is "pod_template_uid__output_format"."""
        pod_template_tokens = [
            term.token for term in get_vocab(
                self.context,
                'Products.PloneMeeting.vocabularies.'
                'generable_pdf_documents_vocabulary')._terms
            if term.token in data['elements']]
        # annexes
        content = super(ItemExportPDFForm, self)._elements_content(
            dict(data, elements=[element_id for element_id in data['elements']
                                 if element_id not in pod_template_tokens]))
        # pod templates
        view = self.context.restrictedTraverse('@@document-generation')
        for token in pod_template_tokens:
            template_uid, output_format = token.split(POD_TEMPLATE_TOKEN_SEPARATOR)
            content[token] = view(template_uid=template_uid, output_format=output_format)
        return content
