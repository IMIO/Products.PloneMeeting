# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.actionspanel.utils import findViewableURL
from imio.helpers.content import get_vocab
from imio.helpers.security import fplog
from plone import api
from plone.autoform import directives
from plone.autoform.form import AutoExtensibleForm
from plone.supermodel import model
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import cleanMemoize
from z3c.form import button
from z3c.form import form
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


def advice_uid_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?advice_uid=advice_uid.
    """
    request = getSite().REQUEST
    return request.get('advice_id', u'')


class IAdviceRemoveInheritance(model.Schema):

    directives.mode(advice_uid='hidden')
    advice_uid = schema.TextLine(
        title=_(u"Advice uid"),
        description=_(u""),
        defaultFactory=advice_uid_default,
        required=False)

    inherited_advice_action = schema.Choice(
        title=_(u"Inherited advice action"),
        description=_(u""),
        vocabulary=SimpleVocabulary(
            [SimpleTerm('ask_locally', 'ask_locally', _(u"Remove inherited advice and ask advice locally")),
             SimpleTerm('remove', 'remove', _(u"Remove inherited advice"))]),
        required=True)


class AdviceRemoveInheritanceForm(AutoExtensibleForm, form.EditForm):
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

    def _advice_infos(self, data):
        '''Init @@advices-icons-infos and returns it.'''
        # check if may remove inherited advice
        advice_infos = self.context.restrictedTraverse('@@advices-icons-infos')
        # initialize advice_infos
        advice_data = self.context.getAdviceDataFor(self.context, data['advice_uid'])
        advice_infos(self.context._shownAdviceTypeFor(advice_data))
        advice_infos._initAdviceInfos(data['advice_uid'])
        return advice_infos

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
                optionalAdvisers = list(self.context.getOptionalAdvisers())
                advisers_vocab = get_vocab(
                    self.context,
                    self.context.getField('optionalAdvisers').vocabulary_factory,
                    **{'include_selected': False, 'include_not_selectable_values': False})
                if data['advice_uid'] in advisers_vocab:
                    optionalAdvisers = list(self.context.getOptionalAdvisers())
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
        self.context.updateLocalRoles()
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
