from DateTime import DateTime
from AccessControl import Unauthorized
from Products.CMFCore.Expression import Expression, createExprContext
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.MeetingItem import ADVICE_AVAILABLE_ON_CONDITION_ERROR
from Products.PloneMeeting.utils import checkPermission
import logging
logger = logging.getLogger('PloneMeeting')


class AdviceDelaysView(BrowserView):
    '''Render the advice available delays HTML on the advices list.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal = getToolByName(self, 'portal_url').getPortalObject()
        self.portal_url = self.portal.absolute_url()
        self.advice = self.request.get('advice_change_delay_advice')
        self.cfg = self.request.get('advice_change_delay_cfg')

    def listSelectableDelays(self, row_id):
        '''Returns a list of delays the current user can change the given p_row_id advice delay to.'''
        # find linked rows in the MeetingConfig.customAdvisers
        isAutomatic, linkedRows = self.cfg._findLinkedRowsFor(row_id)
        # check if current user may change delays for advice
        if not self._mayEditDelays(isAutomatic):
            return []
        return self._availableDelays(linkedRows, row_id)

    def _mayEditDelays(self, isAutomatic):
        '''Check if current user may edit delays for advice.  Given p_isAutomatic
           is a boolean specifying if the advice is an automatic one or not.
           The rule managed here is :
           - An optional (not isAutomatic) advice can be edited if the user,
             has the 'PloneMeeting: Write optional advisers' permission on the item;
           - An automatic advice delay can only be edited by Managers (and MeetingManagers);
           - In both cases (isAutomatic or not) the delay can be changed only if the advice has still
             never be giveable or is currently giveable, but no more when the advice is no more giveable.'''
        # advice is not automatic, the user must have 'PloneMeeting: Write optional advisers' permission
        if not isAutomatic:
            if not checkPermission('PloneMeeting: Write optional advisers', self.context):
                return False
        else:
            # advice is automatic, only Managers and MeetingManagers can change an automatic advice delay
            # and only if the advice still could not be given or if it is currently editable
            tool = getToolByName(self.context, 'portal_plonemeeting')
            if not tool.isManager(self.context) or not checkPermission('Modify portal content', self.context):
                return False
        # we can not change delay for an advice that is no more giveable,
        # aka for wich a delay_stopped_on date is defined
        if self.context.adviceIndex[self.advice['id']]['delay_stopped_on']:
            return False
        return True

    def _availableDelays(self, linkedRows, row_id):
        '''Returns available delays.'''
        res = []
        # evaluate the 'available_on' TAL expression defined on each linkedRows
        availableLinkedRows = []
        ctx = createExprContext(self.context.getParentNode(), self.portal, self.context)
        # Check that the TAL expression on the group returns True
        ctx.setGlobal('item', self.context)
        # set a special value in the request usable in the TAL expression
        # that just specify that we are managing available delays
        # this way, it is easy to protect a custom adviser by just checking
        # this value in the REQUEST
        self.request.set('managing_available_delays', True)
        for linkedRow in linkedRows:
            eRes = False
            try:
                if linkedRow['available_on']:
                    eRes = Expression(linkedRow['available_on'])(ctx)
                else:
                    eRes = True
            except Exception, e:
                logger.warning(ADVICE_AVAILABLE_ON_CONDITION_ERROR % str(e))
            if eRes:
                availableLinkedRows.append(linkedRow)
        self.request.set('managing_available_delays', False)

        # no delay to change to, return
        if not availableLinkedRows:
            return res

        for linkedRow in availableLinkedRows:
            if linkedRow['row_id'] == row_id:
                continue
            res.append((linkedRow['row_id'], linkedRow['delay'], unicode(linkedRow['delay_label'], 'utf-8')))
        return res

    def _mayAccessDelayChangesHistory(self, adviceId=None):
        '''May current user access delay changes history?'''
        if not adviceId:
            adviceId = self.advice['id']
        tool = getToolByName(self.context, 'portal_plonemeeting')
        # MeetingManagers and advisers of the group
        # can access the delay changes history
        if tool.isManager(self.context) or adviceId in [group.getId() for group in tool.getGroupsForUser(suffix='advisers')]:
            return True
        else:
            return False


class AdviceChangeDelayView(BrowserView):
    '''This manage the overlay popup displayed to enter a comment when the delay is changed.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        self.cfg = cfg

    def getDataForRowId(self, row_id):
        '''Return relevant advice infos for given p_row_id.'''
        return self.cfg._dataForCustomAdviserRowId(row_id)

    def __call__(self):
        form = self.request.form
        submitted = form.get('form.buttons.save', False) or form.get('form.submitted', False)
        cancelled = form.get('form.buttons.cancel', False)
        if cancelled:
            # the only way to enter here is the popup overlay not to be shown
            # because while using the popup overlay, the jQ function take care of hidding it
            # while the Cancel button is hit
            return self.request.response.redirect(self.context.absolute_url())
        elif submitted:
            # check that given 'new_advice_delay' is available
            # if not available, just raise Unauthorized
            current_advice_row_id = self.request.get('current_advice_row_id')
            new_advice_row_id = self.request.get('new_advice_row_id')
            listAvailableDelaysView = self.context.restrictedTraverse('@@advice-available-delays')
            listAvailableDelaysView.cfg = self.cfg
            # find right advice in MeetingItem.adviceIndex
            currentAdviceData = self.getDataForRowId(current_advice_row_id)
            listAvailableDelaysView.advice = self.context.adviceIndex[currentAdviceData['group']]
            isAutomatic, linkedRows = self.cfg._findLinkedRowsFor(current_advice_row_id)
            selectableDelays = listAvailableDelaysView.listSelectableDelays(current_advice_row_id)
            # selectableDelays is a list of tuple containing 3 elements, the first is the row_id
            selectableDelays = [selectableDelay[0] for selectableDelay in selectableDelays]
            if not new_advice_row_id in selectableDelays:
                raise Unauthorized
            # update the advice with new delay and relevant data

            newAdviceData = self.getDataForRowId(new_advice_row_id)
            # just keep relevant infos
            dataToUpdate = ('delay',
                            'delay_label',
                            'gives_auto_advice_on_help_message',
                            'row_id')
            for elt in dataToUpdate:
                self.context.adviceIndex[currentAdviceData['group']][elt] = newAdviceData[elt]
            # if the advice was already given, we need to update row_id on the given advice object too
            if not self.context.adviceIndex[currentAdviceData['group']]['type'] == NOT_GIVEN_ADVICE_VALUE:
                adviceObj = getattr(self.context, self.context.adviceIndex[currentAdviceData['group']]['advice_id'])
                adviceObj.advice_row_id = newAdviceData['row_id']
            # if it is an optional advice, update the MeetingItem.optionalAdvisers
            if not isAutomatic:
                optionalAdvisers = list(self.context.getOptionalAdvisers())
                # remove old value
                optionalAdvisers.remove('%s__rowid__%s' % (currentAdviceData['group'],
                                                           currentAdviceData['row_id']))
                # append new value
                optionalAdvisers.append('%s__rowid__%s' % (newAdviceData['group'],
                                                           newAdviceData['row_id']))
                self.context.setOptionalAdvisers(tuple(optionalAdvisers))
            else:
                # if it is an automatic advice, set the 'delay_for_automatic_adviser_changed_manually' to True
                self.context.adviceIndex[currentAdviceData['group']]['delay_for_automatic_adviser_changed_manually'] = True
            self.context.updateLocalRoles()
            # add a line to the item's emergency_change_history
            membershipTool = getToolByName(self.context, 'portal_membership')
            member = membershipTool.getAuthenticatedMember()
            history_data = {'action': (currentAdviceData['delay'], newAdviceData['delay']),
                            'actor': member.getId(),
                            'time': DateTime(),
                            'comment': self.request.get('comment', '')}
            self.context.adviceIndex[currentAdviceData['group']]['delay_changes_history'].append(history_data)
            self.request.response.redirect(self.context.absolute_url() + '/#adviceAndAnnexes')
        return self.index()


class AdviceChangeDelayHistoryView(BrowserView):
    '''Display history of advice delay value changes.'''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request

    def getHistoryInfos(self):
        '''
          Return history of delay changes for an advice.
        '''
        delayChangesView = self.context.restrictedTraverse('@@advice-available-delays')
        adviceId = self.request.get('advice')
        if not delayChangesView._mayAccessDelayChangesHistory(adviceId):
            raise Unauthorized
        return self.context.adviceIndex[adviceId]['delay_changes_history']
