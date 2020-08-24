# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_organization
from imio.actionspanel.interfaces import IContentDeletable
from imio.helpers.content import get_state_infos
from imio.history.browser.views import IHVersionPreviewView
from plone import api
from plone.dexterity.browser.view import DefaultView
from plone.memoize import ram
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from Products.PageTemplates.Expressions import SecureModuleImporter
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


def _delay_icon(memberIsAdviserForGroup, adviceInfo):
    """In case this is a delay aware advice, return a delay_icon
       if advice is not_given/hidden_during_redaction."""
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

    def __call___cachekey(method, self):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        # URL to the advice_type can change if server URL changed
        server_url = self.request.get('SERVER_URL', None)
        # an advice container's modification date is updated upon
        # any change on advice (added, removed, edited, attribute changed)
        # adviceIndex can also be updated by another item from which context inherits
        context_modified = max(int(self.context.modified()), self.context._p_mtime)
        return (self.context.UID(),
                context_modified,
                server_url,
                tool.get_plone_groups_for_user())

    @ram.cache(__call___cachekey)
    def __call__(self):
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advisableGroups = self.context.getAdvicesGroupsInfosForUser(compute_to_edit=False)
        self.advicesByType = self.context.getAdvicesByType()
        self.pm_utils = SecureModuleImporter['Products.PloneMeeting.utils']

        if not self.context.adapted().isPrivacyViewable():
            return '<div style="display: inline">&nbsp;-&nbsp;&nbsp;&nbsp;</div>'
        return super(AdvicesIcons, self).__call__()

    def advicesDelayToWarn(self):
        """We will warn if :
           - 'not_given' are in the addable advices;
           - 'hidden_during_redaction' or 'asked_again' are in the editable advices."""

        userAdviserOrgUids = self.tool.get_orgs_for_user(suffixes=['advisers'], the_objects=False)
        advicesToWarn = {}

        def _updateAdvicesToWarn(adviceType):
            smaller_delay = 999
            # if we did not found an advice to warn for current user, maybe there is an advice
            # with delay to be given by another group, we show it too
            for org_uid, adviceInfo in self.context.adviceIndex.items():
                # find smaller delay
                if (adviceInfo['type'] == adviceType or
                    (adviceType == 'hidden_during_redaction' and
                     adviceInfo['hidden_during_redaction'] and adviceInfo['advice_editable']) or
                    (adviceType == 'considered_not_given_hidden_during_redaction' and
                     adviceInfo['hidden_during_redaction'] and not adviceInfo['advice_editable'])) and \
                   adviceInfo['delay'] and \
                   adviceInfo['delay_infos']['left_delay'] < smaller_delay:
                    if org_uid in userAdviserOrgUids:
                        # determinate delay_icon to use
                        advicesToWarn[adviceType] = adviceInfo, _delay_icon(True, adviceInfo)
                    # check if we already have a adviceToWarn, if user was adviser
                    # for this group, it is prioritary
                    elif not advicesToWarn.get(adviceType) or \
                            (advicesToWarn.get(adviceType) and not advicesToWarn[adviceType][1] == 0):
                        advicesToWarn[adviceType] = adviceInfo, _delay_icon(False, adviceInfo)
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


class AdvicesIconsInfos(BrowserView):
    """ """

    def __call__(self, adviceType):
        """ """
        self._initAdvicesInfos(adviceType)
        return self.index()

    def _initAdvicesInfos(self, adviceType):
        """ """
        self.pm_utils = SecureModuleImporter['Products.PloneMeeting.utils']
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advisableGroups = self.context.getAdvicesGroupsInfosForUser(compute_to_add=False)
        self.advicesToEdit = [info[0] for info in self.advisableGroups[1]]
        self.advicesByType = self.context.getAdvicesByType()
        self.adviceType = adviceType
        self.userAdviserOrgUids = self.tool.get_orgs_for_user(suffixes=['advisers'], the_objects=False)

    def _initAdviceInfos(self, advice_id):
        """ """
        self.advice_id = advice_id
        self.memberIsAdviserForGroup = advice_id in self.userAdviserOrgUids
        self.adviceIsInherited = self.context.adviceIsInherited(advice_id)
        isRealManager = self.tool.isManager(self.context, realManagers=True)
        self.mayEdit = not self.adviceIsInherited and \
            ((self.advicesToEdit and advice_id in self.advicesToEdit) or
             (isRealManager and not self.adviceType == 'not_given'))

    def showLinkToInherited(self, adviceHolder):
        """ """
        return bool(self.adviceIsInherited and self.context._appendLinkedItem(
            adviceHolder, only_viewable=True))

    def mayRemoveInheritedAdvice(self):
        """To remove an inherited advice, must be :
           - MeetingManager and item is not decided;
           - or adviser for p_advice_id group and current item
             in a itemAdviceEditStates review_state."""
        res = False
        if self.adviceIsInherited:
            if self.tool.isManager(self.context) and \
               self.context.queryState() not in self.cfg.getItemDecidedStates():
                res = True
            else:
                if self.cfg.getInheritedAdviceRemoveableByAdviser() and \
                   self.advice_id in self.userAdviserOrgUids and \
                   self.context.queryState() in get_organization(
                        self.advice_id).get_item_advice_edit_states(cfg=self.cfg):
                    return True
        return res

    def mayDelete(self, advice):
        """ """
        return IContentDeletable(advice).mayDelete(advisableGroups=self.advisableGroups)

    def mayView(self):
        """ """
        return self.memberIsAdviserForGroup or \
            self.mayEdit or \
            self.adviceType not in ('hidden_during_redaction', 'considered_not_given_hidden_during_redaction')

    def mayChangeDelay(self):
        """ """
        res = False
        if self.context.adviceIndex[self.advice_id]['delay'] and not self.adviceIsInherited:
            view = self.context.restrictedTraverse('@@advice-available-delays')
            view._initAttributes(self.advice_id)
            res = view.listSelectableDelays() or \
                view._mayAccessDelayChangesHistory() or view._mayReinitializeDelay()
        return res

    def delay_icon(self, adviceInfo):
        """Makes it callable in the template."""
        return _delay_icon(self.memberIsAdviserForGroup, adviceInfo)

    def authorname(self, advice):
        author = api.user.get(advice.Creator())
        return author and author.getProperty('fullname') or advice.Creator()

    def state_infos(self, advice):
        return get_state_infos(advice)


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
        if self.context.advice_type != 'asked_again':
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
            self.context.advice_hide_during_redaction = \
                bool(self.context.portal_type in cfg.getDefaultAdviceHiddenDuringRedaction())
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
        item_state = parent.queryState()
        parent._sendAdviceToGiveMailIfRelevant(old_review_state=item_state,
                                               new_review_state=item_state,
                                               force_resend_if_in_advice_review_states=True)


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


class AdviceView(DefaultView):
    """ """

    def __call__(self):
        """Check if viewable by current user in case smart guy call the right url."""
        parent = self.context.aq_inner.aq_parent
        advice_icons_infos = parent.restrictedTraverse('@@advices-icons-infos')
        advice_type = parent._shownAdviceTypeFor(parent.adviceIndex[self.context.advice_group])
        advice_icons_infos._initAdvicesInfos(advice_type)
        advice_icons_infos._initAdviceInfos(self.context.advice_group)
        if not advice_icons_infos.mayView():
            raise Unauthorized
        return super(AdviceView, self).__call__()
