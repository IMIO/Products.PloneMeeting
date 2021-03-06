# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from imio.helpers.content import get_vocab
from imio.helpers.security import fplog
from persistent.mapping import PersistentMapping
from plone import api
from plone.autoform.directives import widget
from plone.restapi.deserializer import boolean_value
from plone.z3cform.layout import wrap_form
from Products.Five import BrowserView
from Products.PloneMeeting.browser.itemattendee import BaseAttendeeForm
from Products.PloneMeeting.browser.itemattendee import IBaseAttendee
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.utils import get_context_with_request
from Products.PloneMeeting.widgets.pm_number import PMNumberFieldWidget
from Products.PloneMeeting.widgets.pm_selectreadonly import PMSelectReadonlyWidget
from z3c.form import field
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.contentprovider import ContentProviders
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from zope import schema
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component.hooks import getSite
from zope.contentprovider.provider import ContentProviderBase
from zope.i18n import translate
from zope.interface import implements
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


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
        used_vote_terms = get_vocab(
            self.context, "Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary")
        self.usedVoteValues = [term.token for term in used_vote_terms._terms]
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
        is_new_vote = not context.getItemVotes(
            vote_number=vote_number, include_unexisting=False)
        if is_new_vote:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            # only keep NOT_ENCODED_VOTE_VALUE
            ignored_vote_values = list(cfg.getUsedVoteValues())
            ignored_vote_values.append(NOT_VOTABLE_LINKED_TO_VALUE)
            last_vote = context.getItemVotes(
                ignored_vote_values=ignored_vote_values)[-1]
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
    res = request.get('form.widgets.linked_to_previous', None)
    if res is None:
        item_votes = context.getItemVotes(vote_number=vote_number_default())
        res = item_votes['linked_to_previous']
    return res or False


class IVote(Interface):

    voter_uid = schema.Choice(
        title=u'Voter UID',
        required=False,
        vocabulary="Products.PloneMeeting.vocabularies.itemvotersvocabulary", )

    widget('voter', PMSelectReadonlyWidget)
    voter = schema.Choice(
        title=_(u"Voter"),
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


def _get_linked_item_vote_numbers(context, meeting, vote_number=0):
    """Return every votes linked to given p_vote_number."""
    res = []
    item_votes = meeting.itemVotes.get(context.UID())
    if item_votes:
        len_item_votes = len(item_votes)
        # while adding new secret vote, vote_number does still not exist
        if len(item_votes) > vote_number:
            origin_is_linked = item_votes[vote_number]['linked_to_previous']
        else:
            origin_is_linked = bool(context.REQUEST.form.get('form.widgets.linked_to_previous'))
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


def clean_voters_linked_to(context, meeting, vote_number, new_voters):
    """ """
    linked_vote_numbers = _get_linked_item_vote_numbers(context, meeting, vote_number)
    if linked_vote_numbers:
        item_votes = meeting.itemVotes[context.UID()]
        # clean other vote numbers
        # get values edited just now that will no more be useable on linked votes
        kept_voters = [voter_uid for voter_uid, voter_value in new_voters.items()
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


def next_vote_is_linked(itemVotes, vote_number=0):
    """Return True if next vote is linked, useful when on first vote
       that has not the linked_to_previous info."""
    res = False
    if len(itemVotes) > vote_number + 1 and \
       itemVotes[vote_number + 1]['linked_to_previous']:
        res = True
    return res


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
                if wdt.__name__ == 'voter_uid':
                    wdt.mode = HIDDEN_MODE

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

        # set item public votes
        self.meeting.setItemPublicVote(self.context, data, self.vote_number)

        # finish
        voter_uids = [vote['voter_uid'] for vote in self.votes]
        voter_uids = "__".join(voter_uids)
        vote_values = [vote['vote_value'] for vote in self.votes]
        vote_values = "__".join(vote_values)
        extras = 'item={0} vote_number={1} voter_uids={2} vote_values={3}'.format(
            repr(self.context), self.vote_number, voter_uids, vote_values)
        fplog('encode_item_votes', extras=extras)
        api.portal.show_message(
            _("Votes have been encoded for current item."),
            request=self.request)
        self._finished = True

EncodeVotesFormWrapper = wrap_form(EncodeVotesForm)


@provider(IContextAwareDefaultFactory)
def secret_votes_default(context):
    """Default values for secret votes."""
    res = []
    vote_number = vote_number_default()
    item_votes = context.getItemVotes(vote_number=vote_number,
                                      ignored_vote_values=[NOT_VOTABLE_LINKED_TO_VALUE])
    used_vote_terms = get_vocab(
        context,
        "Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary",
        vote_number=vote_number)
    usedVoteValues = [term.token for term in used_vote_terms._terms
                      if term.token != NOT_ENCODED_VOTE_VALUE]
    for usedVoteValue in usedVoteValues:
        data = {'vote_value_id': usedVoteValue,
                'vote_value': usedVoteValue,
                'vote_count': item_votes['votes'].get(usedVoteValue) or 0}
        res.append(data)
    return res


class ISecretVote(Interface):

    vote_value_id = schema.Choice(
        title=u'Vote value id',
        required=False,
        vocabulary="Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary", )

    widget('vote_value', PMSelectReadonlyWidget)
    vote_value = schema.Choice(
        title=_(u"Vote value"),
        required=False,
        vocabulary="Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary", )

    widget('vote_count', PMNumberFieldWidget)
    vote_count = schema.Int(
        title=_(u"Vote count"),
        required=False)


class IEncodeSecretVotes(IBaseAttendee):

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
        title=_(u"Votes"),
        value_type=DictRow(title=u'Votes', schema=ISecretVote),
        defaultFactory=secret_votes_default,
        required=True)

    @invariant
    def validate_votes(data):
        ''' '''
        # prepare Meeting.itemVotes compatible data
        # while datagrid used in an overlay, some <NO_VALUE>
        # wipeout self.votes from these values
        # data.__context__ does not contain the context...
        context = data.__context__ or get_context_with_request(None)
        meeting = context.getMeeting()
        votes = [vote for vote in data.votes if isinstance(vote, dict)]
        data.votes = votes
        # check if max voters of every linked secret votes is not exceeded
        linked_vote_numbers = _get_linked_item_vote_numbers(context, meeting, data.vote_number)
        max_voters = len(context.getItemVoters())
        if linked_vote_numbers:
            # init at current value
            total = sum([vote['vote_count'] for vote in data.votes])
            for linked_vote_number in linked_vote_numbers:
                if linked_vote_number != data.vote_number:
                    linked_vote = context.getItemVotes(vote_number=linked_vote_number)
                    total += sum([vote_count for vote_value, vote_count
                                  in linked_vote['votes'].items()])
        else:
            total = sum([vote['vote_count'] for vote in votes])
        if total > max_voters:
            msg = translate(u'error_can_not_encode_more_than_max_voters',
                            mapping={'max_voters': str(max_voters)},
                            domain="PloneMeeting",
                            context=context.REQUEST)
            raise Invalid(msg)


class EncodeSecretVotesForm(BaseAttendeeForm):
    """ """

    label = _(u"Encode secret votes")
    schema = IEncodeSecretVotes
    fields = field.Fields(IEncodeSecretVotes)
    fields['votes'].widgetFactory = DataGridFieldFactory

    def updateWidgets(self):
        # hide vote_number field
        self.fields['vote_number'].mode = HIDDEN_MODE
        # do not hide it, when hidding it, value is always True???
        # this is hidden using CSS
        # self.fields['linked_to_previous'].mode = HIDDEN_MODE
        super(EncodeSecretVotesForm, self).updateWidgets()
        self.widgets['votes'].allow_delete = False
        self.widgets['votes'].allow_insert = False
        self.widgets['votes'].allow_reorder = False
        self.widgets['votes'].auto_append = False
        self.widgets['votes'].columns[0]['mode'] = HIDDEN_MODE
        for row in self.widgets['votes'].widgets:
            for wdt in row.subform.widgets.values():
                if wdt.__name__ == 'vote_value_id':
                    wdt.mode = HIDDEN_MODE
                elif wdt.__name__ == 'vote_value' and wdt.value:
                    wdt.klass += " {0}".format(wdt.context['vote_value'])

    def max(self, widget):
        """ """
        return len(self.context.getItemVoters())

    def min(self, widget):
        """ """
        return 0

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
        data['votes'] = {}
        for vote in self.votes:
            data['votes'][vote['vote_value_id']] = vote['vote_count']

        # set item public votes
        self.meeting.setItemSecretVote(self.context, data, self.vote_number)

        # finish
        vote_values = [vote['vote_value_id'] for vote in self.votes]
        vote_values = "__".join(vote_values)
        vote_count = [str(vote['vote_count']) for vote in self.votes]
        vote_count = "__".join(vote_count)
        extras = 'item={0} vote_number={1} vote_values={2} vote_count={3}'.format(
            repr(self.context), self.vote_number, vote_values, vote_count)
        fplog('encode_item_secret_votes', extras=extras)
        api.portal.show_message(
            _("Votes have been encoded for current item."),
            request=self.request)
        self._finished = True

EncodeSecretVotesFormWrapper = wrap_form(EncodeSecretVotesForm)


class ItemDeleteVoteView(BrowserView):
    """ """

    def __call__(self, object_uid, redirect=True):
        """ """
        if not self.context._mayChangeAttendees():
            raise Unauthorized

        # redirect can by passed by jQuery, in this case, we receive '0' or '1'
        redirect = boolean_value(redirect)
        vote_number = int(object_uid)
        item_uid = self.context.UID()
        meeting = self.context.getMeeting()
        if item_uid in meeting.itemVotes:
            itemVotes = meeting.itemVotes[item_uid]
            assert self.context._voteIsDeletable(vote_number)

            vote_to_delete = itemVotes[vote_number]
            if self.context.getVotesAreSecret():
                originnal_vote_keys = [str(vote_count) for vote_value, vote_count
                                       in vote_to_delete['votes'].items()]
                originnal_vote_keys = "__".join(originnal_vote_keys)
                originnal_vote_values = [vote_value for vote_value, vote_count
                                         in vote_to_delete['votes'].items()]
                originnal_vote_values = "__".join(originnal_vote_values)
                fp_extras_pattern = 'item={0} vote_number={1} vote_label={2} vote_count={3} vote_values={4}'
            else:
                originnal_vote_keys = [voter_uid for voter_uid in vote_to_delete['voters']]
                originnal_vote_keys = "__".join(originnal_vote_keys)
                originnal_vote_values = [vote_value for vote_value in vote_to_delete['voters'].values()]
                originnal_vote_values = "__".join(originnal_vote_values)
                fp_extras_pattern = 'item={0} vote_number={1} vote_label={2} voter_uids={3} vote_values={4}'
                # call clean_voters_linked_to with every values NOT_ENCODED_VOTE_VALUE
                # to liberate every values
                new_voters = vote_to_delete['voters'].copy()
                new_voters = {voter_uid: NOT_ENCODED_VOTE_VALUE
                              for voter_uid, vote_value in new_voters.items()
                              if vote_value != NOT_VOTABLE_LINKED_TO_VALUE}
                clean_voters_linked_to(self.context, meeting, vote_number, new_voters)

            # delete from meeting itemVote
            deleted_vote = meeting.itemVotes[item_uid].pop(vote_number)
            # if deleted last existing vote (vote_number 0) remove context UID from meeting itemVotes
            if not meeting.itemVotes[item_uid]:
                del meeting.itemVotes[item_uid]
            # finish deletion
            label = deleted_vote['label'] or ""
            extras = fp_extras_pattern.format(
                repr(self.context),
                vote_number,
                label.encode('utf-8'),
                originnal_vote_keys,
                originnal_vote_values)
            fplog('delete_item_votes', extras=extras)
        # message
        api.portal.show_message(
            _("Votes number ${vote_number} have been deleted for current item.",
              mapping={'vote_number': vote_number + 1}),
            request=self.request)
        self._finished = True
