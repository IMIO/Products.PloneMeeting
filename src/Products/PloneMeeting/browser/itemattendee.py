# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone import api
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import notifyModifiedAndReindex
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

    not_present_type = schema.Choice(
        title=_(u"Not present type"),
        description=_(u""),
        vocabulary=u"Products.PloneMeeting.vocabularies.not_present_type_vocabulary",
        required=True)


class ByeByeAttendeeForm(BaseAttendeeForm):
    """ """

    label = _(u'person_byebye')
    schema = IByeByeAttendee
    fields = field.Fields(IByeByeAttendee)

    NOT_PRESENT_MAPPING = {'absent': 'itemAbsents',
                           'excused': 'itemExcused',
                           'nonAttendee': 'itemNonAttendees'}

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
        # a signatory redefined on the item
        # user will first have to select another signatory on meeting or item
        # return a portal_message if trying to set absent and item that is
        # already excused (and the other way round)
        error = False
        for item_to_update in items_to_update:
            if self.person_uid in item_to_update.getItemSignatories(real=True):
                plone_utils.addPortalMessage(
                    _("Can not set ${not_present_type} a person selected as signatory on an item!",
                      mapping={'not_present_type': _('item_not_present_type_{0}'.format(self.not_present_type))}),
                    type='warning')
                error = True
            if self.not_present_type == 'absent' and self.person_uid in item_to_update.getItemExcused():
                plone_utils.addPortalMessage(
                    _("Can not set excused a person selected as absent on an item!"),
                    type='warning')
                error = True
            if self.not_present_type == 'excused' and self.person_uid in item_to_update.getItemAbsents():
                plone_utils.addPortalMessage(
                    _("Can not set absent a person selected as excused on an item!"),
                    type='warning')
                error = True

            if error:
                if item_to_update != self.context:
                    plone_utils.addPortalMessage(
                        _("Please check item at ${item_url}.",
                          mapping={'item_url': item_to_update.absolute_url()}),
                        type='warning')
                self._finished = True
                return

        # apply itemAbsents/itemExcused
        meeting_not_present_attr = getattr(
            self.meeting, self.NOT_PRESENT_MAPPING[self.not_present_type])
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_not_present = meeting_not_present_attr.get(item_to_update_uid, [])
            if self.person_uid not in item_not_present:
                item_not_present.append(self.person_uid)
                meeting_not_present_attr[item_to_update_uid] = item_not_present
                notifyModifiedAndReindex(item_to_update)
        notifyModifiedAndReindex(self.meeting)
        plone_utils.addPortalMessage(
            _("Attendee has been set ${not_present_type}.",
              mapping={'not_present_type': _('item_not_present_type_{0}'.format(self.not_present_type))}))
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

    def _get_meeting_absent_attr(self):
        """ """
        attr = None
        if self.person_uid in self.context.getItemAbsents():
            attr = self.meeting.itemAbsents
        elif self.person_uid in self.context.getItemExcused():
            attr = self.meeting.itemExcused
        else:
            attr = self.meeting.itemNonAttendees
        return attr

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        # check where is person_uid, itemAbsents or itemExcused
        meeting_absent_attr = self._get_meeting_absent_attr()
        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_absents = meeting_absent_attr.get(item_to_update_uid, [])
            if self.person_uid in item_absents:
                item_absents.remove(self.person_uid)
                meeting_absent_attr[item_to_update_uid] = item_absents
                notifyModifiedAndReindex(item_to_update)
        notifyModifiedAndReindex(self.meeting)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(_("Attendee has been set back present."))
        self._finished = True


WelcomeAttendeeFormWrapper = wrap_form(WelcomeAttendeeForm)


class IByeByeNonAttendee(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"non attendee from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class ByeByeNonAttendeeForm(ByeByeAttendeeForm):
    """ """

    label = _(u'nonattendee_byebye')
    schema = IByeByeNonAttendee
    fields = field.Fields(IByeByeNonAttendee)
    NOT_PRESENT_MAPPING = {'nonAttendee': 'itemNonAttendees'}
    not_present_type = 'nonAttendee'


ByeByeNonAttendeeFormWrapper = wrap_form(ByeByeNonAttendeeForm)


class IWelcomeNonAttendee(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will be defined as "
                      u"attendee for the meeting from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class WelcomeNonAttendeeForm(WelcomeAttendeeForm):
    """ """

    label = _(u"nonattendee_welcome")
    schema = IWelcomeNonAttendee
    fields = field.Fields(IWelcomeNonAttendee)

    def _get_meeting_absent_attr(self):
        """ """
        return self.meeting.itemNonAttendees


WelcomeNonAttendeeFormWrapper = wrap_form(WelcomeNonAttendeeForm)


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

    label = _(u'Define this attendee as signatory for this item')
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
                notifyModifiedAndReindex(item_to_update)
        notifyModifiedAndReindex(self.meeting)
        plone_utils.addPortalMessage(_("Attendee has been set signatory."))
        self._finished = True


RedefinedSignatoryFormWrapper = wrap_form(RedefinedSignatoryForm)


class IRemoveRedefinedSignatory(IBaseAttendee):

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, this attendee will no longer be "
                      u"considered item signatory from current item to entered item number. "
                      u"Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class RemoveRedefinedSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'Remove attendee from signatory defined for this item')
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
                notifyModifiedAndReindex(item_to_update)
        notifyModifiedAndReindex(self.meeting)
        plone_utils.addPortalMessage(_("Attendee is no more defined as item signatory."))
        self._finished = True


RemoveRedefinedSignatoryFormWrapper = wrap_form(RemoveRedefinedSignatoryForm)
