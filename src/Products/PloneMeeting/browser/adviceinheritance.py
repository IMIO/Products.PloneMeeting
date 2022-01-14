# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.actionspanel.utils import findViewableURL
from imio.helpers.content import get_vocab
from imio.helpers.security import fplog
from plone import api
from plone.directives import form
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.advices import BaseAdviceInfoForm
from Products.PloneMeeting.browser.advices import IBaseAdviceInfoSchema
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import cleanMemoize
from z3c.form import button
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.i18n import translate
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class IAdviceRemoveInheritance(IBaseAdviceInfoSchema):

    form.widget('inherited_advice_action', RadioFieldWidget)
    inherited_advice_action = schema.Choice(
        title=_(u"Inherited advice action"),
        description=_(u""),
        vocabulary=SimpleVocabulary(
            [SimpleTerm('ask_locally',
                        'ask_locally',
                        _(u"Remove inherited advice and ask advice locally")),
             SimpleTerm('remove',
                        'remove',
                        _(u"Remove inherited advice"))]),
        default="ask_locally",
        required=True)


class AdviceRemoveInheritanceForm(BaseAdviceInfoForm):
    """
      This form will give the possibility to remove an inherited advice :
      - completely (no more asked and registered);
      - remove inheritance and ask advice again if possible, in this case,
        corresponding optional adviser is selected.
    """
    label = _(u"Remove advice inheritance")
    description = u''
    schema = IAdviceRemoveInheritance
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label,
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('save'), name='save_remove_advice_inheritance')
    def handleSaveRemoveAdviceInheritance(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        advice_infos = self._advice_infos(data)
        if not advice_infos.mayRemoveInheritedAdvice():
            raise Unauthorized

        # if 'ask_localy', check if advice_id may be asked locally, if it is not the case
        # return a portal message but do not remove the inherited advice
        advice_asked_locally = False
        if data['inherited_advice_action'] == 'ask_locally':
            if self.context.showOptionalAdvisers():
                advisers_vocab = get_vocab(
                    self.context,
                    self.context.getField('optionalAdvisers').vocabulary_factory,
                    **{'include_selected': False, 'include_not_selectable_values': False})
                if data['advice_uid'] in advisers_vocab:
                    optionalAdvisers = list(self.context.getOptionalAdvisers(computed=True))
                    if data['advice_uid'] not in optionalAdvisers:
                        optionalAdvisers.append(data['advice_uid'])
                        self.context.setOptionalAdvisers(optionalAdvisers)
                    advice_asked_locally = True
            if not advice_asked_locally:
                api.portal.show_message(
                    message=_('remove_advice_inheritance_ask_locally_not_configured'),
                    request=self.request,
                    type='warning')
                self.request.RESPONSE.redirect(self.context.absolute_url())
                return
        del self.context.adviceIndex[data['advice_uid']]
        self.context.update_local_roles()
        if advice_asked_locally:
            api.portal.show_message(
                message=_('remove_advice_inheritance_removed_and_asked_locally'),
                request=self.request)
        else:
            api.portal.show_message(
                message=_('remove_advice_inheritance_removed'),
                request=self.request)
        # in case an adviser removed inherited advice and may not
        # see the item anymore, we redirect him to a viewable place
        cleanMemoize(self.context, prefixes=['borg.localrole.workspace.checkLocalRolesAllowed'])
        url = findViewableURL(self.context, self.request)
        self.request.RESPONSE.redirect(url)

        # add logging message to fingerpointing log
        extras = 'object={0} advice_uid={1} inherited_advice_action={2}'.format(
            repr(self.context),
            data['advice_uid'],
            data['inherited_advice_action'])
        fplog('remove_advice_inheritance', extras=extras)
        return

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.RESPONSE.redirect(self.context.absolute_url())

    def update(self):
        """ """
        super(AdviceRemoveInheritanceForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')


AdviceRemoveInheritanceFormWrapper = wrap_form(AdviceRemoveInheritanceForm)
