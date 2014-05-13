from AccessControl import Unauthorized
from DateTime import DateTime
from Products.CMFCore.Expression import Expression, createExprContext
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
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
        self.mayEdit = self.request.get('advice_change_delay_mayEdit')

    def listSelectableDelays(self, row_id):
        '''Returns a list of delays the current user can change the given p_row_id advice delay to.'''
        res = []
        # find linked rows in the MeetingConfig.customAdvisers
        isAutomatic, linkedRows = self.cfg._findLinkedRowsFor(row_id)
        # check if current user may change delays for advice
        if not self._mayEditDelays(isAutomatic):
            return res

        # evaluate the 'available_on' TAL expression defined on each linkedRows
        availableLinkedRows = []
        ctx = createExprContext(self.context.getParentNode(), self.portal, self.context)
        # Check that the TAL expression on the group returns True
        ctx.setGlobal('item', self.context)
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

        # no delay to change to, return
        if not availableLinkedRows:
            return res

        for linkedRow in availableLinkedRows:
            if linkedRow['row_id'] == row_id:
                continue
            res.append((linkedRow['row_id'], linkedRow['delay'], unicode(linkedRow['delay_label'], 'utf-8')))
        return res

    def _mayEditDelays(self, isAutomatic):
        '''Check if current user may edit delays for advice.  Given p_isAutomatic
           is a boolean specifying if the advice is an automatic one or not.'''
        if not isAutomatic:
            # user must have the 'PloneMeeting: Write optional advisers' on the item
            # to be able to change an optional adviser delay
            if not checkPermission('PloneMeeting: Write optional advisers', self.context):
                return False
        else:
            # only Managers and MeetingManagers can change an automatic advice delay
            # and only if the item or advice can be actually edited by the user
            tool = getToolByName(self.context, 'portal_plonemeeting')
            if not tool.isManager() or \
               (not checkPermission('Modify portal content', self.context) and not self.mayEdit):
                return False
        return True


class Gna(BrowserView):
    '''
      This manage the overlay popup displayed to enter a comment when the emergency is changed.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request

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
            # check that given 'new_emergency_value' is available in the field vocabulary
            # if not available, just raise Unauthorized
            new_emergency_value = self.request.get('new_emergency_value')
            if not new_emergency_value in self.context.listEmergencies().keys():
                raise Unauthorized
            self.context.setEmergency(new_emergency_value)
            # add a line to the item's emergency_change_history
            history_data = {'action': new_emergency_value,
                            'actor': '',
                            'time': DateTime(),
                            'comment': self.request.get('comment', '')}
            self.context.emergency_changes_history.append(history_data)
            self.request.response.redirect(self.context.absolute_url())
        return self.index()


class Gno(BrowserView):
    '''
      Display history of emergency value changes.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
