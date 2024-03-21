# -*- coding: utf-8 -*-
#
# File: Meeting.py
#
# GNU General Public License (GPL)
#

from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass
from appy.gen import No
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.config import get_registry_organizations
from collective.eeafaceted.dashboard.utils import enableFacetedDashboardFor
from copy import deepcopy
from DateTime import DateTime
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.security import fplog
from imio.prettylink.interfaces import IPrettyLink
from OFS.ObjectManager import BeforeDeleteException
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.querystring.querybuilder import queryparser
from plone.app.uuid.utils import uuidToCatalogBrain
from plone.memoize import ram
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DateTimeField
from Products.Archetypes.atapi import IntegerField
from Products.Archetypes.atapi import OrderedBaseFolder
from Products.Archetypes.atapi import OrderedBaseFolderSchema
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import RichWidget
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import StringField
from Products.Archetypes.atapi import TextAreaWidget
from Products.Archetypes.atapi import TextField
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.browser.itemchangeorder import _compute_value_to_add
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.browser.itemchangeorder import _to_integer
from Products.PloneMeeting.browser.itemchangeorder import _use_same_integer
from Products.PloneMeeting.browser.itemvotes import clean_voters_linked_to
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.interfaces import IMeetingWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions
# from Products.PloneMeeting.utils import getStatesBefore
from Products.PloneMeeting.utils import _addManagedPermissions
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import addDataChange
from Products.PloneMeeting.utils import display_as_html
from Products.PloneMeeting.utils import displaying_available_items
from Products.PloneMeeting.utils import fieldIsEmpty
from Products.PloneMeeting.utils import forceHTMLContentTypeForEmptyRichFields
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_next_meeting
from Products.PloneMeeting.utils import getCustomAdapter
from Products.PloneMeeting.utils import getDateFromDelta
from Products.PloneMeeting.utils import getFieldVersion
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import hasHistory
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.PloneMeeting.utils import ItemDuplicatedFromConfigEvent
from Products.PloneMeeting.utils import MeetingLocalRolesUpdatedEvent
from Products.PloneMeeting.utils import rememberPreviousData
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.PloneMeeting.utils import toHTMLStrikedContent
from Products.PloneMeeting.utils import transformAllRichTextFields
from Products.PloneMeeting.utils import updateAnnexesAccess
from Products.PloneMeeting.utils import validate_item_assembly_value
from zope.component import getMultiAdapter
from zope.event import notify
from zope.i18n import translate
from zope.interface import implements

import copy
import interfaces
import itertools
import logging
import os


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants -----------------------------------------
BEFOREDELETE_ERROR = 'A BeforeDeleteException was raised by "%s" while ' \
    'trying to delete a meeting with id "%s"'


# Adapters ---------------------------------------------------------------------
class MeetingWorkflowConditions(object):
    '''Adapts a meeting to interface IMeetingWorkflowConditions.'''
    implements(IMeetingWorkflowConditions)
    security = ClassSecurityInfo()

    def __init__(self, meeting):
        self.context = meeting
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    security.declarePublic('mayAcceptItems')

    def mayAcceptItems(self):
        if self.context.query_state() in self.cfg.getMeetingStatesAcceptingItemsForMeetingManagers():
            return True

    security.declarePublic('mayPublish')

    def mayPublish(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayPublishDecisions')

    def mayPublishDecisions(self):
        '''Used when 'hide_decisions_when_under_writing' wfAdaptation is active.'''
        res = False
        # The user just needs the "Review portal content" permission on the object
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayFreeze')

    def mayFreeze(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayDecide')

    def mayDecide(self):
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayCorrect')

    def mayCorrect(self, destinationState=None):
        '''See doc in interfaces.py.'''
        if not _checkPermission(ReviewPortalContent, self.context):
            return

        meeting_state = self.context.query_state()
        if meeting_state == 'closed':
            if self.tool.isManager(realManagers=True) or \
               'meetingmanager_correct_closed_meeting' in self.cfg.getWorkflowAdaptations():
                return True
            else:
                return No(_('closed_meeting_not_correctable_by_config'))

        return True

    security.declarePublic('mayClose')

    def mayClose(self):
        if _checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayChangeItemsOrder')

    def mayChangeItemsOrder(self):
        res = True
        if not _checkPermission(ModifyPortalContent, self.context) or \
           self.context.query_state() in Meeting.meetingClosedStates:
            res = False
        return res


InitializeClass(MeetingWorkflowConditions)


class MeetingWorkflowActions(object):
    '''Adapts a meeting to interface IMeetingWorkflowActions.'''
    implements(IMeetingWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, meeting):
        self.context = meeting
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    security.declarePrivate('initSequenceNumber')

    def initSequenceNumber(self):
        '''When a meeting is published (or frozen, depending on workflow
           adaptations), we attribute him a sequence number.'''
        if self.context.getMeetingNumber() != -1:
            return  # Already done.
        if self.cfg.getYearlyInitMeetingNumber():
            # I must reinit the meeting number to 0 if it is the first
            # meeting of this year.
            prev = self.context.getPreviousMeeting()
            if prev and \
               (prev.getDate().year() != self.context.getDate().year()):
                self.context.setMeetingNumber(1)
                self.cfg.setLastMeetingNumber(1)
                return
        # If we are here, we must simply increment the meeting number.
        meetingNumber = self.cfg.getLastMeetingNumber() + 1
        self.context.setMeetingNumber(meetingNumber)
        self.cfg.setLastMeetingNumber(meetingNumber)

    security.declarePrivate('doPublish')

    def doPublish(self, stateChange):
        '''When publishing the meeting, initialize the sequence number.'''
        self.initSequenceNumber()

    security.declarePrivate('doFreeze')

    def doFreeze(self, stateChange):
        '''When freezing the meeting, we initialize sequence number.'''
        self.initSequenceNumber()

    security.declarePrivate('doDecide')

    def doDecide(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doClose')

    def doClose(self, stateChange):
        ''' '''
        # Set the firstItemNumber
        unrestrictedMethodsView = getMultiAdapter((self.context, self.context.REQUEST),
                                                  name='pm_unrestricted_methods')
        self.context.setFirstItemNumber(unrestrictedMethodsView.findFirstItemNumber())
        self.context.updateItemReferences()
        # remove annex previews of every items if relevant
        if self.cfg.getRemoveAnnexesPreviewsOnMeetingClosure():
            # add logging message to fingerpointing log
            for item in self.context.get_items(ordered=True):
                annexes = get_annexes(item)
                if annexes:
                    for annex in annexes:
                        self.tool._removeAnnexPreviewFor(item, annex)
                extras = 'item={0} number_of_annexes={1}'.format(repr(item), len(annexes))
                fplog('remove_annex_previews', extras=extras)
            msg = translate(
                u"Preview of annexes were deleted upon meeting closure.",
                domain='PloneMeeting',
                context=self.context.REQUEST)
            api.portal.show_message(msg, request=self.context.REQUEST)

    security.declarePrivate('doPublish_decisions')

    def doPublish_decisions(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doBackToCreated')

    def doBackToCreated(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doBackToDecided')

    def doBackToDecided(self, stateChange):
        # Oups when closing a meeting we have updated the firsItemNumber
        # we need to reverse our action
        self.context.setFirstItemNumber(-1)

    security.declarePrivate('doBackToPublished')

    def doBackToPublished(self, stateChange):
        wfTool = api.portal.get_tool('portal_workflow')
        for item in self.context.get_items():
            if item.query_state() == 'itemfrozen':
                wfTool.doActionFor(item, 'backToItemPublished')
                if item.isLate():
                    wfTool.doActionFor(item, 'backToPresented')
                    # This way we "hide" again all late items.

    security.declarePrivate('doBackToDecisionsPublished')

    def doBackToDecisionsPublished(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doBackToFrozen')

    def doBackToFrozen(self, stateChange):
        pass


InitializeClass(MeetingWorkflowActions)

schema = Schema((

    StringField(
        name='title',
        widget=StringField._properties['widget'](
            visible=False,
            label='Title',
            label_msgid='PloneMeeting_label_title',
            i18n_domain='PloneMeeting',
        ),
        accessor="Title",
        searchable=True,
    ),
    DateTimeField(
        name='date',
        widget=DateTimeField._properties['widget'](
            label='Date',
            label_msgid='PloneMeeting_label_date',
            i18n_domain='PloneMeeting',
        ),
        required=True,
    ),
    DateTimeField(
        name='startDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('startDate') and not here.isTemporary()",
            minute_step=1,
            label='Startdate',
            label_msgid='PloneMeeting_label_startDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    DateTimeField(
        name='midDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('midDate') and not here.isTemporary()",
            minute_step=1,
            label='Middate',
            label_msgid='PloneMeeting_label_midDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    DateTimeField(
        name='endDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('endDate') and not here.isTemporary()",
            minute_step=1,
            label='Enddate',
            label_msgid='PloneMeeting_label_endDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    DateTimeField(
        name='approvalDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('approvalDate')",
            minute_step=1,
            label='Approvaldate',
            label_msgid='PloneMeeting_label_approvalDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    DateTimeField(
        name='convocationDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('convocationDate')",
            minute_step=1,
            label='Convocationdate',
            label_msgid='PloneMeeting_label_convocationDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    TextField(
        name='assembly',
        allowable_content_types="text/plain",
        widget=TextAreaWidget(
            condition="python: 'assembly' in here.shownAssemblyFields()",
            label_msgid="meeting_assembly",
            description="MeetingAssembly",
            description_msgid="assembly_meeting_descr",
            label_method="getLabelAssembly",
            label='Assembly',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/plain",
        default_method="getDefaultAssembly",
        default_output_type="text/html",
        optional=True,
    ),
    TextField(
        name='assemblyExcused',
        allowable_content_types="text/plain",
        optional=True,
        widget=TextAreaWidget(
            condition="python: 'assemblyExcused' in here.shownAssemblyFields()",
            description="MeetingAssemblyExcused",
            description_msgid="assembly_excused_meeting_descr",
            label='Assemblyexcused',
            label_msgid='meeting_assemblyExcused',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_content_type="text/plain",
    ),
    TextField(
        name='assemblyAbsents',
        allowable_content_types="text/plain",
        optional=True,
        widget=TextAreaWidget(
            condition="python: 'assemblyAbsents' in here.shownAssemblyFields()",
            description="MeetingAssemblyAbsents",
            description_msgid="assembly_absents_meeting_descr",
            label='Assemblyabsents',
            label_msgid='meeting_assemblyAbsents',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_content_type="text/plain",
    ),
    TextField(
        name='assemblyGuests',
        allowable_content_types="text/plain",
        optional=True,
        widget=TextAreaWidget(
            condition="python: 'assemblyGuests' in here.shownAssemblyFields()",
            label='Assemblyguests',
            label_msgid='meeting_assemblyGuests',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_content_type="text/plain",
    ),
    TextField(
        name='assemblyProxies',
        allowable_content_types="text/plain",
        optional=True,
        widget=TextAreaWidget(
            condition="python: 'assemblyProxies' in here.shownAssemblyFields()",
            label='Assemblyproxies',
            label_msgid='meeting_assemblyProxies',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_content_type="text/plain",
    ),
    TextField(
        name='assemblyStaves',
        allowable_content_types="text/plain",
        optional=True,
        widget=TextAreaWidget(
            condition="python: 'assemblyStaves' in here.shownAssemblyFields()",
            label='Assemblystaves',
            label_msgid='meeting_assemblyStaves',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_method="getDefaultAssemblyStaves",
        default_content_type="text/plain",
    ),
    TextField(
        name='signatures',
        allowable_content_types=('text/plain',),
        optional=True,
        widget=TextAreaWidget(
            condition="here/showSignatures",
            label_msgid="meeting_signatures",
            label='Signatures',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default_method="getDefaultSignatures",
    ),
    StringField(
        name='place',
        widget=StringField._properties['widget'](
            condition="python: here.attribute_is_used('place')",
            label='Place',
            label_msgid='PloneMeeting_label_place',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        searchable=True,
    ),
    BooleanField(
        name='extraordinarySession',
        default=False,
        widget=BooleanField._properties['widget'](
            condition="python: here.attribute_is_used('extraordinarySession')",
            label='Extraordinarysession',
            label_msgid='PloneMeeting_label_extraordinarySession',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    TextField(
        name='inAndOutMoves',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('inAndOutMoves')",
            description="InAndOutMoves",
            description_msgid="field_reserved_to_meeting_managers_descr",
            label_msgid="PloneMeeting_inAndOutMoves",
            label='Inandoutmoves',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
        searchable=True,
    ),
    TextField(
        name='notes',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('notes')",
            description="Notes",
            description_msgid="field_reserved_to_meeting_managers_descr",
            label_msgid="PloneMeeting_notes",
            label='Notes',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    TextField(
        name='observations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('observations')",
            description="Observations",
            description_msgid="field_vieawable_by_everyone_descr",
            label_msgid="PloneMeeting_meetingObservations",
            label='Observations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    DateTimeField(
        name='preMeetingDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('preMeetingDate')",
            label='Premeetingdate',
            label_msgid='PloneMeeting_label_preMeetingDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    StringField(
        name='preMeetingPlace',
        widget=StringField._properties['widget'](
            condition="python: here.attribute_is_used('preMeetingPlace')",
            label='Premeetingplace',
            label_msgid='PloneMeeting_label_preMeetingPlace',
            i18n_domain='PloneMeeting',
        ),
        searchable=True,
        optional=True,
    ),
    TextField(
        name='preObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('preObservations')",
            description_msgid="field_vieawable_by_everyone_descr",
            label='Preobservations',
            label_msgid='PloneMeeting_label_preObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    TextField(
        name='committeeObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('committeeObservations')",
            description_msgid="field_vieawable_by_everyone_descr",
            label='Committeeobservations',
            label_msgid='PloneMeeting_label_committeeObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    TextField(
        name='votesObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('votesObservations') and "
                      "here.adapted().show_votesObservations()",
            description_msgid="field_vieawable_by_everyone_once_meeting_decided_descr",
            label='Votesobservations',
            label_msgid='PloneMeeting_label_votesObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    TextField(
        name='publicMeetingObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.attribute_is_used('publicMeetingObservations')",
            description_msgid="field_vieawable_by_everyone_descr",
            label='Publicmeetingobservations',
            label_msgid='PloneMeeting_label_publicMeetingObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    TextField(
        name='secretMeetingObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('secretMeetingObservations')",
            description="Secretmeetingobservations",
            description_msgid="field_reserved_to_meeting_managers_descr",
            label='Secretmeetingobservations',
            label_msgid='PloneMeeting_label_secretMeetingObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    TextField(
        name='authorityNotice',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showMeetingManagerReservedField('authorityNotice')",
            description="AuthorityNotice",
            description_msgid="field_reserved_to_meeting_managers_descr",
            label='Authoritynotice',
            label_msgid='PloneMeeting_label_authorityNotice',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        searchable=True,
        optional=True,
    ),
    IntegerField(
        name='meetingNumber',
        default=-1,
        widget=IntegerField._properties['widget'](
            label='Meetingnumber',
            label_msgid='PloneMeeting_label_meetingNumber',
            i18n_domain='PloneMeeting',
        ),
        write_permission="Manage portal",
    ),
    IntegerField(
        name='firstItemNumber',
        default=-1,
        widget=IntegerField._properties['widget'](
            label='Firstitemnumber',
            label_msgid='PloneMeeting_label_firstItemNumber',
            i18n_domain='PloneMeeting',
        ),
        required=True,
        validators=('isInt', ),
        write_permission="Manage portal",
    ),
    StringField(
        name='meetingConfigVersion',
        widget=StringField._properties['widget'](
            label='Meetingconfigversion',
            label_msgid='PloneMeeting_label_meetingConfigVersion',
            i18n_domain='PloneMeeting',
        ),
        write_permission="Manage portal",
    ),
    DateTimeField(
        name='deadlinePublish',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('deadlinePublish') and not here.isTemporary()",
            label='Deadlinepublish',
            label_msgid='PloneMeeting_label_deadlinePublish',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    DateTimeField(
        name='deadlineFreeze',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attribute_is_used('deadlineFreeze') and not here.isTemporary()",
            label='Deadlinefreeze',
            label_msgid='PloneMeeting_label_deadlineFreeze',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),

),
)

Meeting_schema = OrderedBaseFolderSchema.copy() + \
    schema.copy()


class Meeting(OrderedBaseFolder, BrowserDefaultMixin):
    """ A meeting made of items """
    security = ClassSecurityInfo()
    implements(interfaces.IMeeting)

    meta_type = 'Meeting'
    _at_rename_after_creation = True

    schema = Meeting_schema

    meetingClosedStates = ['closed']

    # declarePublic so it is callable in item view template
    # when the meeting is not viewable by the current user
    security.declarePublic('getAssembly')

    security.declarePublic('getPrettyLink')

    def getPrettyLink(self,
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
        adapted.contentValue = tool.formatMeetingDate(self,
                                                      withHour=True,
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

    security.declarePublic('getRawQuery')

    def getRawQuery(self, force_linked_items_query=False, **kwargs):
        """Override default getRawQuery to manage our own."""
        # available items?
        if displaying_available_items(self) and not force_linked_items_query:
            res = self._availableItemsQuery()
        else:
            res = [{'i': 'linkedMeetingUID',
                    'o': 'plone.app.querystring.operation.selection.is',
                    'v': self.UID()}, ]
        return res

    def _availableItemsQuery(self):
        '''Check docstring in IMeeting.'''
        meeting = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        if meeting.query_state() not in cfg.getMeetingStatesAcceptingItemsForMeetingManagers():
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
        late_state = self.adapted().getLateState()
        if meeting.query_state() in self.getStatesBefore(late_state):
            # get items for which the getPreferredMeetingDate is lower or
            # equal to the date of this meeting (self)
            # a no preferred meeting item getPreferredMeetingDate is 1950/01/01
            res.append({'i': 'getPreferredMeetingDate',
                        'o': 'plone.app.querystring.operation.date.lessThan',
                        'v': meeting.getDate()})
        else:
            # after late state, only query items for which preferred meeting is self
            res.append({'i': 'getPreferredMeetingDate',
                        'o': 'plone.app.querystring.operation.date.between',
                        'v': (DateTime('2000/01/01'), meeting.getDate())})
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
        itemNonAttendees = self.getItemNonAttendees(by_persons=by_persons)
        itemAbsents = self.get_item_absents(by_persons=by_persons)
        itemExcused = self.get_item_excused(by_persons=by_persons)
        itemSignatories = self.get_item_signatories(by_signatories=by_persons)
        if only_keys:
            redefined_item_attendees = itemNonAttendees.keys() + \
                itemAbsents.keys() + itemExcused.keys() + itemSignatories.keys()
        else:
            redefined_item_attendees = itemNonAttendees, itemAbsents, \
                itemExcused, itemSignatories
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
            stored_attendees = self.get_all_used_held_positions(the_objects=False)
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
                stored_voters = self.get_voters()
                meeting_voters = [voter.split('_')[1] for voter
                                  in REQUEST.form.get('meeting_voters', [])]
                removed_meeting_voters = set(stored_voters).difference(meeting_voters)
                # public, voters are known
                item_votes = self.get_item_votes()
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

    security.declarePublic('displayStrikedAssembly')

    def displayStrikedAssembly(self):
        """ """
        return toHTMLStrikedContent(self.getAssembly())

    security.declarePublic('displaySignatures')

    def displaySignatures(self):
        """Display signatures as HTML, make sure lines added at end
           of signatures are displayed on screen correctly."""
        return display_as_html(self.getSignatures(), self)

    security.declarePublic('get_all_used_held_positions')

    def get_all_used_held_positions(self, include_new=False, the_objects=True):
        '''This will return every currently stored held_positions.
           If include_new=True, extra held_positions newly selected in the
           configuration are added.
           If p_the_objects=True, we return held_position objects, UID otherwise.
           '''
        # used Persons are held_positions stored in orderedContacts
        contacts = hasattr(self.aq_base, 'orderedContacts') and list(self.orderedContacts) or []
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
            def getKey(item):
                return contacts.index(item.UID)
            brains = sorted(brains, key=getKey)
            contacts = [brain.getObject() for brain in brains]
        return tuple(contacts)

    security.declarePublic('getDefaultAttendees')

    def getDefaultAttendees(self):
        '''The default attendees are the active held_positions
           with 'present' in defaults.'''
        res = []
        if self.checkCreationFlag():
            used_held_positions = self.get_all_used_held_positions(include_new=True)
            res = [held_pos.UID() for held_pos in used_held_positions
                   if held_pos.defaults and 'present' in held_pos.defaults]
        return res

    security.declarePublic('getDefaultSignatories')

    def getDefaultSignatories(self):
        '''The default signatories are the active held_positions
           with a defined signature_number.'''
        res = []
        if self.checkCreationFlag():
            used_held_positions = self.get_all_used_held_positions(include_new=True)
            res = [held_pos for held_pos in used_held_positions
                   if held_pos.defaults and 'present' in held_pos.defaults and held_pos.signature_number]
        return {signer.UID(): signer.signature_number for signer in res}

    security.declarePublic('getDefaultVoters')

    def getDefaultVoters(self):
        '''The default voters are the active held_positions
           with 'voter' in defaults.'''
        res = []
        if self.checkCreationFlag():
            used_held_positions = self.get_all_used_held_positions(include_new=True)
            res = [held_pos.UID() for held_pos in used_held_positions
                   if held_pos.defaults and 'voter' in held_pos.defaults]
        return res

    def _getContacts(self, contact_type=None, uids=None, theObjects=False):
        """ """
        res = []
        orderedContacts = getattr(self, 'orderedContacts', OrderedDict())
        if contact_type:
            for uid, infos in orderedContacts.items():
                if infos[contact_type] and (not uids or uid in uids):
                    res.append(uid)
        else:
            res = uids

        if theObjects:
            catalog = api.portal.get_tool('portal_catalog')
            brains = catalog(UID=res)
            res = [brain.getObject() for brain in brains]

            # keep correct order that was lost by catalog query
            def getKey(item):
                return self.orderedContacts.keys().index(item.UID())
            res = sorted(res, key=getKey)
        return tuple(res)

    security.declarePublic('get_attendees')

    def get_attendees(self, theObjects=False):
        '''Returns the attendees in this meeting.'''
        return self._getContacts('attendee', theObjects=theObjects)

    security.declarePublic('getExcused')

    def getExcused(self, theObjects=False):
        '''Returns the excused in this meeting.'''
        return self._getContacts('excused', theObjects=theObjects)

    security.declarePublic('getAbsents')

    def getAbsents(self, theObjects=False):
        '''Returns the absents in this meeting.'''
        return self._getContacts('absent', theObjects=theObjects)

    security.declarePublic('get_voters')

    def get_voters(self, uids=None, theObjects=False):
        '''Returns the voters in this meeting.'''
        voters = self._getContacts('voter', uids=uids, theObjects=theObjects)
        return voters

    security.declarePublic('get_signatories')

    def get_signatories(self, theObjects=False, by_signature_number=False):
        '''See docstring in previous method.'''
        signers = self._getContacts('signer', theObjects=theObjects)
        # order is important in case we have several same signature_number, the first win
        if theObjects:
            res = OrderedDict(
                [(signer, self.orderedContacts[signer.UID()]['signature_number'])
                 for signer in signers])
        else:
            res = OrderedDict(
                [(signer_uid, self.orderedContacts[signer_uid]['signature_number'])
                 for signer_uid in signers])
        if by_signature_number:
            # reverse res so when several same signature_number, the first win
            res = OrderedDict(reversed(res.items()))
            # keys are values, values are keys
            res = {v: k for k, v in res.items()}
        return dict(res)

    security.declarePublic('getReplacements')

    def getReplacements(self, theObjects=False):
        '''See docstring in previous method.'''
        replaced_uids = self._getContacts('replacement', theObjects=theObjects)
        return {replaced_uid: self.orderedContacts[replaced_uid]['replacement']
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
        return self._get_item_not_present(self.itemAbsents, by_persons=by_persons)

    security.declarePublic('get_item_excused')

    def get_item_excused(self, by_persons=False):
        ''' '''
        return self._get_item_not_present(self.itemExcused, by_persons=by_persons)

    security.declarePublic('getItemNonAttendees')

    def getItemNonAttendees(self, by_persons=False):
        ''' '''
        return self._get_item_not_present(self.itemNonAttendees, by_persons=by_persons)

    security.declarePublic('get_item_signatories')

    def get_item_signatories(self, by_signatories=False, include_position_type=False):
        '''Return itemSignatories, by default the itemSignatories dict has the item UID as key and list
           of signatories as values but if 'p_by_signatories' is True, the informations are returned with
           signatory as key and list of items as value.
           p_include_position_type=True is only relevant when p_by_signatories=False.'''
        signatories = {}
        if by_signatories:
            for item_uid, signatories_infos in self.itemSignatories.items():
                for signature_number, signatory_infos in signatories_infos.items():
                    # do not keep 'position_type' from the stored itemSignatories
                    signatory_uid = signatory_infos['hp_uid']
                    if signatory_uid not in signatories:
                        signatories[signatory_uid] = []
                    signatories[signatory_uid].append(item_uid)
        else:
            for item_uid, signatory_infos in self.itemSignatories.data.items():
                if include_position_type:
                    signatories[item_uid] = signatory_infos.copy()
                else:
                    signatories[item_uid] = {k: v['hp_uid'] for k, v in signatory_infos.items()}

        return signatories

    def get_signature_infos_for(self,
                                item_uid,
                                signatory_uid,
                                render_position_type=False,
                                prefix_position_type=False):
        """Return the signature position_type to use as label and signature_number
           for given p_item_uid and p_signatory_uid."""
        # check if signatory_uid is redefined on the item
        data = self.get_item_signatories(by_signatories=False, include_position_type=True)
        data = {k: v for k, v in data[item_uid].items()
                if v['hp_uid'] == signatory_uid}
        catalog = api.portal.get_tool('portal_catalog')
        hp = catalog(UID=signatory_uid)[0].getObject()
        if data:
            signature_number, position_type = data.items()[0]
        else:
            # if not, then get it from meeting signatories
            signature_number = self.getSignatories()[signatory_uid]
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

    security.declarePublic('get_item_votes')

    def get_item_votes(self):
        ''' '''
        votes = deepcopy(self.itemVotes.data)
        return votes

    security.declarePrivate('setItemPublicVote')

    def setItemPublicVote(self, item, data, vote_number=0):
        """ """
        data = deepcopy(data)
        item_uid = item.UID()
        # set new itemVotes value on meeting
        # first votes
        if item_uid not in self.itemVotes:
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
        if vote_number + 1 > len(self.itemVotes[item_uid]):
            # complete data before storing, if some voters are missing it is
            # because of NOT_VOTABLE_LINKED_TO_VALUE, we add it
            item_voter_uids = item.get_item_voters()
            for item_voter_uid in item_voter_uids:
                if item_voter_uid not in data['voters']:
                    data['voters'][item_voter_uid] = NOT_VOTABLE_LINKED_TO_VALUE
            self.itemVotes[item_uid].append(PersistentMapping(data))
        else:
            # use update in case we only update a subset of votes
            # when some vote NOT_VOTABLE_LINKED_TO_VALUE or so
            # we have nested dicts, data is a dict, containing 'voters' dict
            self.itemVotes[item_uid][vote_number]['voters'].update(data['voters'])
            data.pop('voters')
            self.itemVotes[item_uid][vote_number].update(data)
        # manage linked_to_previous
        # if current vote is linked to other votes, we will set NOT_VOTABLE_LINKED_TO_VALUE
        # as value of vote of voters of other linked votes
        clean_voters_linked_to(item, self, vote_number, new_voters)

    security.declarePrivate('setItemSecretVote')

    def setItemSecretVote(self, item, data, vote_number):
        """ """
        data = deepcopy(data)
        item_uid = item.UID()
        # set new itemVotes value on meeting
        # first votes
        if item_uid not in self.itemVotes:
            self.itemVotes[item_uid] = PersistentList()
            # check if we are not adding a new vote on an item containing no votes at all
            if vote_number == 1:
                # add an empty vote 0
                data_item_vote_0 = item.get_item_votes(
                    vote_number=0,
                    include_vote_number=False,
                    include_unexisting=True)
                self.itemVotes[item_uid].append(PersistentMapping(data_item_vote_0))
        # new vote_number
        if vote_number + 1 > len(self.itemVotes[item_uid]):
            self.itemVotes[item_uid].append(PersistentMapping(data))
        else:
            self.itemVotes[item_uid][vote_number].update(data)

    security.declarePublic('displayUserReplacement')

    def displayUserReplacement(self,
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
           items if date value changed.  Moreover we manage updateItemReferences
           if value changed.'''
        current_date = self.getField('date').get(self, **kwargs)
        if not value == current_date:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
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
           updateItemReferences if value changed.'''
        current_first_item_number = self.getField('firstItemNumber').get(self, **kwargs)
        if not value == current_first_item_number:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
        self.getField('firstItemNumber').set(self, value, **kwargs)

    security.declarePrivate('setMeetingNumber')

    def setMeetingNumber(self, value, **kwargs):
        '''Overrides the field 'meetingNumber' mutator to be able to
           updateItemReferences if value changed.'''
        current_meetingNumber = self.getField('meetingNumber').get(self, **kwargs)
        if not value == current_meetingNumber:
            # add a value in the REQUEST to specify that updateItemReferences is needed
            self.REQUEST.set('need_Meeting_updateItemReferences', True)
        self.getField('meetingNumber').set(self, value, **kwargs)

    security.declarePublic('showMeetingManagerReservedField')

    def showMeetingManagerReservedField(self, name):
        '''When must field named p_name be shown?'''
        tool = api.portal.get_tool('portal_plonemeeting')
        res = not self.isTemporary() and \
            tool.isManager(self) and \
            self.attribute_is_used(name)
        return res

    security.declarePrivate('validate_preMeetingDate')

    def validate_preMeetingDate(self, value):
        '''Checks that the preMeetingDate comes before the meeting date.'''
        if not value or not self.attribute_is_used('preMeetingDate'):
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
                 listTypes=[],
                 ordered=False,
                 theObjects=True,
                 additional_catalog_query={},
                 unrestricted=False,
                 force_linked_items_query=True):
        '''Overrides the Meeting.items accessor.
           Items can be filtered depending on :
           - list of given p_uids;
           - given p_listTypes;
           - returned ordered (by getItemNumber) if p_ordered is True;
           - if p_theObjects is True, MeetingItem objects are returned, else, brains are returned;
           - if p_unrestricted is True it will return every items, not checking permission;
           - if p_force_linked_items_query is True, it will call self.getRawQuery with
             same parameter and force use of query showing linked items, not displaying
             available items.
        '''
        # execute the query using the portal_catalog
        catalog = api.portal.get_tool('portal_catalog')
        catalog_query = self.getRawQuery(force_linked_items_query=force_linked_items_query)
        if listTypes:
            catalog_query.append({'i': 'listType',
                                  'o': 'plone.app.querystring.operation.selection.is',
                                  'v': listTypes},)
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

        if theObjects:
            res = [brain._unrestrictedGetObject() for brain in res]
        return res

    def getRawItems(self):
        """Simply get linked items."""
        catalog = api.portal.get_tool('portal_catalog')
        catalog_query = self.getRawQuery(force_linked_items_query=True)
        query = queryparser.parseFormquery(self, catalog_query)
        res = [brain.UID for brain in catalog.unrestrictedSearchResults(**query)]
        return res

    security.declarePublic('getItemsInOrder')

    def getItemsInOrder(self, late=False, uids=[]):
        """Deprecated, use Meeting.getItems instead."""
        logger.warn('Meeting.getItemsInOrder is deprecated, use Meeting.get_items(ordered=True) instead.')
        listTypes = late and ['late'] or ['normal']
        if '' in uids:
            uids.remove('')
        return self.get_items(uids=uids, listTypes=listTypes, ordered=True)

    security.declarePublic('getItemByNumber')

    def getItemByNumber(self, number):
        '''Gets the item thas has number p_number.'''
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(linkedMeetingUID=self.UID(), getItemNumber=number)
        if not brains:
            return None
        return brains[0].getObject()

    def getLateState(self):
        '''See doc in interfaces.py.'''
        return 'frozen'

    def getStatesBefore_cachekey(method, self, review_state):
        '''cachekey method for self.getStatesBefore.'''
        # do only re-compute if cfg changed or params changed
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return (cfg.getId(), cfg._p_mtime, review_state)

    @ram.cache(getStatesBefore_cachekey)
    def getStatesBefore(self, review_state):
        """
          Returns states before the p_review_state state.
        """
        return getStatesBefore(self, review_state)

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

    def getItemInsertOrder(self, item, cfg, check_cache=True):
        '''Get p_item insertOrder taking cache into account.'''
        # check if cache still valid, will be invalidated if not
        if check_cache:
            self.adapted()._check_insert_order_cache(cfg)
        insert_order = self._insert_order_cache['items'].get(item.UID(), None)
        if insert_order is None or not isinstance(insert_order, list):
            insert_order = item.adapted()._getInsertOrder(cfg)
            self._insert_order_cache['items'][item.UID()] = insert_order
        return insert_order

    security.declareProtected(ModifyPortalContent, 'insertItem')

    def insertItem(self, item, forceNormal=False):
        '''Inserts p_item into my list of "normal" items or my list of "late"
           items. If p_forceNormal is True, and the item should be inserted as
           a late item, it is nevertheless inserted as a normal item.'''
        # First, determine if we must insert the item into the "normal"
        # list of items or to the list of "late" items. Note that I get
        # the list of items *in order* in the case I need to insert the item
        # at another place than at the end.
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        isLate = not forceNormal and item.wfConditions().isLateFor(self)
        if isLate:
            item.setListType(item.adapted().getListTypeLateValue(self))
            toDiscussValue = cfg.getToDiscussLateDefault()
        else:
            item.setListType(item.adapted().getListTypeNormalValue(self))
            toDiscussValue = cfg.getToDiscussDefault()
        items = self.get_items(ordered=True)
        # Set the correct value for the 'toDiscuss' field if required
        if cfg.getToDiscussSetOnItemInsert():
            item.setToDiscuss(toDiscussValue)
        # At what place must we insert the item in the list ?
        insertMethods = cfg.getInsertingMethodsOnAddItem()
        # wipe out insert methods as stored value is a DataGridField
        # and we only need a tuple of insert methods
        insertAtTheEnd = False
        if insertMethods[0]['insertingMethod'] != 'at_the_end':
            # We must insert it according to category or proposing group order
            # (at the end of the items belonging to the same category or
            # proposing group). We will insert the p_item just before the first
            # item whose category/group immediately follows p_item's category/
            # group (or at the end if inexistent). Note that the MeetingManager,
            # in subsequent manipulations, may completely change items order.
            self.adapted()._check_insert_order_cache(cfg)
            itemOrder = self.getItemInsertOrder(item, cfg, check_cache=False)
            higherItemFound = False
            insertIndex = 0  # That's where I will insert the item
            insertIndexIsSubnumber = False
            for anItem in items:
                if higherItemFound:
                    itemNumber = anItem.getItemNumber()
                    # Ok I already know where to insert the item. I just
                    # continue to visit the next items in order to increment their number.
                    # we inserted an integer numer, we need to add '1' to every next items
                    if not insertIndexIsSubnumber:
                        anItem.setItemNumber(itemNumber + 100)
                    elif (insertIndexIsSubnumber and _use_same_integer(itemNumber, insertIndex) and
                          itemNumber > insertIndex):
                        # we inserted a subnumber, we need to update subnumber of same integer
                        anItem.setItemNumber(itemNumber + 1)
                elif self.getItemInsertOrder(anItem, cfg, check_cache=False) > itemOrder:
                    higherItemFound = True
                    itemNumber = anItem.getItemNumber()
                    insertIndex = itemNumber
                    # we will only update next items of same subnumber?
                    insertIndexIsSubnumber = not _is_integer(itemNumber)
                    anItem.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))

            if higherItemFound:
                item.setItemNumber(insertIndex)
            else:
                insertAtTheEnd = True

        if insertMethods[0]['insertingMethod'] == 'at_the_end' or insertAtTheEnd:
            # insert it as next integer number
            if items:
                item.setItemNumber(_to_integer(items[-1].getItemNumber()) + 100)
            else:
                # first added item
                item.setItemNumber(100)

        # Add the item at the end of the items list
        item._update_meeting_link(self)
        self._finalize_item_insert(items_to_update=[item])

    def _finalize_item_insert(self, items_to_update=[]):
        """ """
        # invalidate RAMCache for MeetingItem.getMeeting
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')
        # reindex getItemNumber when item is in the meeting or getItemNumber returns None
        # and reindex linkedMeeting indexes that is used by updateItemReferences using getItems
        lowest_item_number = 0
        for item in items_to_update:
            itemNumber = item.getRawItemNumber()
            if not lowest_item_number or itemNumber < lowest_item_number:
                lowest_item_number = itemNumber
            item.reindexObject(idxs=['getItemNumber',
                                     'listType',
                                     'linkedMeetingUID',
                                     'linkedMeetingDate'])
        # meeting is considered modified, do this before updateItemReferences
        self.notifyModified()

        # update itemReference after 'getItemNumber' has been reindexed of item and
        # items with a higher itemNumber
        self.updateItemReferences(startNumber=lowest_item_number)

    security.declareProtected(ModifyPortalContent, 'removeItem')

    def removeItem(self, item):
        '''Removes p_item from me.'''
        # Remember the item number now; once the item will not be in the meeting
        # anymore, it will loose its number.
        itemNumber = item.getItemNumber()
        items = self.get_items()
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

        # remove item UID from self.itemAbsents/self.itemExcused and self.itemSignatories
        item_uid = item.UID()
        if item_uid in self.itemAbsents:
            del self.itemAbsents[item_uid]
        if item_uid in self.itemExcused:
            del self.itemExcused[item_uid]
        if item_uid in self.itemNonAttendees:
            del self.itemNonAttendees[item_uid]
        if item_uid in self.itemSignatories:
            del self.itemSignatories[item_uid]
        if item_uid in self.itemVotes:
            del self.itemVotes[item_uid]

        # remove item UID from _insert_order_cache
        self._invalidate_insert_order_cache_for(item)

        # make sure item assembly/signatures related fields are emptied
        for field in item.Schema().filterFields(isMetadata=False):
            if field.getName().startswith('itemAssembly') or field.getName() == 'itemSignatures':
                field.set(item, '')

        # Update item numbers
        # in case itemNumber was a subnumber (or a master having subnumber),
        # we will just update subnumbers of the same integer
        itemNumberIsSubnumber = not _is_integer(itemNumber) or bool(self.getItemByNumber(itemNumber + 1))
        for anItem in items:
            anItemNumber = anItem.getItemNumber()
            if anItemNumber > itemNumber:
                if not itemNumberIsSubnumber:
                    anItem.setItemNumber(anItem.getItemNumber() - 100)
                elif itemNumberIsSubnumber and _use_same_integer(itemNumber, anItemNumber):
                    anItem.setItemNumber(anItem.getItemNumber() - _compute_value_to_add(anItemNumber))
        # invalidate RAMCache for MeetingItem.getMeeting
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')

        # reindex relevant indexes now that item is removed
        item.reindexObject(idxs=['listType', 'linkedMeetingUID', 'linkedMeetingDate'])

        # meeting is considered modified, do this before updateItemReferences
        self.notifyModified()

        # update itemReference of item that is no more linked to self and so that will not
        # be updated by Meeting.updateItemReferences and then update items that used
        # a higher item number
        item.updateItemReference()
        self.updateItemReferences(startNumber=itemNumber)

    def updateItemReferences(self, startNumber=0, check_needed=False):
        """Update itemReference of every contained items, if p_startNumber is given,
           we update items starting from p_startNumber itemNumber.
           By default, if p_startNumber=0, every linked items will be updated.
           If p_check_needed is True, we check if value 'need_Meeting_updateItemReferences' in REQUEST is True."""
        # call to updateItemReferences may be deferred for optimization
        if self.REQUEST.get('defer_Meeting_updateItemReferences', False):
            return
        if check_needed and not self.REQUEST.get('need_Meeting_updateItemReferences', False):
            return
        # force disable 'need_Meeting_updateItemReferences' from REQUEST
        self.REQUEST.set('need_Meeting_updateItemReferences', False)

        # we query items from startNumber to last item of the meeting
        # moreover we getItems unrestricted to be sure we have every elements
        brains = self.get_items(
            ordered=True,
            theObjects=False,
            unrestricted=True,
            additional_catalog_query={
                'getItemNumber': {'query': startNumber,
                                  'range': 'min'}, })
        for brain in brains:
            item = brain._unrestrictedGetObject()
            item.updateItemReference()

    security.declarePrivate('getDefaultAssembly')

    def getDefaultAssembly(self):
        if self.attribute_is_used('assembly'):
            tool = api.portal.get_tool('portal_plonemeeting')
            return tool.getMeetingConfig(self).getAssembly()
        return ''

    security.declarePrivate('getDefaultAssemblyStaves')

    def getDefaultAssemblyStaves(self):
        if self.attribute_is_used('assemblyStaves'):
            tool = api.portal.get_tool('portal_plonemeeting')
            return tool.getMeetingConfig(self).getAssemblyStaves()
        return ''

    security.declarePrivate('getDefaultSignatures')

    def getDefaultSignatures(self):
        if self.attribute_is_used('signatures'):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            return cfg.getSignatures()
        return ''

    security.declarePrivate('updateTitle')

    def updateTitle(self):
        '''The meeting title is generated by this method, based on the meeting date.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        title = self.title
        formatted_date = tool.formatMeetingDate(self)
        if title != formatted_date:
            self.setTitle(formatted_date)
            return True

    security.declarePrivate('updatePlace')

    def updatePlace(self):
        '''Updates the place if it comes from special request field
           "place_other".'''
        rq = self.REQUEST
        if ('place' not in rq) or (rq.get('place', '') == 'other'):
            stored_place = self.getPlace()
            new_place = rq.get('place_other', '')
            if stored_place != new_place:
                self.setPlace(new_place)
                return True

    security.declarePrivate('computeDates')

    def computeDates(self):
        '''Computes, for this meeting, the dates which are derived from the
           meeting date when relevant.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        usedAttrs = cfg.getUsedMeetingAttributes()
        meetingDate = self.getDate()
        # Initialize the effective start date with the meeting date
        if 'startDate' in usedAttrs:
            self.setStartDate(meetingDate)
        # Set, by default, mid date to start date + 1 hour.
        if 'midDate' in usedAttrs:
            self.setMidDate(meetingDate + 1 / 24.0)
        # Set, by default, end date to start date + 2 hours.
        if 'endDate' in usedAttrs:
            self.setEndDate(meetingDate + 2 / 24.0)
        # Compute the publish deadline
        if 'deadlinePublish' in usedAttrs and not self.getDeadlinePublish():
            delta = cfg.getPublishDeadlineDefault()
            if not delta.strip() in ('', '0',):
                self.setDeadlinePublish(getDateFromDelta(meetingDate, '-' + delta))
        if 'deadlineFreeze' in usedAttrs and not self.getDeadlineFreeze():
            # Compute the freeze deadline
            delta = cfg.getFreezeDeadlineDefault()
            if not delta.strip() in ('', '0',):
                self.setDeadlineFreeze(getDateFromDelta(meetingDate, '-' + delta))
        if 'preMeetingDate' in usedAttrs and not self.getPreMeetingDate():
            # Compute the date for the pre-meeting
            delta = cfg.getPreMeetingDateDefault()
            if not delta.strip() in ('', '0',):
                self.setPreMeetingDate(getDateFromDelta(meetingDate, '-' + delta))

    security.declarePublic('getUserReplacements')

    def getUserReplacements(self):
        '''Gets the dict storing user replacements.'''
        res = {}
        orderedContacts = getattr(self, 'orderedContacts', OrderedDict())
        for uid, infos in orderedContacts.items():
            if infos['replacement']:
                res[uid] = infos['replacement']
        return res

    security.declarePublic('filterPossibleUserReplacement')

    def filterPossibleUserReplacement(self, allUsers):
        '''Adaptable method to filter possible user replacement.'''
        return allUsers

    def _doUpdateContacts(self,
                          attendees=OrderedDict(),
                          signatories={},
                          replacements={},
                          voters=[]):
        ''' '''
        # attendees must be an OrderedDict to keep order
        if not isinstance(attendees, OrderedDict):
            raise ValueError(
                'Parameter attendees passed to Meeting._doUpdateContacts '
                'must be an OrderedDict !!!')
        # save the ordered contacts so we rely on this, especially when
        # users are disabled in the configuration
        self.orderedContacts.clear()

        for attendee_uid, attendee_type in attendees.items():
            if attendee_uid not in self.orderedContacts:
                self.orderedContacts[attendee_uid] = \
                    {'attendee': False,
                     'excused': False,
                     'absent': False,
                     'signer': False,
                     'signature_number': None,
                     'replacement': None,
                     'voter': False}
            self.orderedContacts[attendee_uid][attendee_type] = True

        for signatory_uid, signature_number in signatories.items():
            self.orderedContacts[signatory_uid]['signer'] = True
            self.orderedContacts[signatory_uid]['signature_number'] = signature_number

        for replaced_uid, replacer_uid in replacements.items():
            self.orderedContacts[replaced_uid]['replacement'] = replacer_uid

        for voter_uid in voters:
            self.orderedContacts[voter_uid]['voter'] = True

        self._p_changed = True

    security.declarePrivate('updateContacts')

    def updateContacts(self):
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

        self._doUpdateContacts(attendees, signatories, replacements, voters)

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
        self.update_local_roles()
        # activate the faceted navigation
        enableFacetedDashboardFor(self,
                                  xmlpath=os.path.dirname(__file__) +
                                  '/faceted_conf/default_dashboard_widgets.xml')
        self.setLayout('meeting_view')
        # update every items itemReference if needed
        self.updateItemReferences(check_needed=True)
        # invalidate last meeting modified
        invalidate_cachekey_volatile_for('Products.PloneMeeting.Meeting.modified', get_again=True)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()

    def _update_after_edit(self):
        """Convenience method that make sure ObjectModifiedEvent and
           at_post_edit_script are called, like it is the case in
           Archetypes.BaseObject.processForm.
           We also call reindexObject here so we avoid multiple reindexation
           as it is already done in processForm.
           This is called when we change something on a meeting and we do not
           use processForm."""
        # WARNING, we do things the same order processForm do it
        # reindexObject is done in _processForm, then notify and
        # call to at_post_edit_script are done
        self.reindexObject()
        notify(ObjectEditedEvent(self))
        self.at_post_edit_script()

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        '''Updates the meeting title.'''
        need_reindex = self.updateTitle()
        need_reindex = self.updatePlace() or need_reindex
        # Update contact-related info (attendees, signatories, replacements...)
        self.updateContacts()
        # Add a line in history if historized fields have changed
        addDataChange(self)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # update every items itemReference if needed
        self.updateItemReferences(check_needed=True)
        # update local roles as power observers local roles may vary depending on meeting_access_on
        self.update_local_roles()
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)
        # invalidate last meeting modified
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.Meeting.modified', get_again=True)
        # invalidate item voters vocabulary in case new voters (un)selected
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.vocabularies.itemvotersvocabulary', get_again=True)
        # invalidate assembly async load on meeting
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.browser.async.AsyncLoadMeetingAssemblyAndSignatures',
            get_again=True)
        if need_reindex:
            self.reindexObject()

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
        self._updatePowerObserversLocalRoles()
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

    def _updatePowerObserversLocalRoles(self):
        '''Give local roles to the groups defined in MeetingConfig.powerObservers.'''
        extra_expr_ctx = _base_extra_expr_ctx(self)
        extra_expr_ctx.update({'meeting': self, })
        cfg = extra_expr_ctx['cfg']
        cfg_id = cfg.getId()
        meetingState = self.query_state()
        for po_infos in cfg.getPowerObservers():
            if meetingState in po_infos['meeting_states'] and \
               _evaluateExpression(self,
                                   expression=po_infos['meeting_access_on'],
                                   extra_expr_ctx=extra_expr_ctx):
                powerObserversGroupId = "%s_%s" % (cfg_id, po_infos['row_id'])
                self.manage_addLocalRoles(powerObserversGroupId, (READER_USECASES['powerobservers'],))

    security.declareProtected(ModifyPortalContent, 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

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

    security.declarePublic('attribute_is_used')

    def attribute_is_used(self, name):
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
        if self.getTagName() != 'Meeting':
            res = self.context
        return res

    security.declarePublic('setFieldFromAjax')

    def setFieldFromAjax(self, fieldName, fieldValue):
        '''See doc in utils.py.'''
        return set_field_from_ajax(self, fieldName, fieldValue)

    security.declarePublic('getFieldVersion')

    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePublic('isDecided')

    def isDecided(self):
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

    security.declarePrivate('addRecurringItems')

    def addRecurringItems(self, recurringItems):
        '''Inserts into this meeting some p_recurringItems. The newly created
           items are copied from recurring items (contained in the meeting
           config) to the folder containing this meeting.'''
        destFolder = self.getParentNode()
        newItems = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        for recurringItem in recurringItems:
            newItems.append(recurringItem.clone(cloneEventAction='Add recurring item',
                                                destFolder=destFolder,
                                                keepProposingGroup=True,
                                                newPortalType=cfg.getItemTypeName()))
        for newItem in newItems:
            # Put the new item in the correct state
            adap = newItem.adapted()
            error = adap.addRecurringItemToMeeting(self)
            if not error:
                notify(ItemDuplicatedFromConfigEvent(newItem, 'as_recurring_item'))
                newItem.reindexObject()

    security.declarePublic('fieldIsEmpty')

    def fieldIsEmpty(self, name):
        '''Is field named p_name empty ?'''
        return fieldIsEmpty(name, self)

    security.declarePublic('numberOfItems')

    def numberOfItems(self):
        '''How much items in this meeting ?'''
        return str(len(self.getRawItems()))

    security.declarePrivate('manage_beforeDelete')

    def manage_beforeDelete(self, item, container):
        '''This is a workaround to avoid a Plone design problem where it is
           possible to remove a folder containing objects you can not remove.'''
        # bypassed for migration to DX
        return
        # If we are here, everything has already been checked before.
        # Just check that the meeting is myself or a Plone Site.
        # We can remove an meeting directly but not "through" his container.
        if item.meta_type not in ('Plone Site', 'Meeting'):
            user = api.user.get_current()
            logger.warn(BEFOREDELETE_ERROR % (user.getId(), self.id))
            raise BeforeDeleteException("can_not_delete_meeting_container")
        # we are removing the meeting
        if item.meta_type == 'Meeting':
            member = api.user.get_current()
            if member.has_role('Manager'):
                item.REQUEST.set('items_to_remove', item.get_items())
        OrderedBaseFolder.manage_beforeDelete(self, item, container)

    security.declarePublic('showAttendeesFields')

    def showAttendeesFields(self):
        '''Display attendee related fields in view/edit?'''
        return (self.attribute_is_used('attendees') or self.get_attendees()) and not self.getAssembly()

    def shownAssemblyFields_cachekey(method, self):
        '''cachekey method for self.shownAssemblyFields.'''
        # do only re-compute if cfg changed or self.changed
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return (cfg.getId(), cfg._p_mtime, self.modified())

    security.declarePublic('shownAssemblyFields')

    @ram.cache(shownAssemblyFields_cachekey)
    def shownAssemblyFields(self):
        '''Return the list of shown assembly field :
           - used assembly fields;
           - not empty assembly fields.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        usedAttrs = cfg.getUsedMeetingAttributes()
        # get assembly fields
        fields = cfg._assembly_fields(field_name=False)
        return [field.getName() for field in fields
                if field.getName() in usedAttrs or field.get(self)]

    security.declarePublic('showSignatures')

    def showSignatures(self):
        '''Show the 'signatures' field?'''
        return self.attribute_is_used('signatures') or self.getSignatures()

    security.declarePublic('show_votesObservations')

    def show_votesObservations(self):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        tool = api.portal.get_tool('portal_plonemeeting')
        res = tool.isManager(meeting)
        if not res:
            cfg = tool.getMeetingConfig(meeting)
            res = isPowerObserverForCfg(cfg) or \
                meeting.adapted().isDecided()
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

    security.declarePublic('getPreviousMeeting')

    def getPreviousMeeting(self, searchMeetingsInterval=60):
        '''Gets the previous meeting based on meeting date. We only search among
           meetings in the previous p_searchMeetingsInterval, which is a number
           of days. If no meeting is found, the method returns None.'''
        meetingDate = self.getDate()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meetingTypeName = cfg.getMeetingTypeName()
        catalog = api.portal.get_tool('portal_catalog')
        # find every meetings before searchMeetingsInterval days before self
        brains = catalog(portal_type=meetingTypeName,
                         getDate={'query': meetingDate - searchMeetingsInterval,
                                  'range': 'min'}, sort_on='getDate',
                         sort_order='reverse')
        res = None
        for brain in brains:
            if brain.getDate < meetingDate:
                res = brain
                break
        if res:
            res = res.getObject()
        return res

    security.declarePublic('getNextMeeting')

    def getNextMeeting(self, cfgId='', dateGap=0):
        '''Gets the next meeting based on meeting date.
           p_cfg can be used to compare meetings from another meetingconfig
           with meeting from the current config.
           p_dateGap is the number of 'dead days' following the date of
           the current meeting in which we do not look for next meeting'''
        tool = api.portal.get_tool('portal_plonemeeting')
        if not cfgId:
            cfg = tool.getMeetingConfig(self)
        else:
            cfg = getattr(tool, cfgId)
        return get_next_meeting(meetingDate=self.getDate(), cfg=cfg, dateGap=dateGap)

    security.declareProtected(ModifyPortalContent, 'processForm')

    def processForm(self, *args, **kwargs):
        '''We override this method because we may need to remember previous
           values of historized fields.'''
        if not self.isTemporary():
            self._v_previousData = rememberPreviousData(self)
        return OrderedBaseFolder.processForm(self, *args, **kwargs)

    security.declarePublic('showInsertOrRemoveSelectedItemsAction')

    def showInsertOrRemoveSelectedItemsAction(self):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        member = api.user.get_current()
        return bool(member.has_permission(ModifyPortalContent, meeting) and
                    not meeting.query_state() in meeting.meetingClosedStates)

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


registerType(Meeting, PROJECTNAME)
