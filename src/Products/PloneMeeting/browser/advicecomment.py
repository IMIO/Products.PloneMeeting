# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.advices import AdviceAdviceInfoForm
from Products.PloneMeeting.browser.advices import IBaseAdviceInfoSchema
from Products.PloneMeeting.config import PMMessageFactory as _
from z3c.form import button
from zope import schema
from zope.i18n import translate
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


@provider(IContextAwareDefaultFactory)
def proposing_group_comment_default(context):
    """
      Get the adviser_id from the REQUEST and get the comment stored
      in MeetingItem.adviceIndex.
    """
    adviser_id = context.REQUEST.get('advice_id', u'')
    return context.adviceIndex[adviser_id]['proposing_group_comment']


class IAdviceProposingGroupComment(IBaseAdviceInfoSchema):

    proposing_group_comment = schema.Text(
        title=_(u"Comment"),
        description=_(u""),
        defaultFactory=proposing_group_comment_default,
        required=True)


class AdviceProposingGroupCommentForm(AdviceAdviceInfoForm):
    """
    """
    label = _(u"Advice proposing group comment")
    description = u''
    schema = IAdviceProposingGroupComment
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label,
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('save'), name='Save')
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        advice_infos = self._advice_infos(data)
        if not advice_infos.mayEditProposingGroupComment():
            raise Unauthorized

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.RESPONSE.redirect(self.context.absolute_url())

    def update(self):
        """ """
        super(AdviceProposingGroupCommentForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')


AdviceProposingGroupCommentFormWrapper = wrap_form(AdviceProposingGroupCommentForm)
