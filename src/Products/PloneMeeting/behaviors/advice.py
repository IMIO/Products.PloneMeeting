# -*- coding: utf-8 -*-
#
# File: behaviors.py
#
# GNU General Public License (GPL)
#

from plone.app.textfield import RichText
from plone.autoform.interfaces import IFormFieldProvider
from plone.directives import form
from plone.supermodel import model
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from zope.interface import alsoProvides


class IAdviceAccountingCommitmentBehavior(model.Schema):

    form.order_before(advice_accounting_commitment='advice_reference')
    form.widget('advice_accounting_commitment', PMRichTextFieldWidget)
    advice_accounting_commitment = RichText(
        title=_(u"title_advice_accounting_commitment"),
        required=False,
        allowed_mime_types=(u"text/html", ))


alsoProvides(IAdviceAccountingCommitmentBehavior, IFormFieldProvider)
