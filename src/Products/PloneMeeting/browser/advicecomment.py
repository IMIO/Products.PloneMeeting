# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone.app.caching.operations.utils import doNotCache
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.advices import AdviceAdviceInfoForm
from Products.PloneMeeting.browser.advices import IBaseAdviceInfoSchema
from Products.PloneMeeting.config import PMMessageFactory as _
from z3c.form import button
from zope import schema
from zope.i18n import translate
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


def get_item(context):
    """Context may be an item or an advice."""
    if context.__class__.__name__ == "MeetingItem":
        return context
    else:
        return context.aq_parent


@provider(IContextAwareDefaultFactory)
def proposing_group_comment_default(context):
    """
      Get the adviser_id from the REQUEST and get the comment stored
      in MeetingItem.adviceIndex.
    """
    adviser_id = context.REQUEST.get('advice_id', u'')
    item = get_item(context)
    return item.adviceIndex[adviser_id]['proposing_group_comment']


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
    description = _(u"Advice proposing group comment description")
    schema = IAdviceProposingGroupComment
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label,
                               domain='PloneMeeting',
                               context=self.request)

    def _init(self, data):
        """ """
        self.item = get_item(self.context)
        self.advice_infos = self._advice_infos(data, self.item)

    def mayEditProposingGroupComment(self):
        """ """
        return 'ajax_load' not in self.request and \
            self.advice_infos.mayEditProposingGroupComment()

    def mayViewProposingGroupComment(self):
        """ """
        return self.advice_infos.mayViewProposingGroupComment()

    @button.buttonAndHandler(_('save'), name='Save')
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        # initialize some values on self
        self._init(data)

        if not self.mayEditProposingGroupComment():
            raise Unauthorized

        # save proposing_group_comment and return
        self.item.adviceIndex[data['advice_uid']]['proposing_group_comment'] = \
            data['proposing_group_comment']
        # make sure advice cache is invalidated as proposing group comment
        # is displayed on advice view and does not change the advice modified date
        advice = self.item.getAdviceObj(data['advice_uid'])
        if advice is not None:
            doNotCache(advice, self.request, self.request.RESPONSE)
        # redirect to item or advice view on correct anchor
        self.request.RESPONSE.redirect(
            self.context.absolute_url() + "#adviceAndAnnexes")

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.RESPONSE.redirect(self.context.absolute_url())

    def update(self):
        """ """
        super(AdviceProposingGroupCommentForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')


AdviceProposingGroupCommentFormWrapper = wrap_form(AdviceProposingGroupCommentForm)
