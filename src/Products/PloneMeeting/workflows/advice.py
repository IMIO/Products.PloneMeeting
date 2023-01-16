# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass
from plone import api
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import ADVICE_GIVEN_HISTORIZED_COMMENT
from Products.PloneMeeting.interfaces import IMeetingAdviceWorkflowActions
from Products.PloneMeeting.interfaces import IMeetingAdviceWorkflowConditions
from zope.interface import implements


class MeetingAdviceWorkflowConditions(object):
    '''Adapts a MeetingAdvice to interface IMeetingAdviceWorkflowConditions.'''
    implements(IMeetingAdviceWorkflowConditions)
    security = ClassSecurityInfo()

    def __init__(self, advice):
        self.context = advice
        self.request = advice.REQUEST

    def _get_workflow(self):
        '''Return the workflow object used by self.context.'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getWorkflowsFor(self.context)[0]

    security.declarePublic('mayGiveAdvice')

    def mayGiveAdvice(self):
        '''See doc in interfaces.py.'''
        return self.request.get('mayGiveAdvice', False)

    security.declarePublic('mayBackToAdviceInitialState')

    def mayBackToAdviceInitialState(self):
        '''See doc in interfaces.py.'''
        return self.request.get('mayBackToAdviceInitialState', False)

    security.declarePublic('mayCorrect')

    def mayCorrect(self, destinationState=None):
        '''See doc in interfaces.py.'''
        res = False
        if _checkPermission(ReviewPortalContent, self.context):
            res = True
        return res


InitializeClass(MeetingAdviceWorkflowConditions)


class MeetingAdviceWorkflowActions(object):
    '''Adapts a MeetingAdvice to interface IMeetingAdviceWorkflowActions.'''
    implements(IMeetingAdviceWorkflowActions)
    security = ClassSecurityInfo()

    def __init__(self, advice):
        self.context = advice
        self.request = advice.REQUEST

    security.declarePrivate('doCorrect')

    def doCorrect(self, stateChange):
        """
          This is an unique wf action called for every transitions beginning with 'backTo'.
          Most of times we do nothing, but in some case, we check the old/new state and
          do some specific treatment.
        """
        pass

    security.declarePrivate('doGiveAdvice')

    def doGiveAdvice(self, stateChange):
        """Historize the advice and save item's relevant data
           if MeetingConfig.historizeItemDataWhenAdviceIsGiven.
           Make sure also the 'advice_given_on' data is correct in item's adviceIndex."""
        # historize
        self.context.historize_if_relevant(ADVICE_GIVEN_HISTORIZED_COMMENT)
        # manage 'advice_given_on' dates
        parent = self.context.aq_parent
        advice_given_on = self.context.get_advice_given_on()
        toLocalizedTime = parent.restrictedTraverse('@@plone').toLocalizedTime
        parent.adviceIndex[self.context.advice_group]['advice_given_on'] = advice_given_on
        parent.adviceIndex[self.context.advice_group]['advice_given_on_localized'] = toLocalizedTime(advice_given_on)


InitializeClass(MeetingAdviceWorkflowActions)
