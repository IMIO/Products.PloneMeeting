from AccessControl import Unauthorized

from zope.component import getMultiAdapter
from zope.i18n import translate

from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE


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
      Manage the fact of going to a given item uid.  This method is used
      in the item navigation widget (go to previous item, go to next item, ...)
    """
    def __call__(self, objectId, idType):
        """
          objectId is either an uid or an item number.  idType discriminate this.
        """
        if idType == 'uid':
            # Search the object in the uid catalog
            obj = self.context.uid_catalog(UID=objectId)[0].getObject()
        elif idType == 'number':
            # The object is an item whose number is given in objectId
            meeting = self.context.uid_catalog(UID=self.context.REQUEST.get('meetingUid'))[0].getObject()
            obj = meeting.getItemByNumber(int(objectId))
        objectUrl = obj.absolute_url()
        return self.context.REQUEST.RESPONSE.redirect(objectUrl)


class ChangeItemOrderView(BrowserView):
    """
      Manage the functionnality that change item order on a meeting.
      Change one level up/down or to a given p_moveNumber.
    """
    def __call__(self, moveType, moveNumber=None):
        """
          Change the items order on a meeting.
          This is an unrestricted method so a MeetingManager can change items
          order even if some items are no more movable because decided
          (and so no more 'Modify portal content' on it).
          We double check that current user can actually mayChangeItemsOrder.
          Anyway, this method move an item, one level up/down or at a given position.
        """
        gotoReferer = self.context.restrictedTraverse('@@actions_panel')._gotoReferer

        # we do this unrestrictively but anyway respect the Meeting.mayChangeItemsOrder
        meeting = self.context.getMeeting()

        if not meeting.wfConditions().mayChangeItemsOrder():
            raise Unauthorized

        # Move the item up (-1), down (+1) or at a given position ?
        if moveType == 'number':
            isDelta = False
            try:
                move = int(moveNumber)
                # In this case, moveNumber specifies the new position where
                # the item must be moved.
            except (ValueError, TypeError):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_number_invalid',
                              domain='PloneMeeting',
                              context=self.request))
                return gotoReferer()
        else:
            isDelta = True
            if moveType == 'up':
                move = -1
            elif moveType == 'down':
                move = 1

        nbOfItems = len(meeting.getRawItems())

        # Calibrate and validate moveValue
        if not isDelta:
            # Is this move allowed ?
            if move in (self.context.getItemNumber(), self.context.getItemNumber()+1):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_did_not_move',
                              domain='PloneMeeting',
                              context=self.request))
                return gotoReferer()
            if (move < 1) or (move > (nbOfItems+1)):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_illegal_move',
                              domain='PloneMeeting',
                              context=self.request))
                return gotoReferer()

        # Move the item
        if nbOfItems >= 2:
            if isDelta:
                # Move the item with a delta of +1 or -1
                oldIndex = self.context.getItemNumber()
                newIndex = oldIndex + move
                if (newIndex >= 1) and (newIndex <= nbOfItems):
                    for item in meeting.getItems():
                        if item.getItemNumber() == newIndex:
                            item.setItemNumber(oldIndex)
                            item.reindexObject(idxs=['getItemNumber'])
                            break
                    self.context.setItemNumber(newIndex)
                    self.context.reindexObject(idxs=['getItemNumber'])
            else:
                # Move the item to an absolute position
                oldIndex = self.context.getItemNumber()
                itemsList = meeting.getItems()
                if move < oldIndex:
                    # We must move the item closer to the first items (up)
                    for item in itemsList:
                        itemNumber = item.getItemNumber()
                        if (itemNumber < oldIndex) and (itemNumber >= move):
                            item.setItemNumber(itemNumber+1)
                            item.reindexObject(idxs=['getItemNumber'])
                        elif itemNumber == oldIndex:
                            item.setItemNumber(move)
                            item.reindexObject(idxs=['getItemNumber'])
                else:
                    # We must move the item closer to the last items (down)
                    for item in itemsList:
                        itemNumber = item.getItemNumber()
                        if itemNumber == oldIndex:
                            item.setItemNumber(move-1)
                            item.reindexObject(idxs=['getItemNumber'])
                        elif (itemNumber > oldIndex) and (itemNumber < move):
                            item.setItemNumber(itemNumber-1)
                            item.reindexObject(idxs=['getItemNumber'])

        # when items order on meeting changed, it is considered modified
        meeting.notifyModified()

        return gotoReferer()


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
