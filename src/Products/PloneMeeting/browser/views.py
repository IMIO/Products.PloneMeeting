# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

import json
import lxml

from zope.component import getMultiAdapter
from zope.i18n import translate

from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from plone import api
from eea.facetednavigation.interfaces import ICriteria
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.indexes import _to_coded_adviser_index


class PloneMeetingAjaxView(BrowserView):
    """
      Manage ajax PloneMeeting functionnalities.
    """


class ItemNavigationWidgetView(BrowserView):
    """
      This manage the view displaying the navigation widget on the item view
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()

    @memoize
    def __call__(self):
        """Memoize as this widget is displayed identically at the top and the bottom of the item view."""
        return super(ItemNavigationWidgetView, self).__call__()

    def display_number(self, itemNumber):
        """Show the displayable version of the p_itemNumber."""
        return _storedItemNumber_to_itemNumber(itemNumber, forceShowDecimal=False)


class ItemMoreInfosView(BrowserView):
    """
      This manage the view displaying more infos about an item in the PrettyLink column
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self, visibleColumns):
        """ """
        self.visibleColumns = visibleColumns
        return super(ItemMoreInfosView, self).__call__()

    @memoize_contextless
    def getItemsListVisibleFields(self):
        """
          Get the topicName from the request and returns it.
        """
        return self.cfg.getItemsListVisibleFields()

    @memoize_contextless
    def showMoreInfos(self):
        """ """
        return self.request.cookies.get('pmShowDescriptions', 'false') == 'true' and True or False


class ItemIsSignedView(BrowserView):
    """
      This manage the view displaying itemIsSigned widget
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()


class PresentSeveralItemsView(BrowserView):
    """
      This manage the view that presents several items into a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, uids):
        """ """
        uid_catalog = getToolByName(self.context, 'uid_catalog')
        wfTool = getToolByName(self, 'portal_workflow')
        for uid in uids:
            obj = uid_catalog.searchResults(UID=uid)[0].getObject()
            wfTool.doActionFor(obj, 'present')
        msg = translate('present_several_items_done',
                        domain='PloneMeeting',
                        context=self.request)
        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage(msg)


class RemoveSeveralItemsView(BrowserView):
    """
      This manage the view that removes several items from a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, uids):
        """ """
        uid_catalog = getToolByName(self.context, 'uid_catalog')
        wfTool = getToolByName(self.context, 'portal_workflow')
        # make sure we have a list of uids, in some case, as it is called
        # by jQuery, we receive only one uid, as a string...
        if isinstance(uids, str):
            uids = [uids]
        for uid in uids:
            obj = uid_catalog(UID=uid)[0].getObject()
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
        msg = translate('remove_several_items_done',
                        domain='PloneMeeting',
                        context=self.request)
        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage(msg)


class DecideSeveralItemsView(BrowserView):
    """
      This manage the view that devide several items at once in a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()

    def __call__(self, uids, transition):
        """ """
        uid_catalog = getToolByName(self.context, 'uid_catalog')
        wfTool = getToolByName(self.context, 'portal_workflow')
        # make sure we have a list of uids, in some case, as it is called
        # by jQuery, we receive only one uid, as a string...
        if isinstance(uids, str):
            uids = [uids]

        for uid in uids:
            obj = uid_catalog(UID=uid)[0].getObject()
            try:
                wfTool.doActionFor(obj, transition)
            except WorkflowException:
                continue
        msg = translate('decide_several_items_done', domain='PloneMeeting', context=self.request)
        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage(msg)


class ItemNumberView(BrowserView):
    """
      This manage the view displaying the itemNumber on the meeting view
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()

    def mayChangeOrder(self):
        """ """
        return self.context.getMeeting().wfConditions().mayChangeItemsOrder()

    def is_integer(self, number):
        """ """
        return _is_integer(number)


class ItemToDiscussView(BrowserView):
    """
      This manage the view displaying toDiscuss widget
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()
        self.tool = getToolByName(self.context, 'portal_plonemeeting')

    def mayEdit(self):
        """ """
        member = getToolByName(self.context, 'portal_membership').getAuthenticatedMember()
        toDiscuss_write_perm = self.context.getField('toDiscuss').write_permission
        return member.has_permission(toDiscuss_write_perm, self.context) and \
            self.context.showToDiscuss()

    @memoize_contextless
    def userIsReviewer(self):
        """ """
        return self.tool.userIsAmong('reviewers')

    @memoize_contextless
    def useToggleDiscuss(self):
        """ """
        return self.context.restrictedTraverse('@@toggle_to_discuss').isAsynchToggleEnabled()


class MeetingBeforeFacetedInfosView(BrowserView):
    """Informations displayed before the faceted on the meeting_view."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)


class MeetingAfterFacetedInfosView(BrowserView):
    """Informations displayed after the faceted on the meeting_view."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)


class PloneMeetingRedirectToAppView(BrowserView):
    """
      This manage the view set on the Plone Site that redirects the connected user
      to the default MeetingConfig after connection.
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def __call__(self):
        '''
          Add a specific portal_message if we have no active meetingConfig to redirect the connected member to.
        '''
        defaultMeetingConfig = self.defaultMeetingConfig()
        if not self.defaultMeetingConfig() and \
           self.portal.portal_membership.getAuthenticatedMember().has_role('Manager'):
            self.portal.plone_utils.addPortalMessage(
                translate('Please specify a default meeting config upon active existing '
                          'meeting configs to be automaatically redirected to it.',
                          domain='PloneMeeting',
                          context=self.request), type='warning')
        # redirect the user to the default meeting config if possible
        if defaultMeetingConfig:
            pmFolder = self.getPloneMeetingTool().getPloneMeetingFolder(defaultMeetingConfig.getId())
            return self.request.RESPONSE.redirect(pmFolder.absolute_url() + "/searches_items")

        return self.index()

    @memoize
    def defaultMeetingConfig(self):
        '''Returns the default MeetingConfig.
           getDefaultMeetingConfig takes care of current member being able to access the MeetingConfig.'''
        return self.getPloneMeetingTool().getDefaultMeetingConfig()

    @memoize
    def getPloneMeetingTool(self):
        '''Returns the tool.'''
        return getToolByName(self.portal, 'portal_plonemeeting')


class ObjectGoToView(BrowserView):
    """
      Manage go to a given itemNumber.  This method is used
      in the item navigation widget (go to previous item, go to next item, ...)
    """
    def __call__(self, itemNumber):
        """
          p_itemNumber is the number of the item we want to go to.  This item
          is in the same meeting than self.context.
        """
        catalog = getToolByName(self.context, 'portal_catalog')
        meeting = self.context.getMeeting()
        itemNumber = _itemNumber_to_storedItemNumber(itemNumber)
        brains = catalog(linkedMeetingUID=meeting.UID(), getItemNumber=itemNumber)
        if not brains:
            self.context.plone_utils.addPortalMessage(
                translate(msgid='item_number_not_accessible',
                          domain='PloneMeeting',
                          context=self.request),
                type='warning')
            return self.request.RESPONSE.redirect(self.context.absolute_url())
        else:
            obj = brains[0].getObject()
            return self.request.RESPONSE.redirect(obj.absolute_url())


class UpdateDelayAwareAdvicesView(BrowserView):
    """
      This is a view that is called as a maintenance task by Products.cron4plone.
      As we use clear days to compute advice delays, it will be launched at 0:00
      each night and update relevant items containing delay-aware advices still addable/editable.
      It will also update the indexAdvisers portal_catalog index.
    """
    def __call__(self):
        query = self._computeQuery()
        self._updateAllAdvices(query=query)

    def _computeQuery(self):
        '''
          Compute the catalog query to execute to get only relevant items to update,
          so items with delay-aware advices still addable/editable.
        '''
        tool = getToolByName(self.context, 'portal_plonemeeting')
        # compute the indexAdvisers index, take every groups, including disabled ones
        # then constuct every possibles cases, by default there is 2 possible values :
        # delay__groupId1__advice_not_given, delay__groupId1__advice_under_edit
        # delay__groupId2__advice_not_given, delay__groupId2__advice_under_edit
        # ...
        meetingGroups = tool.getMeetingGroups(onlyActive=False)
        groupIds = [meetingGroup.getId() for meetingGroup in meetingGroups]
        indexAdvisers = []
        for groupId in groupIds:
            # advice giveable but not given
            indexAdvisers.append("delay__%s_advice_not_given" % groupId)
            # now advice given and still editable
            for advice_state in ADVICE_STATES_ALIVE:
                indexAdvisers.append("delay__%s_%s" % (groupId, advice_state))
        query = {}
        query['indexAdvisers'] = indexAdvisers
        return query

    def _updateAllAdvices(self, query={}):
        '''Update adviceIndex for every items.
           If a p_query is given, it will be used by the portal_catalog query
           we do to restrict update of advices to some subsets of items...'''
        catalog = api.portal.get_tool('portal_catalog')
        if 'meta_type' not in query:
            query['meta_type'] = 'MeetingItem'
        brains = catalog(**query)
        numberOfBrains = len(brains)
        i = 1
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Updating adviceIndex of item at %s' % (i,
                                                                      numberOfBrains,
                                                                      '/'.join(item.getPhysicalPath())))
            i = i + 1
            item.updateLocalRoles()


class DeleteHistoryEventView(BrowserView):
    """
      Delete an event in an object's history.
    """
    def __call__(self, object_uid, event_time):
        # Get the object
        # try to get it from the portal_catalog
        catalog_brains = self.context.portal_catalog(UID=object_uid)
        # if not found, try to get it from the uid_catalog
        if not catalog_brains:
            catalog_brains = self.context.uid_catalog(UID=object_uid)
        # if not found at all, raise
        if not catalog_brains:
            raise KeyError('The given uid could not be found!')
        obj = catalog_brains[0].getObject()

        # now get the event to delete and delete it...
        tool = getToolByName(self.context, 'portal_plonemeeting')
        tool.deleteHistoryEvent(obj, event_time)
        return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])


class PMDocumentGenerationHelperView(ATDocumentGenerationHelperView):
    """ """

    def printHistory(self):
        """Return the history view for templates. """
        historyView = self.context.restrictedTraverse('historyview')()
        historyViewRendered = lxml.html.fromstring(historyView)
        return lxml.html.tostring(historyViewRendered.get_element_by_id('content-core'), method='xml')


class FolderDocumentGenerationHelperView(PMDocumentGenerationHelperView):
    """ """

    def selected_indexAdvisers_data(self, brains):
        """Compute advices data depending on what is selected in the current
           faceted regarding the 'indexAdvisers' index."""
        # get selected 'indexAdvisers' by finding the right faceted criterion
        criteria = ICriteria(self.real_context)._criteria()
        # get the 'indexAdvisers' value where adviser ids are stored
        advisers = []
        for criterion in criteria:
            if criterion.index == 'indexAdvisers':
                facetedQuery = json.loads(self.request.get('facetedQuery', '{}'))
                advisers = facetedQuery[criterion.__name__]

        # now build data
        # we will build following structure :
        # - a list of lists where :
        #   - first element is item;
        #   - next elements are a list of relevant advices data.
        # [
        #   [MeetingItemObject1, ['adviser_data_1', 'adviser_data_2', ]],
        #   [MeetingItemObject2, ['adviser_data_1', ]],
        #   ...
        # ]
        res = []
        for brain in brains:
            subres = {}
            item = brain.getObject()
            subres['item'] = item
            advisers_data = []
            # only keep relevant adviser data and keep order also
            for adviser in advisers:
                for groupId, advice in item.adviceIndex.iteritems():
                    if adviser in _to_coded_adviser_index(item, groupId, advice):
                        # we must keep this adviser
                        advisers_data.append(item.getAdviceDataFor(item, groupId))
            subres['advices'] = advisers_data
            res.append(subres)
        return res


class MeetingDocumentGenerationHelperView(FolderDocumentGenerationHelperView):
    """ """


class ItemDocumentGenerationHelperView(PMDocumentGenerationHelperView):
    """ """


class AdviceDocumentGenerationHelperView(PMDocumentGenerationHelperView):
    """ """
