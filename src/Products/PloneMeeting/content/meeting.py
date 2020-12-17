# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.directives import form
from Products.CMFCore.permissions import ManagePortal
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IMeetingContent
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.interface import implements
from zope.schema import Datetime
from zope.schema import Int
from zope.schema import Text
from zope.schema import TextLine
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget


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
        required=False,
        default_output_type=u"text/html")

    assembly_excused = Text(
        title=_(u"title_assembly_excused"),
        description=_("descr_meeting_assembly_excused"),
        required=False,
        default_output_type=u"text/html")

    assembly_absents = Text(
        title=_(u"title_assembly_absents"),
        description=_("descr_meeting_assembly_absents"),
        required=False,
        default_output_type=u"text/html")

    assembly_guests = Text(
        title=_(u"title_assembly_guests"),
        description=_("descr_assembly_guests"),
        required=False,
        default_output_type=u"text/html")

    assembly_proxies = Text(
        title=_(u"title_assembly_proxies"),
        description=_("descr_assembly_proxies"),
        required=False,
        default_output_type=u"text/html")

    assembly_staves = Text(
        title=_(u"title_assembly_staves"),
        description=_("descr_assembly_staves"),
        required=False,
        default_output_type=u"text/html")

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
