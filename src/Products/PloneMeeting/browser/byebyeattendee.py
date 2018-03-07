# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from zope import interface, schema
from zope.component.hooks import getSite
from zope.i18n import translate
from z3c.form import field, form, button
from plone.z3cform.layout import wrap_form
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


class IByeByeAttendee(interface.Interface):

    person_uid = schema.TextLine(
        title=_(u"Person uid"),
        description=_(u""),
        defaultFactory=person_uid_default,
        required=False)

    apply_until_item_number = schema.TextLine(
        title=_(u"Mark this person as having left the meeting until item number"),
        description=_(u""),
        required=False,
        constraint=validate_apply_until_item_number,)


class ByeByeAttendeeForm(form.Form):
    """
    """
    label = (u"Bye bye attendee from this item to...")
    description = u''
    _finishedSent = False

    fields = field.Fields(IByeByeAttendee)
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label)

    @button.buttonAndHandler(_('Apply'), name='apply_byebye_attendee')
    def handleApplyByeByeAttendee(self, action):
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
        self._doApplyByeByeAttendee()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def update(self):
        """ """
        # we check mayQuickEdit with bypassWritePermissionCheck=True
        # so MeetingManagers are able to edit these infos on decided items
        # until the linked meeting is closed
        if not self.context.mayQuickEdit('itemAbsents',
                                         bypassWritePermissionCheck=True):
            raise Unauthorized

        super(ByeByeAttendeeForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def render(self):
        if self._finishedSent:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ByeByeAttendeeForm, self).render()

    def _doApplyByeByeAttendee(self):
        """ """
        if not self.context.mayQuickEdit('itemAbsents',
                                         bypassWritePermissionCheck=True):
            raise Unauthorized

        self._finishedSent = True


ByeByeAttendeeFormWrapper = wrap_form(ByeByeAttendeeForm)
