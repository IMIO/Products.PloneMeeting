# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface
from z3c.form import field, form, button
from plone import api
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


class IByeByeAttendee(Interface):

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

    schema = IByeByeAttendee

    fields = field.Fields(IByeByeAttendee)
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

    def _may_byebye_attendee(self):
        """Check that :
           - user may quickEdit itemAbsents;
           - person_uid is actually a present attendee."""
        meeting = self.context.getMeeting()
        if meeting and \
           self.context.mayQuickEdit(
            'itemAbsents', bypassWritePermissionCheck=True) and \
           self.person_uid in meeting.getAttendees():
            return True

    def update(self):
        """ """
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
        if not self._may_byebye_attendee():
            raise Unauthorized

        # apply itemAbsents
        item_absents = list(self.context.getItemAbsents())
        if self.person_uid not in item_absents:
            item_absents.append(self.person_uid)
            self.context.setItemAbsents(item_absents)

        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(_("Attendee has been set absent."))
        self._finishedSent = True


ByeByeAttendeeFormWrapper = wrap_form(ByeByeAttendeeForm)
