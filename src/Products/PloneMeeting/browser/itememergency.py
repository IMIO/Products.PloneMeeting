from AccessControl import Unauthorized
from DateTime import DateTime
from Products.Archetypes import DisplayList
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView


class ItemEmergencyView(BrowserView):
    '''Render the item emergency HTML on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self, 'portal_url').getPortalObject().absolute_url()

    def listSelectableEmergencies(self):
        '''Returns a list of emergencies the current user can set the item to.'''
        # we base our actions on avaialble terms in the MeetingItem.emergency field vocabulary
        emergencies = self.context.listEmergencies()
        emergencyKeys = emergencies.keys()
        currentEmergency = self.context.getEmergency()
        # now check if user can ask emergency if it is not already the case
        if not self.mayAskEmergency():
            emergencyKeys.remove('emergency_asked')
        # now check if user can accept/refuse and asked emergency if it is not already the case
        if not self.mayAcceptOrRefuseEmergency():
            emergencyKeys.remove('emergency_accepted')
            emergencyKeys.remove('emergency_refused')
        # now if currentEmergency is still in emergencies, we remove it
        if currentEmergency in emergencies:
            emergencyKeys.remove(currentEmergency)
        # now build a vocabulary with left values
        res = []
        for emergency in emergencies.items():
            if emergency[0] in emergencyKeys:
                res.append(emergency)
        return DisplayList(tuple(res))

    def mayAskEmergency(self):
        '''Returns True if current user may ask emergency for an item.'''
        # by default, everybody able to edit the item can ask emergency
        return True

    def mayAcceptOrRefuseEmergency(self):
        '''Returns True if current user may accept or refuse emergency if asked for an item.'''
        # by default, only MeetingManagers can accept or refuse emergency
        tool = getToolByName(self, 'portal_plonemeeting')
        if tool.isManager():
            return True
        return False


class ChangeItemEmergencyView(BrowserView):
    '''
      This manage the overlay popup displayed when the emergency is changed and need a comment.
      When the emergency change does not need a comment, this views is also used but the comment popup
      is not shown.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request

    def __call__(self):
        form = self.request.form
        # either we received form.submitted in the request because we are triggering
        # a transition that does not need a confirmation or we clicked on the save button of
        # the confirmation popup
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


class ItemEmergencyHistoryView(BrowserView):
    '''
      Display history of emergency value changes.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
