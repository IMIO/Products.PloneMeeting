# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import uuidToObject
from imio.helpers.security import fplog
from persistent.mapping import PersistentMapping
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import redirect
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.interfaces import NO_VALUE
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


def person_uid_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?current_delay_row_id=new_value.
    """
    request = getSite().REQUEST
    return request.get('person_uid', u'')


@provider(IContextAwareDefaultFactory)
def apply_until_item_number_default(context):
    """
      Default value is the current item number.
    """
    return safe_unicode(context.getItemNumber(for_display=True))


class IBaseAttendee(Interface):

    person_uid = schema.TextLine(
        title=_(u"Person uid"),
        description=_(u""),
        defaultFactory=person_uid_default,
        required=False)

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"Specify a number to which this will be applied. "
                      u"Field default is current item number."),
        required=False,
        defaultFactory=apply_until_item_number_default,
        constraint=validate_apply_until_item_number,)


class BaseAttendeeForm(form.Form):
    """Factorize common code used by attendees management forms."""

    description = u''
    _finished = False
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label, domain='PloneMeeting', context=request)
        self.request.set('disable_border', 1)

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        # hide person_uid field
        self.fields['person_uid'].mode = 'hidden'
        form.Form.updateWidgets(self)

    def _update_description(self):
        """Display concerned person as description."""
        person_uid = person_uid_default()
        if person_uid:
            hp = uuidToObject(person_uid, unrestricted=True)
            self.description = self.context.get_attendee_short_title(hp)

    def update(self):
        """ """
        super(BaseAttendeeForm, self).update()
        self._update_description()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')
        self.buttons = self.buttons.select('apply', 'cancel')

    def extractData(self, setErrors=True):
        """ """
        # when using datagridfield in an overlay, it adds empty rows...
        # removes it
        for wid in self.widgets.values():
            # datagridfield
            if hasattr(wid, 'allow_insert'):
                wid.widgets = [sub_wid for sub_wid in wid.widgets
                               if sub_wid._value != NO_VALUE]
        data, errors = super(BaseAttendeeForm, self).extractData()
        return data, errors

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
        # in any case, if attendee (un)set absent/excused/... invalidate itemvoters caching
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.vocabularies.itemvotersvocabulary',
            get_again=True)
        # invalidate attendees async load on meeting
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.browser.async.AsyncLoadMeetingAssemblyAndSignatures',
            get_again=True)

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True
        IRedirect(self.request).redirect(self.context.absolute_url())
        return ""

    def mayChangeAttendees(self):
        """ """
        return self.context._mayChangeAttendees()

    def _doApply(self):
        """ """
        raise NotImplementedError('This must be overrided!')

    def render(self):
        if self._finished:
            # make sure we return nothing, taken into account by ajax query
            return redirect(self.request, self.context.absolute_url())
        return super(BaseAttendeeForm, self).render()


class IByeByeAttendee(IBaseAttendee):

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

    NOT_PRESENT_MAPPING = {'absent': 'item_absents',
                           'excused': 'item_excused'}

    def _mayByeByeAttendeePrecondition(self, items_to_update):
        """Are there condition at execution time that
           makes attendee byebyeable?
           This is the case if used in votes, redefined signatory, ..."""
        error = False
        for item_to_update in items_to_update:
            # item signatory
            if self.person_uid in item_to_update.get_item_signatories(real=True):
                api.portal.show_message(
                    _("Can not set ${not_present_type} a person selected as signatory on an item!",
                      mapping={'not_present_type': _('item_not_present_type_{0}'.format(self.not_present_type))}),
                    type='warning',
                    request=self.request)
                error = True
            # already excused
            if self.not_present_type == 'absent' and self.person_uid in item_to_update.get_item_excused():
                api.portal.show_message(
                    _("Can not set excused a person selected as absent on an item!"),
                    type='warning',
                    request=self.request)
                error = True
            # already absent
            if self.not_present_type == 'excused' and self.person_uid in item_to_update.get_item_absents():
                api.portal.show_message(
                    _("Can not set absent a person selected as excused on an item!"),
                    type='warning',
                    request=self.request)
                error = True
            # item voter
            # if not a voter, continue
            if self.context.show_votes():
                voters = item_to_update.get_item_voters()
                if self.person_uid in voters:
                    # secret
                    if item_to_update.get_votes_are_secret():
                        # is there place to remove a voter?
                        len_voters = len(voters)
                        all_item_votes = item_to_update.get_item_votes()
                        i = 0
                        for item_vote in all_item_votes:
                            encoded_votes_count = item_to_update.getVoteCount(
                                vote_value='any_voted', vote_number=i)
                            if len_voters == encoded_votes_count:
                                api.portal.show_message(
                                    _("Can not set ${not_present_type} "
                                      "a person that voted on an item!",
                                      mapping={
                                          'not_present_type':
                                              _('item_not_present_type_{0}'.format(
                                                self.not_present_type))}),
                                    type='warning',
                                    request=self.request)
                                error = True
                    # public
                    else:
                        all_item_votes = item_to_update.get_item_votes(
                            ignored_vote_values=[NOT_ENCODED_VOTE_VALUE])
                        hp_uid_in_voters = bool([item_vote for item_vote in all_item_votes
                                                 if self.person_uid in item_vote['voters']])
                        if hp_uid_in_voters:
                            api.portal.show_message(
                                _("Can not set ${not_present_type} "
                                  "a person that voted on an item!",
                                  mapping={
                                      'not_present_type':
                                          _('item_not_present_type_{0}'.format(
                                            self.not_present_type))}),
                                type='warning',
                                request=self.request)
                            error = True

            if error:
                if item_to_update != self.context:
                    api.portal.show_message(
                        _("Please check item number ${item_number} at ${item_url}.",
                          mapping={'item_number': item_to_update.getItemNumber(for_display=True),
                                   'item_url': item_to_update.absolute_url()}),
                        type='warning',
                        request=self.request)
                break
        return error

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # return a portal_message if trying to byebye an attendee that is
        # a signatory redefined on the item
        # user will first have to select another signatory on meeting or item
        # return a portal_message if trying to set absent and item that is
        # already excused (and the other way round)
        error = self._mayByeByeAttendeePrecondition(items_to_update)
        if error:
            self._finished = True
            return

        # apply item_absents/item_excused
        meeting_not_present_attr = getattr(
            self.meeting, self.NOT_PRESENT_MAPPING[self.not_present_type])
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_not_present = meeting_not_present_attr.get(item_to_update_uid, [])
            if self.person_uid not in item_not_present:
                item_not_present.append(self.person_uid)
                meeting_not_present_attr[item_to_update_uid] = item_not_present
                notifyModifiedAndReindex(item_to_update)
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} not_present_type={2} from_item_number={3} until_item_number={4}'.format(
            repr(self.context), self.person_uid, self.not_present_type, first_item_number, last_item_number)
        fplog('byebye_item_attendee', extras=extras)
        api.portal.show_message(
            _("Attendee has been set ${not_present_type}.",
              mapping={'not_present_type': _('item_not_present_type_{0}'.format(self.not_present_type))}),
            request=self.request)
        self._finished = True


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# ByeByeAttendeeFormWrapper = wrap_form(ByeByeAttendeeForm)


class IWelcomeAttendee(IBaseAttendee):
    """ """


class WelcomeAttendeeForm(BaseAttendeeForm):
    """ """

    label = _(u"person_welcome")
    schema = IWelcomeAttendee
    fields = field.Fields(IWelcomeAttendee)
    attendee_welcome_msg = _("Attendee has been set back present.")

    def _get_meeting_absent_attr(self):
        """ """
        attr = None
        if self.person_uid in self.context.get_item_absents():
            attr = self.meeting.item_absents
        elif self.person_uid in self.context.get_item_excused():
            attr = self.meeting.item_excused
        else:
            attr = self.meeting.item_non_attendees
        return attr

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        # check where is person_uid, item_absents or item_excused
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
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('welcome_item_attendee', extras=extras)
        api.portal.show_message(self.attendee_welcome_msg, request=self.request)
        self._finished = True


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# WelcomeAttendeeFormWrapper = wrap_form(WelcomeAttendeeForm)


class IByeByeNonAttendee(IBaseAttendee):
    """ """


class ByeByeNonAttendeeForm(ByeByeAttendeeForm):
    """ """

    label = _(u'nonattendee_byebye')
    schema = IByeByeNonAttendee
    fields = field.Fields(IByeByeNonAttendee)
    NOT_PRESENT_MAPPING = {'non_attendee': 'item_non_attendees'}
    not_present_type = 'non_attendee'


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# ByeByeNonAttendeeFormWrapper = wrap_form(ByeByeNonAttendeeForm)


class IWelcomeNonAttendee(IBaseAttendee):
    """ """


class WelcomeNonAttendeeForm(WelcomeAttendeeForm):
    """ """

    label = _(u"nonattendee_welcome")
    schema = IWelcomeNonAttendee
    fields = field.Fields(IWelcomeNonAttendee)
    attendee_welcome_msg = _("Attendee has been set back attendee.")

    def _get_meeting_absent_attr(self):
        """ """
        return self.meeting.item_non_attendees


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# WelcomeNonAttendeeFormWrapper = wrap_form(WelcomeNonAttendeeForm)


def position_type_default():
    """ """
    person_uid = person_uid_default()
    hp = uuidToObject(person_uid, unrestricted=True)
    position_type = hp.secondary_position_type or hp.position_type
    return position_type


class IRedefineSignatory(IBaseAttendee):

    position_type = schema.Choice(
        title=_(u"Signature position type"),
        description=_(u"Position type to use as label for the signature."),
        defaultFactory=position_type_default,
        required=True,
        vocabulary="PMPositionTypes")

    signature_number = schema.Choice(
        title=_(u"Signature number"),
        description=_(u""),
        required=True,
        vocabulary=u"Products.PloneMeeting.vocabularies.numbersvocabulary")


def set_meeting_item_signatory(meeting, item_uid, signature_number, hp_uid, position_type):
    """ """
    updated = False
    item_signatories = meeting.item_signatories.get(item_uid, PersistentMapping())
    if hp_uid not in item_signatories.values():
        updated = True
        item_signatories[signature_number] = PersistentMapping(
            {'hp_uid': hp_uid, 'position_type': position_type})
        meeting.item_signatories[item_uid] = item_signatories
    return updated


class RedefineSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'Define this attendee as signatory for this item')
    schema = IRedefineSignatory
    fields = field.Fields(IRedefineSignatory)

    def mayChangeAttendees(self):
        """ """
        res = super(RedefineSignatoryForm, self).mayChangeAttendees()
        if res:
            # check that person_uid :
            # - is not already a signatory;
            # - is present.
            if self.person_uid in self.meeting.get_signatories() or \
               self.person_uid not in self.meeting.get_attendees():
                res = False
        return res

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # apply signatory
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            updated = set_meeting_item_signatory(
                self.meeting,
                item_to_update_uid,
                self.signature_number,
                self.person_uid,
                self.position_type)
            if updated:
                notifyModifiedAndReindex(item_to_update)
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} signature_number={2} from_item_number={3} until_item_number={4}'.format(
            repr(self.context), self.person_uid, self.signature_number, first_item_number, last_item_number)
        fplog('redefine_item_signatory', extras=extras)
        api.portal.show_message(_("Attendee has been set signatory."), request=self.request)
        self._finished = True


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# RedefinedSignatoryFormWrapper = wrap_form(RedefinedSignatoryForm)


class IRemoveRedefinedSignatory(IBaseAttendee):
    """ """


class RemoveRedefinedSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'Remove attendee from signatory defined for this item')
    schema = IRemoveRedefinedSignatory
    fields = field.Fields(IRemoveRedefinedSignatory)

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # apply signatory
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_signatories = self.meeting.item_signatories.get(item_to_update_uid, {})
            signature_number = [k for k, v in item_signatories.items()
                                if v['hp_uid'] == self.person_uid]
            if signature_number:
                del item_signatories[signature_number[0]]
                # if no more redefined item signatories,
                # remove item UID from meeting.item_signatories
                if item_signatories:
                    self.meeting.item_signatories[item_to_update_uid] = item_signatories
                else:
                    del self.meeting.item_signatories[item_to_update_uid]
                notifyModifiedAndReindex(item_to_update)
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('remove_redefined_item_signatory', extras=extras)
        api.portal.show_message(_("Attendee is no more defined as item signatory."), request=self.request)
        self._finished = True


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# RemoveRedefinedSignatoryFormWrapper = wrap_form(RemoveRedefinedSignatoryForm)


class IRedefineAttendeePosition(IBaseAttendee):

    position_type = schema.Choice(
        title=_(u"Position type to use"),
        description=_(u"Position type to use for the attendee on this item."),
        defaultFactory=position_type_default,
        required=True,
        vocabulary="PMAttendeeRedefinePositionTypes")


def set_meeting_item_attendee_position(meeting, item_uid, hp_uid, position_type):
    """ """
    updated = False
    item_attendees_positions = meeting.item_attendees_positions.get(item_uid, PersistentMapping())
    if hp_uid not in item_attendees_positions.values():
        updated = True
        item_attendees_positions[hp_uid] = PersistentMapping(
            {'position_type': position_type})
        meeting.item_attendees_positions[item_uid] = item_attendees_positions
    return updated


class RedefineAttendeePositionForm(BaseAttendeeForm):
    """ """

    label = _(u'Redefine position for this attendee for this item')
    schema = IRedefineAttendeePosition
    fields = field.Fields(IRedefineAttendeePosition)

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # apply redefined position
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            updated = set_meeting_item_attendee_position(
                self.meeting,
                item_to_update_uid,
                self.person_uid,
                self.position_type)
            if updated:
                notifyModifiedAndReindex(item_to_update)
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('redefine_item_attendee_position', extras=extras)
        api.portal.show_message(_("Attendee position has been redefined."), request=self.request)
        self._finished = True


class IRemoveRedefinedAttendeePosition(IBaseAttendee):
    """ """


class RemoveRedefinedAttendeePositionForm(BaseAttendeeForm):
    """ """

    label = _(u'Remove redefined attendee position for this item')
    schema = IRemoveRedefinedAttendeePosition
    fields = field.Fields(IRemoveRedefinedAttendeePosition)

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        # apply removal of redefined attendee position
        for item_to_update in items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_attendees_positions = self.meeting.item_attendees_positions.get(
                item_to_update_uid, {})
            if self.person_uid in item_attendees_positions:
                del item_attendees_positions[self.person_uid]
            if not item_attendees_positions:
                del self.meeting.item_attendees_positions[item_to_update_uid]
                notifyModifiedAndReindex(item_to_update)
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('remove_redefined_item_attendee_position', extras=extras)
        api.portal.show_message(_("Redefined attendee position was removed."),
                                request=self.request)
        self._finished = True
