# -*- coding: utf-8 -*-
#
# File: Meeting.py
#
# Copyright (c) 2013 by PloneGov
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
from xml.dom import minidom
from appy.gen import No
from App.class_init import InitializeClass
from DateTime import DateTime
from OFS.ObjectManager import BeforeDeleteException
from zope.i18n import translate
from Products.CMFCore.permissions import ReviewPortalContent,ModifyPortalContent
from archetypes.referencebrowserwidget.widget import ReferenceBrowserWidget
from Products.CMFCore.WorkflowCore import WorkflowException
import Products.PloneMeeting
from Products.PloneMeeting.interfaces import IMeetingWorkflowConditions, \
                                             IMeetingWorkflowActions
from Products.PloneMeeting.utils import \
     getWorkflowAdapter, getCustomAdapter, kupuFieldIsEmpty, fieldIsEmpty, \
     KUPU_EMPTY_VALUES, checkPermission, getCurrentMeetingObject, \
     HubSessionsMarshaller, addRecurringItemsIfRelevant, getLastEvent, \
     kupuEquals, getMeetingUsers, getFieldVersion, getDateFromDelta, \
     rememberPreviousData, addDataChange, hasHistory, getHistory, \
     setFieldFromAjax, transformAllRichTextFields
import logging
logger = logging.getLogger('PloneMeeting')

# PloneMeetingError-related constants -----------------------------------------
BEFOREDELETE_ERROR = 'A BeforeDeleteException was raised by "%s" while ' \
    'trying to delete a meeting with id "%s"'

# Marshaller -------------------------------------------------------------------
class MeetingMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a meeting into a XML file that one may get through
       WebDAV.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all_with_metadata'
    fieldsToExclude = ['allItemsAtOnce', 'allowDiscussion']
    rootElementName = 'meeting'

    def marshallSpecificElements(self, meeting, res):
        w = res.write
        HubSessionsMarshaller.marshallSpecificElements(self, meeting, res)
        # Dump non-archetypes dictionaries "entrances" and "departures".
        for name in ('entrances', 'departures'):
            if not hasattr(meeting, name): continue
            self.dumpField(res, name, getattr(meeting, name))

InitializeClass(MeetingMarshaller)

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

    def _atLeastOneDecisionIsTaken(self):
        '''Returns True if at least one decision was taken on an item (excepted
           the decision to delay an item, which is a "non-decision").'''
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() not in self.notDecidedStatesPlusDelayed:
                return True

    def _decisionsAreTakenForEveryItem(self):
        '''Returns True if a decision is taken for every item.'''
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() in self.notDecidedStates:
                return False
        return True

    def _decisionsAreArchivable(self):
        '''Returns True all the decisions may be archived.'''
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() not in self.archivableStates:
                return False
        return True

    def _decisionsWereConfirmed(self):
        '''Returns True if at least one decision was taken on an item'''
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() == 'confirmed': return True

    def _allItemsAreDelayed(self):
        '''Are all items contained in this meeting delayed ?'''
        for item in self.context.getAllItems(ordered=True):
            if not item.adapted().isDelayed(): return False
        return True

    security.declarePublic('mayAcceptItems')
    def mayAcceptItems(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           (self.context.queryState() in self.acceptItemsStates):
            return True

    security.declarePublic('mayPublish')
    def mayPublish(self):
        if not checkPermission(ReviewPortalContent, self.context): return False
        if not self.context.getRawItems():
            return No(translate('item_required_to_publish', domain="PloneMeeting", context=self.context.REQUEST))
        return True

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
        if not checkPermission(ReviewPortalContent, self.context): return
        currentState = self.context.queryState()
        if currentState in ('published', 'frozen'):
            publishedObject = getCurrentMeetingObject(self.context)
            # If we are not on the 'Meeting' page and we try to 'correct' it, HS
            # will try to change presented items' states, which will not be
            # possible if the published object is not the Meeting.
            if isinstance(publishedObject, Meeting) and \
               not self.context.getRawLateItems() and \
               not self._atLeastOneDecisionIsTaken(): return True
        elif currentState == 'decided':
            # Going back from "decided" to previous state is not a true "undo".
            # Indeed, when a meeting is "decided", all items for which no
            # decision was taken are set in "accepted". Going back to
            # "published" does not set them back in their previous state.
            if not self._decisionsWereConfirmed(): return True
        else:
            return True

    security.declarePublic('mayClose')
    def mayClose(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           self._decisionsAreTakenForEveryItem():
            return True

    security.declarePublic('mayArchive')
    def mayArchive(self):
        if checkPermission(ReviewPortalContent, self.context) and \
           self._decisionsAreArchivable():
            return True

    security.declarePublic('mayRepublish')
    def mayRepublish(self): return False

    security.declarePublic('mayChangeItemsOrder')
    def mayChangeItemsOrder(self):
        if not checkPermission(ModifyPortalContent, self.context): return
        if self.context.queryState() not in \
           ('created', 'published', 'frozen', 'decided'): return
        # Once dictionaries "entrances" and "departures" are filled, changing
        # items order would lead to database incoherences.
        if hasattr(self, 'entrances') and self.entrances: return
        if hasattr(self, 'departures') and self.departures: return
        return True

    security.declarePublic('mayDelete')
    def mayDelete(self):
        user = self.context.portal_membership.getAuthenticatedMember()
        if user.has_role('Manager') or not self.context.getRawItems():
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
        if self.context.getMeetingNumber() != -1: return # Already done.
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
        '''When publishing the meeting, I must set automatically all items
           to "published", too.'''
        self.initSequenceNumber()
        for item in self.context.getItemsInOrder():
            if item.queryState() == 'presented':
                self.context.portal_workflow.doActionFor(item, 'itempublish')


    security.declarePrivate('doFreeze')
    def doFreeze(self, stateChange):
        '''When freezing the meeting, I must set automatically all items
           to "itemfrozen", too.'''
        self.initSequenceNumber()
        wfTool = self.context.portal_workflow
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() == 'presented':
                try:
                    wfTool.doActionFor(item, 'itempublish')
                except WorkflowException:
                    # This action may not exist due to a workflow adaptation.
                    pass
            if item.queryState() in ('presented', 'itempublished'):
                wfTool.doActionFor(item, 'itemfreeze')

    security.declarePrivate('doDecide')
    def doDecide(self, stateChange):
        # All items for which a decision was not taken yet are automatically
        # set to "accepted".
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() == 'itemfrozen':
                self.context.portal_workflow.doActionFor(item, 'accept')

    security.declarePrivate('doClose')
    def doClose(self, stateChange):
        # All items in state "accepted" (that were thus not confirmed yet)
        # are automatically set to "confirmed".
        for item in self.context.getAllItems(ordered=True):
            if item.queryState() == 'accepted':
                self.context.portal_workflow.doActionFor(item, 'confirm')
        # For this meeting, what is the number of the first item ?
        meetingConfig = self.context.portal_plonemeeting.getMeetingConfig(
            self.context)
        self.context.setFirstItemNumber(meetingConfig.getLastItemNumber()+1)
        # Update the item counter which is global to the meeting config
        meetingConfig.setLastItemNumber(meetingConfig.getLastItemNumber() +\
                                        len(self.context.getItems()) + \
                                        len(self.context.getLateItems()))

    security.declarePrivate('doArchive')
    def doArchive(self, stateChange):
        # All items must go to 'itemarchived' state.
        for item in self.context.getAllItems(ordered=True):
            self.context.portal_workflow.doActionFor(item, 'itemarchive')

    security.declarePrivate('doRepublish')
    def doRepublish(self, stateChange):
        pass

    security.declarePrivate('doBackToDecided')
    def doBackToDecided(self, stateChange):
        # Oups when closing a meeting we have updated the item counter (which
        # is global to the meeting config). So here we must reverse our action.
        cfg = self.context.portal_plonemeeting.getMeetingConfig(self.context)
        cfg.setLastItemNumber(cfg.getLastItemNumber() -\
                              len(self.context.getItems()) - \
                              len(self.context.getLateItems()))
        self.context.setFirstItemNumber(-1)

    security.declarePrivate('doBackToCreated')
    def doBackToCreated(self, stateChange):
        wfTool = self.context.portal_workflow
        for item in self.context.getItems():
            # I do it only for "normal" items (not for "late" items)
            # because we can't put a meeting back in "created" state if it
            # contains "late" items (so here there will be no "late" items
            # for this meeting). If we want to do it, we will need to
            # unpresent each "late" item first.
            if item.queryState() in ('itempublished', 'itemfrozen'):
                wfTool.doActionFor(item, 'backToPresented')

    security.declarePrivate('doBackToPublished')
    def doBackToPublished(self, stateChange):
        do = self.context.portal_workflow.doActionFor
        for item in self.context.getItems():
            if item.queryState() == 'itemfrozen':
                do(item, 'backToItemPublished')
        for item in self.context.getLateItems():
            if item.queryState() == 'itemfrozen':
                do(item, 'backToItemPublished')
                do(item, 'backToPresented')
                # This way we "hide" again all late items.

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

# Validators -------------------------------------------------------------------
class AllItemsParserError(Exception):
    '''Raised when the AllItemsParser encounters a problem.'''

class AllItemsParser:
    '''Parses the 'allItemsAtOnce' field.'''
    def __init__(self, fieldContent, meeting):
        doc = minidom.parseString("<x>%s</x>" % fieldContent)
        self.root = doc.firstChild
        # We remove empty nodes added by Firefox
        self.removeSpaceTextNodes()
        self.meeting = meeting
        # Some parser error messages
        try:
            d = 'PloneMeeting'
            self.CORRUPTED_BODY = meeting.translate('corruptedBody', domain=d)
            self.CORRUPTED_TITLE= meeting.translate('corruptedTitle', domain=d)
        except AttributeError:
            self.CORRUPTED_BODY = 'Corrupted body.'
            self.CORRUPTED_TITLE = 'Corrupted title.'

    def removeSpaceTextNodes(self):
        '''Removes emtpy nodes added by Firefox'''
        # Position on the first node
        child = self.root.firstChild
        while child:
            # We save the next node
            next = child.nextSibling
            if child.nodeType == child.TEXT_NODE:
                # Is is an empty node ?
                if child.toxml().isspace():
                    # Remove it
                    child.parentNode.removeChild(child)
            # Go to the next child
            child = next

    def parse(self, onItem=None):
        '''Parses (DOM parsing) the XHTML content of a Kupu field. Raises
           AllItemsParserError exceptions if parsing fails. Each time an item
           is parsed, a method p_onItem (if given) is called with args:
           itemNumber, itemTitle, itemBody.'''
        itemNumbers = []
        child = self.root.firstChild
        while child:
            # Parse the item's number and title
            if (child.nodeType == child.TEXT_NODE) or \
               (not child.hasAttribute('id')) or \
               (child.attributes['id'].value != 'itemTitle'):
                raise AllItemsParserError(self.CORRUPTED_BODY)
            if (not child.firstChild) or \
               (child.firstChild.nodeType <> child.TEXT_NODE):
                raise AllItemsParserError(self.CORRUPTED_TITLE)
            # Field must have the form "<number>. <title>"
            numberedTitle = child.firstChild.data
            # Parse number
            number = None
            dotIndex = numberedTitle.find('.')
            if dotIndex == -1:
                raise AllItemsParserError(self.CORRUPTED_TITLE)
            try:
                number = int(numberedTitle[:dotIndex])
                itemNumbers.append(number)
            except ValueError:
                raise AllItemsParserError(self.CORRUPTED_TITLE)
            # Parse title
            title = numberedTitle[dotIndex+1:].strip()
            if not title:
                raise AllItemsParserError(self.CORRUPTED_TITLE)
            # Parse body (description or decision)
            child = child.nextSibling
            if (not child) or (child.nodeType == child.TEXT_NODE) or \
               (not child.hasAttribute('id')) or \
               (child.attributes['id'].value != 'itemBody'):
                raise AllItemsParserError(self.CORRUPTED_BODY)
            body = ''
            bodyChild = child.firstChild
            while bodyChild:
                body += bodyChild.toxml().strip()
                bodyChild = bodyChild.nextSibling
            if self.meeting.adapted().isDecided() and kupuFieldIsEmpty(body):
                raise AllItemsParserError(self.meeting.translate(
                    'corruptedContent', domain='PloneMeeting'))
            child = child.nextSibling
            # Call callback method if defined.
            if onItem:
                onItem(number, title, body)
        nbOfItems = len(self.meeting.getRawItems()) + \
                    len(self.meeting.getRawLateItems())
        if set(itemNumbers) != set(range(1, nbOfItems+1)):
            raise AllItemsParserError(
                self.meeting.translate(
                    'corruptedNumbers', domain='PloneMeeting'))

import UserList
class BunchOfItems(UserList.UserList):
    '''This class represents a bunch of items collected by method
       Meeting.getGroupedItems.'''
    def insertItem(self, indexes, item):
        '''This method inserts p_item into a sub-buch at index p_indexes.
           If p_indexes is a list of indexes instead of a single integer value,
           it means that the item must be inserted into sub-sub-*-bunches.'''
        # Get the index of the sub-bunch where to insert p_item.
        if type(indexes) in (int, long):
            index = indexes
            nextIndexes = None
        else:
            index = indexes[0]
            nextIndexes = indexes[1:]
        # Lenghten self if needed
        while len(self) <= index: self.append(None)
        # Insert the item in the sub-bunch
        if self[index] == None:
            # The sub-bunch does not exist. Create it.
            self[index] = BunchOfItems()
        if nextIndexes:
            self[index].insertItem(nextIndexes, item)
        else:
            # I must append the p_item in this bunch.
            self[index].append(item)

class ItemsIterator:
    '''Method Meeting.getGroupedItems allows to produce lists of items which are
       structured into any level of upper-lists (see class BunchOfItems above).
       Sometimes, one may need to iterate, in order (depth-first search)), over
       all items of such tree. This is the purpose of this class.'''
    def __init__(self, items):
        self.items = items # The tree of items.
        self.indexes = [] # Where we are while walking p_items.

    def _next(self, elems, depth):
        '''Gets, within p_elems, the next item. We are at p_depth within
           self.items.'''
        if not elems: return
        if depth >= len(self.indexes):
            # I've never walked at this depth. Create it within self.indexes
            self.indexes.append(0)
        # Get the element at the current index
        i = self.indexes[depth]
        if i >= len(elems):
            # No more elements here. Try to get the next elem at the higher
            # level
            self.indexes[depth] = 0
            if depth > 0:
                self.indexes[depth-1] += 1
                return self.next()
        else:
            elem = elems[i]
            if elem.__class__.__name__ == 'MeetingItem':
                # We have found the next element. Before returning it, update
                # our indexes.
                if i == len(elems)-1:
                    # We have consumed all items at this level.
                    self.indexes[depth] = 0
                    if depth > 0:
                        self.indexes[depth-1] += 1
                else:
                    self.indexes[depth] += 1
                return elem
            else:
                return self._next(elem, depth+1)

    def next(self):
        '''Get the next item.'''
        return self._next(self.items, 0)
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
            label='Middate',
            label_msgid='PloneMeeting_label_midDate',
            i18n_domain='PloneMeeting',
        ),
        optional= True,
    ),
    DateTimeField(
        name='endDate',
        widget=DateTimeField._properties['widget'](
            condition="python: here.attributeIsUsed('endDate') and not here.isTemporary()",
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
            label='Assembly',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/plain",
        default_method="getDefaultAssembly",
        default_output_type="text/html",
        optional=True,
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
        default_output_type="text/html",
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
        default_output_type="text/html",
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
    TextField(
        name='allItemsAtOnce',
        widget=RichWidget(
            condition="python: here.showAllItemsAtOnce()",
            parastyles=["Title|h2|itemTitle","Body|div|itemBody"],
            description_msgid="all_items_explanation",
            description="AllItemsAtOnce",
            label='Allitemsatonce',
            label_msgid='PloneMeeting_label_allItemsAtOnce',
            i18n_domain='PloneMeeting',
        ),
        default_content_type="text/html",
        allowable_content_types=('text/html',),
        default_output_type="text/html",
        optional=False,
        edit_accessor="getAllItemsAtOnce",
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
# Register the marshaller for DAV/XML export.
Meeting_schema.registerLayer('marshall', MeetingMarshaller())
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
        localizedValue = value + ' ' + DateTime._localzone
        otherMeetings= self.portal_catalog(portal_type=cfg.getMeetingTypeName(),
                                           getDate=DateTime(localizedValue))
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

    security.declarePrivate('validate_allItemsAtOnce')
    def validate_allItemsAtOnce(self, value):
        '''Checks validity of content of field "allItemsAtOnce".

           This field is a temporary buffer (a rich text field) that contains
           numbers, titles and descriptions (or decisions) of all the items
           of a meeting. This allows a MeetingManager to modify all those things
           at once.

           This validator ensures that the user does not break things like the
           structure of each item, the numbering scheme, etc.
        '''
        if not self.attributeIsUsed('allItemsAtOnce'): return
        try:
            AllItemsParser(value, self).parse()
        except AllItemsParserError, aipe:
            return aipe.args[0]

    security.declarePublic('listAssemblyMembers')
    def listAssemblyMembers(self):
        '''Returns the active MeetingUsers having usage "assemblyMember".'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        res = ((u.id, u.Title()) for u in self.getAllUsedMeetingUsers(includeAllActive=True))
        return DisplayList(res)

    security.declarePublic('listSignatories')
    def listSignatories(self):
        '''Returns the active MeetingUsers having usage "signer".'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        res = ((u.id, u.Title()) for u in self.getAllUsedMeetingUsers(usages=['signer',], includeAllActive=True))
        return DisplayList(res)

    security.declarePublic('getAllUsedMeetingUsers')
    def getAllUsedMeetingUsers(self, usages=['assemblyMember',], includeAllActive=False):
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
            return [mUser for mUser in allMeetingUsers if (mUser.getId() in mUserIds or mUser.getId() in allActiveMeetingUsersIds)]
        else:
            # only include selected users
            return [mUser for mUser in allMeetingUsers if mUser.getId() in mUserIds]

    security.declarePublic('getDefaultAttendees')
    def getDefaultAttendees(self):
        '''The default attendees are the active MeetingUsers in the
           corresponding meeting configuration.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        return [u.id for u in meetingConfig.getMeetingUsers()]

    security.declarePublic('getDefaultSignatories')
    def getDefaultSignatories(self):
        '''The default signatories are the active MeetingUsers having usage
           "signer" and whose "signatureIsDefault" is True.'''
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        res = []
        for user in meetingConfig.getMeetingUsers(usages=('signer',)):
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
        if includeReplacements: meetingForRepls = self
        return getMeetingUsers(self, 'attendees', theObjects, includeDeleted,
                               meetingForRepls=meetingForRepls)

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
        if not hasattr(self.aq_base, 'entrances'): return
        itemNumber = item.getItemNumber(relativeTo='meeting')
        if when == 'after': itemNumber += 1
        for number in self.entrances.itervalues():
            if number == itemNumber: return True

    security.declarePublic('getEntrances')
    def getEntrances(self, item, when='after', theObjects=False):
        '''Gets the list of people that entered this meeting after (or
           before, if p_when is "before" or during if p_when is "during") discussion on p_item.'''
        res = []
        if not hasattr(self.aq_base, 'entrances'): return res
        if theObjects: cfg = self.portal_plonemeeting.getMeetingConfig(self)
        itemNumber = item.getItemNumber(relativeTo='meeting')
        for userId, number in self.entrances.iteritems():
            if (when=='before' and number < itemNumber) or \
               (when=='after' and number > itemNumber) or \
               (when=='during' and number == itemNumber):
                if theObjects: res.append(getattr(cfg.meetingusers, userId))
                else:          res.append(userId)
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
        if not hasattr(self.aq_base, 'departures'): return
        itemNumber = item.getItemNumber(relativeTo='meeting')
        if when == 'after': itemNumber += 1
        for number in self.departures.itervalues():
            if number == itemNumber: return True

    security.declarePublic('getDepartures')
    def getDepartures(self, item, when='after', theObjects=False,
                      alsoEarlier=False):
        '''Gets the list of people that left the meeting after (or
           before, if p_when is "before") discussion on p_item. If p_alsoEarlier
           is True, it also includes people that left the meeting earlier.'''
        res = []
        if not hasattr(self.aq_base, 'departures'): return res
        if theObjects: cfg = self.portal_plonemeeting.getMeetingConfig(self)
        itemNumber = item.getItemNumber(relativeTo='meeting')
        if when == 'after': itemNumber += 1
        for userId, number in self.departures.iteritems():
            if alsoEarlier: condition = number <= itemNumber
            else:           condition = number == itemNumber
            if condition:
                if theObjects: res.append(getattr(cfg.meetingusers, userId))
                else:          res.append(userId)
        return res

    security.declarePublic('getSignatories')
    def getSignatories(self, theObjects=False, includeDeleted=True,
                       includeReplacements=False):
        '''See docstring in previous method.

           If p_includeReplacements is True, we will take care of potential user
           replacements defined in this meeting and we will return a user
           replacement for every signatory that has been replaced.'''
        meetingForRepls = None
        if includeReplacements: meetingForRepls = self
        res = getMeetingUsers(self, 'signatories', theObjects, includeDeleted,
                              meetingForRepls=meetingForRepls)
        return res

    security.declarePublic('showObs')
    def showObs(self, name):
        '''When must field named p_name be shown? p_name can be "observations"
           or "preObservations".'''
        isMgr = self.portal_plonemeeting.isManager()
        res = not self.isTemporary() and isMgr and self.attributeIsUsed(name)
        return res

    security.declarePrivate('validate_preMeetingDate')
    def validate_preMeetingDate(self, value):
        '''Checks that the preMeetingDate comes before the meeting date.'''
        if not self.attributeIsUsed('preMeetingDate') or self.isTemporary():
            return
        # The pre-meeting date is required if the field is in use.
        if not value:
            return translate('field_required', domain='PloneMeeting', context=self.REQUEST)
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
            res = self.getItemsInOrder(uids=uids) + \
                  self.getItemsInOrder(late=True, uids=uids)
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
                    condition = condition and (item.UID() in uids) and \
                                user.has_permission('View', item)
                if deadline:
                    # Determine the deadline to use
                    if late: usedDeadline = self.getDeadlineFreeze()
                    else:    usedDeadline = self.getDeadlinePublish()
                    if deadline == 'before':
                        condition = condition and \
                                    item.lastValidatedBefore(usedDeadline)
                    elif deadline == 'after':
                        condition = condition and \
                                    not item.lastValidatedBefore(usedDeadline)
                if condition:
                    keptItems.append(item)
            res = keptItems
        # Sort items according to item number
        res.sort(key = lambda x: x.getItemNumber())
        # Keep only a subset of items if a batchsize is specified.
        if batchSize and (len(res) > batchSize):
            if startNumber > len(res): startNumber = 1
            endNumber = startNumber + batchSize - 1
            keptItems = []
            for item in res:
                itemNb = item.getItemNumber()
                if (itemNb >= startNumber) and (itemNb <= endNumber):
                    keptItems.append(item)
            res = keptItems
        return res

    security.declarePublic('getGroupedItems')
    def getGroupedItems(self, expression, late=False, uids=[], deadline=None,
                        finalizeExpression=None, context={}):
        '''Similar to m_getItemsInOrder, but items are sub-structured into
           BunchOfItems instances, which can themselves contain either items or
           BunchOfItems instances.

           p_expression is a Python expression that will be evaluated on every
           item retrieved by m_getItemsInOrder. This expression will receive
           "item", "previousItem", "meeting" and "previousIndexes" in its
           context, and also variable "context" (in p_context) that can contain
           additional, user-defined, context variables. The expression must
           return, either:
           * an integer value being the index, starting at 0, of the bunch into
             which to insert this item. If this integer is -1, the item will
             not be part of the result;
           * or a list of integer values being the indexes of the bunches and
             sub-bunches into which to insert this item.

           If given, p_finalizeExpression will be evaluated after the final
           result will have been computed. The expression context will contain
           "res" (the result, that the expression can then modify) and
           "meeting".'''
        res = BunchOfItems()
        meeting = self
        previousItem = None
        previousIndexes = None
        for item in self.getItemsInOrder(late, uids, deadline=deadline):
            exec 'indexes = %s' % expression
            if indexes == -1: continue
            previousItem = item
            previousIndexes = indexes
            res.insertItem(indexes, item)
        if finalizeExpression:
            exec finalizeExpression
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

    security.declarePublic('getBeforeFrozenState')
    def getBeforeFrozenState(self):
        '''Predecessor of state "frozen" in a meeting can be "published" or
           "created", depending on workflow adaptations.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        if 'no_publication' in cfg.getWorkflowAdaptations(): return 'created'
        return 'published'

    security.declareProtected("Modify portal content", 'insertItem')
    def insertItem(self, item, forceNormal=False):
        '''Inserts p_item into my list of "normal" items or my list of "late"
           items. If p_forceNormal is True, and the item should be inserted as
           a late item, it is nevertheless inserted as a normal item.'''
        # First, determine if we must insert the item into the "normal"
        # list of items or to the list of "late" items. Note that I get
        # the list of items *in order* in the case I need to insert the item
        # at another place than at the end.
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        isLate = item.wfConditions().isLateFor(self)
        if isLate and not forceNormal:
            items = self.getItemsInOrder(late=True)
            itemsSetter = self.setLateItems
            toDiscussValue = meetingConfig.getToDiscussLateDefault()
        else:
            items = self.getItemsInOrder(late=False)
            itemsSetter = self.setItems
            toDiscussValue = meetingConfig.getToDiscussDefault()
        # Set the correct value for the 'toDiscuss' field if required
        if meetingConfig.getToDiscussSetOnItemInsert():
            item.setToDiscuss(toDiscussValue)
        # At what place must we insert the item in the list ?
        insertMethod = meetingConfig.getSortingMethodOnAddItem()
        insertAtTheEnd = False
        if insertMethod != 'at_the_end':
            # We must insert it according to category or proposing group order
            # (at the end of the items belonging to the same category or
            # proposing group). We will insert the p_item just before the first
            # item whose category/group immediately follows p_item's category/
            # group (or at the end if inexistent). Note that the MeetingManager,
            # in subsequent manipulations, may completely change items order.
            itemOrder = item.adapted().getInsertOrder(insertMethod,self,isLate)
            higherItemFound = False
            insertIndex = 0 # That's where I will insert the item
            for anItem in items:
                if higherItemFound:
                    # Ok I already know where to insert the item. I just
                    # continue to visit the items in order to increment their
                    # number.
                    anItem.setItemNumber(anItem.getItemNumber()+1)
                elif anItem.adapted().getInsertOrder(insertMethod, self, \
                                                     isLate) > itemOrder:
                    higherItemFound = True
                    insertIndex = anItem.getItemNumber()-1
                    anItem.setItemNumber(anItem.getItemNumber()+1)
            if higherItemFound:
                items.insert(insertIndex, item)
                item.setItemNumber(insertIndex+1)
            else:
                insertAtTheEnd = True
        if (insertMethod == 'at_the_end') or insertAtTheEnd:
            # Add the item at the end of the items list
            items.append(item)
            item.setItemNumber(len(items))
        itemsSetter(items)

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
        items.remove(item)
        itemsSetter(items)
        # Update item numbers
        for anItem in itemsGetter():
            if anItem.getItemNumber() > itemNumber:
                anItem.setItemNumber(anItem.getItemNumber()-1)

    security.declarePublic('getAvailableItems')
    def getAvailableItems(self):
        '''Check docstring in IMeeting.'''
        meeting = self.getSelf()
        if meeting.queryState() not in ('created', 'frozen', 'published', \
                                        'decided'): return []
        meetingConfig = meeting.portal_plonemeeting.getMeetingConfig(meeting)
        # First, get meetings accepting items for which the date is lower or
        # equal to the date of this meeting (self)
        meetings = meeting.portal_catalog(
            portal_type=meetingConfig.getMeetingTypeName(),
            getDate={'query': meeting.getDate(), 'range': 'max'},
            )
        meetingUids = [b.getObject().UID() for b in meetings]
        meetingUids.append(ITEM_NO_PREFERRED_MEETING_VALUE)
        # Then, get the items whose preferred meeting is None or is among
        # those meetings.
        itemsUids = meeting.portal_catalog(
            portal_type=meetingConfig.getItemTypeName(),
            review_state='validated',
            getPreferredMeeting=meetingUids,
            sort_on="modified")
        if meeting.queryState() in ('published', 'frozen', 'decided'):
            # Oups. I can only take items which are "late" items.
            res = []
            for uid in itemsUids:
                if uid.getObject().wfConditions().isLateFor(meeting):
                    res.append(uid)
        else:
            res = itemsUids
        return res

    security.declarePrivate('getDefaultAssembly')
    def getDefaultAssembly(self):
        if self.attributeIsUsed('assembly'):
            return self.portal_plonemeeting.getMeetingConfig(self).getAssembly()
        return ''

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
        tool = self.portal_plonemeeting
        if "secondLanguageCfg" in tool.getModelAdaptations():
            # We will create a bilingual title
            lgs = tool.getAvailableInterfaceLanguages().split(',')[:2]
            date1 = tool.formatDate(self.getDate(), lang=lgs[0])
            date2 = tool.formatDate(self.getDate(), lang=lgs[1])
            self.setTitle('%s / %s' % (date1, date2))
        else:
            self.setTitle(tool.formatDate(self.getDate()))

    security.declarePrivate('updatePlace')
    def updatePlace(self):
        '''Updates the place if it comes from special request field
           "place_other".'''
        rq = self.REQUEST
        if not rq.has_key('place') or (rq.get('place', '') == 'other'):
            self.setPlace(rq.get('place_other', ''))

    security.declarePrivate('computeDates')
    def computeDates(self):
        '''Computes, for this meeting, the dates which are derived from the
           meeting date when relevant.'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        usedAttrs = cfg.getUsedMeetingAttributes()
        meetingDate = self.getDate()
        # Initialize the effective start date with the meeting date
        if 'startDate' in usedAttrs: self.setStartDate(meetingDate)
        # Set, by default, mid date to start date + 1 hour.
        if 'midDate' in usedAttrs: self.setMidDate(meetingDate + 1/24.0)
        # Set, by default, end date to start date + 2 hours.
        if 'endDate' in usedAttrs: self.setEndDate(meetingDate + 2/24.0)
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
        if not hasattr(self.aq_base, 'userReplacements'): return {}
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
        if 'attendees' not in usedAttrs: return
        # Store user-related info coming from the request. This info comes from
        # a custom widget, so we need to update the database fields "by hand"
        # here. All request keys from this widget are prefixed with "muser_".
        attendees = []
        if 'excused' in usedAttrs: excused = []
        if 'absents' in usedAttrs: absents = []
        if 'signatories' in usedAttrs: signers = []
        if 'lateAttendees' in usedAttrs: lateAttendees = []
        if useReplacements: replacements = {}
        for key in self.REQUEST.keys():
            if not key.startswith('muser_'): continue
            userId = key[6:].rsplit('_',1)[0]
            try:
                if key.endswith('_attendee'): attendees.append(userId)
                elif key.endswith('_excused'): excused.append(userId)
                elif key.endswith('_absent'): absents.append(userId)
                elif key.endswith('_signer'): signers.append(userId)
                elif key.endswith('_lateAttendee'): lateAttendees.append(userId)
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
            excused.sort(key=allIds.index); self.setExcused(excused)
        if 'absents' in usedAttrs:
            absents.sort(key=allIds.index); self.setAbsents(absents)
        if 'signatories' in usedAttrs:
            signers.sort(key=allIds.index); self.setSignatories(signers)
        if 'lateAttendees' in usedAttrs:
            lateAttendees.sort(key=allIds.index)
            self.setLateAttendees(lateAttendees)
        if useReplacements:
            if hasattr(self.aq_base, 'userReplacements'):
                del self.userReplacements
            # In the userReplacements dict, keys are ids of users being
            # replaced; values are ids of replacement users.
            self.userReplacements = replacements

    security.declarePrivate('setLocalMeetingManagers')
    def setLocalMeetingManagers(self):
        '''When workflow adaptation "local_meeting_managers" is enabled, this
           method grants local role "MeetingManagerLocal" to every
           MeetingManager belonging to the same MeetingGroup as the meeting
           creator (including the meeting creator itself).'''
        # Identify all local managers
        localManagers = []
        for zopeGroup in self.portal_plonemeeting.getGroups(zope=True):
            zGroup = zopeGroup._getGroup()
            for userId in zGroup.getMemberIds():
                user = self.acl_users.getUserById(userId)
                if user.has_role('MeetingManager') and \
                   (userId not in localManagers):
                    localManagers.append(userId)
        # Grant them the corresponding local role
        for userId in localManagers:
            self.manage_addLocalRoles(userId, ('MeetingManagerLocal',))

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
        # If workflow adaptation 'local_meeting_managers' is enabled, set local
        # roles accordingly.
        if 'local_meeting_managers' in meetingConfig.getWorkflowAdaptations():
            self.setLocalMeetingManagers()
        # Apply potential transformations to richtext fields
        transformAllRichTextFields(self)
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=True)
        self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Meeting at %s created by "%s".' % \
                    (self.absolute_url_path(), userId))

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
        # Call sub-product-specific behaviour
        self.adapted().onEdit(isCreated=False)
        self.reindexObject()
        userId = self.portal_membership.getAuthenticatedMember().getId()
        logger.info('Meeting at %s edited by "%s".' % \
                    (self.absolute_url_path(), userId))

    security.declareProtected('Modify portal content', 'transformRichTextField')
    def transformRichTextField(self, fieldName, richContent):
        '''See doc in interfaces.py.'''
        return richContent

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated): '''See doc in interfaces.py.'''

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp): '''See doc in interfaces.py.'''

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

    security.declarePublic('queryState')
    def queryState(self):
        '''In what state am I ?'''
        return self.portal_workflow.getInfoFor(self, 'review_state')

    security.declarePublic('getWorkflowName')
    def getWorkflowName(self):
        '''What is the name of my workflow ?'''
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        return cfg.getMeetingWorkflow()

    security.declarePublic('getLastEvent')
    def getLastEvent(self, transition):
        '''Check doc in called function in utils.py.'''
        return getLastEvent(self, transition)

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
        return meeting.queryState() in ('decided', 'closed', 'archived')

    security.declarePublic('i18n')
    def i18n(self, msg, domain="PloneMeeting"):
        '''Shortcut for translating p_msg in domain PloneMeeting.'''
        return translate(msg, domain=domain, context=self.REQUEST)

    security.declarePublic('showAllItemsAtOnce')
    def showAllItemsAtOnce(self):
        '''Must I show the rich text field that allows to edit all "normal" and
           "late" items at once ?'''
        if not self.attributeIsUsed('allItemsAtOnce'): return False
        # I must have 'write' permissions on every item in order to do this.
        if self.getItems():
            if self.adapted().isDecided():
                writePerms = (ModifyPortalContent, WriteDecision)
            else:
                writePerms = (ModifyPortalContent,)
            currentUser = self.portal_membership.getAuthenticatedMember()
            for item in self.getAllItems():
                for perm in writePerms:
                    if not currentUser.has_permission(perm, item):
                        return False
            return True
        else:
            return False

    security.declarePublic('getAllItemsAtOnce')
    def getAllItemsAtOnce(self):
        '''Creates the content of the "allItemsAtOnce" field from "normal" and
           "late" meeting items presented in this meeting.'''
        if not self.attributeIsUsed('allItemsAtOnce'): return ''
        text = []
        itemNumber = 0
        for itemsList in (self.getItemsInOrder(),
                          self.getItemsInOrder(late=True)):
            for item in itemsList:
                itemNumber += 1
                text.append('<h2 id="itemTitle">%d. %s</h2>' % \
                            (itemNumber, item.Title()))
                text.append('<div id="itemBody">')
                if self.adapted().isDecided():
                    itemBody = item.getDecision()
                else:
                    itemBody = item.Description()
                if not itemBody:
                    itemBody = KUPU_EMPTY_VALUES[0]
                text.append(itemBody)
                text.append('</div>')
        text = "\n".join(text)
        self.getField('allItemsAtOnce').set(self, text)
        return text

    security.declarePublic('updateItem')
    def updateItem(self, itemNumber, itemTitle, itemBody):
        '''Updates the item having number p_itemNumber with new p_itemTitle and
           p_itemBody that come from the 'allItemsAtOnce' field.'''
        item = self.getItemByNumber(itemNumber)
        itemChanged = False
        if not kupuEquals(item.Title(), itemTitle):
            item.setTitle(itemTitle)
            itemChanged = True
        if self.adapted().isDecided():
            # I must update the decision.
            item.setDecision(itemBody)
        else:
            if not kupuEquals(item.Description(), itemBody):
                item.setDescription(itemBody)
                itemChanged = True
        if itemChanged:
            item.pm_modification_date = DateTime() # Now
            item.at_post_edit_script()
        if (not itemChanged) and self.adapted().isDecided():
            # In this case, I must not call at_post_edit_script (which will a.o.
            # remember access on this item) but I must still transform rich text
            # fields because the decison field was updated.
            transformAllRichTextFields(item)

    security.declarePublic('setAllItemsAtOnce')
    def setAllItemsAtOnce(self, value):
        '''p_value is the content of the 'allItemsAtOnce' field, with all items
           numbers, titles and descriptions/decisions in one Kupu field. This
           method updates all the corresponding MeetingItem objects.'''
        try:
            AllItemsParser(value, self).parse(onItem=self.updateItem)
        except AllItemsParserError:
            pass # Normally it should never happen because the validator parsed
                 # p_value some milliseconds earlier.
        # Re-initialise the "allItemsAtOnce" field to blank (the next time it
        # will be shown to the user, it will be updated at this moment).
        self.getField('allItemsAtOnce').set(self, '')

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
        if not recurringItems: return
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
                adap.onDuplicatedFromConfig('as_recurring_item')
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
        if late: return len(self.getRawLateItems())
        else: return len(self.getRawItems())

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
        if rq.has_key(reqKey) and (int(rq[reqKey]) <= nbOfItems):
            res = int(rq[reqKey])
        return res

    security.declarePrivate('manage_beforeDelete')
    def manage_beforeDelete(self, item, container):
        '''This is a workaround to avoid a Plone design problem where it is
           possible to remove a folder containing objects you can not remove.'''
        # If we are here, everything has already been checked before.
        # Just check that the item is myself or a Plone Site.
        # We can remove an item directly but not "through" his container.
        if not item.meta_type in ('Plone Site', 'Meeting'):
            user = self.portal_membership.getAuthenticatedMember()
            logger.warn(BEFOREDELETE_ERROR % (user.getId(), self.id))
            raise BeforeDeleteException, "can_not_delete_meeting_container"
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

    security.declarePublic('showItemAdvices')
    def showItemAdvices(self):
        '''See doc in interfaces.py.'''
        res = False
        meeting = self.getSelf()
        if not meeting.adapted().isDecided():
            res = True
        return res

    security.declarePublic('getFrozenDocuments')
    def getFrozenDocuments(self):
        '''Gets the documents related to this meeting that were frozen.'''
        res = []
        meetingConfig = self.portal_plonemeeting.getMeetingConfig(self)
        for podTemplate in meetingConfig.podtemplates.objectValues():
            if not podTemplate.getFreezeEvent(): continue
            # This template may have lead to the production of a frozen doc
            docId = podTemplate.getDocumentId(self)
            # Try to find this frozen document
            folder = self.getParentNode()
            if not hasattr(folder.aq_base, docId): continue
            res.append(getattr(folder, docId))
        return res

    security.declarePublic('getPreviousMeeting')
    def getPreviousMeeting(self, searchMeetingsInterval=60):
        '''Gets the previous meeting based on meeting date. We only search among
           meetings in the previous p_searchMeetingsInterval, which is a number
           of days. If no meeting is found, the method returns None.'''
        meetingDate = self.getDate()
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        meetingTypeName = cfg.getMeetingTypeName()
        allMeetings = self.portal_catalog(portal_type=meetingTypeName,
            getDate={'query': meetingDate-searchMeetingsInterval,
                     'range': 'min'}, sort_on='getDate', sort_order='reverse')
        indexDate = self.portal_catalog.Indexes['getDate']
        for meeting in allMeetings:
            if indexDate.getEntryForObject(meeting.getRID()) < meetingDate:
                return meeting.getObject()

    security.declarePublic('getNextMeeting')
    def getNextMeeting(self):
        '''Gets the next meeting based on meeting date.'''
        meetingDate = self.getDate()
        cfg = self.portal_plonemeeting.getMeetingConfig(self)
        meetingTypeName = cfg.getMeetingTypeName()
        allMeetings = self.portal_catalog(portal_type=meetingTypeName,
            getDate={'query': meetingDate, 'range': 'min'}, sort_on='getDate')
        indexDate = self.portal_catalog.Indexes['getDate']
        for meeting in allMeetings:
            if indexDate.getEntryForObject(meeting.getRID()) != meetingDate:
                return meeting.getObject()

    security.declareProtected(ModifyPortalContent, 'processForm')
    def processForm(self, *args, **kwargs):
        '''We override this method because we may need to remember previous
           values of historized fields.'''
        if not self.isTemporary():
            self._v_previousData = rememberPreviousData(self)
        return BaseContent.processForm(self, *args, **kwargs)



registerType(Meeting, PROJECTNAME)
# end of class Meeting

##code-section module-footer #fill in your manual code here
def onAddMeeting(meeting, event):
    '''This method is called every time a Meeting is created, even in
       portal_factory. Local roles defined on a meeting define who may view
       or edit it. But at the time the meeting is created in portal_factory,
       local roles are not defined yet. This can be a problem when some
       workflow adaptations are enabled (ie, 'local_meeting_managers'). So here
       we grant role 'Owner' to the currently logged user that allows him,
       in every case, to create the meeting.'''
    user = meeting.portal_membership.getAuthenticatedMember()
    meeting.manage_addLocalRoles(user.getId(), ('Owner',))
##/code-section module-footer

