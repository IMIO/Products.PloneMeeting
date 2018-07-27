# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone import api
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface


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
    _finished = False
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label, domain='PloneMeeting', context=request)

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
        # store every data on self
        for k, v in data.items():
            setattr(self, k, v)
        self.apply_until_item_number = \
            _itemNumber_to_storedItemNumber(
                data.get('apply_until_item_number') or u'0'
                )
        self.meeting = self.context.getMeeting()
        self._doApply()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def mayChangeAttendees(self):
        """ """
        return self.context._mayChangeAttendees()

    def _doApply(self):
        """ """
        raise NotImplementedError('This must be overrided!')

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(BaseAttendeeForm, self).render()


class IByeByeAttendee(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"absent from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class ByeByeAttendeeForm(BaseAttendeeForm):
    """ """

    label = _(u'person_byebye')
    schema = IByeByeAttendee
    fields = field.Fields(IByeByeAttendee)

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        plone_utils = api.portal.get_tool('plone_utils')
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # return a portal_message if trying to byebye an attendee that is
        # a signatory, either defined on the meeting or redefined on the item
        # user will first have to select another signatory on meeting or item
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
                self._finished = True
                return

        # apply itemAbsents
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_absents = self.meeting.itemAbsents.get(item_to_update_uid, [])
            if self.person_uid not in item_absents:
                item_absents.append(self.person_uid)
                self.meeting.itemAbsents[item_to_update_uid] = item_absents
        plone_utils.addPortalMessage(_("Attendee has been set absent."))
        self._finished = True


ByeByeAttendeeFormWrapper = wrap_form(ByeByeAttendeeForm)


class IWelcomeAttendee(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"back into the meeting from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class WelcomeAttendeeForm(BaseAttendeeForm):
    """ """

    label = _(u"person_welcome")
    schema = IWelcomeAttendee
    fields = field.Fields(IWelcomeAttendee)

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        # apply itemAbsents
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_absents = self.meeting.itemAbsents.get(item_to_update_uid, [])
            if self.person_uid in item_absents:
                item_absents.remove(self.person_uid)
                self.meeting.itemAbsents[item_to_update_uid] = item_absents

        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(_("Attendee has been set back present."))
        self._finished = True


WelcomeAttendeeFormWrapper = wrap_form(WelcomeAttendeeForm)


class IRedefinedSignatory(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"signatory from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)

    signature_number = schema.Choice(
        title=_(u"Signature number"),
        description=_(u""),
        required=True,
        values=['1', '2', '3', '4', '5'])


class RedefinedSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'redefine_signatory')
    schema = IRedefinedSignatory
    fields = field.Fields(IRedefinedSignatory)

    def mayChangeAttendees(self):
        """ """
        res = super(RedefinedSignatoryForm, self).mayChangeAttendees()
        if res:
            # check that person_uid :
            # - is not already a signatory;
            # - is present.
            if self.person_uid in self.meeting.getSignatories() or \
               self.person_uid not in self.meeting.getAttendees():
                res = False
        return res

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        plone_utils = api.portal.get_tool('plone_utils')
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # apply signatory
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_signatories = self.meeting.getItemSignatories().get(item_to_update_uid, {})
            if self.person_uid not in item_signatories.values():
                item_signatories[self.signature_number] = self.person_uid
                self.meeting.itemSignatories[item_to_update_uid] = item_signatories
        plone_utils.addPortalMessage(_("Attendee has been set signatory."))
        self._finished = True


RedefinedSignatoryFormWrapper = wrap_form(RedefinedSignatoryForm)


class IRemoveRedefinedSignatory(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be not be "
                      u"considered item signatory from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class RemoveRedefinedSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'remove_redefined_signatory')
    schema = IRemoveRedefinedSignatory
    fields = field.Fields(IRemoveRedefinedSignatory)

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        plone_utils = api.portal.get_tool('plone_utils')
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # apply signatory
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_signatories = self.meeting.getItemSignatories().get(item_to_update_uid, {})
            signature_number = [k for k, v in item_signatories.items() if v == self.person_uid]
            if signature_number:
                del item_signatories[signature_number[0]]
                # if no more redefined item signatories, remove item UID from meeting.itemSignatories
                if item_signatories:
                    self.meeting.itemSignatories[item_to_update_uid] = item_signatories
                else:
                    del self.meeting.itemSignatories[item_to_update_uid]
            plone_utils.addPortalMessage(_("Attendee is no more defined as item signatory."))
        self._finished = True


RemoveRedefinedSignatoryFormWrapper = wrap_form(RemoveRedefinedSignatoryForm)
