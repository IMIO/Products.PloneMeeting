# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.config import PMMessageFactory as _
from z3c.form import button
from z3c.form import form
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from plone.supermodel import model
from plone.autoform.form import AutoExtensibleForm
from plone.autoform import directives
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from plone import api


def advice_id_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?advice_id=advice_id.
    """
    request = getSite().REQUEST
    return request.get('advice_id', u'')


class IAdviceRemoveInheritance(model.Schema):

    directives.mode(advice_id='hidden')
    advice_id = schema.TextLine(
        title=_(u"Advice id"),
        description=_(u""),
        defaultFactory=advice_id_default,
        required=False)

    inherited_advice_action = schema.Choice(
        title=_(u"Inherited advice action"),
        description=_(u""),
        vocabulary=SimpleVocabulary(
            [SimpleTerm('remove', 'remove', 'Remove inherited advice'),
             SimpleTerm('ask_locally', 'ask_locally', 'Remove inherited advice and ask advice locally')]),
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

    @button.buttonAndHandler(_('save'), name='save_remove_advice_inheritance')
    def handleSaveRemoveAdviceInheritance(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # check if may remove inherited advice
        advice_infos = self.context.restrictedTraverse('@@advices-icons-infos')
        # initialize advice_infos
        advice_data = self.context.getAdviceDataFor(self.context, data['advice_id'])
        advice_infos(advice_data['type'])
        advice_is_inherited = self.context.adviceIsInherited(data['advice_id'])
        if not advice_infos.mayRemoveInheritedAdvice(advice_is_inherited, data['advice_id']):
            raise Unauthorized

        # if 'ask_localy', check if advice_id may be asked locally, in case it is not the case
        # return a portal_message but do not remove the inherited advice
        advice_asked_locally = False
        if data['inherited_advice_action'] == 'ask_locally':
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            if cfg.getUseAdvices():
                optionalAdvisers = list(self.context.getOptionalAdvisers())
                if data['advice_id'] not in optionalAdvisers and \
                   data['advice_id'] in self.context.listOptionalAdvisers().keys():
                    optionalAdvisers.append(data['advice_id'])
                    self.context.setOptionalAdvisers(optionalAdvisers)
                    advice_asked_locally = True
            if not advice_asked_locally:
                api.portal.show_message(
                    message='Your current configuration does not allow you to ask '
                            'this advice locally, the inherited advice was not removed. '
                            'Contact your system administrator if necessary.',
                    request=self.request,
                    type='warning')
                self.request.RESPONSE.redirect(self.context.absolute_url())
                return
        del self.context.adviceIndex[data['advice_id']]
        self.context.updateLocalRoles()
        if advice_asked_locally:
            api.portal.show_message(
                message='Advice inheritance was removed and advice is asked locally',
                request=self.request)
        else:
            api.portal.show_message(
                message='Advice inheritance was removed',
                request=self.request)
        self.request.RESPONSE.redirect(self.context.absolute_url())
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
