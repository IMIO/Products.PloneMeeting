# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_plone_groups
from collective.dexteritytextindexer.directives import searchable
from collective.dexteritytextindexer.interfaces import IDynamicTextIndexExtender
from collective.z3cform.datagridfield import BlockDataGridFieldFactory
from collective.z3cform.datagridfield import DictRow
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import richtextval
from imio.helpers.content import uuidsToObjects
from imio.helpers.content import uuidToCatalogBrain
from imio.helpers.content import uuidToObject
from imio.helpers.security import fplog
from imio.prettylink.interfaces import IPrettyLink
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.contenttypes.behaviors.collection import Collection
from plone.app.contenttypes.behaviors.collection import ICollection
from plone.app.querystring.querybuilder import queryparser
from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form
from plone.formwidget.datetime.z3cform.widget import DateFieldWidget
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget
from plone.formwidget.masterselect import MasterSelectField
from plone.memoize import ram
from plone.supermodel import model
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.itemchangeorder import _compute_value_to_add
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.browser.itemchangeorder import _to_integer
from Products.PloneMeeting.browser.itemchangeorder import _use_same_integer
from Products.PloneMeeting.browser.itemvotes import clean_voters_linked_to
from Products.PloneMeeting.config import MEETING_ATTENDEES_ATTRS
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.config import REINDEX_NEEDED_MARKER
from Products.PloneMeeting.interfaces import IDXMeetingContent
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import _get_category
from Products.PloneMeeting.utils import displaying_available_items
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_attendee_short_title
from Products.PloneMeeting.utils import get_next_meeting
from Products.PloneMeeting.utils import get_states_before
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getDateFromDelta
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import ItemDuplicatedFromConfigEvent
from Products.PloneMeeting.utils import MeetingLocalRolesUpdatedEvent
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.utils import validate_item_assembly_value
from Products.PloneMeeting.widgets.pm_orderedselect import PMOrderedSelectFieldWidget
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from Products.PloneMeeting.widgets.pm_textarea import get_textarea_value
from Products.PloneMeeting.widgets.pm_textarea import PMTextAreaFieldWidget
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import directlyProvides
from zope.interface import implementer
from zope.interface import implements
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from zope.schema import getFieldNamesInOrder
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.schema.interfaces import ITokenizedTerm
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary

import itertools
import logging


logger = logging.getLogger('PloneMeeting')

PLACE_OTHER = u"other"


def assembly_constraint(value):
    """Check that opening [[ has it's closing ]]."""
    value = value and value.output
    if not validate_item_assembly_value(value):
        request = getRequest()
        msg = translate('Please check that opening "[[" have corresponding closing "]]".',
                        domain='PloneMeeting',
                        context=request)
        # encode msg in utf-8 for restapi
        raise Invalid(msg.encode('utf-8'))
    return True


class ICommitteesRowSchema(Interface):
    """Schema for DataGridField widget's row of field 'committees'."""

    row_id = schema.Choice(
        title=_("title_committees_row_id"),
        vocabulary='Products.PloneMeeting.vocabularies.meeting_selectable_committees_vocabulary',
        required=True)

    form.widget('date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    date = schema.Datetime(
        title=_("title_committees_date"),
        required=False)

    form.widget('convocation_date', DateFieldWidget, show_today_link=True)
    convocation_date = schema.Date(
        title=_("title_committees_convocation_date"),
        required=False)

    place = schema.TextLine(
        title=_("title_committees_place"),
        required=False)

    form.widget('assembly', PMTextAreaFieldWidget)
    assembly = RichText(
        title=_(u"title_committees_assembly"),
        default_mime_type='text/plain',
        allowed_mime_types=("text/plain", ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('signatures', PMTextAreaFieldWidget)
    signatures = RichText(
        title=_(u"title_committees_signatures"),
        default_mime_type='text/plain',
        allowed_mime_types=("text/plain", ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('attendees', PMOrderedSelectFieldWidget)
    attendees = schema.List(
        title=_("title_committees_attendees"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.selectable_committee_attendees_vocabulary"),
        required=False)

    form.widget('signatories', PMOrderedSelectFieldWidget)
    signatories = schema.List(
        title=_("title_committees_signatories"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.selectable_committee_attendees_vocabulary"),
        required=False)

    # called "committee_observations" because "observations" already exists on meeting class
    committee_observations = RichText(
        title=_(u"title_committees_committee_observations"),
        required=False,
        allowed_mime_types=(u"text/html", ))


class IMeeting(IDXMeetingContent):
    """
        Meeting schema
    """

    # manage title, hidden but indexed
    searchable("title")
    form.omitted('title')
    title = schema.TextLine(
        title=_(u'title_title'),
        required=False)

    form.widget('date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    date = schema.Datetime(
        title=_(u'title_date'),
        required=True)

    form.widget('start_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    start_date = schema.Datetime(
        title=_(u'title_start_date'),
        required=False)

    form.widget('mid_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    mid_date = schema.Datetime(
        title=_(u'title_mid_date'),
        required=False)

    form.widget('mid_start_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    mid_start_date = schema.Datetime(
        title=_(u'title_mid_start_date'),
        required=False)

    form.widget('end_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    end_date = schema.Datetime(
        title=_(u'title_end_date'),
        required=False)

    form.widget('approval_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    approval_date = schema.Datetime(
        title=_(u'title_approval_date'),
        required=False)

    form.widget('convocation_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    convocation_date = schema.Datetime(
        title=_(u'title_convocation_date'),
        required=False)

    form.widget('validation_deadline', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    validation_deadline = schema.Datetime(
        title=_(u'title_validation_deadline'),
        required=False)

    form.widget('freeze_deadline', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    freeze_deadline = schema.Datetime(
        title=_(u'title_freeze_deadline'),
        required=False)

    searchable("place")
    place = MasterSelectField(
        title=_(u"title_place"),
        vocabulary="Products.PloneMeeting.content.meeting.places_vocabulary",
        # avoid a "No value" entry
        required=True,
        default=PLACE_OTHER,
        slave_fields=(
            {'name': 'place_other',
             'slaveID': '#form-widgets-place_other',
             'action': 'enable',
             'hide_values': (PLACE_OTHER, ),
             'siblings': True,
             },
            {'name': 'place_other',
             'slaveID': '#form-widgets-place_other',
             'action': 'show',
             'hide_values': (PLACE_OTHER, ),
             'siblings': True,
             },
        ),
    )

    searchable("place_other")
    place_other = schema.TextLine(
        title=_(u"title_place_other"),
        required=False)

    form.widget('pre_meeting_date', DatetimeFieldWidget, show_today_link=True, show_time=True, first_day=1)
    pre_meeting_date = schema.Datetime(
        title=_(u'title_pre_meeting_date'),
        required=False)

    searchable("pre_meeting_place")
    pre_meeting_place = schema.TextLine(
        title=_(u"title_pre_meeting_place"),
        required=False)

    category = schema.Choice(
        title=_(u'title_category'),
        vocabulary="Products.PloneMeeting.vocabularies.meeting_categories_vocabulary",
        required=False,
    )

    form.widget('videoconference', RadioFieldWidget)
    videoconference = schema.Bool(
        title=_(u'title_videoconference'),
        default=False,
        required=False)

    form.widget('adopts_next_agenda_of', CheckBoxFieldWidget, multiple='multiple')
    adopts_next_agenda_of = schema.List(
        title=_("title_adopts_next_agenda_of"),
        value_type=schema.Choice(
            vocabulary="Products.PloneMeeting.vocabularies.other_mcs_clonable_to_vocabulary"),
        required=False)

    form.widget('extraordinary_session', RadioFieldWidget)
    extraordinary_session = schema.Bool(
        title=_(u'title_extraordinary_session'),
        default=False,
        required=False)

    form.widget('assembly', PMTextAreaFieldWidget)
    assembly = RichText(
        title=_(u"title_assembly"),
        description=_("descr_assembly"),
        default_mime_type='text/plain',
        allowed_mime_types=('text/plain', ),
        output_mime_type='text/x-html-safe',
        constraint=assembly_constraint,
        required=False)

    form.widget('assembly_excused', PMTextAreaFieldWidget)
    assembly_excused = RichText(
        title=_(u"title_assembly_excused"),
        default_mime_type='text/plain',
        allowed_mime_types=('text/plain', ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('assembly_absents', PMTextAreaFieldWidget)
    assembly_absents = RichText(
        title=_(u"title_assembly_absents"),
        default_mime_type='text/plain',
        allowed_mime_types=('text/plain', ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('assembly_guests', PMTextAreaFieldWidget)
    assembly_guests = RichText(
        title=_(u"title_assembly_guests"),
        default_mime_type='text/plain',
        allowed_mime_types=('text/plain', ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('assembly_proxies', PMTextAreaFieldWidget)
    assembly_proxies = RichText(
        title=_(u"title_assembly_proxies"),
        default_mime_type='text/plain',
        allowed_mime_types=('text/plain', ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('assembly_staves', PMTextAreaFieldWidget)
    assembly_staves = RichText(
        title=_(u"title_assembly_staves"),
        default_mime_type='text/plain',
        allowed_mime_types=('text/plain', ),
        output_mime_type='text/x-html-safe',
        required=False)

    form.widget('signatures', PMTextAreaFieldWidget)
    signatures = RichText(
        title=_(u"title_signatures"),
        default_mime_type='text/plain',
        allowed_mime_types=("text/plain", ),
        output_mime_type='text/x-html-safe',
        required=False)

    searchable("assembly_observations")
    form.widget('assembly_observations', PMRichTextFieldWidget)
    assembly_observations = RichText(
        title=_(u"title_assembly_observations"),
        description=_("descr_field_vieawable_by_everyone"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    form.widget('committees',
                BlockDataGridFieldFactory,
                allow_reorder=True,
                auto_append=False,
                display_table_css_class="listing datagridwidget-table-view")
    committees = schema.List(
        title=_(u'title_committees'),
        required=False,
        value_type=DictRow(
            schema=ICommitteesRowSchema,
            required=False))

    searchable("committees_observations")
    form.widget('committees_observations', PMRichTextFieldWidget)
    committees_observations = RichText(
        title=_(u"title_committees_observations"),
        description=_("descr_field_vieawable_by_everyone"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("in_and_out_moves")
    form.widget('in_and_out_moves', PMRichTextFieldWidget)
    in_and_out_moves = RichText(
        title=_(u"title_in_and_out_moves"),
        description=_("descr_field_reserved_to_meeting_managers"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("notes")
    form.widget('notes', PMRichTextFieldWidget)
    notes = RichText(
        title=_(u"title_notes"),
        description=_("descr_field_reserved_to_meeting_managers"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("pre_observations")
    form.widget('pre_observations', PMRichTextFieldWidget)
    pre_observations = RichText(
        title=_(u"title_pre_observations"),
        description=_("descr_field_vieawable_by_everyone"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("observations")
    form.widget('observations', PMRichTextFieldWidget)
    observations = RichText(
        title=_(u"title_observations"),
        description=_("descr_field_vieawable_by_everyone"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("votes_observations")
    form.widget('votes_observations', PMRichTextFieldWidget)
    votes_observations = RichText(
        title=_(u"title_votes_observations"),
        description=_("descr_field_vieawable_by_everyone_once_meeting_decided"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("public_meeting_observations")
    form.widget('public_meeting_observations', PMRichTextFieldWidget)
    public_meeting_observations = RichText(
        title=_(u"title_public_meeting_observations"),
        description=_("descr_field_vieawable_by_everyone"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("secret_meeting_observations")
    form.widget('secret_meeting_observations', PMRichTextFieldWidget)
    secret_meeting_observations = RichText(
        title=_(u"title_secret_meeting_observations"),
        description=_("descr_field_reserved_to_meeting_managers"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("authority_notice")
    form.widget('authority_notice', PMRichTextFieldWidget)
    authority_notice = RichText(
        title=_(u"title_authority_notice"),
        description=_("descr_field_reserved_to_meeting_managers"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    searchable("meetingmanagers_notes")
    form.widget('meetingmanagers_notes', PMRichTextFieldWidget)
    meetingmanagers_notes = RichText(
        title=_(u"title_meetingmanagers_notes"),
        description=_("descr_field_reserved_to_meeting_managers"),
        required=False,
        allowed_mime_types=(u"text/html", ))

    meeting_number = schema.Int(
        title=_(u"title_meeting_number"),
        description=_("descr_config_field_reserved_to_meeting_managers"),
        default=-1,
        required=False)

    first_item_number = schema.Int(
        title=_(u"title_first_item_number"),
        description=_("descr_config_field_reserved_to_meeting_managers"),
        default=-1,
        required=False)

    model.fieldset('dates_and_data',
                   label=_(u"fieldset_dates_and_data"),
                   fields=['date', 'start_date', 'mid_date',
                           'mid_start_date', 'end_date',
                           'approval_date', 'convocation_date',
                           'validation_deadline', 'freeze_deadline',
                           'place', 'place_other', 'category',
                           'videoconference', 'adopts_next_agenda_of',
                           'pre_meeting_date', 'pre_meeting_place',
                           'extraordinary_session'])

    model.fieldset('assembly',
                   label=_(u"fieldset_assembly"),
                   fields=['assembly', 'assembly_excused', 'assembly_absents',
                           'assembly_guests', 'assembly_proxies', 'assembly_staves',
                           'signatures', 'assembly_observations'])

    model.fieldset('committees',
                   label=_(u"fieldset_committees"),
                   fields=['committees', 'committees_observations'])

    model.fieldset('informations',
                   label=_(u"fieldset_informations"),
                   fields=['in_and_out_moves', 'notes',
                           'pre_observations', 'observations',
                           'votes_observations', 'public_meeting_observations',
                           'secret_meeting_observations', 'authority_notice',
                           'meetingmanagers_notes'])

    model.fieldset('parameters',
                   label=_(u"fieldset_parameters"),
                   fields=['meeting_number', 'first_item_number'])

    @invariant
    def validate_dates(data):
        """Validate dates :
           - "date" must be unique (no other Meeting with same date);
           - "pre_meeting_date" must be < "date";
           - "start_date" must be <= "end_date"."""
        context = data.__context__
        if context is None:
            # occurs when adding a new element
            request = getRequest()
            context = request.get('PUBLISHED').context

        # invariant are called several times...
        if context.REQUEST.get("validate_dates_done", False):
            return

        is_meeting = context.__class__.__name__ == "Meeting"
        # check date
        catalog = api.portal.get_tool('portal_catalog')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        brains = catalog.unrestrictedSearchResults(
            portal_type=cfg.getMeetingTypeName(), meeting_date=data.date)
        if brains:
            found = False
            if not is_meeting:
                found = True
            else:
                for brain in brains:
                    # ignore current meeting, use path, available when creating
                    # a meeting using restapi, the UID is still not ready
                    if brain.getPath() != "/".join(context.getPhysicalPath()):
                        found = True
            if found:
                msg = translate('meeting_with_same_date_exists',
                                domain='PloneMeeting',
                                context=context.REQUEST)
                # avoid multiple call to this invariant
                context.REQUEST.set("validate_dates_done", True)
                # encode msg in utf-8 for restapi
                raise Invalid(msg.encode('utf-8'))

        # check pre_meeting_date
        if hasattr(data, 'pre_meeting_date') and \
           data.pre_meeting_date and \
           data.pre_meeting_date > data.date:
            msg = translate("pre_date_after_meeting_date",
                            domain='PloneMeeting',
                            context=context.REQUEST)
            # avoid multiple call to this invariant
            context.REQUEST.set("validate_dates_done", True)
            # encode msg in utf-8 for restapi
            raise Invalid(msg.encode('utf-8'))

        # check start_date/end_date
        # start_date must be before end_date
        # getattr(data, 'start_date', None) does not work as expected with Data...
        if hasattr(data, 'start_date') and \
           data.start_date and \
           hasattr(data, 'end_date') and \
           data.end_date and \
           data.start_date > data.end_date:
            msg = translate("start_date_after_end_date",
                            domain='PloneMeeting',
                            context=context.REQUEST)
            # avoid multiple call to this invariant
            context.REQUEST.set("validate_dates_done", True)
            # encode msg in utf-8 for restapi
            raise Invalid(msg.encode('utf-8'))
        # avoid multiple call to this invariant
        context.REQUEST.set("validate_dates_done", True)

    @invariant
    def validate_attendees(data):
        """Validate attendees."""
        context = data.__context__
        if context is None:
            # occurs when adding a new element
            request = getRequest()
            context = request.get('PUBLISHED').context

        # invariant are called several times...
        request = context.REQUEST
        if context.REQUEST.get("validate_attendees_done", False):
            return

        is_meeting = context.__class__.__name__ == "Meeting"
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)

        if cfg.isUsingContacts():
            # if creating a new meeting, only check if not several same signatories
            signatories = [signatory for signatory in
                           request.form.get('meeting_signatories', [])
                           if signatory]
            # there can not be 2 same signatories
            if signatories:
                signature_numbers = [signatory.split('__signaturenumber__')[1]
                                     for signatory in signatories]
                _validate_attendees_signatories(
                    context, signature_numbers)

            # is editing a meeting, check for removed/used values
            if is_meeting:
                # removed attendees?
                # REQUEST.form['meeting_attendees'] is like
                # ['muser_attendeeuid1_attendee', 'muser_attendeeuid2_excused']
                meeting_attendees = [attendee.split('_')[1] for attendee
                                     in request.form.get('meeting_attendees', [])
                                     if attendee.split('_')[2] == 'attendee']
                all_meeting_attendees = [
                    attendee.split('_')[1] for attendee
                    in request.form.get('meeting_attendees', [])]

                signatory_uids = [signatory.split('__signaturenumber__')[0]
                                  for signatory in signatories]
                _validate_attendees_removed_and_order(
                    context, meeting_attendees, all_meeting_attendees, signatory_uids)

                # removed voters?
                stored_voters = context.get_voters()
                # bypass when not using votes
                if stored_voters:
                    meeting_voters = [voter.split('_')[1] for voter
                                      in request.form.get('meeting_voters', [])]
                    removed_meeting_voters = set(stored_voters).difference(meeting_voters)
                    # public, voters are known
                    item_votes = context.get_item_votes()
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
                        msg = translate(
                            'can_not_remove_public_voter_voted_on_items',
                            mapping={'attendee_title': voter_brain.get_full_title},
                            domain='PloneMeeting',
                            context=request)
                        # avoid multiple call to this invariant
                        context.REQUEST.set("validate_attendees_done", True)
                        # encode msg in utf-8 for restapi
                        raise Invalid(msg.encode('utf-8'))
                    elif highest_secret_votes > len(meeting_voters):
                        msg = translate(
                            'can_not_remove_secret_voter_voted_on_items',
                            domain='PloneMeeting',
                            context=request)
                        # avoid multiple call to this invariant
                        context.REQUEST.set("validate_attendees_done", True)
                        # encode msg in utf-8 for restapi
                        raise Invalid(msg.encode('utf-8'))

        # avoid multiple call to this invariant
        context.REQUEST.set("validate_attendees_done", True)


@form.default_value(field=IMeeting['assembly'])
def default_assembly(data):
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    res = u""
    if "assembly" in cfg.getUsedMeetingAttributes():
        res = safe_unicode(cfg.getAssembly())
    return res


@form.default_value(field=IMeeting['assembly_staves'])
def default_assembly_staves(data):
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    res = u""
    if "assembly_staves" in cfg.getUsedMeetingAttributes():
        res = safe_unicode(cfg.getAssemblyStaves())
    return res


@form.default_value(field=IMeeting['signatures'])
def default_signatures(data):
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    res = u""
    if "signatures" in cfg.getUsedMeetingAttributes():
        res = safe_unicode(cfg.getSignatures())
    return res


@form.default_value(field=IMeeting['place'])
def default_place(data):
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    res = PLACE_OTHER
    if cfg.getPlaces():
        res = safe_unicode(cfg.getPlaces().split('\r\n')[0].strip())
    return res


@form.default_value(field=IMeeting['committees'])
def default_committees(data):
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    used_attrs = cfg.getUsedMeetingAttributes()
    res = []
    if "committees" in used_attrs:
        for committee in cfg.getCommittees():
            # not enabled or item_only, we pass
            if committee['enabled'] != '1':
                continue
            mdata = {}
            mdata['row_id'] = committee['row_id']
            # manage default_values
            for field_id, field_value in committee.items():
                if not field_id.startswith('default_'):
                    continue
                real_field_id = field_id.replace('default_', '')
                # do not set a default value for an optional field not enabled
                if 'committees_{0}'.format(real_field_id) not in used_attrs:
                    continue
                # XXX workaround to remove when MeetingConfig will be DX
                value = committee[field_id]
                if real_field_id in ['assembly', 'signatures']:
                    value = richtextval(value)
                mdata[real_field_id] = value
            # complete data
            for field_name in getFieldNamesInOrder(ICommitteesRowSchema):
                if field_name not in mdata:
                    mdata[field_name] = None
            res.append(mdata)
    return res


def get_all_usable_held_positions(obj, the_objects=True):
    '''This will return every currently stored held_positions if p_obj is a Meeting,
       and will include every selectable held_positions.
       If p_the_objects=True, we return held_position objects, UID otherwise.
       '''
    # used Persons are held_positions stored in orderedContacts
    contacts = base_hasattr(obj, 'ordered_contacts') and list(obj.ordered_contacts) or []
    # append every selectable hp selected in MeetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    selectable_contacts = cfg.getOrderedContacts()
    new_selectable_contacts = [c for c in selectable_contacts if c not in contacts]
    contacts = contacts + new_selectable_contacts
    if contacts and the_objects:
        contacts = uuidsToObjects(uuids=contacts, ordered=True, unrestricted=True)
    return tuple(contacts)


def _validate_attendees_removed_and_order(context, meeting_attendees, all_meeting_attendees, signatory_uids):
    """ """
    request = context.REQUEST
    stored_attendees = context.get_all_attendees()
    removed_meeting_attendees = set(stored_attendees).difference(meeting_attendees)
    # do not go further if not removed attendees
    # this is useful when creating a new meeting from restapi call
    # where ObjectCreated event is triggered after validation
    if removed_meeting_attendees:
        # attendees redefined on items
        redefined_item_attendees = context._get_all_redefined_attendees(
            by_persons=True)
        conflict_attendees = removed_meeting_attendees.intersection(
            redefined_item_attendees)
        if conflict_attendees:
            attendee_uid = tuple(conflict_attendees)[0]
            attendee_brain = uuidToCatalogBrain(attendee_uid)
            msg = translate(
                'can_not_remove_attendee_redefined_on_items',
                mapping={'attendee_title': attendee_brain.get_full_title},
                domain='PloneMeeting',
                context=request)
            # avoid multiple call to this invariant
            context.REQUEST.set("validate_attendees_done", True)
            # encode msg in utf-8 for restapi
            raise Invalid(msg.encode('utf-8'))
        # in theory this is not possible thru the UI as unselecting an attendee
        # will disable the signatory field but this is possible thru the restapi
        removed_signatories = tuple(
            set(signatory_uids).intersection(removed_meeting_attendees))
        if removed_signatories:
            attendee_brain = uuidToCatalogBrain(removed_signatories[0])
            msg = translate(
                'can_not_remove_attendee_defined_as_signatory',
                mapping={'attendee_title': attendee_brain.get_full_title},
                domain='PloneMeeting',
                context=request)
            # avoid multiple call to this invariant
            context.REQUEST.set("validate_attendees_done", True)
            # encode msg in utf-8 for restapi
            raise Invalid(msg.encode('utf-8'))

    # can not remove or add attendees on meeting when attendees order
    # was redefined on items
    item_attendees_order = context._get_item_attendees_order(from_meeting_if_empty=False)
    if item_attendees_order:
        all_added_meeting_attendees = set(all_meeting_attendees).difference(stored_attendees)
        all_removed_meeting_attendees = set(stored_attendees).difference(all_meeting_attendees)
        all_changed_meeting_attendees = tuple(all_added_meeting_attendees) + \
            tuple(all_removed_meeting_attendees)
        if all_changed_meeting_attendees:
            msg = translate(
                'can_not_remove_or_add_attendee_item_attendees_reordered',
                mapping={'item_url': uuidToObject(
                    item_attendees_order.keys()[0]).absolute_url()},
                domain='PloneMeeting',
                context=request)
            # avoid multiple call to this invariant
            context.REQUEST.set("validate_attendees_done", True)
            # encode msg in utf-8 for restapi
            raise Invalid(msg.encode('utf-8'))


def _validate_attendees_signatories(context, signature_numbers):
    if len(signature_numbers) != len(set(signature_numbers)):
        msg = translate(
            'can_not_define_several_same_signature_number',
            domain='PloneMeeting',
            context=context.REQUEST)
        # avoid multiple call to this invariant
        context.REQUEST.set("validate_attendees_done", True)
        # encode msg in utf-8 for restapi
        raise Invalid(msg.encode('utf-8'))


########################################################################
#                                                                      #
#                    SAMPLE TO EXTEND SCHEMA                           #
#                                                                      #
########################################################################
#
# class IMeetingCustomSample(IMeeting):
#     """ """
#
#     form.order_before(extra_field='end_date')
#     extra_field = Int(
#         title=_(u"Sample extra field"),
#         default=0,
#         required=False)
#
#     model.fieldset(
#         'dates_and_data',
#         label=_(u"Dates and data"),
#         fields=['extra_field'])
#
########################################################################


class Meeting(Container):
    """ """

    implements(IMeeting)

    security = ClassSecurityInfo()

    MEETINGCLOSEDSTATES = ['closed']

    # 'optional': is field optional and  selectable in MeetingConfig?
    # if field is not empty, it will be displayed even if optional and not in used_attrs
    # this for history reasons (fields used before, disabled now, ...)
    # 'condition': a python expression
    FIELD_INFOS = {
        'date':
            {'optional': False,
             'condition': ""},
        'start_date':
            {'optional': True,
             'condition': ""},
        'mid_date':
            {'optional': True,
             'condition': ""},
        'mid_start_date':
            {'optional': True,
             'condition': ""},
        'end_date':
            {'optional': True,
             'condition': ""},
        'approval_date':
            {'optional': True,
             'condition': ""},
        'convocation_date':
            {'optional': True,
             'condition': ""},
        'validation_deadline':
            {'optional': True,
             'condition': "python:context.getTagName() == 'Meeting' and context.date and "
                "cfg.show_meeting_manager_reserved_field('validation_deadline')"},
        'freeze_deadline':
            {'optional': True,
             'condition': "python:context.getTagName() == 'Meeting' and context.date and "
                "cfg.show_meeting_manager_reserved_field('freeze_deadline')"},
        'place':
            {'optional': True,
             'condition': ""},
        'place_other':
            {'optional': False,
             'condition': "python:view.show_field('place') and "
                "(view.mode != 'display' or context.place == u'other')"},
        'category':
            {'optional': True,
             'condition': ""},
        'videoconference':
            {'optional': True,
             'condition': ""},
        'adopts_next_agenda_of':
            {'optional': True,
             'condition': ""},
        'extraordinary_session':
            {'optional': True,
             'condition': ""},
        'assembly':
            {'optional': True,
             'condition': "python:'assembly' in view.shown_assembly_fields()"},
        'assembly_excused':
            {'optional': True,
             'condition': "python:'assembly_excused' in view.shown_assembly_fields()"},
        'assembly_absents':
            {'optional': True,
             'condition': "python:'assembly_absents' in view.shown_assembly_fields()"},
        'assembly_guests':
            {'optional': True,
             'condition': "python:'assembly_guests' in view.shown_assembly_fields()"},
        'assembly_proxies':
            {'optional': True,
             'condition': "python:'assembly_proxies' in view.shown_assembly_fields()"},
        'assembly_staves':
            {'optional': True,
             'condition': "python:'assembly_staves' in view.shown_assembly_fields()"},
        'signatures':
            {'optional': True,
             'condition': ""},
        'assembly_observations':
            {'optional': True,
             'condition': ""},
        'committees':
            {'optional': True,
             'condition': "",
             'optional_columns': ['convocation_date', 'place',
                                  'assembly', 'signatures',
                                  'attendees', 'signatories', 'committee_observations']},
        'committees_observations':
            {'optional': True,
             'condition': ""},
        'in_and_out_moves':
            {'optional': True,
             'condition': "python:cfg.show_meeting_manager_reserved_field('in_and_out_moves')"},
        'notes':
            {'optional': True,
             'condition': "python:cfg.show_meeting_manager_reserved_field('notes')"},
        'observations':
            {'optional': True,
             'condition': ""},
        'pre_meeting_date':
            {'optional': True,
             'condition': ""},
        'pre_meeting_place':
            {'optional': True,
             'condition': ""},
        'pre_observations':
            {'optional': True,
             'condition': ""},
        'votes_observations':
            {'optional': True,
             'condition': "python:view.show_votes_observations()"},
        'public_meeting_observations':
            {'optional': True,
             'condition': ""},
        'secret_meeting_observations':
            {'optional': True,
             'condition': "python:cfg.show_meeting_manager_reserved_field('secret_meeting_observations')"},
        'authority_notice':
            {'optional': True,
             'condition': "python:cfg.show_meeting_manager_reserved_field('authority_notice')"},
        'meetingmanagers_notes':
            {'optional': True,
             'condition': "python:cfg.show_meeting_manager_reserved_field('meetingmanagers_notes')"},
        'meeting_number':
            {'optional': True,
             'condition': "python:tool.isManager(cfg)"},
        'first_item_number':
            {'optional': True,
             'condition': "python:tool.isManager(cfg)"},
    }

    security.declarePublic('get_pretty_link')

    def get_pretty_link(self,
                        prefixed=False,
                        short=True,
                        showContentIcon=False,
                        isViewable=True,
                        notViewableHelpMessage=None,
                        appendToUrl='',
                        link_pattern=None,
                        with_hour=True,
                        with_number_of_items=False,
                        include_category_id=True):
        """Return the IPrettyLink version of the title."""
        adapted = IPrettyLink(self)
        tool = api.portal.get_tool('portal_plonemeeting')
        adapted.contentValue = tool.format_date(
            self.date,
            with_hour=with_hour,
            prefixed=prefixed,
            short=short)
        if include_category_id and self.category is not None:
            category = self.get_category(True)
            if category.category_id:
                adapted.contentValue = u"{0} - {1}".format(
                    category.category_id, adapted.contentValue)
        if with_number_of_items:
            adapted.contentValue = u"{0} <span class='meeting-number-items'>[{1}]</span>".format(
                adapted.contentValue, self.number_of_items())
        adapted.isViewable = adapted.isViewable and isViewable
        if notViewableHelpMessage is not None:
            adapted.notViewableHelpMessage = notViewableHelpMessage
        adapted.showContentIcon = showContentIcon
        adapted.appendToUrl = appendToUrl
        if link_pattern:
            adapted.link_pattern = link_pattern
        # this will make link open in available items iframe
        # open in parent (main) frame
        adapted.target = '_parent'
        return adapted.getLink()

    security.declarePublic('getSelf')

    def getSelf(self):
        '''Similar to MeetingItem.getSelf. Check MeetingItem.py for more
           info.'''
        res = self
        if self.getTagName() != 'Meeting':
            res = self.context
        return res

    def get_category(self, the_object=False):
        '''Helper to get the category.
           If p_theObject=True, we return the category object,
           the stored category id otherwise.'''
        return _get_category(
            self,
            self.category,
            the_object=the_object,
            cat_type='meetingcategories')

    def get_assembly(self, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.assembly,
            self,
            for_display=for_display,
            striked=striked,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_assembly_excused(self, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.assembly_excused,
            self,
            for_display=for_display,
            striked=striked,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_assembly_absents(self, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.assembly_absents,
            self,
            for_display=for_display,
            striked=striked,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_assembly_guests(self, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.assembly_guests,
            self,
            for_display=for_display,
            striked=striked,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_assembly_staves(self, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.assembly_staves,
            self,
            for_display=for_display,
            striked=striked,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_assembly_proxies(self, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.assembly_proxies,
            self,
            for_display=for_display,
            striked=striked,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_signatures(self, for_display=False, mark_empty_tags=False, raw=True):
        """ """
        return get_textarea_value(
            self.signatures,
            self,
            for_display=for_display,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_place(self, real=False):
        """ """
        place = self.place
        if not real and self.place == PLACE_OTHER:
            place = self.place_other
        return place

    def get_committee(self, row_id):
        """Return infos about given p_row_id committee."""
        if self.committees:
            for committee in self.committees:
                if committee['row_id'] == row_id:
                    return committee.copy()

    def get_committees(self):
        """Return every defined committees row_id."""
        row_ids = []
        if self.committees:
            for committee in self.committees or []:
                row_ids.append(committee['row_id'])
        return row_ids

    def get_committee_place(self, row_id):
        """Return "place" for given p_row_id committee."""
        value = self.get_committee(row_id)["place"]
        return value

    def get_committee_assembly(self, row_id, for_display=True, striked=True, mark_empty_tags=False, raw=True):
        """Return "assembly" for given p_row_id committee."""
        value = self.get_committee(row_id)["assembly"]
        return get_textarea_value(
            value,
            self,
            for_display=for_display,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_committee_signatures(self, row_id, for_display=False, striked=True, mark_empty_tags=False, raw=True):
        """Return "signatures" for given p_row_id committee."""
        value = self.get_committee(row_id)["signatures"]
        return get_textarea_value(
            value,
            self,
            for_display=for_display,
            mark_empty_tags=mark_empty_tags,
            raw=raw)

    def get_committee_attendees(self, row_id, the_objects=False):
        '''Returns the attendees for given p_row_id committee.'''
        committee_attendees = self.get_committee(row_id).get("attendees", [])
        return self._get_contacts(uids=committee_attendees, the_objects=the_objects)

    def get_committee_signatories(self, row_id, the_objects=False, by_signature_number=False):
        '''Returns the signatories for given p_row_id committee.'''
        committee_signatories = self.get_committee(row_id).get("signatories", [])
        signers = self._get_contacts(uids=committee_signatories, the_objects=the_objects)
        # signature number depends on signatory order
        i = 1
        res = {}
        for signer in signers:
            res[signer] = str(i)
            i += 1
        if by_signature_number:
            # keys are values, values are keys
            res = {v: k for k, v in res.items()}
        return res

    def get_committee_observations(self, row_id, for_display=True, mark_empty_tags=False, raw=True):
        """Return "committee_observations" for given p_row_id committee."""
        value = self.get_committee(row_id)["committee_observations"]
        if not value:
            return value
        return raw and value.raw or value.output

    def get_committee_items(self, row_id, supplement=-1, ordered=True, **kwargs):
        """Return every items of a given committee p_row_id.
           For p_supplement:
           - -1 means only include normal, no supplement;
           - 0 means normal + every supplements;
           - 1, 2, 3, ... only items of supplement 1, 2, 3, ...
           - 99 means every supplements only.
           This is calling get_items under so every parameters of get_items may be given in kwargs."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        available_suppl_ids = cfg.get_supplements_for_committee(row_id)
        committees_index = []
        if supplement == -1:
            committees_index.append(row_id)
        elif supplement == 0:
            committees_index.append(row_id)
            committees_index += available_suppl_ids
        elif supplement == 99:
            committees_index = available_suppl_ids
        else:
            if len(available_suppl_ids) >= supplement:
                committees_index = available_suppl_ids[supplement - 1]
            else:
                # asking for unexisting supplement
                return []
        # we use additional_catalog_query to pass the committees_index to keep
        # keep additional_catalog_query from kwargs if exist
        additional_catalog_query = kwargs.get('additional_catalog_query', {})
        additional_catalog_query.update({'committees_index': committees_index})
        kwargs["additional_catalog_query"] = additional_catalog_query
        return self.get_items(ordered=ordered, **kwargs)

    def get_all_attendees(self, uids=[], the_objects=False):
        '''This will return every currently stored held_positions.
           If p_the_objects=True, we return held_position objects, UID otherwise.'''
        # in some case especially with pm.restapi, validators are called before
        # created event and ordered_contacts may not be initialized
        contacts = uids or (
            base_hasattr(self, 'ordered_contacts') and list(self.ordered_contacts)) or []
        if contacts and the_objects:
            contacts = uuidsToObjects(uuids=contacts, ordered=True, unrestricted=True)
        return tuple(contacts)

    def is_late(self):
        '''Is meeting considered late?
           It is the case if the review_state is after the late state.'''
        meeting_state = self.query_state()
        late_state = self.adapted().get_late_state()
        return late_state and meeting_state not in get_states_before(self, late_state)

    def _available_items_query(self):
        '''Check docstring in IMeeting.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meeting_state = self.query_state()
        if meeting_state not in cfg.getMeetingStatesAcceptingItemsForMeetingManagers():
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
        if not self.is_late():
            # get items for which the preferred_meeting_date is lower or
            # equal to the date of this meeting (self)
            # a no preferred meeting item preferred_meeting_date is 1950/01/01
            res.append({'i': 'preferred_meeting_date',
                        'o': 'plone.app.querystring.operation.date.lessThan',
                        'v': self.date})
        else:
            # after late state, only query items for which preferred meeting is self
            # or a passed meeting, indeed an item that is late for a past meeting is
            # also late for current meeting
            res.append({'i': 'preferred_meeting_date',
                        'o': 'plone.app.querystring.operation.date.between',
                        'v': (datetime(2000, 1, 1), self.date)})
        return res

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

    def _get_contacts(self, contact_type=None, uids=None, the_objects=False):
        """Return contacts.  Parameters p_contact_type and p_uids are mutually exclusive."""
        res = []
        ordered_contacts = getattr(self, 'ordered_contacts', OrderedDict())
        if contact_type:
            # if we have uids, we keep it's order
            uids = uids or ordered_contacts.keys()
            for uid in uids:
                if ordered_contacts[uid][contact_type]:
                    res.append(uid)
        else:
            res = uids

        if res and the_objects:
            res = uuidsToObjects(res, ordered=True, unrestricted=True)
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

    def get_signatories(self, the_objects=False, by_signature_number=False, include_position_type=False):
        '''Returns the signatories in this meeting.'''
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

        if include_position_type:
            # make signature_number the key
            reversed_res = {v: k for k, v in res.items()}
            for signature_number, uid_or_obj in reversed_res.items():
                res[uid_or_obj] = {
                    'signature_number': signature_number,
                    'position_type': uuidToObject(
                        isinstance(uid_or_obj, basestring) and
                        uid_or_obj or uid_or_obj.UID()).position_type}

        if by_signature_number:
            # reverse res so when several same signature_number, the first win
            res = OrderedDict(reversed(res.items()))
            # keys are values, values are keys
            if include_position_type:
                res = {v['signature_number']: {'hp': k, 'position_type': v['position_type']}
                       for k, v in res.items()}
            else:
                res = {v: k for k, v in res.items()}

        return dict(res)

    security.declarePublic('get_replacements')

    def get_replacements(self, the_objects=False):
        '''Returns the replacements in this meeting.'''
        replaced_uids = self._get_contacts('replacement', the_objects=the_objects)
        return {replaced_uid: self.ordered_contacts[replaced_uid]['replacement']
                for replaced_uid in replaced_uids}

    def _get_item_not_present(self, attr, by_persons=False):
        '''Return item not present (item_absents, item_excused, ...)
           by default the attr dict has the item UID as key and list of not_present
           as values but if 'p_by_persons' is True, the informations are returned with
           not_present held position as key and list of items as value.'''
        if by_persons:
            # values are now keys, concatenate a list of lists and remove duplicates
            keys = tuple(set(list(itertools.chain.from_iterable(attr.values()))))
            data = {}
            for key in keys:
                data[key] = [k for k, v in attr.items() if key in v]
        else:
            data = attr.data.copy()
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

    def get_item_signatories(self,
                             by_signatories=False,
                             include_position_type=False,
                             by_signature_number=False):
        '''Return itemSignatories, by default the itemSignatories dict has the
           item UID as key and list of signatories as values, this is done to
           make data more easy to use.
           If 'p_by_signatories' is True, the informations are returned with
           signatory as key and list of items as value.
           If p_by_signature_number, we return a dict with signature number as
           key and list of item signatories as values.
           The parameters are mutually exclusive.'''
        signatories = OrderedDict()
        if by_signatories:
            for item_uid, signatories_infos in self.item_signatories.items():
                for signature_number, signatory_infos in signatories_infos.items():
                    # do not keep 'position_type' from the stored itemSignatories
                    signatory_uid = signatory_infos['hp_uid']
                    if signatory_uid not in signatories:
                        signatories[signatory_uid] = []
                    signatories[signatory_uid].append(item_uid)
        elif by_signature_number:
            for item_uid, signatories_infos in self.item_signatories.items():
                for signature_number, signatory_infos in signatories_infos.items():
                    if signature_number not in signatories:
                        signatories[signature_number] = []
                    signatory = uuidToObject(signatory_infos['hp_uid'], unrestricted=True)
                    signatories[signature_number].append(signatory)
        else:
            for item_uid, signatory_infos in self.item_signatories.data.items():
                if include_position_type:
                    signatories[item_uid] = signatory_infos.copy()
                else:
                    signatories[item_uid] = {k: v['hp_uid'] for k, v in signatory_infos.items()}
        return signatories

    def _get_item_redefined_positions(self):
        """ """
        return deepcopy(self.item_attendees_positions)

    def is_attendee_position_redefined(self, hp_uid, item_uid=None):
        """ """
        redefined_positions = self._get_item_redefined_positions()
        found = False
        if item_uid:
            found = item_uid in redefined_positions and \
                hp_uid in redefined_positions[item_uid]
        else:
            for item_uid, infos in redefined_positions.items():
                if hp_uid in infos:
                    found = True
                    break
        return found

    def get_signature_infos_for(self,
                                item_uid,
                                signatory_uid,
                                render_position_type=False,
                                prefix_position_type=False):
        """Return the signature position_type to use as label and signature_number
           for given p_item_uid and p_signatory_uid."""
        # check if signatory_uid is redefined on the item
        data = self.get_item_signatories(by_signatories=False, include_position_type=True)
        data = {k: v['position_type'] for k, v in data.get(item_uid, {}).items()
                if v['hp_uid'] == signatory_uid}
        hp = uuidToObject(signatory_uid, unrestricted=True)
        if data:
            signature_number, position_type = data.items()[0]
        else:
            # if not, then get it from meeting signatories
            signature_number = self.get_signatories()[signatory_uid]
            # position type is the one of the signatory (signatory_uid)
            position_type = hp.position_type
        res = {}
        res['signature_number'] = signature_number
        if render_position_type:
            if prefix_position_type:
                res['position_type'] = hp.get_prefix_for_gender_and_number(
                    include_value=True,
                    forced_position_type_value=position_type)
            else:
                res['position_type'] = hp.get_label(
                    forced_position_type_value=position_type)
        else:
            res['position_type'] = position_type
        return res

    def get_attendee_position_for(self,
                                  item_uid,
                                  hp_uid,
                                  render_position_type=False,
                                  prefix_position_type=False):
        """Return the attendee position_type to use as label
           for given p_item_uid and p_signatory_uid."""
        # check if hp_uid is redefined on the item
        data = {}
        redefined_positions = self._get_item_redefined_positions()
        if item_uid in redefined_positions and \
           hp_uid in redefined_positions[item_uid]:
            data = redefined_positions[item_uid][hp_uid]
        hp = uuidToObject(hp_uid, unrestricted=True)
        position_type = data.get('position_type', hp.position_type)
        if render_position_type:
            if prefix_position_type:
                position_type = hp.get_prefix_for_gender_and_number(
                    include_value=True,
                    forced_position_type_value=position_type)
            else:
                position_type = hp.get_label(
                    forced_position_type_value=position_type)
        return position_type

    def _get_item_attendees_order(self, item_uid=None, from_meeting_if_empty=True):
        """ """
        if not base_hasattr(self, 'item_attendees_order'):
            return []

        all_uids = []
        if item_uid:
            all_uids = self.item_attendees_order.get(item_uid)
            if not all_uids and from_meeting_if_empty:
                all_uids = self.get_all_attendees()
        else:
            # return the entire value
            return deepcopy(self.item_attendees_order)
        return all_uids

    def _set_item_attendees_order(self, item_uid, values):
        """ """
        self.item_attendees_order[item_uid] = values

    security.declarePublic('get_item_votes')

    def get_item_votes(self, item_uid=None, as_copy=True):
        ''' '''
        if item_uid:
            # avoid deepcopy returned data as it leads to perf problems
            # with huge item_votes (50 voters, 30 votes on same item)
            # See testPerformances.test_pm_Speed_AsyncLoadItemAssemblyAndSignatures
            if as_copy:
                return deepcopy(self.item_votes.data.get(item_uid, []))
            else:
                return self.item_votes.data.get(item_uid, [])
        else:
            if as_copy:
                return deepcopy(self.item_votes.data)
            else:
                return self.item_votes.data

    security.declarePrivate('set_item_public_vote')

    def set_item_public_vote(self, item, data, vote_number=0):
        """ """
        data = deepcopy(data)
        item_uid = item.UID()
        # set new item_votes value on meeting
        # first votes
        if item_uid not in self.item_votes:
            self.item_votes[item_uid] = PersistentList()
            # check if we are not adding a new vote on an item containing no votes at all
            if vote_number == 1:
                # add an empty vote 0
                data_item_vote_0 = item.get_item_votes(
                    vote_number=0,
                    include_extra_infos=False,
                    include_unexisting=True)
                # make sure we use persistent for 'voters'
                data_item_vote_0['voters'] = PersistentMapping(data_item_vote_0['voters'])
                self.item_votes[item_uid].append(PersistentMapping(data_item_vote_0))
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
        elif 'voters' not in self.item_votes[item_uid][vote_number]:
            # changing poll_type for vote_number, in this case 'voters' key does not exist
            self.item_votes[item_uid][vote_number] = PersistentMapping(data)
        else:
            # use update in case we only update a subset of votes
            # when some vote NOT_VOTABLE_LINKED_TO_VALUE or so
            # we have nested dicts, data is a dict, containing 'voters' dict
            self.item_votes[item_uid][vote_number]['voters'].update(data['voters'])
            data.pop('voters')
            self.item_votes[item_uid][vote_number].update(data)
        # will invalidate MeetingItem.get_item_votes cache
        self.item_votes[item_uid]._p_changed = True
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
                    include_extra_infos=False,
                    include_unexisting=True)
                self.item_votes[item_uid].append(PersistentMapping(data_item_vote_0))
        # new vote_number
        if vote_number + 1 > len(self.item_votes[item_uid]):
            self.item_votes[item_uid].append(PersistentMapping(data))
        else:
            # when changing poll_type from public to secret
            # make sure key "voters" is removed
            self.item_votes[item_uid][vote_number].pop('voters', None)
            self.item_votes[item_uid][vote_number].update(data)
        # will invalidate MeetingItem.get_item_votes cache
        self.item_votes[item_uid]._p_changed = True

    security.declarePublic('display_user_replacement')

    def display_user_replacement(self,
                                 held_position_uid,
                                 include_held_position_label=True,
                                 include_sub_organizations=True):
        '''Display the user remplacement from p_held_position_uid.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        held_position = uuidToObject(held_position_uid, unrestricted=True)
        if include_held_position_label:
            return get_attendee_short_title(
                held_position,
                cfg,
                include_sub_organizations=include_sub_organizations)
        else:
            person = held_position.get_person()
            return person.get_title()

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
           - if p_force_linked_items_query is True, it will call _get_query with
             same parameter and force use of query showing linked items, not displaying
             available items.
        '''
        # execute the query using the portal_catalog
        catalog = api.portal.get_tool('portal_catalog')
        collection_behavior = ICollection(self)
        catalog_query = collection_behavior._get_query(
            force_linked_items_query=force_linked_items_query)
        if list_types:
            catalog_query.append({'i': 'listType',
                                  'o': 'plone.app.querystring.operation.selection.is',
                                  'v': list_types},)
        if uids:
            catalog_query.append({'i': 'UID',
                                  'o': 'plone.app.querystring.operation.selection.is',
                                  'v': uids},)
        if ordered:
            collection_behavior = ICollection(self)
            query = queryparser.parseFormquery(
                self,
                catalog_query,
                sort_on=collection_behavior._get_sort_on(
                    force_linked_items_query=force_linked_items_query))
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
        return self.get_items(the_objects=False, unrestricted=True)

    security.declarePublic('get_item_by_number')

    def get_item_by_number(self, number):
        '''Gets the item thas has number p_number.'''
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(
            meeting_uid=self.UID(), getItemNumber=number)
        if not brains:
            return None
        return brains[0]._unrestrictedGetObject()

    def get_late_state(self):
        '''See doc in interfaces.py.'''
        return 'frozen'

    def _check_insert_order_cache(self, cfg):
        '''See doc in interfaces.py.'''
        meeting = self.get_self()
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
                'orderedGroupsInCharge',
                'committees']

    def _init_insert_order_cache(self, cfg):
        '''See doc in interfaces.py.'''
        meeting = self.get_self()
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
        items = self.get_items(ordered=True, unrestricted=True)
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

        item._update_meeting_link(self)
        # store number of items
        self._number_of_items = len(items) + 1
        self._finalize_item_insert(items_to_update=[item])
        # add logging message to fingerpointing log
        extras = 'object={0} meeting={1} meeting_date={2} item_preferred_meeting_uid={3}'.format(
            repr(item), repr(self), self.date, item.getPreferredMeeting())
        fplog('insert_item_in_meeting', extras=extras)

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
                                     'meeting_uid',
                                     'meeting_date'])
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
        items = self.get_items(unrestricted=True)
        try:
            item._update_meeting_link(None)
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

        # remove item UID from meeting attendees attributes
        item_uid = item.UID()
        for attendee_attr in MEETING_ATTENDEES_ATTRS:
            if item_uid in getattr(self, attendee_attr):
                del getattr(self, attendee_attr)[item_uid]

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
        item.reindexObject(idxs=['getItemNumber',
                                 'listType',
                                 'meeting_uid',
                                 'meeting_date'])

        # store number of items
        self._number_of_items = len(items)
        # meeting is considered modified, do this before update_item_references
        self.notifyModified()

        # update itemReference of item that is no more linked to self and so that will not
        # be updated by Meeting.update_item_references and then update items that used
        # a higher item number
        item.update_item_reference()
        self.update_item_references(start_number=item_number)
        # add logging message to fingerpointing log
        extras = 'object={0} meeting={1} meeting_date={2}'.format(
            repr(item), repr(self), self.date)
        fplog('remove_item_from_meeting', extras=extras)

    def _may_update_item_references(self):
        '''See docstring in interfaces.py.'''
        may_update = False
        meeting = self.getSelf()
        may_update = meeting.is_late()
        if not may_update:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(meeting)
            may_update = cfg.getComputeItemReferenceForItemsOutOfMeeting()
        return may_update

    def update_item_references(self, start_number=0, check_needed=False, clear=False):
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

        if clear or self.adapted()._may_update_item_references():
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
                item.update_item_reference(clear=clear)

    security.declarePrivate('update_title')

    def update_title(self):
        '''The meeting title is generated by this method, based on the meeting date.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        new_title = tool.format_date(self.date, with_hour=True)
        if self.category is not None:
            category = self.get_category(True)
            if category.category_id:
                new_title = u"{0} - {1}".format(
                    self.get_category(True).category_id, new_title)
        if self.title != new_title:
            self.setTitle(new_title)
            return True

    security.declarePrivate('compute_dates')

    def compute_dates(self):
        '''Computes, for this meeting, the dates which are derived from the
           meeting date when relevant.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        used_attrs = cfg.getUsedMeetingAttributes()
        # Initialize the effective start date with the meeting date
        if 'start_date' in used_attrs and not self.start_date:
            self.start_date = self.date
        # Set, by default, mid date to start date + 1 hour.
        if 'mid_date' in used_attrs and not self.mid_date:
            self.mid_date = self.date + timedelta(hours=1)
        # Set, by default, mid_start_date to start date + 1 hour.
        if 'mid_start_date' in used_attrs and not self.mid_start_date:
            self.mid_start_date = self.date + timedelta(hours=1)
        # Set, by default, end date to start date + 2 hours.
        if 'end_date' in used_attrs and not self.end_date:
            self.end_date = self.date + timedelta(hours=2)
        # Compute the deadlines
        if 'validation_deadline' in used_attrs and not getattr(self, 'validation_deadline', None):
            delta = cfg.getValidationDeadlineDefault()
            if not delta.strip() in ('', '0',):
                self.validation_deadline = getDateFromDelta(self.date, '-' + delta)
        if 'freeze_deadline' in used_attrs and not getattr(self, 'freeze_deadline', None):
            delta = cfg.getFreezeDeadlineDefault()
            if not delta.strip() in ('', '0',):
                self.freeze_deadline = getDateFromDelta(self.date, '-' + delta)

    def update_first_item_number(self,
                                 update_item_references=True,
                                 get_items_additional_catalog_query={},
                                 force=False):
        """ """
        # only update if still the initial value
        if self.attribute_is_used('first_item_number') and (self.first_item_number == -1 or force):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            # as this may be applied on a closed meeting, we can not protect the method
            # with a permission, so we check if user isManager
            if not tool.isManager(cfg):
                raise Unauthorized
            updated = False
            if "first_item_number" in cfg.getYearlyInitMeetingNumbers():
                # I must reinit the first_item_number to 1 if it is the first
                # meeting of this year.
                prev = self.get_previous_meeting(interval=365)
                if not prev or \
                   (prev.date.year != self.date.year):
                    self.first_item_number = 1
                    updated = True

            if updated is False:
                unrestricted_methods = getMultiAdapter(
                    (self, self.REQUEST), name='pm_unrestricted_methods')
                self.first_item_number = \
                    unrestricted_methods.findFirstItemNumber(
                        get_items_additional_catalog_query=get_items_additional_catalog_query)
            if update_item_references:
                self.update_item_references()
            api.portal.show_message(_("first_item_number_init",
                                      mapping={"first_item_number": self.first_item_number}),
                                    request=self.REQUEST)

    security.declarePublic('get_user_replacements')

    def get_user_replacements(self):
        '''Gets the dict storing user replacements.'''
        res = {}
        ordered_contacts = getattr(self, 'ordered_contacts', OrderedDict())
        for uid, infos in ordered_contacts.items():
            if infos['replacement']:
                res[uid] = infos['replacement']
        return res

    security.declareProtected(ModifyPortalContent, '_update_attendee_type')

    def _update_attendee_type(self, attendee_uid, attendee_type, force_clear=False):
        """ """
        if force_clear or attendee_uid not in self.ordered_contacts:
            self.ordered_contacts[attendee_uid] = \
                {'attendee': False,
                 'excused': False,
                 'absent': False,
                 'signer': False,
                 'signature_number': None,
                 'replacement': None,
                 'voter': False}
        self.ordered_contacts[attendee_uid][attendee_type] = True
        self._p_changed = True

    def _update_signature_number(self, signatory_uid, signature_number):
        """ """
        if signature_number is not None:
            self.ordered_contacts[signatory_uid]['signer'] = True
            self.ordered_contacts[signatory_uid]['signature_number'] = signature_number
        else:
            self.ordered_contacts[signatory_uid]['signer'] = False
            self.ordered_contacts[signatory_uid]['signature_number'] = None
        self._p_changed = True

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
            self._update_attendee_type(attendee_uid, attendee_type)

        for signatory_uid, signature_number in signatories.items():
            self._update_signature_number(signatory_uid, signature_number)

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

    def _update_after_edit(self, idxs=['*']):
        """Convenience method that make sure ObjectModifiedEvent is called.
           We also call reindexObject here so we avoid multiple reindexation.
           This is called when we change something on an element without
           tiggering too much things."""
        notifyModifiedAndReindex(self, extra_idxs=idxs, notify_event=True)

    def update_local_roles(self, avoid_reindex=False, **kwargs):
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
        self._update_using_groups_local_roles()
        _addManagedPermissions(self)
        # notify that localRoles have been updated
        notify(MeetingLocalRolesUpdatedEvent(self, old_local_roles))
        # not really necessary here but easier
        # update annexes categorized_elements to store 'visible_for_groups'
        updateAnnexesAccess(self)
        # reindex object security except if avoid_reindex=True and localroles are the same
        # XXX check on currently_migrating_meeting_dx to be removed after Meeting migrated to DX
        if not self.REQUEST.get('currently_migrating_meeting_dx') and \
           (not avoid_reindex or old_local_roles != self.__ac_local_roles__):
            self.reindexObjectSecurity()

    def getIndexesRelatedTo(self, related_to='annex', check_deferred=True):
        '''See doc in interfaces.py.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if related_to == 'annex':
            idxs = ['SearchableText']
        if check_deferred and related_to in tool.getDeferParentReindex():
            # mark meeting reindex deferred so it can be updated at right moment
            meeting = self.getSelf()
            setattr(meeting, REINDEX_NEEDED_MARKER, True)
            idxs.remove('SearchableText')
        return idxs

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

    def _update_using_groups_local_roles(self):
        '''When using MeetingConfig.usingGroups, only defined groups will get
           access to the meeting.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for org_uid in cfg.getUsingGroups():
            for plone_group_id in get_plone_groups(
                    org_uid, ids_only=True, verify_group_exist=False):
                self.manage_addLocalRoles(plone_group_id, ('Reader', ))

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

    def attribute_is_used_cachekey(method, self, name):
        '''cachekey method for self.attribute_is_used.'''
        return "{0}.{1}".format(self.portal_type, name)

    security.declarePublic('attribute_is_used')

    @ram.cache(attribute_is_used_cachekey)
    def attribute_is_used(self, name):
        '''Is the attribute named p_name used in this meeting config ?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return (name in cfg.getUsedMeetingAttributes())

    def query_state_cachekey(method, self):
        '''cachekey method for self.query_state.'''
        return self.workflow_history

    security.declarePublic('query_state')

    # not ramcached perf tests says it does not change anything
    # and this avoid useless entry in cache
    # @ram.cache(query_state_cachekey)
    def query_state(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    security.declarePublic('get_self')

    def get_self(self):
        '''Similar to MeetingItem.get_self. Check MeetingItem.py for more
           info.'''
        res = self
        if self.getTagName() != 'Meeting':
            res = self.context
        return res

    security.declarePublic('is_decided')

    def is_decided(self):
        meeting = self.get_self()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        meeting_wf = cfg.getMeetingWorkflow(True)
        if "decided" in meeting_wf.states:
            return meeting.query_state() in ('decided', 'closed', 'decisions_published', )
        else:
            # when using no_decide, items may be decided when meeting is frozen
            # and when using no_freeze, items may be decided when meeting is created
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
        meeting_uid = self.UID()
        for recurring_item in recurring_items:
            # Set current meeting as preffered meeting, this way it will
            # be considered as "late item" for this meeting if relevant.
            new_items.append(recurring_item.clone(
                cloneEventAction='Add recurring item',
                destFolder=dest_folder,
                keepProposingGroup=True,
                newPortalType=cfg.getItemTypeName(),
                item_attrs={'preferredMeeting': meeting_uid}))
        for new_item in new_items:
            # Put the new item in the correct state
            adapted = new_item.adapted()
            error = adapted.addRecurringItemToMeeting(self)
            if not error:
                notify(ItemDuplicatedFromConfigEvent(new_item, 'as_recurring_item'))

    security.declarePublic('number_of_items')

    def number_of_items(self, as_str=False):
        '''How much items in this meeting ?
           If p_as_str=True, we return a str.  This is necessary when returned
           for JS as when 0, nothing is returned by Zope.'''
        if as_str:
            return str(getattr(self, "_number_of_items"))
        else:
            return getattr(self, "_number_of_items")

    security.declarePublic('show_votes')

    def show_votes(self):
        '''See doc in interfaces.py.'''
        res = False
        meeting = self.get_self()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        if cfg.getUseVotes() or meeting.get_voters():
            res = True
        return res

    security.declarePublic('get_previous_meeting')

    def get_previous_meeting(self, interval=180):
        '''Gets the previous meeting based on meeting date. We only search among
           meetings in the previous p_interval, which is a number
           of days. If no meeting is found, the method returns None.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meeting_type_name = cfg.getMeetingTypeName()
        catalog = api.portal.get_tool('portal_catalog')
        # find every meetings before searchMeetingsInterval days before self
        brains = catalog(
            portal_type=meeting_type_name,
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


class MeetingSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        # return (IMeetingCustomSample, )
        return (IMeeting, )


class MeetingCollection(Collection):
    """ """

    def _set_sort_on(self, value):
        self.context.sort_on = value

    def _get_sort_on(self, force_linked_items_query=False):
        if displaying_available_items(self.context) and not force_linked_items_query:
            return 'getProposingGroup'
        else:
            return 'getItemNumber'

    sort_on = property(_get_sort_on, _set_sort_on)

    def _set_query(self, value):
        self.context.query = value

    def _get_query(self, force_linked_items_query=False, **kwargs):
        """Override default ICollection behavior _get_query to manage our own."""
        # available items?
        if displaying_available_items(self.context) and not force_linked_items_query:
            res = self.context._available_items_query()
        else:
            res = [{'i': 'meeting_uid',
                    'o': 'plone.app.querystring.operation.selection.is',
                    'v': self.context.UID()}, ]
        return res

    query = property(_get_query, _set_query)


class MeetingSearchableTextExtender(object):
    adapts(IMeeting)
    implements(IDynamicTextIndexExtender)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        """Include annexes title in SearchableText."""
        res = []
        for annex in get_annexes(self.context):
            res.append(annex.Title())
        res = ' '.join(res)
        return res


@implementer(ITokenizedTerm)
class UnicodeSimpleTerm(object):
    """Simple tokenized term used by SimpleVocabulary that may have unicode value."""

    def __init__(self, value, token=None, title=None):
        """ """
        self.value = value
        if token is None:
            token = value
        # XXX change with SimpleTerm, do not str(token)
        self.token = token
        self.title = title
        if title is not None:
            directlyProvides(self, ITitledTokenizedTerm)


class PlacesVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """XXX warning, we need unicode term value, so we use UnicodeSimpleTerm.
           Indeed we store the plain value that may contain special characters."""
        terms = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # XXX with MeetingConfig AT, place is stored as utf-8, we need unicode
        places = [safe_unicode(place) for place in cfg.getPlaces().strip().split('\r\n')
                  if place.strip()]
        # history when context is a Meeting
        if context.getTagName() == "Meeting" and \
           context.place and \
           context.place not in places and \
           context.place != PLACE_OTHER:
            places.append(context.place)

        for place in places:
            terms.append(UnicodeSimpleTerm(place, place, place))
        terms.append(UnicodeSimpleTerm(
            PLACE_OTHER, PLACE_OTHER, translate('other_place',
                                                domain='PloneMeeting',
                                                context=context.REQUEST,
                                                default=u"Other")))
        return SimpleVocabulary(terms)


PlacesVocabularyFactory = PlacesVocabulary()
