# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_plone_group_id
from imio.actionspanel.interfaces import IContentDeletable
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_user_fullname
from imio.helpers.content import get_vocab_values
from imio.helpers.workflow import get_state_infos
from imio.history.browser.views import EventPreviewView
from imio.history.interfaces import IImioHistory
from imio.history.utils import get_event_by_time
from imio.history.utils import getLastWFAction
from plone import api
from plone.autoform import directives
from plone.autoform.form import AutoExtensibleForm
from plone.dexterity.browser.edit import DefaultEditForm
from plone.dexterity.browser.view import DefaultView
from plone.memoize import ram
from plone.supermodel import model
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from Products.PloneMeeting.browser.advicechangedelay import _reinit_advice_delay
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import get_event_field_data
from Products.PloneMeeting.utils import is_proposing_group_editor
from Products.PloneMeeting.utils import isPowerObserverForCfg
from z3c.form import form
from zope import schema
from zope.component import getAdapter
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.lifecycleevent import Attributes
from zope.lifecycleevent import ObjectModifiedEvent

import json


def _delay_icon(memberIsAdviserForGroup, advice_info):
    """In case this is a delay aware advice, return a delay_icon
       if advice is not_given/hidden_during_redaction."""
    if not memberIsAdviserForGroup:
        return 'advice_with_delay_disabled_big.png'
    else:
        delay_status = advice_info['delay_infos']['delay_status']
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
        cfg = tool.getMeetingConfig(self.context)
        # when advices to add, the add advice icon is displayed
        # this takes PowerAdviser into account as well
        has_advices_to_add = self.context.getAdvicesGroupsInfosForUser(
            compute_to_edit=False)
        # confidential advices
        # check confidential advices if not MeetingManager
        isManager = tool.isManager(cfg)
        may_view_confidential_advices = True
        # bypass if no advices
        # but we need nevertheless to compute has_advices_to_add because
        # we may have no advices and no advices and power adviser may add advice
        advices = self.context.adviceIndex.values()
        isPrivacyViewable = True
        if advices and not isManager:
            isPrivacyViewable = self.context.isPrivacyViewable()
            if isPrivacyViewable:
                # if current user is a power observer that would not see the advice
                # we store user plone groups because a power adviser may see a confidential advice
                # if member of the proposingGroup
                confidential_advices = [advice for advice in advices
                                        if advice["isConfidential"] and
                                        not get_plone_group_id(advice["id"], "advisers") in
                                        get_plone_groups_for_user()]
                may_view_confidential_advices = not confidential_advices or \
                    not isPowerObserverForCfg(cfg, power_observer_types=cfg.getAdviceConfidentialFor())
        return (repr(self.context),
                self.context.adviceIndex._p_mtime,
                server_url,
                has_advices_to_add,
                isPrivacyViewable,
                may_view_confidential_advices)

    @ram.cache(__call___cachekey)
    def __call__(self):
        self.advisableGroups = self.context.getAdvicesGroupsInfosForUser(compute_to_edit=False)
        self.advicesToAdd = self.advisableGroups[0]
        self.advicesToEdit = self.advisableGroups[1]
        self.advicesByType = self.context.getAdvicesByType()
        if self.advicesByType or self.advicesToAdd:
            self.tool = api.portal.get_tool('portal_plonemeeting')
            self.cfg = self.tool.getMeetingConfig(self.context)
            self.portal = api.portal.get()
            self.portal_url = self.portal.absolute_url()
            self.userAdviserOrgUids = self.tool.get_orgs_for_user(suffixes=['advisers'])
            self.advice_infos = self.context.getAdviceDataFor(self.context, ordered=True)
            self.every_advice_types = get_vocab_values(self.tool, 'ConfigAdviceTypes')
            if not self.context.adapted().isPrivacyViewable():
                return '<div style="display: inline">&nbsp;-&nbsp;&nbsp;&nbsp;</div>'
        return super(AdvicesIcons, self).__call__()

    def advicesDelayToWarn(self):
        """We will warn if :
           - 'not_given' are in the addable advices;
           - 'hidden_during_redaction' or 'asked_again' are in the editable advices."""

        advicesToWarn = {}

        def _updateAdvicesToWarn(adviceType):
            smaller_delay = 999
            # if we did not found an advice to warn for current user, maybe there is an advice
            # with delay to be given by another group, we show it too
            for org_uid, advice_info in self.advice_infos.items():
                # find smaller delay
                if (advice_info['type'] == adviceType or
                    (adviceType == 'hidden_during_redaction' and
                     advice_info['hidden_during_redaction'] and advice_info['advice_editable']) or
                    (adviceType == 'considered_not_given_hidden_during_redaction' and
                     advice_info['hidden_during_redaction'] and not advice_info['advice_editable'])) and \
                   advice_info['delay'] and \
                   advice_info['delay_infos']['left_delay'] < smaller_delay:
                    if org_uid in self.userAdviserOrgUids:
                        # determinate delay_icon to use
                        advicesToWarn[adviceType] = advice_info, _delay_icon(True, advice_info)
                    # check if we already have a adviceToWarn, if user was adviser
                    # for this group, it is prioritary
                    elif not advicesToWarn.get(adviceType) or \
                            (advicesToWarn.get(adviceType) and not advicesToWarn[adviceType][1] == 0):
                        advicesToWarn[adviceType] = advice_info, _delay_icon(False, advice_info)
                    else:
                        continue
                    smaller_delay = advice_info['delay_infos']['left_delay']

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
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advisableGroups = self.context.getAdvicesGroupsInfosForUser(
            compute_to_add=True, compute_power_advisers=False)
        self.advicesToAdd = self.advisableGroups[0]
        self.advicesToEdit = self.advisableGroups[1]
        self.advicesByType = self.context.getAdvicesByType()
        self.adviceType = adviceType
        self.userAdviserOrgUids = self.tool.get_orgs_for_user(suffixes=['advisers'])
        self.itemReviewState = self.context.query_state()
        org_uid = self.context.getProposingGroup()
        # when on an ItemTemplate, there may be no org_uid
        self.userIsInProposingGroup = org_uid and self.tool.user_is_in_org(org_uid=org_uid) or False
        self.isManager = self.tool.isManager(self.cfg)
        self.isRealManager = self.tool.isManager(realManagers=True)
        # edit proposingGroup comment, only compute if item not decided
        # by default editable by Managers only
        self.userIsProposingGroupCommentEditor = False
        self.userMayEditItem = False
        # when on an ItemTemplate, there may be no org_uid
        if org_uid and self.cfg.getEnableAdviceProposingGroupComment():
            self.userIsProposingGroupCommentEditor = self.isRealManager
            self.userMayEditItem = self.isRealManager
            if not self.context.is_decided(self.cfg, self.itemReviewState):
                self.userIsProposingGroupCommentEditor = self.isManager or \
                    is_proposing_group_editor(org_uid, self.cfg)
                self.userMayEditItem = _checkPermission(ModifyPortalContent, self.context)

    def _initAdviceInfos(self, advice):
        """ """
        self.advice_id = advice['id']
        self.memberIsAdviserForGroup = self.advice_id in self.userAdviserOrgUids
        self.adviceIsInherited = self.context.adviceIsInherited(self.advice_id)
        self.mayEdit = not self.adviceIsInherited and \
            ((self.advicesToEdit and self.advice_id in self.advicesToEdit) or
             (self.isRealManager and not self.adviceType == 'not_given'))
        self.adviceHolder = advice.get('adviceHolder', None) or self.context
        self.adviceHolderIsViewable = self.adviceHolder.isViewable()
        self.obj = advice.get('advice_id', None) and \
            self.adviceHolder.get(advice['advice_id'], None)
        self.show_history = self.obj and self.adviceHolderIsViewable and \
            self.obj.restrictedTraverse('@@contenthistory').show_history()

    def showLinkToInherited(self, adviceHolder):
        """ """
        return bool(self.adviceIsInherited and self.context._appendLinkedItem(
            adviceHolder, self.tool, self.cfg, only_viewable=True))

    def mayRemoveInheritedAdvice(self):
        """To remove an inherited advice, must be :
           - MeetingManager and item is not decided;
           - or adviser for p_advice_id group and current item
             in a itemAdviceEditStates review_state."""
        res = False
        if self.adviceIsInherited:
            if self.tool.isManager(realManagers=True) or \
               (self.tool.isManager(self.cfg) and
                    not self.context.is_decided(self.cfg)):
                res = True
            else:
                if self.cfg.getInheritedAdviceRemoveableByAdviser() and \
                   self.advice_id in self.userAdviserOrgUids and \
                   self.itemReviewState in self.cfg.getItemAdviceStatesForOrg(self.advice_id):
                    res = True
        return res

    def mayDelete(self, advice):
        """ """
        return IContentDeletable(advice).mayDelete()

    def mayView(self):
        """ """
        return self.memberIsAdviserForGroup or \
            self.mayEdit or \
            self.adviceType not in ('hidden_during_redaction',
                                    'considered_not_given_hidden_during_redaction')

    def mayChangeDelay(self):
        """ """
        res = False
        if self.context.adviceIndex[self.advice_id]['delay'] and not self.adviceIsInherited:
            view = self.context.unrestrictedTraverse('@@advice-available-delays')
            view._initAttributes(self.advice_id)
            res = view.listSelectableDelays() or \
                view._mayAccessDelayChangesHistory() or view._mayReinitializeDelay()
        return res

    def delay_icon(self, advice_info):
        """Makes it callable in the template."""
        return _delay_icon(self.memberIsAdviserForGroup, advice_info)

    def state_infos(self, advice):
        return get_state_infos(advice)

    def get_adviser_group_ids(self, advice_id):
        """Return list of Plone groups ids having a role in p_advice_id advice WF."""
        advice_portal_type = self.context._advicePortalTypeForAdviser(advice_id)
        suffixes = ["advisers"]
        # for performance reason, if portal_type is the basic "meetingadvice"
        # we only return the "_advisers" suffixed group
        if advice_portal_type != "meetingadvice":
            local_roles = self.portal.portal_types[advice_portal_type].localroles
            # get every suffixes used by localroles
            suffixes = []
            for review_state, infos in local_roles['advice_group'].items():
                for k, v in infos.items():
                    if k not in suffixes:
                        suffixes.append(k)
        return json.dumps(["{0}_{1}".format(advice_id, suffix) for suffix in suffixes])

    def mayEditProposingGroupComment(self):
        """Proposing group may edit comment if able to edit item (not on an inherited advice).
           Advice comment may be changed by proposingGroup when:
           - member is a group editor (not an observer for example);
           - item is editable or advice is addable/editable."""
        res = False
        if self.cfg.getEnableAdviceProposingGroupComment():
            advice_info = self.context.adviceIndex[self.advice_id]
            if not self.adviceIsInherited:
                if self.userIsProposingGroupCommentEditor and \
                    (self.isRealManager or self.userMayEditItem or
                     (advice_info['advice_addable'] or advice_info['advice_editable'])):
                    res = True
        return res

    def mayViewProposingGroupComment(self):
        """May view comment:
           - Proposing group;
           - Asked advice advisers;
           - (Meeting)Managers."""
        res = False
        if self.cfg.getEnableAdviceProposingGroupComment() or \
           self.context.adviceIndex[self.advice_id]["proposing_group_comment"]:
            # bypass for (Meeting)Managers
            if self.isManager or \
               self.memberIsAdviserForGroup or \
               self.userIsInProposingGroup:
                res = True
        return res


class AdviceInfos(BrowserView):
    """Main infos shared between advice popup and advice view."""

    def __call__(self, advice_uid, displayedReviewState, customMessageInfos):
        """ """
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.advice = self.context.adviceIndex.get(advice_uid)
        self.adviceType = self.advice['type']
        self.adviceHolder = self.advice.get('adviceHolder', None) or self.context
        self.obj = self.adviceHolder.get(self.advice['advice_id']) if \
            self.advice.get('advice_id', None) else None
        self.displayedReviewState = displayedReviewState
        self.customMessageInfos = customMessageInfos
        self.advice_given_by = self.get_advice_given_by()
        if self.obj is not None:
            # show_history
            adviceHolder = self.advice.get('adviceHolder', None) or self.obj
            adviceHolderIsViewable = adviceHolder.isViewable()
            self.show_history = self.obj and adviceHolderIsViewable and \
                self.obj.restrictedTraverse('@@contenthistory').show_history()
        return self.index()

    def adviser_users(self, advice_info):
        """ """
        res = u''
        if advice_info['userids']:
            res = self.context._displayAdviserUsers(
                advice_info['userids'], self.portal_url, self.tool)
        return res

    def get_advice_given_by(self):
        """The advice was given by advice WF transition before "giveAdvice"."""
        given_by = None
        if self.obj and self.obj._get_final_state_id() != 'advice_given':
            # if final_state_id is actually 'advice_given' we can not compute
            # given_by we are only able to know who created the advice
            last_before_give_advice_event = getLastWFAction(
                self.obj,
                transition=self.obj._get_final_transition_id(),
                ignore_previous_event_actions=['backToAdviceInitialState'])
            if last_before_give_advice_event:
                given_by = get_user_fullname(last_before_give_advice_event["actor"])
        return given_by

    def get_user_fullname(self, user_id):
        return get_user_fullname(user_id)


class ChangeAdviceHiddenDuringRedactionView(BrowserView):
    """View that toggle the advice.advice_hide_during_redaction attribute."""

    def __call__(self):
        # user must be able to edit the advice
        if not _checkPermission(ModifyPortalContent, self.context):
            raise Unauthorized
        else:
            # toggle the value
            self.context.advice_hide_during_redaction = not bool(self.context.advice_hide_during_redaction)
            # when advice_hide_during_redaction, it is handled by ObjectModifiedEvent
            notify(ObjectModifiedEvent(
                self.context,
                Attributes(None, 'advice_hide_during_redaction')))
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
            self.context.historize_if_relevant(comment='advice_asked_again_and_historized_comments')
            # now we may change advice_type to 'asked_again'
            self.context.advice_type = 'asked_again'
            # and we may also set 'advice_hide_during_redaction' to the default
            # XXX for now we do not manage MeetingConfig.defaultAdviceHiddenDuringRedaction
            # when advice is "asked_again", see https://support.imio.be/browse/PM-3883
            # value defined in the MeetingConfig
            # tool = api.portal.get_tool('portal_plonemeeting')
            # cfg = tool.getMeetingConfig(self.context)
            # self.context.advice_hide_during_redaction = \
            #     bool(self.context.portal_type in cfg.getDefaultAdviceHiddenDuringRedaction())
            # reinitialize advice delay if relevant
            advice_uid = self.context.advice_group
            if parent.adviceIndex[advice_uid]['delay']:
                _reinit_advice_delay(parent, advice_uid)
        else:
            # we are about to set the advice back to original value
            if not parent.adapted().mayBackToPreviousAdvice(self.context):
                raise Unauthorized
            # get last version_id and fall back to it
            adapter = getAdapter(self.context, IImioHistory, 'advice_given')
            adapter.revert_to_last_event()

        notify(ObjectModifiedEvent(self.context))
        item_state = parent.query_state()
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


class AdviceEventPreviewView(EventPreviewView):
    """ """

    def _update(self, event):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.advice_style = self.cfg.getAdviceStyle()
        # store some advice data
        self.advice_url = self.context.absolute_url()
        self.advice_type = get_event_field_data(event["advice_data"], "advice_type")
        self.advice_comment = get_event_field_data(event["advice_data"], "advice_comment")
        self.advice_observations = get_event_field_data(event["advice_data"], "advice_observations")
        self.event_time = repr(float(event['time']))
        self.userAdviserOrgUids = self.tool.get_orgs_for_user(suffixes=['advisers'])
        self.userOrgUids = self.tool.get_orgs_for_user()

    def __call__(self, event):
        self._update(event)
        return super(AdviceEventPreviewView, self).__call__(event)

    def may_view_historized_data(self):
        """Viewable by:
           - (Meeting)Managers
           - proposingGroup members;
           - advice _advisers group members."""
        return self.tool.isManager(self.cfg) or \
            self.context.advice_group in self.userAdviserOrgUids or \
            self.context.aq_parent.getProposingGroup() in self.userOrgUids


class AdviceGivenHistoryView(BrowserView):
    """ """

    def __call__(self, event_time):
        """ """
        event = get_event_by_time(self.context, 'advice_given', float_event_time=event_time)
        view = self.context.restrictedTraverse('@@history-event-preview')
        view._update(event)
        if not view.may_view_historized_data():
            raise Unauthorized
        self.advice_data = event['advice_data']
        self.item_data = event['item_data']
        return super(AdviceGivenHistoryView, self).__call__()


def _display_asked_again_warning(advice, parent):
    """If advice is "asked_again" and current user is adviser
       for advice_group display a message explaining to change the advice_type."""
    if advice.advice_type == "asked_again":
        advisers_group_id = get_plone_group_id(advice.advice_group, 'advisers')
        if parent.adviceIndex[advice.advice_group]['advice_editable']:
            if advisers_group_id in get_plone_groups_for_user():
                api.portal.show_message(
                    _("warning_advice_asked_again_need_to_change_advice_type"),
                    request=advice.REQUEST, type="warning")


class AdviceView(DefaultView):
    """ """

    def __call__(self):
        """Check if viewable by current user in case smart guy call the right url."""
        self.parent = self.context.aq_inner.aq_parent
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advice_icons_infos = self.parent.unrestrictedTraverse('@@advices-icons-infos')
        advice_type = self.parent._shownAdviceTypeFor(self.parent.adviceIndex[self.context.advice_group])
        self.advice_icons_infos._initAdvicesInfos(advice_type)
        self.advice_icons_infos._initAdviceInfos(self.parent.adviceIndex[self.context.advice_group])
        if not self.advice_icons_infos.mayView():
            raise Unauthorized
        _display_asked_again_warning(self.context, self.parent)
        return super(AdviceView, self).__call__()


class AdviceEdit(DefaultEditForm):
    """
        Edit form redefinition to display message when advice "asked_again".
    """

    def update(self):
        super(AdviceEdit, self).update()
        if not self.actions.executedActions:
            _display_asked_again_warning(self.context, self.context.aq_inner.aq_parent)
        # check if need to auto hide the advice if it is "asked_again"
        if self.context.advice_type == 'asked_again' and \
           self.context.advice_hide_during_redaction is False:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            if self.context.portal_type in cfg.getDefaultAdviceHiddenDuringRedaction():
                api.portal.show_message(_("advice_hide_during_redaction_set_auto_to_true"),
                                        request=self.request)
                self.widgets['advice_hide_during_redaction'].value = ['true']


def advice_uid_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?advice_uid=advice_uid.
    """
    request = getRequest()
    return request.get('advice_id', u'')


class IBaseAdviceInfoSchema(model.Schema):

    directives.mode(advice_uid='hidden')
    advice_uid = schema.TextLine(
        title=_(u"Advice uid"),
        description=_(u""),
        defaultFactory=advice_uid_default,
        required=False)


class BaseAdviceInfoForm(AutoExtensibleForm, form.EditForm):
    """
      Base form make to work also when advice is not given.
    """
    label = _(u"")
    description = u''
    schema = IBaseAdviceInfoSchema
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(
            self.label, domain='PloneMeeting', context=self.request)

    def _advice_infos(self, data, context=None):
        '''Init @@advices-icons-infos and returns it.'''
        context = context or self.context
        # check if may remove inherited advice
        advice_infos = context.unrestrictedTraverse('@@advices-icons-infos')
        # initialize advice_infos
        advice_data = context.getAdviceDataFor(context, data['advice_uid'])
        advice_infos(context._shownAdviceTypeFor(advice_data))
        advice_infos._initAdviceInfos(advice_data)
        return advice_infos
