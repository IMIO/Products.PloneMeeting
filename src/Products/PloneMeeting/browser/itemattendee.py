# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from imio.helpers.cache import invalidate_cachekey_volatile_for
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.autoform.directives import widget
from plone.restapi.deserializer import boolean_value
from plone.z3cform.layout import wrap_form
from Products.Five import BrowserView
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import fplog
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.contentprovider import ContentProviders
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from zope import schema
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component.hooks import getSite
from zope.contentprovider.provider import ContentProviderBase
from zope.i18n import translate
from zope.interface import implements
from zope.interface import Interface
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


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
    """Factorize common code used by attendees management forms."""

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
        # in any case, if attendee (un)set absent/excused/... invalidate itemvoters caching
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.vocabularies.itemvotersvocabulary',
            get_again=True)

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
            self.request.RESPONSE.redirect(self.context.absolute_url())
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
                           'excused': 'itemExcused'}

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
        error = False
        for item_to_update in items_to_update:
            if self.person_uid in item_to_update.getItemSignatories(real=True):
                api.portal.show_message(
                    _("Can not set ${not_present_type} a person selected as signatory on an item!",
                      mapping={'not_present_type': _('item_not_present_type_{0}'.format(self.not_present_type))}),
                    type='warning',
                    request=self.request)
                error = True
            if self.not_present_type == 'absent' and self.person_uid in item_to_update.getItemExcused():
                api.portal.show_message(
                    _("Can not set excused a person selected as absent on an item!"),
                    type='warning',
                    request=self.request)
                error = True
            if self.not_present_type == 'excused' and self.person_uid in item_to_update.getItemAbsents():
                api.portal.show_message(
                    _("Can not set absent a person selected as excused on an item!"),
                    type='warning',
                    request=self.request)
                error = True

            if error:
                if item_to_update != self.context:
                    api.portal.show_message(
                        _("Please check item at ${item_url}.",
                          mapping={'item_url': item_to_update.absolute_url()}),
                        type='warning',
                        request=self.request)
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
    attendee_welcome_msg = _("Attendee has been set back present.")

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
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('welcome_item_attendee', extras=extras)
        api.portal.show_message(self.attendee_welcome_msg, request=self.request)
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
    NOT_PRESENT_MAPPING = {'non_attendee': 'itemNonAttendees'}
    not_present_type = 'non_attendee'


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
    attendee_welcome_msg = _("Attendee has been set back attendee.")

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
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} signature_number={2} from_item_number={3} until_item_number={4}'.format(
            repr(self.context), self.person_uid, self.signature_number, first_item_number, last_item_number)
        fplog('redefine_item_signatory', extras=extras)
        api.portal.show_message(_("Attendee has been set signatory."), request=self.request)
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
        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} hp={1} from_item_number={2} until_item_number={3}'.format(
            repr(self.context), self.person_uid, first_item_number, last_item_number)
        fplog('remove_redefined_item_signatory', extras=extras)
        api.portal.show_message(_("Attendee is no more defined as item signatory."), request=self.request)
        self._finished = True


RemoveRedefinedSignatoryFormWrapper = wrap_form(RemoveRedefinedSignatoryForm)


class DisplaySelectAllProvider(ContentProviderBase):
    """
      This ContentProvider will just display
      the select all controls to ease selecting same vote value for everyone.
    """
    template = \
        ViewPageTemplateFile('templates/display_select_all_vote_value.pt')

    def __init__(self, context, request, view):
        super(DisplaySelectAllProvider, self).__init__(
            context, request, view)
        self.__parent__ = view

    def render(self):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        self.usedVoteValues = cfg.getUsedVoteValues()
        return self.template()


def vote_number_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?vote_number=0.
    """
    request = getSite().REQUEST
    return request.get('vote_number', 0)


@provider(IContextAwareDefaultFactory)
def votes_default(context):
    """Default values for votes :
       - either we have itemVotes and we use it on voters;
       - or we do not have and we use the default value defined on MeetingConfig."""
    res = []
    vote_number = vote_number_default()
    item_votes = context.getItemVotes(vote_number=vote_number,
                                      ignored_vote_values=[NOT_VOTABLE_LINKED_TO_VALUE])
    # keep order using getItemVoters
    item_voter_uids = context.getItemVoters()

    # when adding a new vote linked_to_previous, only keep possible voters
    if item_votes['linked_to_previous']:
        new_vote = not context.getItemVotes(
            vote_number=vote_number, include_unexisting=False)
        if new_vote:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            usedVoteValues = cfg.getUsedVoteValues()
            ignored_vote_values = [v for v in usedVoteValues
                                   if v != NOT_ENCODED_VOTE_VALUE]
            ignored_vote_values.append(NOT_VOTABLE_LINKED_TO_VALUE)
            last_vote = context.getItemVotes(
                vote_number=-1,
                ignored_vote_values=ignored_vote_values)
            item_voter_uids = [item_voter_uid for item_voter_uid in item_voter_uids
                               if item_voter_uid in last_vote['voters']]

    for item_voter_uid in item_voter_uids:
        # voter could not be there because ignored_vote_values
        if item_voter_uid in item_votes['voters']:
            data = {'voter_uid': item_voter_uid,
                    'voter': item_voter_uid,
                    'vote_value': item_votes['voters'][item_voter_uid]}
            res.append(data)
    return res


@provider(IContextAwareDefaultFactory)
def label_default(context):
    """ """
    res = None
    item_votes = context.getItemVotes(vote_number=vote_number_default())
    if item_votes and item_votes['label']:
        res = item_votes['label']
    return res


@provider(IContextAwareDefaultFactory)
def linked_to_previous_default(context):
    """ """
    request = getSite().REQUEST
    res = request.get('linked_to_previous', None)
    if res is None:
        item_votes = context.getItemVotes(vote_number=vote_number_default())
        res = item_votes['linked_to_previous']
    return res


class IVote(Interface):

    voter_uid = schema.Choice(
        title=u'Voter UID',
        required=False,
        vocabulary="Products.PloneMeeting.vocabularies.itemvotersvocabulary", )

    voter = schema.Choice(
        title=u'Voter',
        required=False,
        vocabulary="Products.PloneMeeting.vocabularies.itemvotersvocabulary", )

    widget('vote_value', RadioFieldWidget)
    vote_value = schema.Choice(
        title=u'',   # no title as we use column header for select all vote values
        required=False,
        vocabulary="Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary", )


class IEncodeVotes(IBaseAttendee):

    vote_number = schema.Int(
        title=_(u"Vote number"),
        description=_(u""),
        defaultFactory=vote_number_default,
        required=False)

    label = schema.TextLine(
        title=_(u"Label"),
        description=_(u"Free label that will identify the vote, "
                      u"useful when several votes are defined on an item. "
                      u"Leave empty if not used."),
        defaultFactory=label_default,
        required=False)

    linked_to_previous = schema.Bool(
        title=_(u"Linked to previous"),
        description=_(u"This will link this vote with the previous one, "
                      u"if so, voter may only vote for one of the linked votes."),
        defaultFactory=linked_to_previous_default,
        required=False)

    votes = schema.List(
        title=u'Votes',
        value_type=DictRow(title=u'Votes', schema=IVote),
        defaultFactory=votes_default,
        required=True
    )


class EncodeVotesForm(BaseAttendeeForm):
    """ """
    implements(IFieldsAndContentProvidersForm)
    contentProviders = ContentProviders()
    contentProviders['select_all'] = DisplaySelectAllProvider
    contentProviders['select_all'].position = 4

    label = _(u"Encode votes")
    schema = IEncodeVotes
    fields = field.Fields(IEncodeVotes)
    fields['votes'].widgetFactory = DataGridFieldFactory

    def updateWidgets(self):
        # hide vote_number field
        self.fields['vote_number'].mode = HIDDEN_MODE
        # do not hide it, when hidding it, value is always True???
        # this is hidden using CSS
        # self.fields['linked_to_previous'].mode = HIDDEN_MODE
        super(EncodeVotesForm, self).updateWidgets()
        self.widgets['votes'].allow_delete = False
        self.widgets['votes'].allow_insert = False
        self.widgets['votes'].allow_reorder = False
        self.widgets['votes'].auto_append = False
        self.widgets['votes'].columns[0]['mode'] = HIDDEN_MODE
        for row in self.widgets['votes'].widgets:
            for wdt in row.subform.widgets.values():
                if wdt.__name__ == 'voter':
                    wdt.mode = DISPLAY_MODE
                elif wdt.__name__ == 'voter_uid':
                    wdt.mode = HIDDEN_MODE

    def _getLinkedItemVoteNumbers(self, vote_number=0):
        """Return every votes linked to given p_vote_number."""
        res = []
        item_votes = self.meeting.itemVotes[self.context.UID()]
        len_item_votes = len(item_votes)

        origin_is_linked = item_votes[vote_number]['linked_to_previous']

        if origin_is_linked:
            # find first
            i = vote_number - 1
            while i and item_votes[i]['linked_to_previous']:
                res.append(i)
                i -= 1
            # i is now on the vote previous first 'linked_to_previous', keep it
            res.append(i)

        # not origin_is_linked only way is next or origin_is_linked, need to get next too
        res.append(vote_number)
        i = vote_number + 1
        while i < len_item_votes and item_votes[i]['linked_to_previous']:
            res.append(i)
            i += 1
        # not linked, return an empty list
        if res == [vote_number]:
            res = []
        return res

    def cleanVotersLinkedTo(self, vote_number, new_voters):
        """ """
        linked_vote_numbers = self._getLinkedItemVoteNumbers(vote_number)
        if linked_vote_numbers:
            item_votes = self.meeting.itemVotes[self.context.UID()]
            # wipeout other vote numbers
            # get values edited just now that will no more be useable on linked votes
            current_item_votes = item_votes[vote_number]
            kept_voters = [voter_uid for voter_uid, voter_value in current_item_votes['voters'].items()
                           if voter_value not in [NOT_ENCODED_VOTE_VALUE, NOT_VOTABLE_LINKED_TO_VALUE]]
            for linked_vote_number in linked_vote_numbers:
                if linked_vote_number == vote_number:
                    continue
                linked_item_vote = item_votes[linked_vote_number]
                for voter_uid, vote_value in linked_item_vote['voters'].items():
                    if voter_uid in kept_voters:
                        linked_item_vote['voters'][voter_uid] = NOT_VOTABLE_LINKED_TO_VALUE
                    elif vote_value == NOT_VOTABLE_LINKED_TO_VALUE and \
                            voter_uid in new_voters and \
                            new_voters[voter_uid] == NOT_ENCODED_VOTE_VALUE:
                        # this is potentially a liberated vote value
                        linked_item_vote['voters'][voter_uid] = NOT_ENCODED_VOTE_VALUE

    def _doApply(self):
        """ """
        if not self.mayChangeAttendees():
            raise Unauthorized

        # prepare Meeting.itemVotes compatible data
        # while datagrid used in an overlay, some <NO_VALUE>
        # wipeout self.votes from these values
        self.votes = [vote for vote in self.votes if isinstance(vote, dict)]
        data = {}
        data['label'] = self.label
        data['linked_to_previous'] = self.linked_to_previous
        data['voters'] = PersistentMapping()
        for vote in self.votes:
            data['voters'][vote['voter_uid']] = vote['vote_value']
        item_uid = self.context.UID()
        # set new itemVotes value on meeting
        # first votes
        if item_uid not in self.meeting.itemVotes:
            self.meeting.itemVotes[item_uid] = PersistentList()
            # check if we are not adding a new vote on an item containing no votes at all
            if self.vote_number == 1:
                # add an empty vote 0
                data_item_vote_0 = self.context.getItemVotes(
                    vote_number=0,
                    include_vote_number=False,
                    include_unexisting=True)
                # make sure we use persistent for 'voters'
                data_item_vote_0['voters'] = PersistentMapping(data_item_vote_0['voters'])
                self.meeting.itemVotes[item_uid].append(PersistentMapping(data_item_vote_0))
        new_voters = data.get('voters')
        # new vote_number
        if self.vote_number + 1 > len(self.meeting.itemVotes[item_uid]):
            # complete data before storing, if some voters are missing it is
            # because of NOT_VOTABLE_LINKED_TO_VALUE, we add it
            item_voter_uids = self.context.getItemVoters()
            for item_voter_uid in item_voter_uids:
                if item_voter_uid not in data['voters']:
                    data['voters'][item_voter_uid] = NOT_VOTABLE_LINKED_TO_VALUE
            self.meeting.itemVotes[item_uid].append(PersistentMapping(data))
        else:
            # use update in case we only update a subset of votes
            # when some vote NOT_VOTABLE_LINKED_TO_VALUE or so
            # we have nested dicts, data is a dict, containing 'voters' dict
            self.meeting.itemVotes[item_uid][self.vote_number]['voters'].update(data['voters'])
            data.pop('voters')
            self.meeting.itemVotes[item_uid][self.vote_number].update(data)
        # manage linked_to_previous
        # if current vote is linked to other votes, we will set NOT_VOTABLE_LINKED_TO_VALUE
        # as value of vote of voters of other linked votes
        self.cleanVotersLinkedTo(self.vote_number, new_voters)

        # finish
        voter_uids = [vote['voter_uid'] for vote in self.votes]
        voter_uids = "_".join(voter_uids)
        vote_values = [vote['vote_value'] for vote in self.votes]
        vote_values = "_".join(vote_values)
        extras = 'item={0} voter_uids={1} vote_values={2}'.format(
            repr(self.context), voter_uids, vote_values)
        fplog('encode_item_votes', extras=extras)
        api.portal.show_message(
            _("Votes have been encoded for current item."),
            request=self.request)
        self._finished = True

EncodeVotesFormWrapper = wrap_form(EncodeVotesForm)


class ItemDeleteVoteView(BrowserView):
    """ """

    def __call__(self, object_uid, redirect=True):
        """ """
        if not self.context._mayChangeAttendees():
            raise Unauthorized

        # redirect can by passed by jQuery, in this case, we receive '0' or '1'
        redirect = boolean_value(redirect)
        object_uid = int(object_uid)
        item_uid = self.context.UID()
        # delete from meeting itemVote
        meeting = self.context.getMeeting()
        deleted_vote = meeting.itemVotes[item_uid].pop(object_uid)
        # finish
        voter_uids = [voter_uid for voter_uid in deleted_vote['voters']]
        voter_uids = "_".join(voter_uids)
        vote_values = [vote_value for vote_value in deleted_vote['voters'].values()]
        vote_values = "_".join(vote_values)
        extras = 'item={0} vote_number={1} vote_label={2} voter_uids={3} vote_values={4}'.format(
            repr(self.context),
            object_uid,
            deleted_vote['label'],
            voter_uids,
            vote_values)
        fplog('delete_item_votes', extras=extras)
        api.portal.show_message(
            _("Votes number ${vote_number} have been deleted for current item.",
              mapping={'vote_number': object_uid + 1}),
            request=self.request)
        self._finished = True
