# -*- coding: utf-8 -*-
#
# File: annexes.py
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

from AccessControl import Unauthorized
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from plone import api
from imio.history.browser.views import IHVersionPreviewView


class AdvicesIcons(BrowserView):
    """
      Advices displayed as icons.
    """
    def __init__(self, context, request):
        """ """
        super(AdvicesIcons, self).__init__(context, request)
        self.tool = getToolByName(self, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()

    def __call__(self):
        if not self.context.adapted().isPrivacyViewable():
            return '-'
        return super(AdvicesIcons, self).__call__()

    def advicesDelayToWarn(self, advicesByType, userAdviserGroupIds):
        """We will warn if :
           - 'not_given' are in the addable advices;
           - 'hidden_during_redaction' or 'asked_again' are in the editable advices."""

        advicesToWarn = {}

        def _findAdviceToWarn(adviceType):
            smaller_delay = 999
            # if we did not found an advice to warn for current user, maybe there is an advice
            # with delay to be given by another group, we show it too
            for groupId, adviceInfo in self.context.adviceIndex.items():
                # find smaller delay
                if (adviceInfo['type'] == adviceType or (adviceType == 'hidden_during_redaction' and
                                                         adviceInfo['hidden_during_redaction'])) and \
                   adviceInfo['delay'] and \
                   adviceInfo['delay_infos']['left_delay'] < smaller_delay:
                    if groupId in userAdviserGroupIds:
                        advicesToWarn[adviceType] = adviceInfo, 0
                    # check if we already have a adviceToWarn, if user was adviser
                    # for this group, it is prioritary
                    elif not advicesToWarn.get(adviceType) or \
                            (advicesToWarn.get(adviceType) and not advicesToWarn[adviceType][1] == 0):
                        advicesToWarn[adviceType] = adviceInfo, 1
                    else:
                        continue
                    smaller_delay = adviceInfo['delay_infos']['left_delay']

        _findAdviceToWarn('not_given')
        _findAdviceToWarn('hidden_during_redaction')
        _findAdviceToWarn('asked_again')

        return advicesToWarn


class ChangeAdviceHiddenDuringRedactionView(BrowserView):
    """View that toggle the advice.advice_hide_during_redaction attribute."""

    def __call__(self):
        # user must be able to edit the advice
        if not _checkPermission(ModifyPortalContent, self.context):
            raise Unauthorized
        else:
            # toggle the value
            self.context.advice_hide_during_redaction = not bool(self.context.advice_hide_during_redaction)
            notify(ObjectModifiedEvent(self.context))
            if self.request.RESPONSE.status != 200:
                self.request.RESPONSE.status = 200
                if self.request.get('HTTP_REFERER') != self.request.RESPONSE.getHeader('location'):
                    return self.request.RESPONSE.getHeader('location')


class ChangeAdviceAskedAgainView(BrowserView):
    """View that change advice from someting to 'asked_again' and
       from 'asked_again' back to original advice."""

    def __call__(self):
        """ """
        pr = getToolByName(self.context, 'portal_repository')
        parent = self.context.getParentNode()
        if not self.context.advice_type == 'asked_again':
            # we are about to set advice to 'asked_again'
            if not parent.adapted().mayAskAdviceAgain(self.context):
                raise Unauthorized
            # historize the given advice if it was modified since last version
            self.context.versionate_if_relevant(comment='advice_asked_again_and_historized_comments')
            # now we may change advice_type to 'asked_again'
            self.context.advice_type = 'asked_again'
            # and we may also set 'advice_hide_during_redaction' to the default
            # value defined in the MeetingConfig
            tool = getToolByName(self.context, 'portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            self.context.advice_hide_during_redaction = cfg.getDefaultAdviceHiddenDuringRedaction()
        else:
            # we are about to set the advice back to original value
            if not parent.adapted().mayBackToPreviousAdvice(self.context):
                raise Unauthorized
            # get last version_id and fall back to it
            last_version_id = pr.getHistoryMetadata(self.context)._available[-1]
            self.context.revertversion(version_id=last_version_id)
            # revertversion would redirect to somewhere, break this
            self.request.RESPONSE.status = 200

        notify(ObjectModifiedEvent(self.context))


class AdviceConfidentialityView(BrowserView):
    """Display advice confidentiality infos."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()

    def __call__(self, advice):
        self.advice = advice
        return super(AdviceConfidentialityView, self).__call__()


class AdviceVersionPreviewView(IHVersionPreviewView):
    """ """
    def __init__(self, context, request):
        """ """
        super(AdviceVersionPreviewView, self).__init__(context, request)
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        self.adviceStyle = cfg.getAdviceStyle()
