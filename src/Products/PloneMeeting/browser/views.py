from AccessControl import Unauthorized

from zope.component import getMultiAdapter
from zope.i18n import translate

from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.indexes import _compute_sortable_itemNumber


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
        return self.tool.readCookie('pmShowDescriptions') == 'true' and True or False


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
        # make sure we have a list of uids, in some case, as it is called
        # by jQuery, we receive only one uid, as a string...
        if isinstance(uids, str):
            uids = [uids]
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
        return member.has_permission(self.context.getField('toDiscuss').write_permission, self.context) and self.context.showToDiscuss()

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
        brains = catalog(linkedMeetingUID=meeting.UID(),
                         sortable_itemNumber=_compute_sortable_itemNumber(itemNumber))
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


class ChangeItemOrderView(BrowserView):
    """
      Manage the functionnality that change item order on a meeting.
      Change one level up/down or to a given p_moveNumber.
    """

    def _compute_value_to_add(self, itemNumber):
        """ """
        if itemNumber.is_integer():
            return 1
        else:
            # XXX to be changed
            return 0.1

    def __call__(self, moveType, moveNumber=None):
        """
          Change the items order on a meeting.
          This is an unrestricted method so a MeetingManager can change items
          order even if some items are no more movable because decided
          (and so no more 'Modify portal content' on it).
          We double check that current user can actually mayChangeItemsOrder.
          Anyway, this method move an item, one level up/down or at a given position.
        """
        # we do this unrestrictively but anyway respect the Meeting.mayChangeItemsOrder
        meeting = self.context.getMeeting()

        if not meeting.wfConditions().mayChangeItemsOrder():
            raise Unauthorized

        itemNumber = self.context.getItemNumber()

        # Move the item up (-1), down (+1) or at a given position ?
        if moveType == 'number':
            try:
                moveNumber = float(moveNumber)
                # In this case, moveNumber specifies the new position where
                # the item must be moved.
            except (ValueError, TypeError):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_number_invalid',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return

        nbOfItems = len(meeting.getRawItems())

        # Calibrate and validate moveValue
        if moveType == 'number':
            # Is this move allowed ?
            if moveNumber == itemNumber:
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_did_not_move',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
            if (moveNumber < 1) or (moveNumber > nbOfItems):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_illegal_move',
                              mapping={'nbOfItems': nbOfItems},
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
            # we are using a decimal (like 1.1 or 12.4) check that it is allowed
            # if we specified "3.1", item number "3" must exist,
            # if we specified "3.3", item number "3.2" must exist
            if not moveNumber.is_integer():
                newInteger, newDecimal = str(moveNumber).split('.')
                newDecimal = str(int(newDecimal) - 1)
                newInteger = int(newInteger)
                newDecimal = int(newDecimal)
                previousItemNumber = float('{0}.{1}'.format(newInteger, newDecimal))
                previousItem = meeting.getItemByNumber(previousItemNumber)
                if not previousItem or previousItem == self.context:
                    self.context.plone_utils.addPortalMessage(
                        translate(msgid='item_illegal_decimal',
                                  domain='PloneMeeting',
                                  context=self.request),
                        type='warning')
                    return

        # Move the item
        if nbOfItems >= 2:
            if not moveType == 'number':
                # switch the items
                oldIndex = self.context.getItemNumber()
                if moveType == 'up':
                    if oldIndex == 1:
                        # moving first item 'up', does not change anything
                        # actually it is not possible in the UI because the 'up'
                        # icon is not displayed on the first item
                        return
                    otherNumber = self.context.getSiblingItemNumber('previous')
                else:
                    # moveType == 'down'
                    otherNumber = self.context.getSiblingItemNumber('next')
                otherItem = meeting.getItemByNumber(otherNumber)
                self.context.setItemNumber(otherItem.getItemNumber())
                self.context.reindexObject(idxs=['sortable_itemNumber'])
                otherItem.setItemNumber(oldIndex)
                otherItem.reindexObject(idxs=['sortable_itemNumber'])
            else:
                # Move the item to an absolute position
                oldIndex = self.context.getItemNumber()
                itemsList = meeting.getItems()
                if moveNumber < oldIndex:
                    # We must move the item closer to the first items (up)
                    if moveNumber.is_integer() and oldIndex.is_integer():
                        for item in itemsList:
                            itemNumber = round(item.getItemNumber(), 5)
                            if (itemNumber < oldIndex) and (itemNumber >= moveNumber):
                                item.setItemNumber(itemNumber+1)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                            elif itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                    elif not moveNumber.is_integer() and oldIndex.is_integer():
                        # moving "13" to "12.1" or "12.5"
                        for item in itemsList:
                            itemNumber = round(item.getItemNumber(), 5)
                            integer, decimal = str(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                            elif itemNumber >= moveNumber:
                                # an itemNumber with decimal using same integer as moveNumber?
                                if integer == newInteger:
                                    item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                elif itemNumber >= oldIndex:
                                    # use same integer as
                                    item.setItemNumber(itemNumber - 1)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                    elif moveNumber.is_integer() and not oldIndex.is_integer():
                        # moving "12.1" to "10" or "5"
                        oldInteger, oldDecimal = str(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        for item in itemsList:
                            itemNumber = round(item.getItemNumber(), 5)
                            integer, decimal = str(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                            elif itemNumber >= moveNumber:
                                # like "12.2" that needs to become "12.1"
                                # special case when moving "7.2" to "7", just update the "7 and 7.x"
                                if moveNumber == oldInteger:
                                    if not integer == oldInteger:
                                        continue
                                    if itemNumber < oldIndex:
                                        item.setItemNumber(itemNumber + self._compute_value_to_add(oldIndex))
                                    else:
                                        item.setItemNumber(itemNumber - self._compute_value_to_add(oldIndex))
                                elif integer == oldInteger and decimal > oldDecimal:
                                    item.setItemNumber(itemNumber + 1 - self._compute_value_to_add(itemNumber))
                                else:
                                    item.setItemNumber(itemNumber + 1)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                    elif not moveNumber.is_integer() and not oldIndex.is_integer():
                        # moving "12.2" to "4.1" or "4.3"
                        oldInteger, oldDecimal = str(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        newInteger, newDecimal = str(moveNumber).split('.')
                        newInteger = int(newInteger)
                        newDecimal = int(newDecimal)
                        for item in itemsList:
                            itemNumber = round(item.getItemNumber(), 5)
                            integer, decimal = str(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                            elif itemNumber >= moveNumber:
                                # like "12.2" that needs to become "12.1"
                                if integer == oldInteger and decimal > oldDecimal:
                                    item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                elif integer == newInteger:
                                    item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['sortable_itemNumber'])
                else:
                    if moveNumber.is_integer() and oldIndex.is_integer():
                        # We must move the item closer to the last items (down)
                        movingMasterElement = bool(meeting.getItemByNumber(oldIndex + 0.1))
                        for item in itemsList:
                            itemNumber = round(item.getItemNumber(), 5)
                            integer, decimal = str(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if movingMasterElement:
                                if itemNumber == oldIndex:
                                    item.setItemNumber(moveNumber)
                                    item.reindexObject(idxs=['sortable_itemNumber'])
                                elif integer == oldIndex:
                                    # if we moved the first element of subelements
                                    # (like '2' and there is '2.1', '2.2')
                                    # we need to remove 0.1 to following elements...
                                    item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['sortable_itemNumber'])
                                elif itemNumber >= moveNumber:
                                    item.setItemNumber(itemNumber + 1)
                                    item.reindexObject(idxs=['sortable_itemNumber'])
                            else:
                                if itemNumber == oldIndex:
                                    item.setItemNumber(moveNumber)
                                    item.reindexObject(idxs=['sortable_itemNumber'])
                                elif (itemNumber > oldIndex) and (itemNumber <= moveNumber):
                                    item.setItemNumber(itemNumber - 1)
                                    item.reindexObject(idxs=['sortable_itemNumber'])
                    elif not moveNumber.is_integer() and oldIndex.is_integer():
                        # moving "4" to "12.1" or "12.5"
                        # special case, moving
                        for item in itemsList:
                            itemNumber = round(item.getItemNumber(), 5)
                            newInteger, newDecimal = str(moveNumber).split('.')
                            newInteger = int(newInteger)
                            newDecimal = int(newDecimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['sortable_itemNumber'])
                            # take every items before, including every 12.x
                            elif itemNumber > oldIndex:
                                if itemNumber == newInteger:
                                    if itemNumber <= moveNumber:
                                        item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                    else:
                                        item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                else:
                                    # use same integer as
                                    item.setItemNumber(itemNumber - 1)
                                item.reindexObject(idxs=['sortable_itemNumber'])


        # when items order on meeting changed, it is considered modified
        meeting.notifyModified()


class UpdateDelayAwareAdvicesView(BrowserView):
    """
      This is a view that is called as a maintenance task by Products.cron4plone.
      As we use clear days to compute advice delays, it will be launched at 0:00
      each night and update relevant items containing delay-aware advices still addable/editable.
      It will also update the indexAdvisers portal_catalog index.
    """
    def __call__(self):
        tool = getToolByName(self.context, 'portal_plonemeeting')
        query = self._computeQuery()
        tool._updateAllAdvices(query=query)

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
