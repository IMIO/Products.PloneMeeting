# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collections import OrderedDict
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from imio.helpers.content import get_vocab
from imio.helpers.security import fplog
from persistent.mapping import PersistentMapping
from plone import api
from plone.autoform.directives import widget
from plone.restapi.deserializer import boolean_value
from Products.Five import BrowserView
from Products.PloneMeeting.browser.itemattendee import BaseAttendeeForm
from Products.PloneMeeting.browser.itemattendee import IBaseAttendee
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import get_context_with_request
from Products.PloneMeeting.utils import notifyModifiedAndReindex
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


def _build_voting_groups(context, caching=True):
    """Build voting groups informations that will be used to manage the votes by group."""

    # caching is done in the REQUEST because this is called 2 times
    if caching and hasattr(context, "REQUEST"):
        res = getattr(context.REQUEST, '_build_voting_groups', None)

    if res is None:
        res = OrderedDict([('all', {'title': 'All', 'uids': []}),
                           ('others', {'title': 'Others', 'uids': []})])
        for voter in context.get_item_voters(theObjects=True):
            group_id = 'others'
            voting_group = voter.voting_group
            # use a voting_group if selected, else use 'others
            if voting_group and not voting_group.isBroken():
                org = voting_group.to_object
                group_id = org.getId()
                if group_id not in res:
                    res[group_id] = {'title': org.title, 'uids': []}
            res[group_id]['uids'].append(voter.UID())
        # only keep PLONEGROUP_ORG if any other value than 'all'
        if res.keys() == ['all', 'others']:
            res.pop('others')
        else:
            # reorder so PLONEGROUP_ORG is at the end
            ordered = res.keys()
            ordered += [ordered.pop(1)]
            res = OrderedDict((k, res[k]) for k in ordered)
        # caching
        if caching and hasattr(context, "REQUEST"):
            context.REQUEST.set('_build_voting_groups', res)
    return res


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
        self.used_vote_values = [term.token for term in used_vote_terms._terms]
        self.groups = _build_voting_groups(self.context)
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
    item_votes = context.get_item_votes(
        vote_number=vote_number,
        ignored_vote_values=[NOT_VOTABLE_LINKED_TO_VALUE])
    # keep order using get_item_voters
    item_voter_uids = context.get_item_voters()
    # when adding a new vote linked_to_previous, only keep possible voters
    if item_votes['linked_to_previous']:
        is_new_vote = not context.get_item_votes(
            vote_number=vote_number, include_unexisting=False)
        if is_new_vote:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(context)
            # only keep NOT_ENCODED_VOTE_VALUE
            ignored_vote_values = list(cfg.getUsedVoteValues())
            ignored_vote_values.append(NOT_VOTABLE_LINKED_TO_VALUE)
            last_vote = context.get_item_votes(
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
    item_votes = context.get_item_votes(vote_number=vote_number_default())
    if item_votes and item_votes['label']:
        res = item_votes['label']
    return res


@provider(IContextAwareDefaultFactory)
def linked_to_previous_default(context):
    """ """
    request = getSite().REQUEST
    res = request.get('form.widgets.linked_to_previous', None)
    if res is None:
        item_votes = context.get_item_votes(vote_number=vote_number_default())
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
        required=True)

    label = schema.TextLine(
        title=_(u"Label"),
        description=_(u"Free label that will identify the vote, "
                      u"useful when several votes are defined on an item. "
                      u"Leave empty if not used."),
        defaultFactory=label_default,
        required=False)


def _get_linked_item_vote_numbers(context, meeting, vote_number=0):
    """Return every votes linked to given p_vote_number."""
    res = []
    item_votes = meeting.item_votes.get(context.UID())
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
        item_votes = meeting.item_votes[context.UID()]
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


def is_vote_updatable_for(context, item_to_update):
    """Given p_item_to_update will be updatable if it is the context or
       if using same pollType and same voters and not using several or linked votes."""
    res = False
    if context == item_to_update or \
       (item_to_update.getPollType() != 'no_vote' and
        context.get_item_votes(vote_number=0).get('poll_type', context.getPollType()) ==
        item_to_update.get_item_votes(vote_number=0).get('poll_type', item_to_update.getPollType()) and
        context.get_item_voters() == item_to_update.get_item_voters() and
            len(item_to_update.get_item_votes()) < 2):
        res = True
    return res


def display_item_numbers(numbers):
    """Manage displaying given p_elements with following result:
       - 1 numbers: "2";
       - 2 numbers: "2 & 3";
       - 5 numbers: "2, 3, 4, 5 & 6".
    """
    if len(numbers) > 1:
        res = ", ".join(numbers[:-1]) + " & " + numbers[-1]
    else:
        res = numbers[0]
    return res


class EncodeVotesForm(BaseAttendeeForm):
    """ """
    implements(IFieldsAndContentProvidersForm)
    contentProviders = ContentProviders()
    contentProviders['select_all'] = DisplaySelectAllProvider
    contentProviders['select_all'].position = 2

    label = _(u"Encode votes")
    schema = IEncodeVotes
    fields = field.Fields(IEncodeVotes)
    fields['votes'].widgetFactory = DataGridFieldFactory

    id = "item-encode-votes-form"

    def updateWidgets(self):
        # hide vote_number field
        self.fields['vote_number'].mode = HIDDEN_MODE
        # add a css class corresponding to group of held positions
        groups = _build_voting_groups(self.context)
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
            if row.subform.context is None:
                continue
            voter_uid = row.subform.context['voter_uid']
            group_id = [group_id for group_id, values in groups.items()
                        if voter_uid in values['uids']]
            if group_id:
                row.addClass(group_id[0])
            for wdt in row.subform.widgets.values():
                if wdt.__name__ == 'voter_uid':
                    wdt.mode = HIDDEN_MODE
        # disable apply_until_item_number when using several votes
        # or if poll_type was redefined
        if _should_disable_apply_until_item_number(self.context):
            apply_until_item_number = self.widgets['apply_until_item_number']
            apply_until_item_number.disabled = "disabled"
            apply_until_item_number.title = _(
                u"Not available when using several votes on same item.")

    def _doApply(self):
        """ """
        error = super(EncodeVotesForm, self)._doApply()
        if error:
            return error

        # prepare Meeting.item_votes compatible data
        # while datagrid used in an overlay, some <NO_VALUE>
        # wipeout self.votes from these values
        self.votes = [vote for vote in self.votes if isinstance(vote, dict)]
        data = {}
        data['label'] = self.label
        data['linked_to_previous'] = self.linked_to_previous
        data['voters'] = PersistentMapping()
        for vote in self.votes:
            data['voters'][vote['voter_uid']] = vote['vote_value']
        # add poll_type in case it was redefined
        vote_infos = self.context.get_item_votes(vote_number=self.vote_number)
        if 'poll_type' in vote_infos:
            data['poll_type'] = vote_infos['poll_type']

        updated = []
        not_updated = []
        for item_to_update in self.items_to_update:
            # set item public votes
            if is_vote_updatable_for(self.context, item_to_update):
                self.meeting.set_item_public_vote(item_to_update, data, self.vote_number)
                notifyModifiedAndReindex(item_to_update)
                updated.append(item_to_update.getItemNumber(for_display=True))
            else:
                not_updated.append(item_to_update.getItemNumber(for_display=True))

        # finish
        voter_uids = [vote['voter_uid'] for vote in self.votes]
        voter_uids = "__".join(voter_uids)
        vote_values = [vote['vote_value'] for vote in self.votes]
        vote_values = "__".join(vote_values)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} vote_number={1} voter_uids={2} vote_values={3} ' \
            'from_item_number={4} until_item_number={5}'.format(
                repr(self.context),
                self.vote_number,
                voter_uids,
                vote_values,
                first_item_number,
                last_item_number)
        fplog('encode_item_votes', extras=extras)
        if len(updated) == 1:
            api.portal.show_message(
                _("Votes have been encoded for current item."),
                request=self.request)
        else:
            api.portal.show_message(
                _("Votes have been encoded for items \"${item_numbers}\".",
                  mapping={'item_numbers': display_item_numbers(updated)}),
                request=self.request)

        # display items that could not be updated
        if not_updated:
            api.portal.show_message(
                _("error_updating_votes_for_items",
                  mapping={'item_numbers': display_item_numbers(not_updated)}),
                request=self.request, type="warning")
        self._finished = True


@provider(IContextAwareDefaultFactory)
def secret_votes_default(context):
    """Default values for secret votes."""
    res = []
    vote_number = vote_number_default()
    item_votes = context.get_item_votes(vote_number=vote_number,
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

    label = schema.TextLine(
        title=_(u"Label"),
        description=_(u"Free label that will identify the vote, "
                      u"useful when several votes are defined on an item. "
                      u"Leave empty if not used."),
        defaultFactory=label_default,
        required=False)

    @invariant
    def validate_votes(data):
        ''' '''
        # prepare Meeting.item_votes compatible data
        # while datagrid used in an overlay, some <NO_VALUE>
        # wipeout self.votes from these values
        # data.__context__ does not contain the context...
        context = data.__context__ or get_context_with_request(None)
        meeting = context.getMeeting()
        votes = [vote for vote in data.votes if isinstance(vote, dict)]
        data.votes = votes
        # when used in an overlay, PMNumberWidget number browser validation
        # is not done, so we do it here... wrong values are received as None
        none_values = [v for v in votes if v["vote_count"] is None]
        if none_values:
            msg = translate(u'error_some_values_are_not_integers',
                            domain="PloneMeeting",
                            context=context.REQUEST)
            raise Invalid(msg)
        # check if max voters of every linked secret votes is not exceeded
        linked_vote_numbers = _get_linked_item_vote_numbers(context, meeting, data.vote_number)
        max_voters = len(context.get_item_voters())
        if linked_vote_numbers:
            # init at current value
            total = sum([vote['vote_count'] for vote in data.votes])
            for linked_vote_number in linked_vote_numbers:
                if linked_vote_number != data.vote_number:
                    linked_vote = context.get_item_votes(vote_number=linked_vote_number)
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


def _should_disable_apply_until_item_number(context):
    """Is it possible to use the "apply_until_item_number" field?"""
    vote_number = context.REQUEST.get('vote_number', 0)
    if len(context.get_item_votes()) > 1 or \
       vote_number > 0 or \
       context.get_item_votes(vote_number).get('poll_type', None) != \
       context.getPollType():
        return True
    return False


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
        # disable apply_until_item_number when using several votes
        if _should_disable_apply_until_item_number(self.context):
            apply_until_item_number = self.widgets['apply_until_item_number']
            apply_until_item_number.disabled = "disabled"
            apply_until_item_number.title = _(u"Not available when using several votes on same item.")

    def max(self, widget):
        """ """
        return len(self.context.get_item_voters())

    def min(self, widget):
        """ """
        return 0

    def _doApply(self):
        """ """
        error = super(EncodeSecretVotesForm, self)._doApply()
        if error:
            return error

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

        updated = []
        not_updated = []
        for item_to_update in self.items_to_update:
            # set item secret vote
            if is_vote_updatable_for(self.context, item_to_update):
                self.meeting.set_item_secret_vote(item_to_update, data, self.vote_number)
                notifyModifiedAndReindex(item_to_update)
                updated.append(item_to_update.getItemNumber(for_display=True))
            else:
                not_updated.append(item_to_update.getItemNumber(for_display=True))

        # finish
        vote_values = [vote['vote_value_id'] for vote in self.votes]
        vote_values = "__".join(vote_values)
        vote_count = [str(vote['vote_count']) for vote in self.votes]
        vote_count = "__".join(vote_count)
        first_item_number = self.items_to_update[0].getItemNumber(for_display=True)
        last_item_number = self.items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} vote_number={1} vote_values={2} vote_count={3} ' \
            'from_item_number={4} until_item_number={5}'.format(
                repr(self.context),
                self.vote_number,
                vote_values,
                vote_count,
                first_item_number,
                last_item_number)
        fplog('encode_item_secret_votes', extras=extras)
        if len(updated) == 1:
            api.portal.show_message(
                _("Votes have been encoded for current item."),
                request=self.request)
        else:
            api.portal.show_message(
                _("Votes have been encoded for items \"${item_numbers}\".",
                  mapping={'item_numbers': display_item_numbers(updated)}),
                request=self.request)

        # display items that could not be updated
        if not_updated:
            api.portal.show_message(
                _("error_updating_votes_for_items",
                  mapping={'item_numbers': display_item_numbers(not_updated)}),
                request=self.request, type="warning")
        self._finished = True


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
        if item_uid in meeting.item_votes:
            item_votes = meeting.item_votes[item_uid]
            assert self.context._voteIsDeletable(meeting, vote_number)

            vote_to_delete = item_votes[vote_number]
            if self.context.get_vote_is_secret(meeting, vote_number):
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
            deleted_vote = meeting.item_votes[item_uid].pop(vote_number)
            # if deleted last existing vote (vote_number 0) remove context UID from meeting itemVotes
            if not meeting.item_votes[item_uid]:
                del meeting.item_votes[item_uid]
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
