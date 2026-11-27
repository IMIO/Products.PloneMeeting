# -*- coding: utf-8 -*-

from imio.esign.browser.actions import RecreateSessionFormView
from imio.esign.browser.actions import RecreateSessionView
from imio.esign.browser.views import ExternalSessionCreateView
from imio.esign.browser.views import SessionDeleteView
from imio.esign.browser.views import SessionFilesView
from imio.esign.browser.views import SessionsListingView
from imio.esign.utils import get_session_info
from imio.helpers.cache import get_current_user_id
from imio.prettylink.interfaces import IPrettyLink
from plone import api
from Products.PloneMeeting.config import ESIGNWATCHERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.esign.utils import esign_access_groups
from Products.PloneMeeting.esign.utils import may_manage_session
from Products.PloneMeeting.esign.utils import user_is_signer
from zope.i18n import translate


class PMSessionsListingView(SessionsListingView):

    def __init__(self, context, request):
        super(PMSessionsListingView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def available(self):
        if super(PMSessionsListingView, self).available():
            return bool(
                esign_access_groups()) or \
            self.tool.isManager(realManagers=True) or \
            user_is_signer()

    def get_dashboard_link(self, session):
        # if a cfg could not be initialized, we get it from the session first element
        if self.cfg is None:
            session_info = get_session_info(session['id'])
            self.cfg = self.tool.get(session_info['cfg_id'])
        # compute url
        url = ""
        if self.cfg:
            pm_folder = self.tool.getPloneMeetingFolder(self.cfg.getId())
            if 'searches_decisions' in self.request.getURL():
                searches_folder_id = 'searches_decisions'
                collection_uid = self.cfg.get('searches').get('searches_decisions').get(
                    'searchmeetingsinesignsessions').UID()
            else:
                searches_folder_id = 'searches_items'
                collection_uid = self.cfg.get('searches').get('searches_items').get(
                    'searchitemsinesignsessions').UID()
            url = "{pm_folder_url}/{searches_folder_id}#c3=20&b_start=0&c1={collection_uid}" \
                "&esign_session_id={session_id}".format(
                    pm_folder_url=pm_folder.absolute_url(),
                    searches_folder_id=searches_folder_id,
                    collection_uid=collection_uid,
                    session_id=session["id"],
                )
        return url

    def get_sessions(self):
        """Filter sessions by MeetingConfig.
           Only keep sessions user is MeetingManager for."""
        every_sessions = super(PMSessionsListingView, self).get_sessions()
        if self.tool.isManager(realManagers=True):
            return every_sessions
        manager_user_groups = esign_access_groups()
        manager_cfg_ids = [
            group.replace("_%s" % MEETINGMANAGERS_GROUP_SUFFIX, "").replace(
                "_%s" % ESIGNWATCHERS_GROUP_SUFFIX, "")
            for group in manager_user_groups]
        sessions = [session for session in every_sessions
                    if session['cfg_id'] in manager_cfg_ids]
        # check if user is a signer for a session
        userid = get_current_user_id()
        if not sessions and user_is_signer(userid):
            email = api.user.get(userid).getProperty('email')
            sessions = [session for session in every_sessions
                        if email in [signer['email'] for signer in session['signers']]]
        return sessions


class PMSessionFilesView(SessionFilesView):

    def _get_item_static_infos(self, item):
        """Display the item labels and item reference using the @@static-infos view,
           the same way it is displayed in the dashboards.
           Labels are displayed if enabled and item is privacy viewable.
           Item reference is displayed when it is displayed on the item view, it is not
           considered private so we do not check isPrivacyViewable."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        visible_columns = []
        if 'labels' in cfg.getUsedItemAttributes() and item.adapted().isPrivacyViewable():
            visible_columns.append('static_labels')
        if item.adapted().show_item_reference():
            visible_columns.append('static_item_reference')
        if not visible_columns:
            return u""
        return item.restrictedTraverse('@@static-infos')(visibleColumns=visible_columns)

    def get_file_link(self, ctx, obj):
        if ctx.getTagName() == 'MeetingItem':
            pretty_link = ctx.getPrettyLink(
                contentValue=ctx.Title(withItemNumber=True, withMeetingDate=True))
            item_infos = self._get_item_static_infos(ctx)

        elif ctx.getTagName() == 'Meeting':
            item_infos = u""
            pretty_link = ctx.get_pretty_link(
                prefixed=True, short=False, showContentIcon=True)

        child_infos_view = obj.restrictedTraverse('categorized-childs-infos')
        element = ctx.categorized_elements[obj.UID()]
        signed_info = u"&nbsp;<div class='tooltipster-categorized-elements' " \
            u"style='display: inline;'><span class='{0}' title='{1}' /></div>".format(
            child_infos_view.get_css_classses_for('signed', element),
            translate(child_infos_view.get_tag_title_for('signed', element),
                      domain='collective.iconifiedcategory', context=self.request))

        more_infos_link = "&nbsp;<a href='{0}/@@categorized-annexes'>" \
            "<img style='vertical-align: middle;' src='{1}/++resource++collective.iconifiedcategory.images" \
            "/more_infos.png' /> <span>{2}</span></a>".format(
            ctx.absolute_url(),
            api.portal.get().absolute_url(),
            translate(
                "More infos",
                domain="collective.iconifiedcategory",
                context=self.request), )

        descr = self._get_file_link_descr(ctx, obj)

        # static infos are displayed as block, no need for a <br>
        return pretty_link + (item_infos or u"<br>") + u"<span class='file_link_file'>➔ " + \
            IPrettyLink(obj).getLink() + signed_info + more_infos_link + "</span>" + descr


class PMSessionDeleteView(SessionDeleteView):
    """ """

    def may_delete_session(self):
        """Check if the user may delete sessions, see may_manage_session."""
        return may_manage_session(self.request.get("esign_session_id"))


class PMExternalSessionCreateView(ExternalSessionCreateView):
    """ """

    def may_create_external_sessions(self):
        """Check if the user may create external sessions, see may_manage_session."""
        return may_manage_session(self.request.get("session_id"))


class PMRecreateSessionView(RecreateSessionView):
    """ """

    def may_recreate_session(self, state=None):
        if state in self.NON_RECREATABLE_STATES:
            return False
        return may_manage_session(self.request.form.get("esign_session_id"))

    def get_new_session_title(self, old, old_session_id):
        """Replace last part after "Session " by {sign_id} so it can be
           set at creation (in case first element of old session was not kept.
           A session title is like:
           [iA.Délib] - ... - Session 013999900001
        """
        return old["title"][:-12] + "{sign_id}"


class PMRecreateSessionFormView(RecreateSessionFormView):
    """ """

    def may_recreate_session(self, state=None):
        if state in self.NON_RECREATABLE_STATES:
            return False
        return may_manage_session(self.request.form.get("esign_session_id"))
