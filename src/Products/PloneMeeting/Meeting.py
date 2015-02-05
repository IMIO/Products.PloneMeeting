# -*- coding: utf-8 -*-
#
# File: Meeting.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
from appy.gen import No
from collections import OrderedDict
from App.class_init import InitializeClass
from DateTime import DateTime
from DateTime.DateTime import _findLocalTimeZoneName
from OFS.ObjectManager import BeforeDeleteException
from zope.component import getMultiAdapter
from zope.event import notify
from zope.i18n import translate
from plone.memoize import ram
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import ModifyPortalContent, ReviewPortalContent, View
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions, IMeetingWorkflowActions
from Products.PloneMeeting.utils import getWorkflowAdapter, getCustomAdapter, \
    fieldIsEmpty, checkPermission, addRecurringItemsIfRelevant, getLastEvent, \
    getMeetingUsers, getFieldVersion, getDateFromDelta, \
    rememberPreviousData, addDataChange, hasHistory, getHistory, \
    setFieldFromAjax, transformAllRichTextFields, forceHTMLContentTypeForEmptyRichFields, \
    ItemDuplicatedFromConfigEvent, cleanRamCacheFor
from Products.PloneMeeting import PMMessageFactory as _
import logging
logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants -----------------------------------------
BEFOREDELETE_ERROR = 'A BeforeDeleteException was raised by "%s" while ' \
    'trying to delete a meeting with id "%s"'
NO_SECOND_LANGUAGE_ERROR = 'Unable to find the second supported language in ' \
    'portal_languages, either only one language is supported, or more than 2 languages' \
    'are supported.  Please contact system administrator.'


# Adapters ---------------------------------------------------------------------
class MeetingWorkflowConditions:
    '''Adapts a meeting to interface IMeetingWorkflowConditions.'''
    implements(IMeetingWorkflowConditions)
    security = ClassSecurityInfo()

    # Item states when a decision was not take yet.
    notDecidedStates = ('presented', 'itempublished', 'itemfrozen')
    notDecidedStatesPlusDelayed = notDecidedStates + ('delayed',)
    # Item states when a final decision is taken
    archivableStates = ('confirmed', 'delayed', 'refused')

    # Meeting states for meetings accepting items
    acceptItemsStates = ('created', 'published', 'frozen', 'decided')

    def __init__(self, meeting):
        self.context = meeting

    def _decisionsAreArchivable(self):
        '''Returns True all the decisions may be archived.'''
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() not in self.archivableStates:
                return False
        return True

    def _decisionsWereConfirmed(self):
        '''Returns True if at least one decision was taken on an item'''
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() == 'confirmed':
                return True

    security.declarePublic('mayAcceptItems')
    def mayAcceptItems(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           (self.context.queryState() in self.acceptItemsStates):
            return True

    security.declarePublic('mayPublish')
    def mayPublish(self):
        if not checkPermission(ReviewPortalContent, self.context):
            return False
        if not self.context.getRawItems():
            return No(translate('item_required_to_publish',
                                domain="PloneMeeting",
                                context=self.context.REQUEST))
        return True

    security.declarePublic('mayPublishDecisions')
    def mayPublishDecisions(self):
        '''Used when 'hide_decisions_when_under_writing' wfAdaptation is active.'''
        res = False
        # The user just needs the "Review portal content" permission on the object
        if checkPermission(ReviewPortalContent, self.context):
            res = True
        return res

    security.declarePublic('mayFreeze')
    def mayFreeze(self):
        return self.mayPublish()

    security.declarePublic('mayDecide')
    def mayDecide(self):
        '''May decisions on this meeting be taken?'''
        if checkPermission(ReviewPortalContent, self.context):
            if not self.context.getDate().isPast():
                return No(translate('meeting_in_past', domain="PloneMeeting", context=self.context.REQUEST))
            # Check that all items are OK.
            res = True
            msgs = []
            for item in self.context.getAllItems(ordered=True):
                if item.queryState() == 'itemfrozen':
                    mayDecide = item.wfConditions().mayDecide()
                    if not mayDecide:
                        if isinstance(mayDecide, No):
                            msgs.append(mayDecide.msg)
                        res = False
                        break
            if msgs:
                res = No(u' - '.join(msgs))
            return res
        return False

    security.declarePublic('mayCorrect')
    def mayCorrect(self):
        if not checkPermission(ReviewPortalContent, self.context):
            return
        currentState = self.context.queryState()
        if currentState in ('published', 'frozen', 'decisions_published', ):
            if checkPermission(ReviewPortalContent, self.context):
                return True
        elif currentState == 'decided':
            # Going back from "decided" to previous state is not a true "undo".
            # Indeed, when a meeting is "decided", all items for which no
            # decision was taken are set in "accepted". Going back to
            # "published" does not set them back in their previous state.
            if not self._decisionsWereConfirmed():
                return True
        else:
            return True

    security.declarePublic('mayClose')
    def mayClose(self):
        if checkPermission(ReviewPortalContent, self.context):
            return True

    security.declarePublic('mayArchive')
    def mayArchive(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           self._decisionsAreArchivable():
            return True

    security.declarePublic('mayRepublish')
    def mayRepublish(self):
        return False

    security.declarePublic('mayChangeItemsOrder')
    def mayChangeItemsOrder(self):
        if not checkPermission(ModifyPortalContent, self.context):
            return
        # the meeting can not be in a closed state
        if self.context.queryState() in Meeting.meetingClosedStates:
            return
        # Once dictionaries "entrances" and "departures" are filled, changing
        # items order would lead to database incoherences.
        if hasattr(self, 'entrances') and self.entrances:
            return
        if hasattr(self, 'departures') and self.departures:
            return
        return True

InitializeClass(MeetingWorkflowConditions)


class MeetingWorkflowActions:
    '''Adapts a meeting to interface IMeetingWorkflowActions.'''
    implements(IMeetingWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, meeting):
        self.context = meeting

    security.declarePrivate('initSequenceNumber')
    def initSequenceNumber(self):
        '''When a meeting is published (or frozen, depending on workflow
           adaptations), we attribute him a sequence number.'''
        if self.context.getMeetingNumber() != -1:
            return  # Already done.
        cfg = self.context.portal_plonemeeting.getMeetingConfig(self.context)
        if cfg.getYearlyInitMeetingNumber():
            # I must reinit the meeting number to 0 if it is the first
            # meeting of this year.
            prev = self.context.getPreviousMeeting()
            if prev and \
               (prev.getDate().year() != self.context.getDate().year()):
                self.context.setMeetingNumber(1)
                cfg.setLastMeetingNumber(1)
                return
        # If we are here, we must simply increment the meeting number.
        meetingNumber = cfg.getLastMeetingNumber()+1
        self.context.setMeetingNumber(meetingNumber)
        cfg.setLastMeetingNumber(meetingNumber)

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
        self.context.setFirstItemNumber(unrestrictedMethodsView.findFirstItemNumberForMeeting(self.context))

    security.declarePrivate('doPublish_decisions')
    def doPublish_decisions(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doArchive')
    def doArchive(self, stateChange):
        ''' '''
        pass

    security.declarePrivate('doRepublish')
    def doRepublish(self, stateChange):
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
        wfTool = getToolByName(self.context, 'portal_workflow')
        for item in self.context.getItems():
            if item.queryState() == 'itemfrozen':
                wfTool.doActionFor(item, 'backToItemPublished')
        for item in self.context.getLateItems():
            if item.queryState() == 'itemfrozen':
                wfTool.doActionFor(item, 'backToItemPublished')
                wfTool.doActionFor(item, 'backToPresented')
                # This way we "hide" again all late items.

    security.declarePrivate('doBackToDecisionsPublished')
    def doBackToDecisionsPublished(self, stateChange):
        '''When the wfAdaptation 'hide_decisions_when_under_writing' is activated.'''
        pass

    security.declarePrivate('doBackToFrozen')
    def doBackToFrozen(self, stateChange):
        pass

    security.declarePrivate('doBackToClosed')
    def doBackToClosed(self, stateChange):
        # Every item must go back to its previous state: confirmed, delayed or
        # refused.
        wfTool = self.context.portal_workflow
        for item in self.context.getAllItems(ordered=True):
            itemHistory = item.workflow_history['meetingitem_workflow']
            previousState = itemHistory[-2]['review_state']
            previousState = previousState[0].upper() + previousState[1:]
            wfTool.doActionFor(item, 'backTo' + previousState)

InitializeClass(MeetingWorkflowActions)
##/code-section module-header

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
            condition="python: here.attributeIsUsed('startDate') and not here.isTemporary()",
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
            condition="python: here.attributeIsUsed('midDate') and not here.isTemporary()",
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
            condition="python: here.attributeIsUsed('endDate') and not here.isTemporary()",
            minute_step=1,
            label='Enddate',
            label_msgid='PloneMeeting_label_endDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    TextField(
        name='signatures',
        allowable_content_types=('text/plain',),
        optional=True,
        widget=TextAreaWidget(
            condition="python: here.attributeIsUsed('signatures')",
            label_msgid="meeting_signatures",
            label='Signatures',
            i18n_domain='PloneMeeting',
        ),
        default_content_type='text/plain',
        default_method="getDefaultSignatures",
    ),
    LinesField(
        name='signatories',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('signatories')",
            format="checkbox",
            label_msgid="meeting_signatories",
            label='Signatories',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listSignatories',
        default_method="getDefaultSignatories",
        enforceVocabulary=True,
        optional=True,
    ),
    TextField(
        name='assembly',
        allowable_content_types="text/plain",
        widget=TextAreaWidget(
            condition="python: here.attributeIsUsed('assembly')",
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
            condition="python: here.attributeIsUsed('assemblyExcused')",
            description="MeetingAssemblyExcused",
            description_msgid="assembly_excused_meeting_descr",
            label='Assemblyexcused',
            label_msgid='PloneMeeting_label_assemblyExcused',
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
            condition="python: here.attributeIsUsed('assemblyAbsents')",
            description="MeetingAssemblyAbsents",
            description_msgid="assembly_absents_meeting_descr",
            label='Assemblyabsents',
            label_msgid='PloneMeeting_label_assemblyAbsents',
            i18n_domain='PloneMeeting',
        ),
        default_output_type="text/html",
        default_content_type="text/plain",
    ),
    LinesField(
        name='attendees',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('attendees')",
            label='Attendees',
            label_msgid='PloneMeeting_label_attendees',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary='listAssemblyMembers',
        default_method="getDefaultAttendees",
    ),
    LinesField(
        name='excused',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('excused')",
            label='Excused',
            label_msgid='PloneMeeting_label_excused',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary='listAssemblyMembers',
    ),
    LinesField(
        name='absents',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('absents')",
            label='Absents',
            label_msgid='PloneMeeting_label_absents',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary='listAssemblyMembers',
    ),
    LinesField(
        name='lateAttendees',
        widget=MultiSelectionWidget(
            condition="python: here.attributeIsUsed('lateAttendees')",
            label='Lateattendees',
            label_msgid='PloneMeeting_label_lateAttendees',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        multiValued=1,
        vocabulary='listAssemblyMembers',
    ),
    StringField(
        name='place',
        widget=StringField._properties['widget'](
            condition="python: here.attributeIsUsed('place')",
            label='Place',
            label_msgid='PloneMeeting_label_place',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
        searchable=True,
    ),
    TextField(
        name='observations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showObs('observations')",
            label_msgid="PloneMeeting_meetingObservations",
            rows=15,
            label='Observations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
    ),
    DateTimeField(
        name='preMeetingDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attributeIsUsed('preMeetingDate')",
            label='Premeetingdate',
            label_msgid='PloneMeeting_label_preMeetingDate',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    StringField(
        name='preMeetingPlace',
        widget=StringField._properties['widget'](
            condition="python: here.attributeIsUsed('preMeetingPlace')",
            label='Premeetingplace',
            label_msgid='PloneMeeting_label_preMeetingPlace',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    TextField(
        name='preObservations',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            condition="python: here.showObs('preObservations')",
            rows=15,
            label='Preobservations',
            label_msgid='PloneMeeting_label_preObservations',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        default_output_type="text/x-html-safe",
        optional=True,
    ),
    ReferenceField(
        name='items',
        widget=ReferenceBrowserWidget(
            visible=False,
            label='Items',
            label_msgid='PloneMeeting_label_items',
            i18n_domain='PloneMeeting',
        ),
        allowed_types="('MeetingItem',)",
        multiValued=True,
        relationship="MeetingItems",
    ),
    ReferenceField(
        name='lateItems',
        widget=ReferenceBrowserWidget(
            visible=False,
            label='Lateitems',
            label_msgid='PloneMeeting_label_lateItems',
            i18n_domain='PloneMeeting',
        ),
        allowed_types="('MeetingItem',)",
        multiValued=True,
        relationship="MeetingLateItems",
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
        write_permission="Manage portal",
        read_permission="Manage portal",
    ),
    StringField(
        name='meetingConfigVersion',
        widget=StringField._properties['widget'](
            label='Meetingconfigversion',
            label_msgid='PloneMeeting_label_meetingConfigVersion',
            i18n_domain='PloneMeeting',
        ),
        read_permission="Manage portal",
        write_permission="Manage portal",
    ),
    DateTimeField(
        name='deadlinePublish',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attributeIsUsed('deadlinePublish') and not here.isTemporary()",
            label='Deadlinepublish',
            label_msgid='PloneMeeting_label_deadlinePublish',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),
    DateTimeField(
        name='deadlineFreeze',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attributeIsUsed('deadlineFreeze') and not here.isTemporary()",
            label='Deadlinefreeze',
            label_msgid='PloneMeeting_label_deadlineFreeze',
            i18n_domain='PloneMeeting',
        ),
        optional=True,
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

Meeting_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
##/code-section after-schema

class Meeting(BaseContent, BrowserDefaultMixin):
    """ A meeting made of items """
    security = ClassSecurityInfo()
    implements(interfaces.IMeeting)

    meta_type = 'Meeting'
    _at_rename_after_creation = True

    schema = Meeting_schema

    ##code-section class-header #fill in your manual code here
    meetingClosedStates = ['closed', 'archived']
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePrivate('validate_date')
    def validate_date(self, value):
        '''There can't be several meetings with the same date and hour.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        # add GMT+x value
        localizedValue0 = value + ' ' + _findLocalTimeZoneName(0)
        localizedValue1 = value + ' ' + _findLocalTimeZoneName(1)
        # make sure we look for existing meetings in both possible
        # time zones because if we just changed timezone, we could create
        # another meeting with same date of an existing that was created with previous timezone...
        otherMeetings = self.portal_catalog(portal_type=cfg.getMeetingTypeName(),
                                            getDate=(DateTime(localizedValue0), DateTime(localizedValue1), ))
        if otherMeetings:
            for m in otherMeetings:
                if m.getObject() != self:
                    return self.i18n('meeting_with_same_date_exists')

    security.declarePrivate('validate_place')
    def validate_place(self, value):
        '''If "other" is selected, field "place_other" must contain
           something.'''
        rq = self.REQUEST
        if (value == 'other') and not rq.get('place_other', None):
            return self.i18n('place_other_required')

    security.declarePublic('listAssemblyMembers')
    def listAssemblyMembers(self):
        '''Returns the active MeetingUsers having usage "assemblyMember".'''
        res = ((u.id, u.Title()) for u in self.getAllUsedMeetingUsers(includeAllActive=True))
        return DisplayList(res)

    security.declarePublic('listSignatories')
    def listSignatories(self):
        '''Returns the active MeetingUsers having usage "signer".'''
        res = ((u.id, u.Title()) for u in self.getAllUsedMeetingUsers(usages=['signer', ],
                                                                      includeAllActive=True))
        return DisplayList(res)

    security.declarePublic('getAllUsedMeetingUsers')
    def getAllUsedMeetingUsers(self, usages=['assemblyMember', ], includeAllActive=False):
        '''This will return every used MeetingUsers no matter they are
           active or not.  This make it possible to deactivate a MeetingUser
           but still see it on old meetings.  If p_includeAllActive is True,
           every active users (with usage assemblyMember) will be added so adding
           a MeetingUser in the configuration will make it useable while editing an
           existing meeting.'''
        # used MeetingUsers are users really saved in attendess, absents, excused, replacements
        mUserIds = set(self.getAttendees()).union(set(self.getAbsents())).union(set(self.getExcused()))
        # keep order as defined in the configuration
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        # get every potential assembly members, inactive included
        allMeetingUsers = cfg.getMeetingUsers(usages=usages, onlyActive=False)
        allActiveMeetingUsers = cfg.getMeetingUsers(usages=usages, theObjects=False)
        allActiveMeetingUsersIds = [mUser.getId for mUser in allActiveMeetingUsers]
        if includeAllActive:
            # include selected users + all existing active users
            return [mUser for mUser in allMeetingUsers if
                    (mUser.getId() in mUserIds or mUser.getId() in allActiveMeetingUsersIds)]
        else:
            # only include selected users
            return [mUser for mUser in allMeetingUsers if mUser.getId() in mUserIds]

    security.declarePublic('getDefaultAttendees')
    def getDefaultAttendees(self):
        '''The default attendees are the active MeetingUsers in the
           corresponding meeting configuration.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return [u.id for u in cfg.getMeetingUsers()]

    security.declarePublic('getDefaultSignatories')
    def getDefaultSignatories(self):
        '''The default signatories are the active MeetingUsers having usage
           "signer" and whose "signatureIsDefault" is True.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        res = []
        for user in cfg.getMeetingUsers(usages=('signer',)):
            if user.getSignatureIsDefault():
                res.append(user.id)
        return res

    security.declarePublic('getAttendees')
    def getAttendees(self, theObjects=False, includeDeleted=True,
                     includeReplacements=False):
        '''Returns the attendees in this meeting. When used by Archetypes,
           this method returns a list of attendee ids; when used elsewhere
           (with p_theObjects=True), it returns a list of true MeetingUser
           objects. If p_includeDeleted is True, it includes a FakeMeetingUser
           instance for every MeetingUser that has been deleted (works only
           when p_theObjects is True).

           If p_includeReplacements is True, we will take care of potential user
           replacements defined in this meeting and we will return a user
           replacement for every attendee that has been replaced.'''
        meetingForRepls = None
        if includeReplacements:
            meetingForRepls = self
        return getMeetingUsers(self, 'attendees', theObjects, includeDeleted,
                               meetingForRepls=meetingForRepls)

    security.declarePublic('getExcused')
    def getExcused(self, theObjects=False):
        '''See docstring in previous method.'''
        return getMeetingUsers(self, 'excused', theObjects, True)

    security.declarePublic('getAbsents')
    def getAbsents(self, theObjects=False):
        '''See docstring in previous method.'''
        return getMeetingUsers(self, 'absents', theObjects, True)

    security.declarePublic('getItemAbsents')
    def getItemAbsents(self):
        '''Returns a dict. Keys are meeting user IDs; every value is the list
           of items for which this user is noted as 'itemAbsent' in the field
           of the same name (fields meeting.departures/entrances are not taken
           into account).'''
        res = {}
        for item in self.getAllItems(ordered=True):
            for userId in item.getItemAbsents():
                if userId in res:
                    res[userId].append(item)
                else:
                    res[userId] = [item]
        return res

    security.declarePublic('getLateAttendees')
    def getLateAttendees(self, theObjects=False):
        '''See docstring in previous method.'''
        return getMeetingUsers(self, 'lateAttendees', theObjects, True)

    security.declarePublic('getEntranceItem')
    def getEntranceItem(self, userId):
        '''p_userId represents a special user that was not present in the
           meeting since its beginning (=a late attendee). This method returns,
           if known, the number of the item when the person has entered the
           meeting (so the person has effectively attended discussion on this
           item).'''
        if hasattr(self.aq_base, 'entrances') and (userId in self.entrances):
            return self.entrances[userId]

    security.declarePublic('hasEntrance')
    def hasEntrance(self, item, when='after'):
        '''Is there at least one people that entered this meeting after (or
           before, if p_when is "before") discussion on p_item?'''
        if not hasattr(self.aq_base, 'entrances'):
            return
        itemNumber = item.getItemNumber(relativeTo='meeting')
        if when == 'after':
            itemNumber += 1
        for number in self.entrances.itervalues():
            if number == itemNumber:
                return True

    security.declarePublic('getEntrances')
    def getEntrances(self, item, when='after', theObjects=False):
        '''Gets the list of people that entered this meeting after (or
           before, if p_when is "before" or during if p_when is "during") discussion on p_item.'''
        res = []
        if not hasattr(self.aq_base, 'entrances'):
            return res
        if theObjects:
            tool = getToolByName(self, 'portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
        itemNumber = item.getItemNumber(relativeTo='meeting')
        for userId, number in self.entrances.iteritems():
            if (when == 'before' and number < itemNumber) or \
               (when == 'after' and number > itemNumber) or \
               (when == 'during' and number == itemNumber):
                if theObjects:
                    res.append(getattr(cfg.meetingusers, userId))
                else:
                    res.append(userId)
        return res

    security.declarePublic('getDepartureItem')
    def getDepartureItem(self, userId):
        '''p_userId represents a special user that left the meeting BEFORE
           having discussed some item. This method returns, if known, the number
           of this item.'''
        if hasattr(self.aq_base, 'departures') and (userId in self.departures):
            return self.departures[userId]

    security.declarePublic('hasDeparture')
    def hasDeparture(self, item, when='after'):
        '''Is there at least one people that left this meeting after (or
           before, if p_when is "before") discussion on p_item?'''
        if not hasattr(self.aq_base, 'departures'):
            return
        itemNumber = item.getItemNumber(relativeTo='meeting')
        if when == 'after':
            itemNumber += 1
        for number in self.departures.itervalues():
            if number == itemNumber:
                return True

    security.declarePublic('getDepartures')
    def getDepartures(self, item, when='after', theObjects=False,
                      alsoEarlier=False):
        '''Gets the list of people that left the meeting after (or
           before, if p_when is "before") discussion on p_item. If p_alsoEarlier
           is True, it also includes people that left the meeting earlier.'''
        res = []
        if not hasattr(self.aq_base, 'departures'):
            return res
        if theObjects:
            tool = getToolByName(self, 'portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
        itemNumber = item.getItemNumber(relativeTo='meeting')
        if when == 'after':
            itemNumber += 1
        for userId, number in self.departures.iteritems():
            if alsoEarlier:
                condition = number <= itemNumber
            else:
                condition = number == itemNumber
            if condition:
                if theObjects:
                    res.append(getattr(cfg.meetingusers, userId))
                else:
                    res.append(userId)
        return res

    security.declarePublic('getSignatories')
    def getSignatories(self, theObjects=False, includeDeleted=True,
                       includeReplacements=False):
        '''See docstring in previous method.

           If p_includeReplacements is True, we will take care of potential user
           replacements defined in this meeting and we will return a user
           replacement for every signatory that has been replaced.'''
        meetingForRepls = None
        if includeReplacements:
            meetingForRepls = self
        res = getMeetingUsers(self, 'signatories', theObjects, includeDeleted,
                              meetingForRepls=meetingForRepls)
        return res

    security.declarePublic('showObs')
    def showObs(self, name):
        '''When must field named p_name be shown? p_name can be "observations"
           or "preObservations".'''
        isMgr = self.portal_plonemeeting.isManager(self)
        res = not self.isTemporary() and isMgr and self.attributeIsUsed(name)
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

    security.declarePublic('getAllItems')
    def getAllItems(self, uids=[], ordered=False):
        '''Gets all items presented to this meeting ("normal" and "late" items)
           If p_uids is not empty, only items whose uids are in it are returned
           (it will work only when returning an ordered list).'''
        if not ordered:
            res = self.getItems() + self.getLateItems()
        else:
            res = self.getItemsInOrder(uids=uids) + self.getItemsInOrder(late=True, uids=uids)
        return res

    security.declarePublic('getItemsInOrder')
    def getItemsInOrder(self, late=False, uids=[], batchSize=None,
                        startNumber=1, deadline=None):
        '''Get items in order. If p_late is True, gets the "late" items, and
           not the "normal" items. If p_uids is not empty, only items whose
           uids are in it are returned. If p_batchSize is not None, this method
           will return maximum p_batchSize items, starting at number
           p_startNumber. If p_deadline is not None, it can be:
           - "before": in this case, only items that have respected the deadline
                       are in the result;
           - "after": in this case, only items that have not respected the
                      deadline are in the result.
           The deadline is considered to be respected if the item has been
           validated before the deadline. The deadline is:
           - meeting.deadlinePublish if we return "normal" items (p_late=False);
           - meeting.deadlineFreeze if we return "late" items (p_late=True).
        '''
        # Get the required items list (late or normal), unsorted.
        itemsGetter = self.getItems
        if late:
            itemsGetter = self.getLateItems
        res = itemsGetter()
        # Keep only some of those items if required by method parameters.
        if uids or deadline:
            user = self.portal_membership.getAuthenticatedMember()
            keptItems = []
            for item in res:
                # Compute the condition determining if this item must be kept.
                condition = True
                if uids:
                    # Keep only items whose uid is in p_uids, and ensure the
                    # current user has the right to view them (uids filtering
                    # is used within POD templates).
                    condition = condition and (item.UID() in uids) and user.has_permission(View, item)
                if deadline:
                    # Determine the deadline to use
                    if late:
                        usedDeadline = self.getDeadlineFreeze()
                    else:
                        usedDeadline = self.getDeadlinePublish()
                    if deadline == 'before':
                        condition = condition and item.lastValidatedBefore(usedDeadline)
                    elif deadline == 'after':
                        condition = condition and not item.lastValidatedBefore(usedDeadline)
                if condition:
                    keptItems.append(item)
            res = keptItems
        # Sort items according to item number
        res.sort(key=lambda x: x.getItemNumber())
        # Keep only a subset of items if a batchsize is specified.
        if batchSize and (len(res) > batchSize):
            if startNumber > len(res):
                startNumber = 1
            endNumber = startNumber + batchSize - 1
            keptItems = []
            for item in res:
                itemNb = item.getItemNumber()
                if (itemNb >= startNumber) and (itemNb <= endNumber):
                    keptItems.append(item)
            res = keptItems
        return res

    security.declarePublic('getJsItemUids')
    def getJsItemUids(self):
        '''Returns Javascript code for initializing a Javascript variable with
           all item UIDs.'''
        res = ''
        for uid in self.getRawItems():
            res += 'itemUids["%s"] = true;\n' % uid
        for uid in self.getRawLateItems():
            res += 'itemUids["%s"] = true;\n' % uid
        return res

    security.declarePublic('getItemByNumber')
    def getItemByNumber(self, number):
        '''Gets the item thas has number p_number.'''
        # It is a "normal" or "late" item ?
        itemsGetter = self.getItems
        itemNumber = number
        if number > len(self.getRawItems()):
            itemsGetter = self.getLateItems
            itemNumber -= len(self.getRawItems())
        # Find the item.
        res = None
        for item in itemsGetter():
            if item.getItemNumber() == itemNumber:
                res = item
                break
        return res

    def getBeforeFrozenStates_cachekey(method, self):
        '''cachekey method for self.getBeforeFrozenStates.'''
        # do only recompute once by REQUEST
        return (self, str(self.REQUEST.debug))

    @ram.cache(getBeforeFrozenStates_cachekey)
    def getBeforeFrozenStates(self):
        """
          Returns states before the meeting is frozen, so states where
          an item is still not considered as a late item.
        """
        wfTool = getToolByName(self, 'portal_workflow')
        meetingWF = wfTool.getWorkflowsFor(self)[0]
        # get the 'frozen' state
        if not 'frozen' in meetingWF.states:
            return ''
        frozenState = meetingWF.states['frozen']
        # get back to the meeting WF initial state
        res = []
        initial_state = meetingWF.initial_state
        new_state_id = ''
        new_state = frozenState
        while not new_state_id == initial_state:
            for transition in new_state.transitions:
                if transition.startswith('backTo'):
                    new_state_id = meetingWF.transitions[transition].new_state_id
                    res.append(new_state_id)
                    new_state = meetingWF.states[new_state_id]
        return res

    security.declarePublic('getBeforeFrozenState')
    def getBeforeFrozenState(self):
        '''Predecessor of state "frozen" in a meeting can be "published" or
           "created", depending on workflow adaptations.
           So get the workflow state and check where is leading
           the 'backToXXX' leaving transition.'''
        wfTool = getToolByName(self, 'portal_workflow')
        meetingWF = wfTool.getWorkflowsFor(self)[0]
        # get the 'frozen' state
        if not 'frozen' in meetingWF.states:
            return ''
        frozenState = meetingWF.states['frozen']
        for transition in frozenState.transitions:
            if transition.startswith('backTo'):
                return meetingWF.transitions[transition].new_state_id
        return ''

    security.declareProtected("Modify portal content", 'insertItem')
    def insertItem(self, item, forceNormal=False):
        '''Inserts p_item into my list of "normal" items or my list of "late"
           items. If p_forceNormal is True, and the item should be inserted as
           a late item, it is nevertheless inserted as a normal item.'''
        # First, determine if we must insert the item into the "normal"
        # list of items or to the list of "late" items. Note that I get
        # the list of items *in order* in the case I need to insert the item
        # at another place than at the end.
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        isLate = item.wfConditions().isLateFor(self)
        if isLate and not forceNormal:
            items = self.getItemsInOrder(late=True)
            itemsSetter = self.setLateItems
            toDiscussValue = cfg.getToDiscussLateDefault()
        else:
            items = self.getItemsInOrder(late=False)
            itemsSetter = self.setItems
            toDiscussValue = cfg.getToDiscussDefault()
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
            itemOrder = item.adapted().getInsertOrder(insertMethods, self, isLate)
            higherItemFound = False
            insertIndex = 0  # That's where I will insert the item
            for anItem in items:
                if higherItemFound:
                    # Ok I already know where to insert the item. I just
                    # continue to visit the items in order to increment their
                    # number.
                    anItem.setItemNumber(anItem.getItemNumber()+1)
                elif anItem.adapted().getInsertOrder(insertMethods, self, isLate) > itemOrder:
                    higherItemFound = True
                    insertIndex = anItem.getItemNumber()-1
                    anItem.setItemNumber(anItem.getItemNumber()+1)
            if higherItemFound:
                items.insert(insertIndex, item)
                item.setItemNumber(insertIndex+1)
            else:
                insertAtTheEnd = True
        if insertMethods[0]['insertingMethod'] == 'at_the_end' or insertAtTheEnd:
            # Add the item at the end of the items list
            items.append(item)
            item.setItemNumber(len(items))
        itemsSetter(items)
        # invalidate RAMCache for MeetingItem.getMeeting
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')
        # meeting is considered modified
        self.notifyModified()

    security.declareProtected("Modify portal content", 'removeItem')
    def removeItem(self, item):
        '''Removes p_item from me.'''
        # Remember the item number now; once the item will not be in the meeting
        # anymore, it will loose its number.
        itemNumber = item.getItemNumber()
        itemsGetter = self.getItems
        itemsSetter = self.setItems
        items = itemsGetter()
        if item not in items:
            itemsGetter = self.getLateItems
            itemsSetter = self.setLateItems
            items = itemsGetter()
        try:
            items.remove(item)
        except ValueError:
            # in case this is called by onItemRemoved, the item
            # does not exist anymore and is no more in the items list
            # so we pass
            pass
        itemsSetter(items)
        # Update item numbers
        for anItem in itemsGetter():
            if anItem.getItemNumber() > itemNumber:
                anItem.setItemNumber(anItem.getItemNumber()-1)
        # invalidate RAMCache for MeetingItem.getMeeting
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.getMeeting')
        # meeting is considered modified
        self.notifyModified()

    security.declarePublic('getAvailableItems')
    def getAvailableItems(self):
        '''Check docstring in IMeeting.'''
        meeting = self.getSelf()
        if meeting.queryState() not in MEETING_STATES_ACCEPTING_ITEMS:
            return []
        tool = getToolByName(meeting, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        # First, get meetings accepting items for which the date is lower or
        # equal to the date of this meeting (self)
        meetings = meeting.portal_catalog(
            portal_type=cfg.getMeetingTypeName(),
            getDate={'query': meeting.getDate(), 'range': 'max'}, )
        meetingUids = [b.getObject().UID() for b in meetings]
        meetingUids.append(ITEM_NO_PREFERRED_MEETING_VALUE)
        # Then, get the items whose preferred meeting is None or is among
        # those meetings.
        brains = meeting.portal_catalog(
            portal_type=cfg.getItemTypeName(),
            review_state='validated',
            getPreferredMeeting=meetingUids,
            sort_on="modified")
        if meeting.queryState() in MEETING_NOT_CLOSED_STATES:
            # Oups. I can only take items which are "late" items.
            res = []
            meetingUID = meeting.UID()
            for brain in brains:
                # first bypass brains for which preferredMeeting is not current meeting
                if not brain.getPreferredMeeting == meetingUID:
                    continue
                if brain.getObject().wfConditions().isLateFor(meeting):
                    res.append(brain)
        else:
            res = brains
        return res

    security.declarePrivate('getDefaultAssembly')
    def getDefaultAssembly(self):
        if self.attributeIsUsed('assembly'):
            return self.portal_plonemeeting.getMeetingConfig(self).getAssembly()
        return ''

    security.declarePublic('getStrikedAssembly')
    def getStrikedAssembly(self, groupByDuty=True):
        '''
          Generates a HTML version of the assembly :
          - strikes absents (represented using [[Member assembly name]])
          - add a 'mltAssembly' class to generated <p> so it can be used in the Pod Template
          If p_groupByDuty is True, the result will be generated with members having the same
          duty grouped, and the duty only displayed once at the end of the list of members
          having this duty...  This is only relevant if MeetingUsers are enabled.
        '''
        meeting = self.getSelf()
        # either we use free textarea to define assembly...
        if meeting.getAssembly():
            tool = getToolByName(meeting, 'portal_plonemeeting')
            return tool.toHTMLStrikedContent(meeting.getAssembly())
        # ... or we use MeetingUsers
        elif meeting.getAttendees():
            res = []
            attendeeIds = meeting.getAttendees()
            groupedByDuty = OrderedDict()
            for mUser in meeting.getAllUsedMeetingUsers():
                userId = mUser.getId()
                userTitle = mUser.Title()
                userDuty = mUser.getDuty()
                # if we group by duty, create an OrderedDict where the key is the duty
                # and the value is a list of meetingUsers having this duty
                if groupByDuty:
                    if not userDuty in groupedByDuty:
                        groupedByDuty[userDuty] = []
                    if userId in attendeeIds:
                        groupedByDuty[userDuty].append(mUser.Title())
                    else:
                        groupedByDuty[userDuty].append("<strike>%s</strike>" % userTitle)
                else:
                    if userId in attendeeIds:
                        res.append("%s - %s" % (mUser.Title(), userDuty))
                    else:
                        res.append("<strike>%s - %s</strike>" % (mUser.Title(), userDuty))
            if groupByDuty:
                for duty in groupedByDuty:
                    # check if every member of given duty are striked, we strike the duty also
                    everyStriked = True
                    for elt in groupedByDuty[duty]:
                        if not elt.startswith('<strike>'):
                            everyStriked = False
                            break
                    res.append(', '.join(groupedByDuty[duty]) + ' - ' + duty)
                    if len(groupedByDuty[duty]) > 1:
                        # add a trailing 's' to the duty if several members have the same duty...
                        res[-1] = res[-1] + 's'
                    if everyStriked:
                        lastAdded = res[-1]
                        # strike the entire line and remove existing <strike> tags
                        lastAdded = "<strike>" + lastAdded.replace('<strike>', '').replace('</strike>', '') + \
                                    "</strike>"
                        res[-1] = lastAdded
            return "<p class='mltAssembly'>" + '<br />'.join(res) + "</p>"

    security.declarePrivate('getDefaultSignatures')
    def getDefaultSignatures(self):
        if self.attributeIsUsed('signatures'):
            cfg = self.portal_plonemeeting.getMeetingConfig(self)
            return cfg.getSignatures()
        return ''

    security.declarePrivate('updateTitle')
    def updateTitle(self):
        '''The meeting title is generated by this method, based on the meeting
           date.'''
        # The meeting title is only used for search purposes, to let the user
        # search the meeting based on day of week or month in the available
        # interface languages (and because Plone requires a title). At every
        # place in HS/PM, we always deduce the meeting "title" based on its date
        # and the required formatting.
        tool = getToolByName(self, 'portal_plonemeeting')
        if "secondLanguageCfg" in tool.getModelAdaptations():
            # We will create a bilingual title
            languages = getToolByName(self, 'portal_languages')
            firstLanguage = languages.getDefaultLanguage()[0:2]
            secondLanguage = tool.findSecondLanguage()[0:2]
            if not secondLanguage:
                raise TypeError(NO_SECOND_LANGUAGE_ERROR)
            date1 = tool.formatMeetingDate(self, lang=firstLanguage)
            date2 = tool.formatMeetingDate(self, lang=secondLanguage)
            self.setTitle('%s / %s' % (date1, date2))
        else:
            self.setTitle(tool.formatMeetingDate(self))

    security.declarePrivate('updatePlace')
    def updatePlace(self):
        '''Updates the place if it comes from special request field
           "place_other".'''
        rq = self.REQUEST
        if (not 'place' in rq) or (rq.get('place', '') == 'other'):
            self.setPlace(rq.get('place_other', ''))

    security.declarePrivate('computeDates')
    def computeDates(self):
        '''Computes, for this meeting, the dates which are derived from the
           meeting date when relevant.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        usedAttrs = cfg.getUsedMeetingAttributes()
        meetingDate = self.getDate()
        # Initialize the effective start date with the meeting date
        if 'startDate' in usedAttrs:
            self.setStartDate(meetingDate)
        # Set, by default, mid date to start date + 1 hour.
        if 'midDate' in usedAttrs:
            self.setMidDate(meetingDate + 1/24.0)
        # Set, by default, end date to start date + 2 hours.
        if 'endDate' in usedAttrs:
            self.setEndDate(meetingDate + 2/24.0)
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

    security.declarePublic('getItemsCount')
    def getItemsCount(self):
        '''Returns the amount of MeetingItems in a Meeting'''
        return len(self.getRawItems()) + len(self.getRawLateItems())

    security.declarePublic('getUserReplacements')
    def getUserReplacements(self):
        '''Gets the dict storing user replacements.'''
        if not hasattr(self.aq_base, 'userReplacements'):
            return {}
        return self.userReplacements

    security.declarePrivate('updateMeetingUsers')
    def updateMeetingUsers(self):
        '''After a meeting has been created or edited, we update here the info
           related to meeting users implied in the meeting: attendees,
           signatories, replacements...'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        usedAttrs = cfg.getUsedMeetingAttributes()
        useReplacements = cfg.getUseUserReplacements()
        # Do it only if MeetingUser-based user management is enabled.
        if 'attendees' not in usedAttrs:
            return
        # Store user-related info coming from the request. This info comes from
        # a custom widget, so we need to update the database fields "by hand"
        # here. All request keys from this widget are prefixed with "muser_".
        attendees = []
        if 'excused' in usedAttrs:
            excused = []
        if 'absents' in usedAttrs:
            absents = []
        if 'signatories' in usedAttrs:
            signers = []
        if 'lateAttendees' in usedAttrs:
            lateAttendees = []
        if useReplacements:
            replacements = {}
        for key in self.REQUEST.keys():
            if not key.startswith('muser_'):
                continue
            userId = key[6:].rsplit('_', 1)[0]
            try:
                if key.endswith('_attendee'):
                    attendees.append(userId)
                elif key.endswith('_excused'):
                    excused.append(userId)
                elif key.endswith('_absent'):
                    absents.append(userId)
                elif key.endswith('_signer'):
                    signers.append(userId)
                elif key.endswith('_lateAttendee'):
                    lateAttendees.append(userId)
                elif key.endswith('_replacement'):
                    replacement = self.REQUEST.get(key)
                    if replacement:
                        replacements[userId] = replacement
            except NameError:
                pass
        # Keep right order among attendees
        allIds = cfg.meetingusers.objectIds()
        attendees.sort(key=allIds.index)
        # Update the DB fields.
        self.setAttendees(attendees)
        if 'excused' in usedAttrs:
            excused.sort(key=allIds.index)
            self.setExcused(excused)
        if 'absents' in usedAttrs:
            absents.sort(key=allIds.index)
            self.setAbsents(absents)
        if 'signatories' in usedAttrs:
            signers.sort(key=allIds.index)
            self.setSignatories(signers)
        if 'lateAttendees' in usedAttrs:
            lateAttendees.sort(key=allIds.index)
            self.setLateAttendees(lateAttendees)
        if useReplacements:
            if hasattr(self.aq_base, 'userReplacements'):
                del self.userReplacements
            # In the userReplacements dict, keys are ids of users being
            # replaced; values are ids of replacement users.
            self.userReplacements = replacements

    security.declarePrivate('at_post_create_script')
    def at_post_create_script(self):
        '''Initializes the meeting title and inserts recurring items if
           relevant.'''
        self.updateTitle()
        self.updatePlace()
        self.computeDates()
        # Update user-related info (attendees, signatories, replacements...)
        self.updateMeetingUsers()
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        self.setMeetingConfigVersion(meetingConfig.getConfigVersion())
        addRecurringItemsIfRelevant(self, '_init_')
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Update 'power observers' local roles given to the
        # corresponding MeetingConfig powerobsevers group in case the 'initial_wf_state'
        # is selected as viewable by 'powerobservers'
        self.updatePowerObserversLocalRoles()
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Meeting at %s created by "%s".' % (self.absolute_url_path(), userId))

    security.declarePrivate('at_post_edit_script')
    def at_post_edit_script(self):
        '''Updates the meeting title.'''
        self.updateTitle()
        self.updatePlace()
        # Update user-related info (attendees, signatories, replacements...)
        self.updateMeetingUsers()
        # Add a line in history if historized fields have changed
        addDataChange(self)
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Make sure we have 'text/html' for every Rich fields
        forceHTMLContentTypeForEmptyRichFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)
        # notify modified
        notify(ObjectEditedEvent(self))
        self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Meeting at %s edited by "%s".' % (self.absolute_url_path(), userId))

    security.declarePublic('updatePowerObserversLocalRoles')
    def updatePowerObserversLocalRoles(self):
        '''Configure local role for use case 'power_observers' and 'restricted_power_observers'
           to the corresponding MeetingConfig 'powerobservers/restrictedpowerobservers' group.'''
        # First, remove 'power observer' local roles granted to (restricted) powerobservers.
        self.portal_plonemeeting.removeGivenLocalRolesFor(self,
                                                          role_to_remove=READER_USECASES['powerobservers'],
                                                          suffixes=[POWEROBSERVERS_GROUP_SUFFIX, ])
        self.portal_plonemeeting.removeGivenLocalRolesFor(self,
                                                          role_to_remove=READER_USECASES['restrictedpowerobservers'],
                                                          suffixes=[RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX, ])
        # Then, add local roles for powerobservers.
        meetingState = self.queryState()
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        if meetingState in cfg.getMeetingPowerObserversStates():
            powerObserversGroupId = "%s_%s" % (cfg.getId(), POWEROBSERVERS_GROUP_SUFFIX)
            self.manage_addLocalRoles(powerObserversGroupId, (READER_USECASES['powerobservers'],))
        elif meetingState in cfg.getMeetingRestrictedPowerObserversStates():
            restrictedPowerObserversGroupId = "%s_%s" % (cfg.getId(), RESTRICTEDPOWEROBSERVERS_GROUP_SUFFIX)
            self.manage_addLocalRoles(restrictedPowerObserversGroupId, (READER_USECASES['restrictedpowerobservers'],))

    security.declareProtected('Modify portal content', 'transformRichTextField')
    def transformRichTextField(self, fieldName, richContent):
        '''See doc in interfaces.py.'''
        return richContent

    security.declareProtected('Modify portal content', 'onEdit')
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

    security.declarePublic('getHistory')
    def getHistory(self, *args, **kwargs):
        '''See doc in utils.py.'''
        return getHistory(self, *args, **kwargs)

    security.declarePublic('attributeIsUsed')
    def attributeIsUsed(self, name):
        '''Is the attribute named p_name used in this meeting config ?'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        return (name in meetingConfig.getUsedMeetingAttributes())

    def queryState_cachekey(method, self):
        '''cachekey method for self.queryState.'''
        return self.workflow_history

    security.declarePublic('queryState')
    @ram.cache(queryState_cachekey)
    def queryState(self):
        '''In what state am I ?'''
        wfTool = getToolByName(self, 'portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    security.declarePublic('getWorkflowName')
    def getWorkflowName(self):
        '''What is the name of my workflow ?'''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        return cfg.getMeetingWorkflow()

    security.declarePublic('getLastEvent')
    def getLastEvent(self, transition=None):
        '''Check doc in called function in utils.py.'''
        return getLastEvent(self, transition=transition)

    security.declarePublic('getObject')
    def getObject(self):
        '''Some macros must work with either an object or a brain as input.'''
        return self

    security.declarePublic('getSelf')
    def getSelf(self):
        '''Similar to MeetingItem.getSelf. Check MeetingItem.py for more
           info.'''
        res = self
        if self.__class__.__name__ != 'Meeting':
            res = self.context
        return res

    security.declarePublic('setFieldFromAjax')
    def setFieldFromAjax(self, fieldName, fieldValue):
        '''See doc in utils.py.'''
        return setFieldFromAjax(self, fieldName, fieldValue)

    security.declarePublic('getFieldVersion')
    def getFieldVersion(self, fieldName, changes=False):
        '''See doc in utils.py.'''
        return getFieldVersion(self, fieldName, changes)

    security.declarePublic('isDecided')
    def isDecided(self):
        meeting = self.getSelf()
        return meeting.queryState() in ('decided', 'closed', 'archived', 'decisions_published', )

    security.declarePublic('i18n')
    def i18n(self, msg, domain="PloneMeeting"):
        '''Shortcut for translating p_msg in domain PloneMeeting.'''
        return translate(msg, domain=domain, context=self.REQUEST)

    security.declarePublic('getSpecificDocumentContext')
    def getSpecificDocumentContext(self):
        '''See doc in interfaces.py.'''
        return {}

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
        sourceFolder = recurringItems[0].getParentNode()
        copiedData = sourceFolder.manage_copyObjects(
            ids=[ri.id for ri in recurringItems])
        destFolder = self.getParentNode()
        # Paste the items in the Meeting folder
        pastedItems = self.portal_plonemeeting.pasteItems(
            destFolder, copiedData, copyAnnexes=True)
        for newItem in pastedItems:
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

    security.declarePublic('mustShowLateItems')
    def mustShowLateItems(self, itemStart, maxShownItems):
        '''When consulting a meeting, we need to display the late items if we
           are on the last page of the normal items and if there are late
           items. p_itemStart is the number of the first normal item currently
           displayed; p_maxShownItems is the maximum number of normal items
           shown at once.'''
        onLastPage = (itemStart + maxShownItems) > len(self.getRawItems())
        if onLastPage and (len(self.getRawLateItems()) > 0):
            return True
        else:
            return False

    security.declarePublic('numberOfItems')
    def numberOfItems(self, late=False):
        '''How much items in this meeting ?'''
        if late:
            return len(self.getRawLateItems())
        else:
            return len(self.getRawItems())

    security.declarePublic('getBatchStartNumber')
    def getBatchStartNumber(self, late=False):
        '''When displaying meeting_view, I need to now the start number of the
           normal and late items lists. If they are in the request, I take it
           from there, excepted if they are wrong (ie an item has been deleted
           or removed from a list and as a consequence the page I must show
           does not exist anymore.'''
        res = 1
        rq = self.REQUEST
        if late:
            reqKey = 'lStartNumber'
            nbOfItems = len(self.getRawLateItems())
        else:
            reqKey = 'iStartNumber'
            nbOfItems = len(self.getRawItems())
        if reqKey in rq and (int(rq[reqKey]) <= nbOfItems):
            res = int(rq[reqKey])
        return res

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''This is a workaround to avoid a Plone design problem where it is
           possible to remove a folder containing objects you can not remove.'''
        # If we are here, everything has already been checked before.
        # Just check that the meeting is myself or a Plone Site.
        # We can remove an meeting directly but not "through" his container.
        if not item.meta_type in ('Plone Site', 'Meeting'):
            user = self.portal_membership.getAuthenticatedMember()
            logger.warn(BEFOREDELETE_ERROR % (user.getId(), self.id))
            raise BeforeDeleteException("can_not_delete_meeting_container")
        # we are removing the meeting
        if item.meta_type == 'Meeting':
            membershipTool = getToolByName(item, 'portal_membership')
            member = membershipTool.getAuthenticatedMember()
            if 'wholeMeeting' in item.REQUEST and member.has_role('Manager'):
                item.REQUEST.set('items_to_remove', item.getItems() + item.getLateItems())
        BaseContent.manage_beforeDelete(self, item, container)

    security.declarePublic('showVotes')
    def showVotes(self):
        '''See doc in interfaces.py.'''
        res = False
        meeting = self.getSelf()
        meetingConfig = meeting.portal_plonemeeting.getMeetingConfig(meeting)
        if meetingConfig.getUseVotes():
            # The meeting must have started. But what date to take into account?
            now = DateTime()
            meetingStartDate = meeting.getDate()
            if meeting.attributeIsUsed('startDate') and meeting.getStartDate():
                meetingStartDate = meeting.getStartDate()
            if meetingStartDate < now:
                res = True
        return res

    security.declarePublic('getFrozenDocuments')
    def getFrozenDocuments(self):
        '''Gets the documents related to this meeting that were frozen.'''
        res = []
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        for podTemplate in meetingConfig.podtemplates.objectValues():
            if not podTemplate.getFreezeEvent():
                continue
            # This template may have lead to the production of a frozen doc
            docId = podTemplate.getDocumentId(self)
            # Try to find this frozen document
            folder = self.getParentNode()
            if not hasattr(folder.aq_base, docId):
                continue
            res.append(getattr(folder, docId))
        return res

    security.declarePublic('getPreviousMeeting')
    def getPreviousMeeting(self, searchMeetingsInterval=60):
        '''Gets the previous meeting based on meeting date. We only search among
           meetings in the previous p_searchMeetingsInterval, which is a number
           of days. If no meeting is found, the method returns None.'''
        meetingDate = self.getDate()
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meetingTypeName = cfg.getMeetingTypeName()
        catalog = getToolByName(self, 'portal_catalog')
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
    def getNextMeeting(self):
        '''Gets the next meeting based on meeting date.'''
        meetingDate = self.getDate()
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        meetingTypeName = cfg.getMeetingTypeName()
        catalog = getToolByName(self, 'portal_catalog')
        # find every meetings after self.getDate
        brains = catalog(portal_type=meetingTypeName,
                         getDate={'query': meetingDate, 'range': 'min'},
                         sort_on='getDate')
        res = None
        for brain in brains:
            if brain.getDate > meetingDate:
                res = brain
                break
        if res:
            res = res.getObject()
        return res

    security.declareProtected(ModifyPortalContent, 'processForm')
    def processForm(self, *args, **kwargs):
        '''We override this method because we may need to remember previous
           values of historized fields.'''
        if not self.isTemporary():
            self._v_previousData = rememberPreviousData(self)
        return BaseContent.processForm(self, *args, **kwargs)

    security.declarePublic('decideSeveralItems')
    def decideSeveralItems(self, uids=None, transition=None):
        '''On meeting, we can decided severals items at once.
           p_uids is A STRING representing items separated by commas.
           This string ENDS WITH a final comma so is like :
           'itemuid1,itemuid2,itemuid3,itemuid4,'
           p_transition is the transition to trigger on given items.'''
        if transition is None:
            return self.portal_plonemeeting.gotoReferer()

        if not uids:
            msg = self.translate('no_selected_items', domain='PloneMeeting')
            self.plone_utils.addPortalMessage(msg)
            return self.portal_plonemeeting.gotoReferer()

        uid_catalog = getToolByName(self, 'uid_catalog')
        wf_tool = getToolByName(self, 'portal_workflow')
        for uid in uids.split(','):
            if not uid:
                continue
            obj = uid_catalog.searchResults(UID=uid)[0].getObject()
            try:
                wf_tool.doActionFor(obj, transition)
            except WorkflowException:
                continue
        msg = self.translate('decide_several_items_done', domain='PloneMeeting')
        self.plone_utils.addPortalMessage(msg)
        return self.portal_plonemeeting.gotoReferer()

    security.declarePublic('presentSeveralItems')
    def presentSeveralItems(self, uids=None):
        '''On meeting, we can present severals items at once.
           p_uids is A STRING representing items separated by commas.
           This string ENDS WITH a final comma so is like :
           'itemuid1,itemuid2,itemuid3,itemuid4,'.'''
        if not uids:
            msg = self.translate('no_selected_items', domain='PloneMeeting')
            self.plone_utils.addPortalMessage(msg)
            return self.portal_plonemeeting.gotoReferer()

        uid_catalog = getToolByName(self, 'uid_catalog')
        wfTool = getToolByName(self, 'portal_workflow')
        for uid in uids.split(','):
            if not uid:
                continue
            obj = uid_catalog.searchResults(UID=uid)[0].getObject()
            wfTool.doActionFor(obj, 'present')

        return self.portal_plonemeeting.gotoReferer()

    security.declarePublic('showRemoveSelectedItemsAction')
    def showRemoveSelectedItemsAction(self):
        '''See doc in interfaces.py.'''
        meeting = self.getSelf()
        member = getToolByName(meeting, 'portal_membership').getAuthenticatedMember()
        return bool(member.has_permission(ModifyPortalContent, meeting) and
                    not meeting.queryState() in meeting.meetingClosedStates)

    security.declarePublic('removeSeveralItems')
    def removeSeveralItems(self, uids=None):
        '''On meeting, we can remove severals items at once.
           p_uids is A STRING representing items separated by commas.
           This string ENDS WITH a final comma so is like :
           'itemuid1,itemuid2,itemuid3,itemuid4,'.'''
        tool = getToolByName(self, 'portal_plonemeeting')
        if not uids:
            msg = self.translate('no_selected_items', domain='PloneMeeting')
            plone_utils = getToolByName(self, 'plone_utils')
            plone_utils.addPortalMessage(msg)
            return tool.gotoReferer()

        uid_catalog = getToolByName(self, 'uid_catalog')
        wfTool = getToolByName(self, 'portal_workflow')
        for uid in uids.split(','):
            if not uid:
                continue
            obj = uid_catalog.searchResults(UID=uid)[0].getObject()
            # execute every 'back' transitions until item is in state 'validated'
            changedState = True
            while not obj.queryState() == 'validated':
                availableTransitions = wfTool.getTransitionsFor(obj)
                if not availableTransitions or not changedState:
                    break
                changedState = False
                for tr in availableTransitions:
                    if tr['id'].startswith('back'):
                        wfTool.doActionFor(obj, tr['id'])
                        changedState = True
                        break

        return tool.gotoReferer()

    security.declarePublic('getLabelAssembly')
    def getLabelAssembly(self):
        '''
          Depending on the fact that we use 'assembly' alone or
          'assembly, excused, absents', we will translate the 'assembly' label
          a different way.
        '''
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'assemblyExcused' in usedMeetingAttributes or \
           'assemblyAbsents' in usedMeetingAttributes:
            return _('PloneMeeting_label_attendees')
        else:
            return _('meeting_assembly')



registerType(Meeting, PROJECTNAME)
# end of class Meeting

##code-section module-footer #fill in your manual code here
##/code-section module-footer
