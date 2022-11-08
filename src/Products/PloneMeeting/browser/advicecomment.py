# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.security import fplog
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.advices import BaseAdviceInfoForm
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
        required=False)


class AdviceProposingGroupCommentForm(BaseAdviceInfoForm):
    """
    """
    label = _(u"Advice proposing group comment")
    description = _(u"Advice proposing group comment description")
    schema = IAdviceProposingGroupComment
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _init(self, data):
        """ """
        self.item = get_item(self.context)
        self.advice_infos = self._advice_infos(data, self.item)
        self.label = u"{1} - {0}".format(
            translate(self.label, context=self.request),
            translate(
                "Advice of ${advice_name}",
                mapping={'advice_name':
                         self.context.adviceIndex[data['advice_uid']]['name']},
                domain='PloneMeeting',
                context=self.request))

    def _check_auth(self, data):
        """Raise Unauthorized if current user may not view or edit comment."""
        # initialize some values on self
        self._init(data)
        if not self.mayEditProposingGroupComment() or \
           not self.mayViewProposingGroupComment():
            raise Unauthorized

    def mayEditProposingGroupComment(self):
        """ """
        return self.advice_infos.mayEditProposingGroupComment()

    def mayViewProposingGroupComment(self):
        """ """
        return self.advice_infos.mayViewProposingGroupComment()

    @button.buttonAndHandler(_('save'), name='Save')
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        # check that user is not trying to workaround security
        self._check_auth(data)

        # save proposing_group_comment and return, make sure we do not set None
        self.item.adviceIndex[data['advice_uid']]['proposing_group_comment'] = \
            data['proposing_group_comment'] or u""
        # make sure advice cache is invalidated as proposing group comment
        # is displayed on advice view and does not change the advice modified date
        advice = self.item.getAdviceObj(data['advice_uid'])
        # redirect to item or advice view on correct anchor
        self.request.RESPONSE.redirect(
            self.context.absolute_url() + "#adviceAndAnnexes")
        # invalidate advice view cache
        if advice is not None:
            # as we use etags, we will change the _p_mtime because
            # doNotCache(advice, self.request, self.request.RESPONSE)
            # seems to work with FF but not with Chrome...
            # Setting an arbitrary attribute will update _p_mtime
            # description is not used but exists on any DX content
            advice.description = advice.description
        extras = 'item={0} advice_id={1}'.format(
            repr(self.item), data['advice_uid'])
        fplog('edit_proposing_group_comment', extras=extras)

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.RESPONSE.redirect(self.context.absolute_url())

    def update(self):
        """ """
        super(AdviceProposingGroupCommentForm, self).update()
        self._check_auth({"advice_uid": self.widgets['advice_uid'].value})
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')


AdviceProposingGroupCommentFormWrapper = wrap_form(AdviceProposingGroupCommentForm)
