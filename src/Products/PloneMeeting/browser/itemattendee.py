# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface
from z3c.form import field, form, button
from plone import api
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber


def person_uid_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?current_delay_row_id=new_value.
    """
    request = getSite().REQUEST
    return request.get('person_uid', u'')


class IBaseAttendee(Interface):

    person_uid = schema.TextLine(
        title=_(u"Person uid"),
        description=_(u""),
        defaultFactory=person_uid_default,
        required=False)


class BaseAttendeeForm(form.Form):
    """Factorize common code used by ByeBye attendee and Welcome attendee forms."""

    description = u''
    _finishedSent = False
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label)

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        # hide person_uid field
        self.fields['person_uid'].mode = 'hidden'
        form.Form.updateWidgets(self)

    def update(self):
        """ """
        super(BaseAttendeeForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')
        self.buttons = self.buttons.select('apply', 'cancel')

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do adapt item signatures
        self.person_uid = data.get('person_uid')
        self.apply_until_item_number = \
            _itemNumber_to_storedItemNumber(
                data.get('apply_until_item_number') or u'0'
                )
        self._doApply()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def _doApply(self):
        """ """
        raise NotImplementedError('This must be overrided!')

    def render(self):
        if self._finishedSent:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(BaseAttendeeForm, self).render()


class IByeByeAttendee(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"absent from current item to entered item number.  "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class ByeByeAttendeeForm(BaseAttendeeForm):
    """ """

    label = (u"Manage specific absents for items")
    schema = IByeByeAttendee
    fields = field.Fields(IByeByeAttendee)

    def _doApply(self):
        """ """
        if not self.context._mayChangeAttendees():
            raise Unauthorized

        plone_utils = api.portal.get_tool('plone_utils')
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.context.getMeeting())

        # return a portal_message if trying to byebye an attendee that is
        # specifically selected as itemSignatory on current item
        for item_to_update in items_to_update:
            if self.person_uid in item_to_update.getItemSignatories(real=True):
                plone_utils.addPortalMessage(
                    _("Can not set absent a person selected as signatory on an item!"),
                    type='warning')
                if item_to_update != self.context:
                    plone_utils.addPortalMessage(
                        _("Please check item at ${item_url}.",
                          mapping={'item_url': item_to_update.absolute_url()}),
                        type='warning')
                self._finishedSent = True
                return

        # apply itemAbsents
        for item_to_update in items_to_update:
            item_absents = list(item_to_update.getItemAbsents())
            if self.person_uid not in item_absents:
                item_absents.append(self.person_uid)
                item_to_update.setItemAbsents(item_absents)
        plone_utils.addPortalMessage(_("Attendee has been set absent."))
        self._finishedSent = True


ByeByeAttendeeFormWrapper = wrap_form(ByeByeAttendeeForm)


class IWelcomeAttendee(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"back into the meeting from current item to entered item number.  "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class WelcomeAttendeeForm(BaseAttendeeForm):
    """ """

    label = (u"Welcome attendee from this item to...")
    schema = IWelcomeAttendee
    fields = field.Fields(IWelcomeAttendee)

    def _doApply(self):
        """ """
        if not self.context._mayChangeAttendees():
            raise Unauthorized

        # apply itemAbsents
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.context.getMeeting())
        for item_to_update in items_to_update:
            item_absents = list(item_to_update.getItemAbsents())
            if self.person_uid in item_absents:
                item_absents.remove(self.person_uid)
                item_to_update.setItemAbsents(item_absents)

        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(_("Attendee has been set back present."))
        self._finishedSent = True


ByeByeAttendeeFormWrapper = wrap_form(ByeByeAttendeeForm)
