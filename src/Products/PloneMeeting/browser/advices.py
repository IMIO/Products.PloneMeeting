# -*- coding: utf-8 -*-
#
# File: advices.py
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
from imio.actionspanel.interfaces import IContentDeletable
from imio.history.browser.views import IHVersionPreviewView
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from Products.PloneMeeting.interfaces import IMeetingItem
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


def delay_icon(memberIsAdviserForGroup, adviceInfo):
    """In case this is a delay aware advie, return a delay_icon is advie is not_given/hidden_during_redaction."""
    if not memberIsAdviserForGroup:
        return 'advice_with_delay_disabled_big.png'
    else:
        delay_status = adviceInfo['delay_infos']['delay_status']
        if delay_status == 'still_time':
            return 'advice_with_delay_big_green.png'
        elif delay_status == 'still_time_but_alert':
            return 'advice_with_delay_big_orange.png'
        elif delay_status == 'timed_out':
            return 'advice_with_delay_big_red.png'
        else:
            return 'advice_with_delay_big.png'


class AdvicesIcons(BrowserView):
    """
      Advices displayed as icons.
    """
    def __call__(self):
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advisableGroups = self.context.getAdvicesGroupsInfosForUser()
        self.advicesByType = self.context.getAdvicesByType()

        if not self.context.adapted().isPrivacyViewable():
            return '<div style="display: inline">&nbsp;-&nbsp;&nbsp;&nbsp;</div>'
        return super(AdvicesIcons, self).__call__()

    def advicesDelayToWarn(self):
        """We will warn if :
           - 'not_given' are in the addable advices;
           - 'hidden_during_redaction' or 'asked_again' are in the editable advices."""

        userAdviserGroupIds = [group.getId() for group in self.tool.getGroupsForUser(suffixes=['advisers'])]
        advicesToWarn = {}

        def _updateAdvicesToWarn(adviceType):
            smaller_delay = 999
            # if we did not found an advice to warn for current user, maybe there is an advice
            # with delay to be given by another group, we show it too
            for groupId, adviceInfo in self.context.adviceIndex.items():
                # find smaller delay
                if (adviceInfo['type'] == adviceType or
                    (adviceType == 'hidden_during_redaction' and
                     adviceInfo['hidden_during_redaction'] and adviceInfo['advice_editable']) or
                    (adviceType == 'considered_not_given_hidden_during_redaction' and
                     adviceInfo['hidden_during_redaction'] and not adviceInfo['advice_editable'])) and \
                   adviceInfo['delay'] and \
                   adviceInfo['delay_infos']['left_delay'] < smaller_delay:
                    if groupId in userAdviserGroupIds:
                        # determinate delay_icon to use
                        advicesToWarn[adviceType] = adviceInfo, delay_icon(True, adviceInfo)
                    # check if we already have a adviceToWarn, if user was adviser
                    # for this group, it is prioritary
                    elif not advicesToWarn.get(adviceType) or \
                            (advicesToWarn.get(adviceType) and not advicesToWarn[adviceType][1] == 0):
                        advicesToWarn[adviceType] = adviceInfo, delay_icon(False, adviceInfo)
                    else:
                        continue
                    smaller_delay = adviceInfo['delay_infos']['left_delay']

        _updateAdvicesToWarn('not_given')
        _updateAdvicesToWarn('hidden_during_redaction')
        _updateAdvicesToWarn('considered_not_given_hidden_during_redaction')
        _updateAdvicesToWarn('asked_again')

        return advicesToWarn

    def getAddableAdvicePortalTypes(self, advicesToAdd):
        """ """
        res = []
        for adviceToAdd in advicesToAdd:
            advice_portal_type = self.context.adapted()._advicePortalTypeForAdviser(adviceToAdd)
            if advice_portal_type not in res:
                res.append(advice_portal_type)
        return res

    def get_tooltipster_base_class(self):
        """Return a different CSS class if context is a dashboard or not
           so we may initialize the tooltipster differently (regarding 'position' especially)."""
        published = self.request.get('PUBLISHED', None)
        published = published and published.aq_parent or self.context
        base_class = 'tooltipster-dashboard-advices-infos'
        if IMeetingItem.providedBy(published):
            base_class = 'tooltipster-advices-infos'
        return base_class


class AdvicesIconsInfos(BrowserView):
    """ """

    def __call__(self, adviceType):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advisableGroups = self.context.getAdvicesGroupsInfosForUser()
        self.advicesByType = self.context.getAdvicesByType()
        self.adviceType = adviceType
        return self.index()

    def showLinkToInherited(self, adviceIsInherited, adviceHolder):
        """ """
        return bool(adviceIsInherited and self.context._appendLinkedItem(adviceHolder, only_viewable=True))

    def mayDelete(self, advice):
        """ """
        return IContentDeletable(advice).mayDelete(advisableGroups=self.advisableGroups)

    def delay_icon(self, memberIsAdviserForGroup, adviceInfo):
        """Makes it callable in the template."""
        return delay_icon(memberIsAdviserForGroup, adviceInfo)

    def authorname(self, advice):
        author = api.user.get(advice.Creator())
        return author and author.getProperty('fullname') or advice.Creator()


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
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            self.context.advice_hide_during_redaction = cfg.getDefaultAdviceHiddenDuringRedaction()
        else:
            pr = api.portal.get_tool('portal_repository')
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
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, advice):
        self.advice = advice
        return super(AdviceConfidentialityView, self).__call__()


class AdviceVersionPreviewView(IHVersionPreviewView):
    """ """
    def __init__(self, context, request):
        """ """
        super(AdviceVersionPreviewView, self).__init__(context, request)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        self.adviceStyle = cfg.getAdviceStyle()
