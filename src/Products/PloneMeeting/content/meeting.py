# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.config import get_registry_organizations
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.prettylink.interfaces import IPrettyLink
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.querystring.querybuilder import queryparser
from plone.app.textfield import RichText
from plone.app.uuid.utils import uuidToCatalogBrain
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget
from plone.memoize import ram
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.browser.itemchangeorder import _compute_value_to_add
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.browser.itemchangeorder import _to_integer
from Products.PloneMeeting.browser.itemchangeorder import _use_same_integer
from Products.PloneMeeting.browser.itemvotes import clean_voters_linked_to
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.interfaces import IMeetingContent
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import display_as_html
from Products.PloneMeeting.utils import displaying_available_items
from Products.PloneMeeting.utils import fieldIsEmpty
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import get_next_meeting
from Products.PloneMeeting.utils import get_states_before
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import hasHistory
from Products.PloneMeeting.utils import ItemDuplicatedFromConfigEvent
from Products.PloneMeeting.utils import MeetingLocalRolesUpdatedEvent
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import toHTMLStrikedContent
from Products.PloneMeeting.utils import transformAllRichTextFields
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.utils import validate_item_assembly_value
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.event import notify
from zope.i18n import translate
from zope.interface import implements
from zope.schema import Datetime
from zope.schema import Int
from zope.schema import Text
from zope.schema import TextLine

import copy
import itertools
import logging
import os

logger = logging.getLogger('PloneMeeting')


class IMeeting(IMeetingContent):
    """
        Meeting schema
    """

    form.widget('date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    date = Datetime(
        title=_(u'title_date'),
        required=True)

    form.widget('start_date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    start_date = Datetime(
        title=_(u'title_start_date'),
        required=True)

    form.widget('mid_date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    mid_date = Datetime(
        title=_(u'title_mid_date'),
        required=True)

    form.widget('end_date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    end_date = Datetime(
        title=_(u'title_end_date'),
        required=True)

    form.widget('approval_date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    approval_date = Datetime(
        title=_(u'title_approval_date'),
        required=True)

    form.widget('convocation_date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    convocation_date = Datetime(
        title=_(u'title_convocation_date'),
        required=True)

    assembly = Text(
        title=_(u"title_assembly"),
        description=_("descr_meeting_assembly"),
        required=False)

    assembly_excused = Text(
        title=_(u"title_assembly_excused"),
        description=_("descr_meeting_assembly_excused"),
        required=False)

    assembly_absents = Text(
        title=_(u"title_assembly_absents"),
        description=_("descr_meeting_assembly_absents"),
        required=False)

    assembly_guests = Text(
        title=_(u"title_assembly_guests"),
        description=_("descr_assembly_guests"),
        required=False)

    assembly_proxies = Text(
        title=_(u"title_assembly_proxies"),
        description=_("descr_assembly_proxies"),
        required=False)

    assembly_staves = Text(
        title=_(u"title_assembly_staves"),
        description=_("descr_assembly_staves"),
        required=False)

    signatures = Text(
        title=_(u"title_signatures"),
        description=_("descr_signatures"),
        required=False)

    place = TextLine(
        title=_(u"title_place"),
        required=False)

    form.widget('extraordinary_session', RadioFieldWidget)
    extraordinary_session = schema.Bool(
        title=_(u'title_extraordinary_session'),
        description=_("descr_extraordinary_session"),
        required=False)

    form.widget('in_and_out_moves', PMRichTextFieldWidget)
    in_and_out_moves = RichText(
        title=_(u"title_in_and_out_moves"),
        description=_("field_reserved_to_meeting_managers_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('notes', PMRichTextFieldWidget)
    notes = RichText(
        title=_(u"title_notes"),
        description=_("field_reserved_to_meeting_managers_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('observations', PMRichTextFieldWidget)
    observations = RichText(
        title=_(u"title_observations"),
        description=_("field_vieawable_by_everyone_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('pre_meeting_date', DatetimeFieldWidget, show_today_link=True, show_time=True)
    pre_meeting_date = Datetime(
        title=_(u'title_pre_meeting_date'),
        required=True)

    pre_meeting_place = TextLine(
        title=_(u"title_pre_meeting_place"),
        required=False)

    form.widget('pre_observations', PMRichTextFieldWidget)
    pre_observations = RichText(
        title=_(u"title_pre_observations"),
        description=_("field_vieawable_by_everyone_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('committee_observations', PMRichTextFieldWidget)
    committee_observations = RichText(
        title=_(u"title_committee_observations"),
        description=_("field_vieawable_by_everyone_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('votes_observations', PMRichTextFieldWidget)
    votes_observations = RichText(
        title=_(u"title_votes_observations"),
        description=_("field_vieawable_by_everyone_once_meeting_decided_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('public_meeting_observations', PMRichTextFieldWidget)
    public_meeting_observations = RichText(
        title=_(u"title_public_meeting_observations"),
        description=_("field_vieawable_by_everyone_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('secret_meeting_observations', PMRichTextFieldWidget)
    secret_meeting_observations = RichText(
        title=_(u"title_secret_meeting_observations"),
        description=_("field_reserved_to_meeting_managers_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('authority_notice', PMRichTextFieldWidget)
    authority_notice = RichText(
        title=_(u"title_authority_notice"),
        description=_("field_reserved_to_meeting_managers_descr"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.write_permission(meeting_number=ManagePortal)
    meeting_number = Int(
        title=_(u"title_meeting_number"),
        description=_("field_reserved_to_meeting_managers_descr"),
        default=-1,
        required=False)

    form.write_permission(first_item_number=ManagePortal)
    first_item_number = Int(
        title=_(u"title_first_item_number"),
        description=_("field_reserved_to_meeting_managers_descr"),
        required=False)


class Meeting(Container):
    """ """

    implements(IMeeting)

    security = ClassSecurityInfo()

    MEETINGCLOSEDSTATES = ['closed']

    security.declarePublic('get_pretty_link')

    def get_pretty_link(self,
                        prefixed=False,
                        short=True,
                        showContentIcon=False,
                        isViewable=True,
                        notViewableHelpMessage=None,
                        appendToUrl='',
                        link_pattern=None):
        """Return the IPrettyLink version of the title."""
        adapted = IPrettyLink(self)
        tool = api.portal.get_tool('portal_plonemeeting')
        adapted.contentValue = tool.format_date(self,
                                                with_hour=True,
                                                prefixed=prefixed,
                                                short=short)
        adapted.isViewable = adapted.isViewable and isViewable
        if notViewableHelpMessage is not None:
            adapted.notViewableHelpMessage = notViewableHelpMessage
        adapted.showContentIcon = showContentIcon
        adapted.appendToUrl = appendToUrl
        if link_pattern:
            adapted.link_pattern = link_pattern
        return adapted.getLink()

    security.declarePublic('get_raw_query')

    def get_raw_query(self, force_linked_items_query=False, **kwargs):
        """Override default get_raw_query to manage our own."""
        # available items?
        if displaying_available_items(self) and not force_linked_items_query:
            res = self._available_items_query()
        else:
            res = [{'i': 'linkedMeetingUID',
                    'o': 'plone.app.querystring.operation.selection.is',
                    'v': self.UID()}, ]
        return res

    def _available_items_query(self):
        '''Check docstring in IMeeting.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meeting_state = self.query_state()
        if meeting_state not in cfg.adapted().getMeetingStatesAcceptingItems():
            # make sure the query returns nothing, add a dummy parameter
            return [{'i': 'UID',
                     'o': 'plone.app.querystring.operation.selection.is',
                     'v': 'dummy_unexisting_uid'}]
        res = [{'i': 'portal_type',
                'o': 'plone.app.querystring.operation.selection.is',
                'v': cfg.getItemTypeName()},
               {'i': 'review_state',
                'o': 'plone.app.querystring.operation.selection.is',
                'v': 'validated'},
               ]

        # before late state, accept items having any preferred meeting
        late_state = self.adapted().get_late_state()
        if meeting_state in get_states_before(self, late_state):
            # get items for which the getPreferredMeetingDate is lower or
            # equal to the date of this meeting (self)
            # a no preferred meeting item getPreferredMeetingDate is 1950/01/01
            res.append({'i': 'getPreferredMeetingDate',
                        'o': 'plone.app.querystring.operation.date.lessThan',
                        'v': self.date})
        else:
            # after late state, only query items for which preferred meeting is self
            res.append({'i': 'getPreferredMeetingDate',
                        'o': 'plone.app.querystring.operation.date.between',
                        'v': (datetime(2000, 1, 1), self.date)})
        return res

    security.declarePublic('getSort_on')

    def getSort_on(self, force_linked_items_query=False):
        """ """
        if displaying_available_items(self) and not force_linked_items_query:
            return 'getProposingGroup'
        else:
            return 'getItemNumber'

    security.declarePublic('selectedViewFields')

    def selectedViewFields(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # some columns are displayed in the 'Purpose' column
        if displaying_available_items(self):
            visibleCols = cfg.getAvailableItemsListVisibleColumns()
        else:
            visibleCols = cfg.getItemsListVisibleColumns()
        itemsListVisibleColumns = [col for col in visibleCols if not col.startswith('static_')]
        itemsListVisibleColumns.insert(0, u'pretty_link')
        if not displaying_available_items(self):
            itemsListVisibleColumns.insert(0, u'getItemNumber')
            itemsListVisibleColumns.insert(0, u'listType')
        itemsListVisibleColumns.append(u'select_row')
        # selectedViewFields must return a list of tuple
        return [(elt, elt) for elt in itemsListVisibleColumns]

    def _get_all_redefined_attendees(self, by_persons=False, only_keys=True):
        """Returns a list of dicts."""
        item_non_attendees = self.get_item_non_attendees(by_persons=by_persons)
        item_absents = self.get_item_absents(by_persons=by_persons)
        item_excused = self.get_item_excused(by_persons=by_persons)
        item_signatories = self.get_item_signatories(by_signatories=by_persons)
        if only_keys:
            redefined_item_attendees = item_non_attendees.keys() + \
                item_absents.keys() + item_excused.keys() + item_signatories.keys()
        else:
            redefined_item_attendees = item_non_attendees, item_absents, \
                item_excused, item_signatories
        return redefined_item_attendees

    def post_validate(self, REQUEST=None, errors=None):
        '''Validate attendees in post_validate as there is no field in schema for it.
           - an attendee may not be unselected if something is redefined for it on an item.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        if cfg.isUsingContacts() and not self.isTemporary():
            # removed attendees
            # REQUEST.form['meeting_attendees'] is like
            # ['muser_attendeeuid1_attendee', 'muser_attendeeuid2_excused']
            stored_attendees = self.getAllUsedHeldPositions(the_objects=False)
            meeting_attendees = [attendee.split('_')[1] for attendee
                                 in REQUEST.form.get('meeting_attendees', [])]
            removed_meeting_attendees = set(stored_attendees).difference(meeting_attendees)
            # attendees redefined on items
            redefined_item_attendees = self._get_all_redefined_attendees(by_persons=True)
            conflict_attendees = removed_meeting_attendees.intersection(
                redefined_item_attendees)
            if conflict_attendees:
                attendee_uid = tuple(removed_meeting_attendees)[0]
                attendee_brain = uuidToCatalogBrain(attendee_uid)
                errors['meeting_attendees'] = translate(
                    'can_not_remove_attendee_redefined_on_items',
                    mapping={'attendee_title': attendee_brain.get_full_title},
                    domain='PloneMeeting',
                    context=REQUEST)
            else:
                # removed voters
                stored_voters = self.getVoters()
                meeting_voters = [voter.split('_')[1] for voter
                                  in REQUEST.form.get('meeting_voters', [])]
                removed_meeting_voters = set(stored_voters).difference(meeting_voters)
                # public, voters are known
                item_votes = self.getItemVotes()
                voter_uids = []
                highest_secret_votes = 0
                for votes in item_votes.values():
                    for vote in votes:
                        if 'voters' in vote:
                            # public
                            voter_uids += [k for k, v in vote['voters'].items()
                                           if v != NOT_ENCODED_VOTE_VALUE]
                        else:
                            secret_votes = sum([v for k, v in vote['votes'].items()])
                            if secret_votes > highest_secret_votes:
                                highest_secret_votes = secret_votes
                voter_uids = list(set(voter_uids))
                conflict_voters = removed_meeting_voters.intersection(
                    voter_uids)
                if conflict_voters:
                    voter_uid = tuple(removed_meeting_voters)[0]
                    voter_brain = uuidToCatalogBrain(voter_uid)
                    errors['meeting_attendees'] = translate(
                        'can_not_remove_public_voter_voted_on_items',
                        mapping={'attendee_title': voter_brain.get_full_title},
                        domain='PloneMeeting',
                        context=REQUEST)
                elif highest_secret_votes > len(meeting_voters):
                    errors['meeting_attendees'] = translate(
                        'can_not_remove_secret_voter_voted_on_items',
                        domain='PloneMeeting',
                        context=REQUEST)

        return errors

    security.declarePrivate('validate_date')

    def validate_date(self, value):
        '''There can't be several meetings with the same date and hour.'''
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        # DateTime('2020-05-28 11:00') will result in DateTime('2020/05/28 11:00:00 GMT+0')
        # DateTime('2020/05/28 11:00') will result in DateTime('2020/05/28 11:00:00 GMT+2')
        # so make sure value uses "/" instead "-"
        value = value.replace("-", "/")
        otherMeetings = catalog(portal_type=cfg.getMeetingTypeName(), getDate=DateTime(value))
        if otherMeetings:
            for m in otherMeetings:
                if m.getObject() != self:
                    return translate('meeting_with_same_date_exists',
                                     domain='PloneMeeting',
                                     context=self.REQUEST)

    security.declarePrivate('validate_place')

    def validate_place(self, value):
        '''If "other" is selected, field "place_other" must contain
           something.'''
        rq = self.REQUEST
        if (value == 'other') and not rq.get('place_other', None):
            return translate('place_other_required',
                             domain='PloneMeeting',
                             context=rq)

    security.declarePrivate('validate_assembly')

    def validate_assembly(self, value):
        '''Validate the assembly field.'''
        if not validate_item_assembly_value(value):
            return translate('Please check that opening "[[" have corresponding closing "]]".',
                             domain='PloneMeeting',
                             context=self.REQUEST)

    security.declarePublic('display_striked_assembly')

    def display_striked_assembly(self):
        """ """
        return toHTMLStrikedContent(self.assembly.output)

    security.declarePublic('display_signatures')

    def display_signatures(self):
        """Display signatures as HTML, make sure lines added at end
           of signatures are displayed on screen correctly."""
        return display_as_html(self.getSignatures(), self)

    security.declarePublic('getAllUsedHeldPositions')

    def get_all_used_held_positions(self, include_new=False, the_objects=True):
        '''This will return every currently stored held_positions.
           If include_new=True, extra held_positions newly selected in the
           configuration are added.
           If p_the_objects=True, we return held_position objects, UID otherwise.
           '''
        # used Persons are held_positions stored in orderedContacts
        contacts = hasattr(self.aq_base, 'ordered_contacts') and list(self.ordered_contacts) or []
        if include_new:
            # now getOrderedContacts from MeetingConfig and append new contacts at the end
            # this is the case while adding new contact and editing existing meeting
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            selectable_contacts = cfg.getOrderedContacts()
            new_selectable_contacts = [c for c in selectable_contacts if c not in contacts]
            contacts = contacts + new_selectable_contacts

        if the_objects:
            # query held_positions
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(UID=contacts)

            # make sure we have correct order because query was not sorted
            # we need to sort found brains according to uids
            def get_key(item):
                return contacts.index(item.UID)
            brains = sorted(brains, key=get_key)
            contacts = [brain.getObject() for brain in brains]
        return tuple(contacts)

    security.declarePublic('getDefaultAttendees')

    def getDefaultAttendees(self):
        '''The default attendees are the active held_positions
           with 'present' in defaults.'''
        res = []
        if self.checkCreationFlag():
            used_held_positions = self.getAllUsedHeldPositions(include_new=True)
            res = [held_pos.UID() for held_pos in used_held_positions
                   if held_pos.defaults and 'present' in held_pos.defaults]
        return res

    security.declarePublic('getDefaultSignatories')

    def getDefaultSignatories(self):
        '''The default signatories are the active held_positions
           with a defined signature_number.'''
        res = []
        if self.checkCreationFlag():
            used_held_positions = self.getAllUsedHeldPositions(include_new=True)
            res = [held_pos for held_pos in used_held_positions
                   if held_pos.defaults and 'present' in held_pos.defaults and held_pos.signature_number]
        return {signer.UID(): signer.signature_number for signer in res}

    security.declarePublic('getDefaultVoters')

    def getDefaultVoters(self):
        '''The default voters are the active held_positions
           with 'voter' in defaults.'''
        res = []
        if self.checkCreationFlag():
            used_held_positions = self.getAllUsedHeldPositions(include_new=True)
            res = [held_pos.UID() for held_pos in used_held_positions
                   if held_pos.defaults and 'voter' in held_pos.defaults]
        return res

    def _get_contacts(self, contact_type=None, uids=None, the_objects=False):
        """ """
        res = []
        ordered_contacts = getattr(self, 'ordered_contacts', OrderedDict())
        if contact_type:
            for uid, infos in ordered_contacts.items():
                if infos[contact_type] and (not uids or uid in uids):
                    res.append(uid)
        else:
            res = uids

        if the_objects:
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(UID=res)
            res = [brain.getObject() for brain in brains]

            # keep correct order that was lost by catalog query
            def get_key(item):
                return self.ordered_contacts.keys().index(item.UID())
            res = sorted(res, key=get_key)
        return tuple(res)

    security.declarePublic('get_attendees')

    def get_attendees(self, the_objects=False):
        '''Returns the attendees in this meeting.'''
        return self._get_contacts('attendee', the_objects=the_objects)

    security.declarePublic('get_excused')

    def get_excused(self, the_objects=False):
        '''Returns the excused in this meeting.'''
        return self._get_contacts('excused', the_objects=the_objects)

    security.declarePublic('get_absents')

    def get_absents(self, the_objects=False):
        '''Returns the absents in this meeting.'''
        return self._get_contacts('absent', the_objects=the_objects)

    security.declarePublic('get_voters')

    def get_voters(self, uids=None, the_objects=False):
        '''Returns the voters in this meeting.'''
        voters = self._get_contacts('voter', uids=uids, the_objects=the_objects)
        return voters

    security.declarePublic('get_signatories')

    def get_signatories(self, the_objects=False, by_signature_number=False):
        '''See docstring in previous method.'''
        signers = self._get_contacts('signer', the_objects=the_objects)
        # order is important in case we have several same signature_number, the first win
        if the_objects:
            res = OrderedDict(
                [(signer, self.ordered_contacts[signer.UID()]['signature_number'])
                 for signer in signers])
        else:
            res = OrderedDict(
                [(signer_uid, self.ordered_contacts[signer_uid]['signature_number'])
                 for signer_uid in signers])
        if by_signature_number:
            # reverse res so when several same signature_number, the first win
            res = OrderedDict(reversed(res.items()))
            # keys are values, values are keys
            res = {v: k for k, v in res.items()}
        return dict(res)

    security.declarePublic('get_replacements')

    def get_replacements(self, the_objects=False):
        '''See docstring in previous method.'''
        replaced_uids = self._get_contacts('replacement', the_objects=the_objects)
        return {replaced_uid: self.ordered_contacts[replaced_uid]['replacement']
                for replaced_uid in replaced_uids}

    def _get_item_not_present(self, attr, by_persons=False):
        '''Return item not present (itemAbsents, itemExcused) by default the attr dict has the item UID
           as key and list of not_present as values but if 'p_by_persons' is True, the informations
           are returned with not_present held position as key and list of items as value.'''
        if by_persons:
            # values are now keys, concatenate a list of lists and remove duplicates
            keys = tuple(set(list(itertools.chain.from_iterable(attr.values()))))
            data = {}
            for key in keys:
                data[key] = [k for k, v in attr.items() if key in v]
        else:
            data = copy.deepcopy(attr.data)
        return data

    security.declarePublic('get_item_absents')

    def get_item_absents(self, by_persons=False):
        ''' '''
        return self._get_item_not_present(self.item_absents, by_persons=by_persons)

    security.declarePublic('get_item_excused')

    def get_item_excused(self, by_persons=False):
        ''' '''
        return self._get_item_not_present(self.item_excused, by_persons=by_persons)

    security.declarePublic('get_item_non_attendees')

    def get_item_non_attendees(self, by_persons=False):
        ''' '''
        return self._get_item_not_present(self.item_non_attendees, by_persons=by_persons)

    security.declarePublic('get_item_signatories')

    def get_item_signatories(self, by_signatories=False, include_position_type=False):
        '''Return itemSignatories, by default the itemSignatories dict has the item UID as key and list
           of signatories as values but if 'p_by_signatories' is True, the informations are returned with
           signatory as key and list of items as value.
           p_include_position_type=True is only relevant when p_by_signatories=False.'''
        signatories = {}
        if by_signatories:
            for item_uid, signatories_infos in self.item_signatories.items():
                for signature_number, signatory_infos in signatories_infos.items():
                    # do not keep 'position_type' from the stored itemSignatories
                    signatory_uid = signatory_infos['hp_uid']
                    if signatory_uid not in signatories:
                        signatories[signatory_uid] = []
                    signatories[signatory_uid].append(item_uid)
        else:
            for item_uid, signatory_infos in self.item_signatories.data.items():
                if include_position_type:
                    signatories[item_uid] = signatory_infos.copy()
                else:
                    signatories[item_uid] = {k: v['hp_uid'] for k, v in signatory_infos.items()}

        return signatories

    def get_signature_infos_for(self, item_uid, signatory_uid):
        """Return the signature position_type to use as label and signature_number
           for given p_item_uid and p_signatory_uid."""
        data = self.get_item_signatories(by_signatories=False, include_position_type=True)
        data = {k: v for k, v in data[item_uid].items()
                if v['hp_uid'] == signatory_uid}
        res = {}
        catalog = api.portal.get_tool('portal_catalog')
        res['signature_number'] = data.keys()[0]
        hp = catalog(UID=signatory_uid)[0].getObject()
        res['position_type'] = hp.get_label(
            forced_position_type_value=data.values()[0]['position_type'])
        return res

    security.declarePublic('get_item_votes')

    def get_item_votes(self):
        ''' '''
        votes = deepcopy(self.item_votes.data)
        return votes

    security.declarePrivate('set_item_public_vote')

    def setItemPublicVote(self, item, data, vote_number=0):
        """ """
        data = deepcopy(data)
        item_uid = item.UID()
        # set new itemVotes value on meeting
        # first votes
        if item_uid not in self.item_votes:
            self.itemVotes[item_uid] = PersistentList()
            # check if we are not adding a new vote on an item containing no votes at all
            if vote_number == 1:
                # add an empty vote 0
                data_item_vote_0 = item.get_item_votes(
                    vote_number=0,
                    include_vote_number=False,
                    include_unexisting=True)
                # make sure we use persistent for 'voters'
                data_item_vote_0['voters'] = PersistentMapping(data_item_vote_0['voters'])
                self.itemVotes[item_uid].append(PersistentMapping(data_item_vote_0))
        new_voters = data.get('voters')
        # new vote_number
        if vote_number + 1 > len(self.item_votes[item_uid]):
            # complete data before storing, if some voters are missing it is
            # because of NOT_VOTABLE_LINKED_TO_VALUE, we add it
            item_voter_uids = item.get_item_voters()
            for item_voter_uid in item_voter_uids:
                if item_voter_uid not in data['voters']:
                    data['voters'][item_voter_uid] = NOT_VOTABLE_LINKED_TO_VALUE
            self.item_votes[item_uid].append(PersistentMapping(data))
        else:
            # use update in case we only update a subset of votes
            # when some vote NOT_VOTABLE_LINKED_TO_VALUE or so
            # we have nested dicts, data is a dict, containing 'voters' dict
            self.item_votes[item_uid][vote_number]['voters'].update(data['voters'])
            data.pop('voters')
            self.item_votes[item_uid][vote_number].update(data)
        # manage linked_to_previous
        # if current vote is linked to other votes, we will set NOT_VOTABLE_LINKED_TO_VALUE
        # as value of vote of voters of other linked votes
        clean_voters_linked_to(item, self, vote_number, new_voters)

    security.declarePrivate('set_item_secret_vote')

    def set_item_secret_vote(self, item, data, vote_number):
        """ """
        data = deepcopy(data)
        item_uid = item.UID()
        # set new itemVotes value on meeting
        # first votes
        if item_uid not in self.item_votes:
            self.item_votes[item_uid] = PersistentList()
            # check if we are not adding a new vote on an item containing no votes at all
            if vote_number == 1:
                # add an empty vote 0
                data_item_vote_0 = item.get_item_votes(
                    vote_number=0,
                    include_vote_number=False,
                    include_unexisting=True)
                self.item_votes[item_uid].append(PersistentMapping(data_item_vote_0))
        # new vote_number
        if vote_number + 1 > len(self.item_votes[item_uid]):
            self.item_votes[item_uid].append(PersistentMapping(data))
        else:
            self.item_votes[item_uid][vote_number].update(data)

    security.declarePublic('display_user_replacement')

    def display_user_replacement(self,
                                 held_position_uid,
                                 include_held_position_label=True,
                                 include_sub_organizations=True):
        '''Display the user remplacement from p_held_position_uid.'''
        catalog = api.portal.get_tool('portal_catalog')
        held_position = catalog(UID=held_position_uid)[0].getObject()
        if include_held_position_label:
            return held_position.get_short_title(
                include_sub_organizations=include_sub_organizations)
        else:
            person = held_position.get_person()
            return person.get_title()

    security.declarePrivate('setDate')

    def setDate(self, value, **kwargs):
        '''Overrides the field 'date' mutator so we reindex every linked
           items if date value changed.  Moreover we manage update_item_references
           if value changed.'''
        current_date = self.getField('date').get(self, **kwargs)
        if not value == current_date:
            # add a value in the REQUEST to specify that update_item_references is needed
            self.REQUEST.set('need_Meeting_update_item_references', True)
            # store new date before updating items so items get
            # right date when calling meeting.getDate
            self.getField('date').set(self, value, **kwargs)
            catalog = api.portal.get_tool('portal_catalog')
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            # items linked to the meeting
            brains = catalog(portal_type=cfg.getItemTypeName(),
                             linkedMeetingUID=self.UID())
            # items having the meeting as the preferredMeeting
            brains = brains + catalog(portal_type=cfg.getItemTypeName(),
                                      getPreferredMeeting=self.UID())
            for brain in brains:
                item = brain.getObject()
                item.reindexObject(idxs=['linkedMeetingDate', 'getPreferredMeetingDate'])
            # clean cache for "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
            invalidate_cachekey_volatile_for(
                "Products.PloneMeeting.vocabularies.meetingdatesvocabulary", get_again=True)

    security.declarePrivate('setFirstItemNumber')

    def setFirstItemNumber(self, value, **kwargs):
        '''Overrides the field 'firstItemNumber' mutator to be able to
           update_item_references if value changed.'''
        current_first_item_number = self.getField('firstItemNumber').get(self, **kwargs)
        if not value == current_first_item_number:
            # add a value in the REQUEST to specify that update_item_references is needed
            self.REQUEST.set('need_Meeting_update_item_references', True)
        self.getField('firstItemNumber').set(self, value, **kwargs)

    security.declarePrivate('setMeetingNumber')

    def setMeetingNumber(self, value, **kwargs):
        '''Overrides the field 'meetingNumber' mutator to be able to
           update_item_references if value changed.'''
        current_meetingNumber = self.getField('meetingNumber').get(self, **kwargs)
        if not value == current_meetingNumber:
            # add a value in the REQUEST to specify that update_item_references is needed
            self.REQUEST.set('need_Meeting_update_item_references', True)
        self.getField('meetingNumber').set(self, value, **kwargs)

    security.declarePublic('showMeetingManagerReservedField')

    def showMeetingManagerReservedField(self, name):
        '''When must field named p_name be shown?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        res = not self.isTemporary() and \
            tool.isManager(self) and \
            self.attributeIsUsed(name)
        return res

    security.declarePrivate('validate_preMeetingDate')

    def validate_preMeetingDate(self, value):
        '''Checks that the preMeetingDate comes before the meeting date.'''
        if not value or not self.attributeIsUsed('preMeetingDate'):
            return
        # Get the meeting date from the request
        try:
            meetingDate = DateTime(self.REQUEST['date'])
        except DateTime.DateError:
            meetingDate = None
        except DateTime.SyntaxError:
            meetingDate = None
        # Compare meeting and pre-meeting dates
        if meetingDate and (DateTime(value) >= meetingDate):
            label = 'pre_date_after_meeting_date'
            return translate(label, domain='PloneMeeting', context=self.REQUEST)

    def get_items(self,
                  uids=[],
                  list_types=[],
                  ordered=False,
                  the_objects=True,
                  additional_catalog_query={},
                  unrestricted=False,
                  force_linked_items_query=True):
        '''Return items linked to this meeting.
        Items can be filtered depending on :
           - list of given p_uids;
           - given p_list_types;
           - returned ordered (by getItemNumber) if p_ordered is True;
           - if p_the_objects is True, MeetingItem objects are returned, else, brains are returned;
           - if p_unrestricted is True it will return every items, not checking permission;
           - if p_force_linked_items_query is True, it will call self.get_raw_query with
             same parameter and force use of query showing linked items, not displaying
             available items.
        '''
        # execute the query using the portal_catalog
        catalog = api.portal.get_tool('portal_catalog')
        catalog_query = self.get_raw_query(force_linked_items_query=force_linked_items_query)
        if list_types:
            catalog_query.append({'i': 'listType',
                                  'o': 'plone.app.querystring.operation.selection.is',
                                  'v': list_types},)
        if uids:
            catalog_query.append({'i': 'UID',
                                  'o': 'plone.app.querystring.operation.selection.is',
                                  'v': uids},)
        if ordered:
            query = queryparser.parseFormquery(
                self,
                catalog_query,
                sort_on=self.getSort_on(force_linked_items_query=force_linked_items_query))
        else:
            query = queryparser.parseFormquery(self, catalog_query)

        # append additional_catalog_query
        query.update(additional_catalog_query)
        if unrestricted:
            res = catalog.unrestrictedSearchResults(**query)
        else:
            res = catalog(**query)

        if the_objects:
            res = [brain._unrestrictedGetObject() for brain in res]
        return res

    def get_raw_items(self):
        """Simply get linked items."""
        catalog = api.portal.get_tool('portal_catalog')
        catalog_query = self.get_raw_query(force_linked_items_query=True)
        query = queryparser.parseFormquery(self, catalog_query)
        res = [brain.UID for brain in catalog.unrestrictedSearchResults(**query)]
        return res

    security.declarePublic('get_item_by_number')

    def get_item_by_number(self, number):
        '''Gets the item thas has number p_number.'''
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(linkedMeetingUID=self.UID(), getItemNumber=number)
        if not brains:
            return None
        return brains[0].getObject()

    def get_late_state(self):
        '''See doc in interfaces.py.'''
        return 'frozen'

    def _check_insert_order_cache(self, cfg):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        invalidate = False
        invalidate = not base_hasattr(meeting, '_insert_order_cache') or \
            meeting._insert_order_cache['categories_modified'] != cfg.categories.modified() or \
            meeting._insert_order_cache['plonegroup_orgs'] != get_registry_organizations()

        # check cfg attrs
        if not invalidate:
            for key in meeting._insert_order_cache.keys():
                if key.startswith('cfg_'):
                    if meeting._insert_order_cache[key] != getattr(cfg, key[4:]):
                        invalidate = True
                        break
        if invalidate:
            meeting.adapted()._init_insert_order_cache(cfg)
        return invalidate

    def _insert_order_cache_cfg_attrs(self, cfg):
        '''See doc in interfaces.py.'''
        return ['insertingMethodsOnAddItem',
                'listTypes',
                'selectablePrivacies',
                'usedPollTypes',
                'orderedAssociatedOrganizations',
                'orderedGroupsInCharge']

    def _init_insert_order_cache(self, cfg):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        meeting._insert_order_cache = PersistentMapping()
        for cfg_attr in meeting.adapted()._insert_order_cache_cfg_attrs(cfg):
            key = 'cfg_{0}'.format(cfg_attr)
            value = deepcopy(getattr(cfg, cfg_attr))
            meeting._insert_order_cache[key] = value
        meeting._insert_order_cache['categories_modified'] = cfg.categories.modified()
        meeting._insert_order_cache['plonegroup_orgs'] = get_registry_organizations()
        meeting._insert_order_cache['items'] = PersistentMapping()

    def _invalidate_insert_order_cache_for(self, item):
        '''Invalidate cache for given p_item.'''
        item_uid = item.UID()
        if base_hasattr(self, '_insert_order_cache') and \
           self._insert_order_cache['items'].get(item_uid, None) is not None:
            del self._insert_order_cache['items'][item_uid]

    def get_item_insert_order(self, item, cfg, check_cache=True):
        '''Get p_item insertOrder taking cache into account.'''
        # check if cache still valid, will be invalidated if not
        if check_cache:
            self.adapted()._check_insert_order_cache(cfg)
        insert_order = self._insert_order_cache['items'].get(item.UID(), None)
        if insert_order is None or not isinstance(insert_order, list):
            insert_order = item.adapted()._getInsertOrder(cfg)
            self._insert_order_cache['items'][item.UID()] = insert_order
        return insert_order

    security.declareProtected(ModifyPortalContent, 'insert_item')

    def insert_item(self, item, force_normal=False):
        '''Inserts p_item into my list of "normal" items or my list of "late"
           items. If p_force_normal is True, and the item should be inserted as
           a late item, it is nevertheless inserted as a normal item.'''
        # First, determine if we must insert the item into the "normal"
        # list of items or to the list of "late" items. Note that I get
        # the list of items *in order* in the case I need to insert the item
        # at another place than at the end.
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        is_late = not force_normal and item.wfConditions().isLateFor(self)
        if is_late:
            item.setListType(item.adapted().getListTypeLateValue(self))
            to_discuss_value = cfg.getToDiscussLateDefault()
        else:
            item.setListType(item.adapted().getListTypeNormalValue(self))
            to_discuss_value = cfg.getToDiscussDefault()
        items = self.get_items(ordered=True)
        # Set the correct value for the 'toDiscuss' field if required
        if cfg.getToDiscussSetOnItemInsert():
            item.setToDiscuss(to_discuss_value)
        # At what place must we insert the item in the list ?
        insert_methods = cfg.getInsertingMethodsOnAddItem()
        # wipe out insert methods as stored value is a DataGridField
        # and we only need a tuple of insert methods
        insert_at_the_end = False
        if insert_methods[0]['insertingMethod'] != 'at_the_end':
            # We must insert it according to category or proposing group order
            # (at the end of the items belonging to the same category or
            # proposing group). We will insert the p_item just before the first
            # item whose category/group immediately follows p_item's category/
            # group (or at the end if inexistent). Note that the MeetingManager,
            # in subsequent manipulations, may completely change items order.
            self.adapted()._check_insert_order_cache(cfg)
            item_order = self.get_item_insert_order(item, cfg, check_cache=False)
            higher_item_found = False
            insert_index = 0  # That's where I will insert the item
            insert_index_is_subnumber = False
            for an_item in items:
                if higher_item_found:
                    item_number = an_item.getItemNumber()
                    # Ok I already know where to insert the item. I just
                    # continue to visit the next items in order to increment their number.
                    # we inserted an integer numer, we need to add '1' to every next items
                    if not insert_index_is_subnumber:
                        an_item.setItemNumber(item_number + 100)
                    elif (insert_index_is_subnumber and
                          _use_same_integer(item_number, insert_index) and
                          item_number > insert_index):
                        # we inserted a subnumber, we need to update subnumber of same integer
                        an_item.setItemNumber(item_number + 1)
                elif self.get_item_insert_order(an_item, cfg, check_cache=False) > item_order:
                    higher_item_found = True
                    item_number = an_item.getItemNumber()
                    insert_index = item_number
                    # we will only update next items of same subnumber?
                    insert_index_is_subnumber = not _is_integer(item_number)
                    an_item.setItemNumber(item_number + _compute_value_to_add(item_number))

            if higher_item_found:
                item.setItemNumber(insert_index)
            else:
                insert_at_the_end = True

        if insert_methods[0]['insertingMethod'] == 'at_the_end' or insert_at_the_end:
            # insert it as next integer number
            if items:
                item.setItemNumber(_to_integer(items[-1].getItemNumber()) + 100)
            else:
                # first added item
                item.setItemNumber(100)

        # Add the item at the end of the items list
        item._update_meeting_link(meeting_uid=self.UID())
        self._finalize_item_insert(items_to_update=[item])

    def _finalize_item_insert(self, items_to_update=[]):
        """ """
        # invalidate RAMCache for MeetingItem.getMeeting
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')
        # reindex getItemNumber when item is in the meeting or getItemNumber returns None
        # and reindex linkedMeeting indexes that is used by update_item_references using getItems
        lowest_item_number = 0
        for item in items_to_update:
            item_number = item.getRawItemNumber()
            if not lowest_item_number or item_number < lowest_item_number:
                lowest_item_number = item_number
            item.reindexObject(idxs=['getItemNumber',
                                     'listType',
                                     'linkedMeetingUID',
                                     'linkedMeetingDate'])
        # meeting is considered modified, do this before update_item_references
        self.notifyModified()

        # update itemReference after 'getItemNumber' has been reindexed of item and
        # items with a higher itemNumber
        self.update_item_references(start_number=lowest_item_number)

    security.declareProtected(ModifyPortalContent, 'remove_item')

    def remove_item(self, item):
        '''Removes p_item from me.'''
        # Remember the item number now; once the item will not be in the meeting
        # anymore, it will loose its number.
        item_number = item.getItemNumber()
        items = self.get_items()
        try:
            item._update_meeting_link(meeting_uid=None)
            items.remove(item)
            # set listType back to 'normal' if it was late
            # if it is another value (custom), we do not change it
            if item.getListType() == 'late':
                item.setListType('normal')
        except ValueError:
            # in case this is called by onItemRemoved, the item
            # does not exist anymore and is no more in the items list
            # so we pass
            pass

        # remove item UID from self.itemAbsents/self.itemExcused and self.itemSignatories
        item_uid = item.UID()
        if item_uid in self.item_absents:
            del self.item_absents[item_uid]
        if item_uid in self.item_excused:
            del self.item_excused[item_uid]
        if item_uid in self.item_non_attendees:
            del self.item_non_attendees[item_uid]
        if item_uid in self.item_signatories:
            del self.item_signatories[item_uid]
        if item_uid in self.item_votes:
            del self.item_votes[item_uid]

        # remove item UID from _insert_order_cache
        self._invalidate_insert_order_cache_for(item)

        # make sure item assembly/signatures related fields are emptied
        for field in item.Schema().filterFields(isMetadata=False):
            if field.getName().startswith('itemAssembly') or field.getName() == 'itemSignatures':
                field.set(item, '')

        # Update item numbers
        # in case itemNumber was a subnumber (or a master having subnumber),
        # we will just update subnumbers of the same integer
        item_number_is_subnumber = not _is_integer(item_number) or \
            bool(self.get_item_by_number(item_number + 1))
        for an_item in items:
            an_item_number = an_item.getItemNumber()
            if an_item_number > item_number:
                if not item_number_is_subnumber:
                    an_item.setItemNumber(an_item.getItemNumber() - 100)
                elif item_number_is_subnumber and _use_same_integer(item_number, an_item_number):
                    an_item.setItemNumber(an_item.getItemNumber() -
                                          _compute_value_to_add(an_item_number))
        # invalidate RAMCache for MeetingItem.getMeeting
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')

        # reindex relevant indexes now that item is removed
        item.reindexObject(idxs=['listType', 'linkedMeetingUID', 'linkedMeetingDate'])

        # meeting is considered modified, do this before update_item_references
        self.notifyModified()

        # update itemReference of item that is no more linked to self and so that will not
        # be updated by Meeting.update_item_references and then update items that used
        # a higher item number
        item.update_item_reference()
        self.update_item_references(start_number=item_number)

    def update_item_references(self, start_number=0, check_needed=False):
        """Update reference of every contained items, if p_start_number is given,
           we update items starting from p_start_number itemNumber.
           By default, if p_start_number=0, every linked items will be updated.
           If p_check_needed is True, we check if value 'need_Meeting_update_item_references'
           in REQUEST is True."""
        # call to update_item_references may be deferred for optimization
        if self.REQUEST.get('defer_Meeting_update_item_references', False):
            return
        if check_needed and not self.REQUEST.get('need_Meeting_update_item_references', False):
            return
        # force disable 'need_Meeting_update_item_references' from REQUEST
        self.REQUEST.set('need_Meeting_update_item_references', False)

        # we query items from start_number to last item of the meeting
        # moreover we get_items unrestricted to be sure we have every elements
        brains = self.get_items(
            ordered=True,
            the_objects=False,
            unrestricted=True,
            additional_catalog_query={
                'getItemNumber': {'query': start_number,
                                  'range': 'min'}, })
        for brain in brains:
            item = brain._unrestrictedGetObject()
            item.update_item_reference()

    security.declarePrivate('getDefaultAssembly')

    def getDefaultAssembly(self):
        if self.attributeIsUsed('assembly'):
            tool = api.portal.get_tool('portal_plonemeeting')
            return tool.getMeetingConfig(self).getAssembly()
        return ''

    security.declarePrivate('getDefaultAssemblyStaves')

    def getDefaultAssemblyStaves(self):
        if self.attributeIsUsed('assemblyStaves'):
            tool = api.portal.get_tool('portal_plonemeeting')
            return tool.getMeetingConfig(self).getAssemblyStaves()
        return ''

    security.declarePrivate('getDefaultSignatures')

    def getDefaultSignatures(self):
        if self.attributeIsUsed('signatures'):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            return cfg.getSignatures()
        return ''

    security.declarePrivate('update_title')

    def update_title(self):
        '''The meeting title is generated by this method, based on the meeting date.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        title = self.title
        formatted_date = tool.format_date(self.date)
        if title != formatted_date:
            self.setTitle(formatted_date)
            return True

    security.declarePrivate('update_place')

    def update_place(self):
        '''Updates the place if it comes from special request field
           "place_other".'''
        rq = self.REQUEST
        if ('place' not in rq) or (rq.get('place', '') == 'other'):
            stored_place = self.place
            new_place = rq.get('place_other', '')
            if stored_place != new_place:
                self.place = new_place
                return True

    security.declarePrivate('compute_dates')

    def compute_dates(self):
        '''Computes, for this meeting, the dates which are derived from the
           meeting date when relevant.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        used_attrs = cfg.getUsedMeetingAttributes()
        # Initialize the effective start date with the meeting date
        if 'start_date' in used_attrs:
            self.start_date(self.date)
        # Set, by default, mid date to start date + 1 hour.
        if 'mid_date' in used_attrs:
            self.mid_date = self.date + timedelta(hours=1)
        # Set, by default, end date to start date + 2 hours.
        if 'end_date' in used_attrs:
            self.end_date = self.date + timedelta(hours=2)
        if 'pre_meeting_date' in used_attrs and not self.pre_meeting_date:
            # Compute the date for the pre-meeting
            delta = cfg.getPreMeetingDateDefault()
            if not delta.strip() in ('', '0',):
                self.pre_meeting_date = self.date - timedelta(hours=int(delta))

    security.declarePublic('get_user_replacements')

    def get_user_replacements(self):
        '''Gets the dict storing user replacements.'''
        res = {}
        ordered_contacts = getattr(self, 'ordered_contacts', OrderedDict())
        for uid, infos in ordered_contacts.items():
            if infos['replacement']:
                res[uid] = infos['replacement']
        return res

    def _do_update_contacts(self,
                            attendees=OrderedDict(),
                            signatories={},
                            replacements={},
                            voters=[]):
        ''' '''
        # attendees must be an OrderedDict to keep order
        if not isinstance(attendees, OrderedDict):
            raise ValueError(
                'Parameter attendees passed to Meeting._do_update_contacts '
                'must be an OrderedDict !!!')
        # save the ordered contacts so we rely on this, especially when
        # users are disabled in the configuration
        self.ordered_contacts.clear()

        for attendee_uid, attendee_type in attendees.items():
            if attendee_uid not in self.ordered_contacts:
                self.ordered_contacts[attendee_uid] = \
                    {'attendee': False,
                     'excused': False,
                     'absent': False,
                     'signer': False,
                     'signature_number': None,
                     'replacement': None,
                     'voter': False}
            self.ordered_contacts[attendee_uid][attendee_type] = True

        for signatory_uid, signature_number in signatories.items():
            self.ordered_contacts[signatory_uid]['signer'] = True
            self.ordered_contacts[signatory_uid]['signature_number'] = signature_number

        for replaced_uid, replacer_uid in replacements.items():
            self.ordered_contacts[replaced_uid]['replacement'] = replacer_uid

        for voter_uid in voters:
            self.ordered_contacts[voter_uid]['voter'] = True

        self._p_changed = True

    security.declarePrivate('update_contacts')

    def update_contacts(self):
        '''After a meeting has been created or edited, we update here the info
           related to contacts implied in the meeting: attendees, excused,
           absents, signatories, replacements, ...'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)

        if not cfg.isUsingContacts():
            return

        # attendees, excused, absents
        meeting_attendees = self.REQUEST.get('meeting_attendees', [])
        # remove leading muser_ and return a list of tuples, position_uid, attendee_type
        attendees = OrderedDict()
        for key in meeting_attendees:
            # remove leading muser_
            prefix, position_uid, attendee_type = key.split('_')
            attendees[position_uid] = attendee_type

        # signatories, remove ''
        meeting_signatories = [
            signatory for signatory in self.REQUEST.get('meeting_signatories', []) if signatory]
        signatories = {}
        for key in meeting_signatories:
            signatory, signature_number = key.split('__signaturenumber__')
            signatories[signatory] = signature_number

        # replacements, remove ''
        meeting_replacements = [
            replacer for replacer in self.REQUEST.get('meeting_replacements', []) if replacer]
        replacements = {}
        for key in meeting_replacements:
            replaced, replacer = key.split('__replacedby__')
            replacements[replaced] = replacer

        # voters
        meeting_voters = self.REQUEST.get('meeting_voters', [])
        # remove leading muser_ and return a list of tuples, position_uid, attendee_type
        voters = []
        for key in meeting_voters:
            # remove leading muser_ and ending _voter
            prefix, position_uid, suffix = key.split('_')
            voters.append(position_uid)

        self._do_update_contacts(attendees, signatories, replacements, voters)

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self):
        ''' '''
        # place to store item absents
        self.itemAbsents = PersistentMapping()
        # place to store item excused
        self.itemExcused = PersistentMapping()
        # place to store item non attendees
        self.itemNonAttendees = PersistentMapping()
        # place to store item signatories
        self.itemSignatories = PersistentMapping()
        # place to store item votes
        self.itemVotes = PersistentMapping()
        # place to store attendees when using contacts
        self.orderedContacts = OrderedDict()
        self.updateTitle()
        self.updatePlace()
        self.computeDates()
        # Update contact-related info (attendees, signatories, replacements...)
        self.updateContacts()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        self.setMeetingConfigVersion(cfg.getConfigVersion())
        # addRecurringItemsIfRelevant(self, '_init_')
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        self.updateLocalRoles()
        # activate the faceted navigation
        enableFacetedDashboardFor(self,
                                  xmlpath=os.path.dirname(__file__) +
                                  '/faceted_conf/default_dashboard_widgets.xml')
        self.setLayout('meeting_view')
        # update every items itemReference if needed
        self.update_item_references(check_needed=True)
        # invalidate last meeting modified
        invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.modified', get_again=True)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()

    def _update_after_edit(self, idxs=['*']):
        """Convenience method that make sure ObjectModifiedEvent is called.
           We also call reindexObject here so we avoid multiple reindexation.
           This is called when we change something on an element without
           tiggering too much things."""
        notifyModifiedAndReindex(self, extra_idxs=idxs, notify_event=True)

    def update_local_roles(self, **kwargs):
        """Update various local roles."""
        # remove every localRoles then recompute
        old_local_roles = self.__ac_local_roles__.copy()
        self.__ac_local_roles__.clear()
        # add 'Owner' local role
        self.manage_addLocalRoles(self.owner_info()['id'], ('Owner',))
        # Update every 'power observers' local roles given to the
        # corresponding MeetingConfig.powerObsevers
        # it is done on every edit because of 'meeting_access_on' TAL expression
        self._update_power_observers_local_roles()
        _addManagedPermissions(self)
        # notify that localRoles have been updated
        notify(MeetingLocalRolesUpdatedEvent(self, old_local_roles))
        # not really necessary here but easier
        # update annexes categorized_elements to store 'visible_for_groups'
        updateAnnexesAccess(self)
        # reindex object security except if avoid_reindex=True and localroles are the same
        avoid_reindex = kwargs.get('avoid_reindex', False)
        if not avoid_reindex or old_local_roles != self.__ac_local_roles__:
            self.reindexObjectSecurity()

    def _update_power_observers_local_roles(self):
        '''Give local roles to the groups defined in MeetingConfig.powerObservers.'''
        extra_expr_ctx = _base_extra_expr_ctx(self)
        extra_expr_ctx.update({'meeting': self, })
        cfg = extra_expr_ctx['cfg']
        cfg_id = cfg.getId()
        meeting_state = self.query_state()
        for po_infos in cfg.getPowerObservers():
            if meeting_state in po_infos['meeting_states'] and \
               _evaluateExpression(self,
                                   expression=po_infos['meeting_access_on'],
                                   extra_expr_ctx=extra_expr_ctx):
                power_observers_group_id = "%s_%s" % (cfg_id, po_infos['row_id'])
                self.manage_addLocalRoles(power_observers_group_id,
                                          (READER_USECASES['powerobservers'],))

    security.declarePublic('wfConditions')

    def wfConditions(self):
        '''Returns the adapter that implements the interface that proposes
           methods for use as conditions in the workflow associated with this
           meeting.'''
        return getWorkflowAdapter(self, conditions=True)

    security.declarePublic('wfActions')

    def wfActions(self):
        '''Returns the adapter that implements the interface that proposes
           methods for use as actions in the workflow associated with this
           meeting.'''
        return getWorkflowAdapter(self, conditions=False)

    security.declarePublic('adapted')

    def adapted(self):
        '''Gets the "adapted" version of myself. If no custom adapter is found,
           this method returns me.'''
        return getCustomAdapter(self)

    security.declarePublic('hasHistory')

    def hasHistory(self, fieldName=None):
        '''See doc in utils.py.'''
        return hasHistory(self, fieldName)

    security.declarePublic('attributeIsUsed')

    def attributeIsUsed(self, name):
        '''Is the attribute named p_name used in this meeting config ?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        meetingConfig = tool.getMeetingConfig(self)
        return (name in meetingConfig.getUsedMeetingAttributes())

    def query_state_cachekey(method, self):
        '''cachekey method for self.query_state.'''
        return self.workflow_history

    security.declarePublic('query_state')

    @ram.cache(query_state_cachekey)
    def query_state(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    security.declarePublic('getSelf')

    def getSelf(self):
        '''Similar to MeetingItem.getSelf. Check MeetingItem.py for more
           info.'''
        res = self
        if self.__class__.__name__ != 'Meeting':
            res = self.context
        return res

    security.declarePublic('getFieldVersion')

    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePublic('is_decided')

    def is_decided(self):
        meeting = self.getSelf()
        return meeting.query_state() in ('decided', 'closed', 'decisions_published', )

    security.declarePublic('getSpecificMailContext')

    def getSpecificMailContext(self, event, translationMapping):
        '''See doc in interfaces.py.'''
        return None

    security.declarePublic('includeMailRecipient')

    def includeMailRecipient(self, event, userId):
        '''See doc in interfaces.py.'''
        return True

    def add_recurring_items_if_relevant(self, transition):
        '''Sees in the meeting config linked to p_meeting if the triggering of
           p_transition must lead to the insertion of some recurring items in
           p_meeting.'''
        rec_items = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for item in cfg.getRecurringItems():
            if item.getMeetingTransitionInsertingMe() == transition:
                rec_items.append(item)
        if rec_items:
            self.add_recurring_items(rec_items)

    security.declarePrivate('add_recurring_items')

    def add_recurring_items(self, recurring_items):
        '''Inserts into this meeting some p_recurring_items.
           The newly created items are copied from recurring items
           (contained in the meeting config) to the folder containing
           this meeting.'''
        dest_folder = self.aq_inner.aq_parent
        new_items = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for recurring_item in recurring_items:
            new_items.append(recurring_item.clone(
                cloneEventAction='Add recurring item',
                destFolder=dest_folder,
                keepProposingGroup=True,
                newPortalType=cfg.getItemTypeName()))
        for new_item in new_items:
            # Put the new item in the correct state
            adapted = new_item.adapted()
            error = adapted.addRecurringItemToMeeting(self)
            if not error:
                notify(ItemDuplicatedFromConfigEvent(new_item, 'as_recurring_item'))
                new_item.reindexObject()

    security.declarePublic('fieldIsEmpty')

    def fieldIsEmpty(self, name):
        '''Is field named p_name empty ?'''
        return fieldIsEmpty(name, self)

    security.declarePublic('number_of_items')

    def number_of_items(self):
        '''How much items in this meeting ?'''
        return str(len(self.get_raw_items()))

    security.declarePublic('show_attendees_fields')

    def show_attendees_fields(self):
        '''Display attendee related fields in view/edit?'''
        return (self.attribute_is_used('attendees') or
                self.get_attendees()) and not self.assembly

    def shown_assembly_fields_cachekey(method, self):
        '''cachekey method for self.shown_assembly_fields.'''
        # do only re-compute if cfg changed or self.changed
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return (cfg.getId(), cfg._p_mtime, self.modified())

    security.declarePublic('shown_assembly_fields')

    @ram.cache(shown_assembly_fields_cachekey)
    def shown_assembly_fields(self):
        '''Return the list of shown assembly field :
           - used assembly fields;
           - not empty assembly fields.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        used_attrs = cfg.getUsedMeetingAttributes()
        # get assembly fields
        fields = cfg._assembly_fields(field_name=False)
        return [field.getName() for field in fields
                if field.getName() in used_attrs or field.get(self)]

    security.declarePublic('show_signatures')

    def show_signatures(self):
        '''Show the 'signatures' field?'''
        return self.attribute_is_used('signatures') or self.get_signatures()

    security.declarePublic('show_votes_observations')

    def show_votes_observations(self):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        res = tool.isManager(meeting)
        if not res:
            cfg = tool.getMeetingConfig(meeting)
            res = tool.isPowerObserverForCfg(cfg) or \
                meeting.adapted().is_decided()
        return res

    security.declarePublic('show_votes')

    def show_votes(self):
        '''See doc in interfaces.py.'''
        res = False
        meeting = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        if cfg.getUseVotes() or meeting.get_voters():
            res = True
        return res

    security.declarePublic('get_previous_meeting')

    def get_previous_meeting(self, interval=60):
        '''Gets the previous meeting based on meeting date. We only search among
           meetings in the previous p_interval, which is a number
           of days. If no meeting is found, the method returns None.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meeting_type_name = cfg.getMeetingTypeName()
        catalog = api.portal.get_tool('portal_catalog')
        # find every meetings before searchMeetingsInterval days before self
        brains = catalog(portal_type=meeting_type_name,
                         meeting_date={'query': self.date - timedelta(days=interval),
                                       'range': 'min'},
                         sort_on='meeting_date',
                         sort_order='reverse')
        res = None
        for brain in brains:
            meeting = brain.getObject()
            if meeting.date < self.date:
                res = meeting
                break
        return res

    security.declarePublic('get_next_meeting')

    def get_next_meeting(self, cfg_id='', date_gap=0):
        '''Gets the next meeting based on meeting date.
           p_cfg can be used to compare meetings from another meetingconfig
           with meeting from the current config.
           p_dateGap is the number of 'dead days' following the date of
           the current meeting in which we do not look for next meeting'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not cfg_id:
            cfg = tool.getMeetingConfig(self)
        else:
            cfg = getattr(tool, cfg_id)
        return get_next_meeting(meeting_date=self.date, cfg=cfg, date_gap=date_gap)

    security.declarePublic('show_insert_or_remove_selected_items_action')

    def show_insert_or_remove_selected_items_action(self):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        member = api.user.get_current()
        return bool(member.has_permission(ModifyPortalContent, meeting) and
                    not meeting.query_state() in meeting.MEETINGCLOSEDSTATES)

    security.declarePublic('getLabelAssembly')

    def getLabelAssembly(self):
        '''
          Depending on the fact that we use 'assembly' alone or
          'assembly, excused, absents', we will translate the 'assembly' label
          a different way.
        '''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'assemblyExcused' in usedMeetingAttributes or \
           'assemblyAbsents' in usedMeetingAttributes:
            return _('PloneMeeting_label_attendees')
        else:
            return _('meeting_assembly')


class MeetingSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IMeeting, )
