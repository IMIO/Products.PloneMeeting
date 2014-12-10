from DateTime import DateTime
from AccessControl import Unauthorized
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.Archetypes import DisplayList


class ItemCompletenessView(BrowserView):
    '''Render the item completeness HTML on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self, 'portal_url').getPortalObject().absolute_url()

    def listSelectableCompleteness(self):
        '''Returns a list of completeness the current user can set the item to.'''
        # we base our actions on avaialble terms in the MeetingItem.completeness field vocabulary
        completenesses = self.context.listCompleteness()
        completenessKeys = completenesses.keys()
        currentCompleteness = self.context.getCompleteness()
        # now check if user can evaluate completeness
        if not self.context.adapted().mayEvaluateCompleteness():
            completenessKeys.remove('completeness_complete')
            completenessKeys.remove('completeness_incomplete')
            completenessKeys.remove('completeness_not_yet_evaluated')
            completenessKeys.remove('completeness_evaluation_not_required')
        # now check if user can set to 'completeness_evaluation_asked_again'
        if not self.context.adapted().mayAskCompletenessEvalAgain():
            completenessKeys.remove('completeness_evaluation_asked_again')
        # now if currentComplenteness is still in completeness, we remove it
        if currentCompleteness in completenessKeys:
            completenessKeys.remove(currentCompleteness)
        # now build a vocabulary with left values
        res = []
        for completeness in completenesses.items():
            if completeness[0] in completenessKeys:
                res.append(completeness)
        return DisplayList(tuple(res))


class ChangeItemCompletenessView(BrowserView):
    '''This manage the overlay popup displayed to enter a comment when the completeness is changed.'''

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
            # change completeness value, it will also check that given 'new_completeness_value'
            # is available in the field vocabulary if not available, and selectable by current user
            self._changeCompleteness(self.request.get('new_completeness_value'),
                                     comment=self.request.get('comment', ''))
            # update item
            self.context.at_post_edit_script()
            self.request.response.redirect(self.context.absolute_url())
        return self.index()

    def _changeCompleteness(self, new_completeness_value, bypassSecurityCheck=False, comment=''):
        '''Helper method that change completeness and manage completeness history.'''
        # make sure new_completeness_value exists in MeetingItem.listCompleteness vocabulary
        if not new_completeness_value in self.context.listCompleteness():
            raise KeyError("New value %s does not correspond to a value of MeetingItem.listCompleteness")

        if not bypassSecurityCheck and not new_completeness_value in \
           self.context.restrictedTraverse('@@item-completeness').listSelectableCompleteness():
            raise Unauthorized
        self.context.setCompleteness(new_completeness_value)
        # add a line to the item's completeness_changes_history
        membershipTool = getToolByName(self.context, 'portal_membership')
        member = membershipTool.getAuthenticatedMember()
        history_data = {'action': new_completeness_value,
                        'actor': member.getId(),
                        'time': DateTime(),
                        'comment': comment}
        self.context.completeness_changes_history.append(history_data)
        self.context.reindexObject(idxs=['getCompleteness', ])


class ItemCompletenessHistoryView(BrowserView):
    '''Display history of emergency value changes.'''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
