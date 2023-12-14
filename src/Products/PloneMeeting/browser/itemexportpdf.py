# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.helpers.content import get_vocab
from plone.directives import form
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from PyPDF2 import PdfReader
from PyPDF2 import PdfFileWriter
from z3c.form import button
from z3c.form import field
from z3c.form import form as z3c_form
from zope import schema
from zope.i18n import translate
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


@provider(IContextAwareDefaultFactory)
def annex_ids_default(context):
    """Select every annexes by default."""
    vocab = get_vocab(
        context,
        u"Products.PloneMeeting.vocabularies.item_export_pdf_contained_annexes_vocabulary")
    return vocab.by_token.keys()


class IDuplicateItem(form.Schema):
    """ """

    pod_template_uids = schema.List(
        title=_(u"Document to generate"),
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
    fields = field.Fields(IDuplicateItem)
    fields["pod_template_uids"].widgetFactory = PMCheckBoxFieldWidget
    fields["annex_ids"].widgetFactory = PMCheckBoxFieldWidget
    fields["annex_decision_ids"].widgetFactory = PMCheckBoxFieldWidget

    ignoreContext = True  # don't use context to get widget data

    label = _(u"Export PDF")
    description = _('Disabled (greyed) annexes are not PDF documents.')
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Export PDF',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Apply'), name='apply_export_pdf')
    def handleApply(self, action):
        self._check_auth()
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._doApply(data)

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

    def _doApply(self, data):
        """ """
        # make sure data is correct
        self._check_data(data)
        self.request.response.setHeader('Content-Type', 'application/pdf')
        self.request.response.setHeader('Content-disposition', 'attachment;filename=file.pdf')
        kept_annexes_ids = data['annex_ids'] + data['annex_decision_ids']
        annex_paths = [annex.file._blob._p_blob_committed for annex in get_annexes(self.context)
                       if annex.getId() in kept_annexes_ids]

        output_writer = PdfFileWriter()
        stamp = PdfFileReader(open(stamp_path, 'rb'))
        content_file = open(self.filepath, 'rb')
        content = PdfFileReader(content_file)
        counter = 0
        for page in content.pages:
            if counter == 0:
                stamp_content = stamp.getPage(0)
                page.mergePage(stamp_content)
            output_writer.addPage(page)
            counter += 1
        output_writer.write(self.output)
        os.remove(stamp_path)


        return "123456"

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def update(self):
        """ """
        self._check_auth()
        super(ItemExportPDFForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def _check_auth(self):
        """Raise Unauthorized if current user may not duplicate the item."""
        if not self.context.show_export_pdf_action():
            raise Unauthorized

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ItemExportPDFForm, self).render()


ItemExportPDFFormWrapper = wrap_form(ItemExportPDFForm)
