# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidToObject
from imio.helpers.security import fplog
from persistent.mapping import PersistentMapping
from plone import api
from plone.z3cform.fieldsets.utils import move
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import get_attendee_short_title
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import redirect
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.interfaces import NO_VALUE
from zExceptions import BadRequest
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import Interface
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


WRONG_PERSON_UID = "No held_position found with UID \"%s\"!"
WRONG_POSITION_TYPE = "Given position_type \"%s\" does not exist!"


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
        self.meeting = self.context.getMeeting()

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        # hide person_uid field
        self.fields['person_uid'].mode = 'hidden'
        move(self, 'apply_until_item_number', after='*')
        form.Form.updateWidgets(self)

    def _update_description(self):
        """Display concerned person as description."""
        person_uid = person_uid_default()
        if person_uid:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            hp = uuidToObject(person_uid, unrestricted=True)
            if not hp:
                raise BadRequest(WRONG_PERSON_UID % person_uid)
            self.description = get_attendee_short_title(
                hp, cfg, item=self.context, meeting=self.meeting)

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
        if not self.mayChangeAttendees():
            raise Unauthorized

        self.items_to_update = _itemsToUpdate(
            from_item_number=self.context.getItemNumber(relativeTo='meeting'),
            until_item_number=self.apply_until_item_number,
            meeting=self.meeting)

        error = self.mayApplyPrecondition(self.items_to_update)
        if error:
            self._finished = True
            return error

        # a sub form must call
        # error = super(SubAttendeeForm, self)._doApply()
        # if error:
        #     return error
        # then do his job

    def render(self):
        if self._finished:
            # make sure we return nothing, taken into account by ajax query
            return redirect(self.request, self.context.absolute_url())
        return super(BaseAttendeeForm, self).render()

    def _checkMayApplyPrecondition(self, item_to_update):
        """Must return a tuple with error True/False and a msg."""
        error, msg = False, None
        return error, msg

    def mayApplyPrecondition(self, items_to_update):
        """Base method that manage checking if action is authorized.
           A sub form will have to override the _checkMayApplyPrecondition method."""
        error = False
        final_msg = ''
        for item_to_update in items_to_update:
            error, msg = self._checkMayApplyPrecondition(item_to_update)
            if error:
                if item_to_update != self.context:
                    final_msg = translate(
                        "Please check item number ${item_number} at ${item_url}.",
                        mapping={'item_number': item_to_update.getItemNumber(for_display=True),
                                 'item_url': item_to_update.absolute_url()},
                        domain="PloneMeeting", context=self.request)
                    api.portal.show_message(final_msg, type='warning', request=self.request)
                break
        # add a \n before final_msg if any
        if final_msg:
            final_msg = u"\n{0}".format(final_msg)
        return error and (msg + final_msg) or False


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

    def _checkMayApplyPrecondition(self, item_to_update):
        """Check that:
           - is an attendee on the meeting;
           - is not a signatory on the item;
           - is an attendee on the item;
           - is not a voter."""
        error = False
        msg = None
        # attendee not present on meeting
        if self.person_uid not in self.meeting.get_attendees():
            msg = translate(
                "Can not set \"${not_present_type}\" a person that is not present on the meeting!",
                mapping={'not_present_type': _(self.not_present_type)},
                domain="PloneMeeting", context=self.request)
            api.portal.show_message(msg, type='warning', request=self.request)
            error = True
        # item signatory
        elif self.person_uid in item_to_update.get_item_signatories(real=True):
            msg = translate(
                "Can not set \"${not_present_type}\" a person selected as signatory on an item!",
                mapping={'not_present_type': _(self.not_present_type)},
                domain="PloneMeeting", context=self.request)
            api.portal.show_message(msg, type='warning', request=self.request)
            error = True
        # attendee not present on item
        elif self.person_uid not in self.context.get_attendees():
            msg = translate(
                "Can not set \"${not_present_type}\" a person that is not present on the item!",
                mapping={'not_present_type': _(self.not_present_type)},
                domain="PloneMeeting", context=self.request)
            api.portal.show_message(msg, type='warning', request=self.request)
            error = True

        # item voter
        # if not a voter, continue
        if not error and self.context.show_votes():
            voters = item_to_update.get_item_voters()
            if self.person_uid in voters:
                all_item_votes = item_to_update.get_item_votes(
                    ignored_vote_values=[NOT_ENCODED_VOTE_VALUE])
                i = 0
                # used when vote is secret
                len_voters = len(voters)
                for item_vote in all_item_votes:
                    # secret
                    if item_to_update.get_vote_is_secret(self.meeting, vote_number=i):
                        # every voters voted?
                        encoded_votes_count = item_to_update.get_vote_count(
                            self.meeting, vote_value='any_voted', vote_number=i)
                        if len_voters == encoded_votes_count:
                            msg = translate(
                                "Can not set \"${not_present_type}\" "
                                "a person that voted on an item!",
                                domain="PloneMeeting",
                                mapping={
                                    'not_present_type':
                                    translate(
                                        self.not_present_type,
                                        domain="PloneMeeting",
                                        context=self.request)},
                                context=self.request)
                            api.portal.show_message(msg,
                                                    type='warning',
                                                    request=self.request)
                            error = True
                    # public
                    else:
                        if self.person_uid in item_vote['voters']:
                            msg = translate("Can not set \"${not_present_type}\" "
                                            "a person that voted on an item!",
                                            domain="PloneMeeting",
                                            mapping={
                                                'not_present_type':
                                                translate(
                                                    self.not_present_type,
                                                    domain="PloneMeeting",
                                                    context=self.request)},
                                            context=self.request)
                            api.portal.show_message(msg,
                                                    type='warning',
                                                    request=self.request)
                            error = True
        return error, msg

    def _doApply(self):
        """ """
        error = super(ByeByeAttendeeForm, self)._doApply()
        if error:
            return error

        # apply item_absents/item_excused
        meeting_not_present_attr = getattr(
            self.meeting, self.NOT_PRESENT_MAPPING[self.not_present_type])
        for item_to_update in self.items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_not_present = meeting_not_present_attr.get(item_to_update_uid, [])
            if self.person_uid not in item_not_present:
                item_not_present.append(self.person_uid)
                meeting_not_present_attr[item_to_update_uid] = item_not_present
                notifyModifiedAndReindex(item_to_update)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} not_present_type={2} from_item_number={3} until_item_number={4}'.format(
            repr(self.context), self.person_uid, self.not_present_type, first_item_number, last_item_number)
        fplog('byebye_item_attendee', extras=extras)
        api.portal.show_message(
            _("Attendee has been set ${not_present_type}.",
              mapping={'not_present_type': _('{0}'.format(self.not_present_type))}),
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
        error = super(WelcomeAttendeeForm, self)._doApply()
        if error:
            return error

        # check where is person_uid, item_absents/item_excused/item_non_attendees
        meeting_absent_attr = self._get_meeting_absent_attr()
        for item_to_update in self.items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_absents = meeting_absent_attr.get(item_to_update_uid, [])
            if self.person_uid in item_absents:
                item_absents.remove(self.person_uid)
                meeting_absent_attr[item_to_update_uid] = item_absents
                notifyModifiedAndReindex(item_to_update)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
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


def signature_number_default():
    """
      Get the value from the REQUEST as it is passed when editing
      already redefined item signatory.
    """
    request = getSite().REQUEST
    return request.get('signature_number', u'1')


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
        defaultFactory=signature_number_default,
        required=True,
        vocabulary=u"Products.PloneMeeting.vocabularies.numbersvocabulary")


def _set_meeting_item_signatory(meeting, item_uid, signature_number, hp_uid, position_type):
    """Set an item signatory.  If already item signatory, it may be directly
       changed to another signatory number."""
    # check if already redefined, if already redefined, remove it
    item_sigantories = meeting.item_signatories.get(item_uid, {})
    for item_signature_number, item_signatory in item_sigantories.items():
        if item_signatory['hp_uid'] == hp_uid:
            # remove redefined item signatory
            _remove_item_signatory(meeting, item_uid, item_signature_number)

    item_signatories = meeting.item_signatories.get(item_uid, PersistentMapping())
    item_signatories[signature_number] = PersistentMapping(
        {'hp_uid': hp_uid, 'position_type': position_type})
    meeting.item_signatories[item_uid] = item_signatories


class RedefineSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'Define this attendee as signatory for this item')
    schema = IRedefineSignatory
    fields = field.Fields(IRedefineSignatory)

    def _checkMayApplyPrecondition(self, item_to_update):
        """Check that person_uid:
           - is not already a signatory, on meeting or item;
           - is present;
           - position_type exists."""
        error = False
        msg = None
        # these checks are essentially for restapi as Web UI will prevent these actions
        if self.person_uid in self.meeting.get_signatories():
            msg = translate(
                "Can not set \"Signatory\" a person that is already signatory on the meeting!",
                domain="PloneMeeting", context=self.request)
            api.portal.show_message(msg, type='warning', request=self.request)
            error = True
        elif self.person_uid not in self.meeting.get_attendees():
            msg = translate(
                "Can not set \"Signatory\" a person that is not present on the meeting!",
                domain="PloneMeeting", context=self.request)
            api.portal.show_message(msg, type='warning', request=self.request)
            error = True
        elif self.position_type not in get_vocab(self.context, self.schema['position_type'].vocabularyName):
            raise BadRequest(WRONG_POSITION_TYPE % self.position_type)
        return error, msg

    def _doApply(self):
        """ """
        error = super(RedefineSignatoryForm, self)._doApply()
        if error:
            return error

        # apply signatory
        for item_to_update in self.items_to_update:
            item_to_update_uid = item_to_update.UID()
            _set_meeting_item_signatory(
                self.meeting,
                item_to_update_uid,
                self.signature_number,
                self.person_uid,
                self.position_type)
            notifyModifiedAndReindex(item_to_update)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} signature_number={2} from_item_number={3} until_item_number={4}'.format(
            repr(self.context), self.person_uid, self.signature_number, first_item_number, last_item_number)
        fplog('redefine_item_signatory', extras=extras)
        api.portal.show_message(_("Attendee has been set signatory."), request=self.request)
        self._finished = True


# do not wrap_form or it breaks the portal_messages displayed in xhr request
# RedefinedSignatoryFormWrapper = wrap_form(RedefinedSignatoryForm)


class IRemoveRedefinedSignatory(IBaseAttendee):
    """ """


def _remove_item_signatory(meeting, item_uid, signature_number):
    """ """
    del meeting.item_signatories[item_uid][signature_number]
    # if no more redefined item signatories,
    # remove item UID from meeting.item_signatories
    if not meeting.item_signatories[item_uid]:
        del meeting.item_signatories[item_uid]


class RemoveRedefinedSignatoryForm(BaseAttendeeForm):
    """ """

    label = _(u'Remove attendee from signatory defined for this item')
    schema = IRemoveRedefinedSignatory
    fields = field.Fields(IRemoveRedefinedSignatory)

    def _doApply(self):
        """ """
        error = super(RemoveRedefinedSignatoryForm, self)._doApply()
        if error:
            return error

        # apply signatory
        for item_to_update in self.items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_signatories = self.meeting.item_signatories.get(item_to_update_uid, {})
            signature_number = [k for k, v in item_signatories.items()
                                if v['hp_uid'] == self.person_uid]
            if signature_number:
                _remove_item_signatory(self.meeting, item_to_update_uid, signature_number[0])
                notifyModifiedAndReindex(item_to_update)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('remove_redefined_item_signatory', extras=extras)
        api.portal.show_message(
            _("Attendee is no more defined as item signatory."), request=self.request)
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

    def _checkMayApplyPrecondition(self, item_to_update):
        """Condition to apply:
           - new position_type must exist."""
        error = False
        msg = None
        if self.position_type not in get_vocab(self.context, "PMAttendeeRedefinePositionTypes"):
            # could only happen with restapi
            raise BadRequest(WRONG_POSITION_TYPE % self.position_type)
        return error, msg

    def _doApply(self):
        """ """
        error = super(RedefineAttendeePositionForm, self)._doApply()
        if error:
            return error

        # apply redefined position
        for item_to_update in self.items_to_update:
            item_to_update_uid = item_to_update.UID()
            updated = set_meeting_item_attendee_position(
                self.meeting,
                item_to_update_uid,
                self.person_uid,
                self.position_type)
            if updated:
                notifyModifiedAndReindex(item_to_update)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('redefine_item_attendee_position', extras=extras)
        api.portal.show_message(
            _("Attendee position has been redefined."), request=self.request)
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
        error = super(RemoveRedefinedAttendeePositionForm, self)._doApply()
        if error:
            return error

        # apply removal of redefined attendee position
        for item_to_update in self.items_to_update:
            item_to_update_uid = item_to_update.UID()
            item_attendees_positions = self.meeting.item_attendees_positions.get(
                item_to_update_uid, {})
            if self.person_uid in item_attendees_positions:
                del item_attendees_positions[self.person_uid]
            if not item_attendees_positions:
                del self.meeting.item_attendees_positions[item_to_update_uid]
                notifyModifiedAndReindex(item_to_update)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('remove_redefined_item_attendee_position', extras=extras)
        api.portal.show_message(
            _("Redefined attendee position was removed."), request=self.request)
        self._finished = True


class ChangeAttendeeOrderView(BrowserView):
    """ """

    def __call__(self, attendee_uid, position):
        """ """
        if not self.context._mayChangeAttendees():
            raise Unauthorized
        # get attendee and move it to right position
        meeting = self.context.getMeeting()
        all_uids = list(self.context.get_all_attendees(the_objects=False))
        attendee_uid_index = all_uids.index(attendee_uid)
        all_uids.insert(position - 1, all_uids.pop(attendee_uid_index))
        all_uids = tuple(all_uids)
        context_uid = self.context.UID()
        # if finally the order is back to the order of the meeting
        # remove the item UID from item_attendees_order
        if all_uids == meeting.get_all_attendees(the_objects=False):
            meeting.item_attendees_order.pop(context_uid)
        else:
            meeting._set_item_attendees_order(context_uid, all_uids)

        # log
        extras = 'item={0} hp={1} position={2}'.format(
            repr(self.context), attendee_uid, position)
        fplog('change_item_attendees_order', extras=extras)
        # message
        api.portal.show_message(
            _("Attendee position was changed."), request=self.request)
        return True


class ReinitAttendeesOrderView(BrowserView):
    """ """

    def __call__(self):
        """ """
        if not self.context._mayChangeAttendees():
            raise Unauthorized

        meeting = self.context.getMeeting()
        meeting.item_attendees_order.pop(self.context.UID())

        # log
        extras = 'item={0}'.format(repr(self.context))
        fplog('reinit_item_attendees_order', extras=extras)
        # message
        api.portal.show_message(
            _("Attendees order was reinitialized to meeting order for this item."),
            request=self.request)
        return redirect(self.request, self.context.absolute_url())
