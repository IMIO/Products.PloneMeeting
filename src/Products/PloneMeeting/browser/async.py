# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.cache import get_cachekey_volatile
from plone import api
from plone.memoize import ram
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.utils import sendMailIfRelevant
from zope.i18n import translate


class Discuss(BrowserView):

    IMG_TEMPLATE = u'<img class="toDiscussEditable" src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()

    def isAsynchToggleEnabled(self):
        """
          Return True if the asynchronous call is enabled.
          Indeed, in some case, it can be necessary to deactivate the asynchronous call
          so the page is reloaded entirely if some other area are updated after
          having toggled the toDiscuss value.
        """
        return True

    def asynchToggle(self):
        """
          Toggle the MeetingItem.toDiscuss attribute from True to False and False to True
          asynchronously, meaning that the entire page is not fully reloaded but only the
          relevant icon.
        """
        if not _checkPermission(ModifyPortalContent, self.context):
            raise Unauthorized

        toDiscuss = not self.context.getToDiscuss()
        self.context.setToDiscuss(toDiscuss)
        self.context.adapted().onDiscussChanged(toDiscuss)

        if toDiscuss:
            filename = 'toDiscussYes.png'
            name = 'discussNo'
            title_msgid = 'to_discuss_yes_edit'
        else:
            filename = 'toDiscussNo.png'
            name = 'discussYes'
            title_msgid = 'to_discuss_no_edit'

        title = self.context.translate(title_msgid,
                                       domain="PloneMeeting")

        portal_url = self.portal.absolute_url()
        src = "%s/%s" % (portal_url, filename)

        html = self.IMG_TEMPLATE % (src, title, name)
        self.context._update_after_edit()
        return html

    def synchToggle(self, itemUid, discussAction):
        """
          This is a synchronous way of toggling toDiscuss.
          The asynchronous asynchToggle here above will only reload the clicked icon.
          If for some reason it is necessary that the page is fully reloaded,
          like for example to display a portal_message or because something else
          has changed on the page, this is the method to use.
          Here, it manages for example the fact that a reviewer can ask
          an item to be discussed and that will display a portal_message to this user.
        """
        item = self.context.uid_catalog(UID=itemUid)[0].getObject()
        if discussAction == 'ask':
            # I must send a mail to MeetingManagers for notifying them that a reviewer
            # wants to discuss this item.
            sendMailEnabled = sendMailIfRelevant(item, 'askDiscussItem', 'meetingmanagers', isSuffix=True)
            if sendMailEnabled:
                msgId = 'to_discuss_ask_mail_sent'
            else:
                msgId = 'to_discuss_ask_mail_not_sent'
            self.context.plone_utils.addPortalMessage(
                item.translate(msgId, domain='PloneMeeting'))
        elif discussAction == 'toggle':
            # I must toggle the "toDiscuss" switch on the item
            toDiscuss = not item.getToDiscuss()
            item.setToDiscuss(toDiscuss)
            item.adapted().onDiscussChanged(toDiscuss)
        self.context._update_after_edit()
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])


class TakenOverBy(BrowserView):
    """
      View that switch the item 'takenOverBy' from None to current user and from current user to None.
    """
    IMG_TEMPLATE = u'<span class="takenOverByEditable %s" title="%s" name="%s">\n%s\n</span>'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()

    def toggle(self, takenOverByFrom):
        if not self.context.adapted().mayTakeOver():
            raise Unauthorized

        member = api.user.get_current()
        memberId = member.getId()

        tool = api.portal.get_tool('portal_plonemeeting')
        currentlyTakenOverBy = self.context.getTakenOverBy()
        if currentlyTakenOverBy and \
           not currentlyTakenOverBy == takenOverByFrom and \
           not currentlyTakenOverBy == memberId:
            plone_utils = api.portal.get_tool('plone_utils')
            plone_utils.addPortalMessage(
                self.context.translate("The item you tried to take over was already taken "
                                       "over in between by ${fullname}. You can take it over "
                                       "now if you are sure that the other user do not handle it.",
                                       mapping={'fullname': unicode(tool.getUserName(currentlyTakenOverBy),
                                                                    'utf-8')},
                                       domain="PloneMeeting"),
                type='warning')
            self.request.RESPONSE.status = 500
            return

        # toggle value
        if not currentlyTakenOverBy:
            self.context.setTakenOverBy(memberId)
            newlyTakenOverBy = memberId
        else:
            self.context.setTakenOverBy('')
            newlyTakenOverBy = ''

        css_class = 'takenOverByNobody'
        name = 'takenOverByNo'
        title_msgid = 'taken_over_by_no_edit'
        if newlyTakenOverBy:
            if memberId == newlyTakenOverBy:
                css_class = 'takenOverByCurrentUser'
            else:
                css_class = 'takenOverByOtherUser'
            name = 'takenOverByYes'
            title_msgid = 'taken_over_by_yes_edit'

        title = translate(title_msgid,
                          domain="PloneMeeting",
                          context=self.request)

        if newlyTakenOverBy:
            taken_over_by = translate('Taken over by ${fullname}',
                                      mapping={'fullname': unicode(tool.getUserName(memberId),
                                                                   'utf-8')},
                                      domain="PloneMeeting",
                                      default="Taken over by ${fullname}",
                                      context=self.request)
        else:
            taken_over_by = translate('(Nobody)',
                                      domain="PloneMeeting",
                                      default="(Nobody)",
                                      context=self.request)

        html = self.IMG_TEMPLATE % (css_class, title, name, taken_over_by)
        # do not notifyModifiedAndReindex because an item may be taken over
        # when it is decided by members of the proposingGroup
        self.context.reindexObject(idxs=['getTakenOverBy'])
        return html


class AdviceIsConfidential(BrowserView):
    """
      View that switch an advice 'isConfidential' attribute using an ajax call.
    """
    IMG_TEMPLATE = u'<img src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()

    def toggle(self, UID):
        # get the adviceId
        adviceId = UID.split('__')[1]

        # check if current user may edit advice confidentiality
        if not self.context.adapted().mayEditAdviceConfidentiality(adviceId):
            raise Unauthorized

        isConfidential = self.context.adviceIndex[adviceId]['isConfidential']
        # toggle value
        self.context.adviceIndex[adviceId]['isConfidential'] = not isConfidential

        if isConfidential:
            filename = 'isConfidentialNo.png'
            name = 'isConfidentialYes'
            title_msgid = 'advice_is_confidential_no_edit'
        else:
            filename = 'isConfidentialYes.png'
            name = 'isConfidentialNo'
            title_msgid = 'advice_is_confidential_yes_edit'

        title = translate(title_msgid,
                          domain="PloneMeeting",
                          context=self.request)
        portal_url = self.portal.absolute_url()
        src = "%s/%s" % (portal_url, filename)
        html = self.IMG_TEMPLATE % (src, title, name)
        self.context._update_after_edit()
        return html


class BudgetRelated(BrowserView):
    """
      View that switch the item 'budgetRelated' attribute using an ajax call.
    """
    IMG_TEMPLATE = u'<img class="budgetRelatedEditable" src="%s" name="%s" title="%s" />' \
                   u' <span class="discreet %s">%s</span>'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()

    def toggle(self):
        if not _checkPermission(WriteBudgetInfos, self.context):
            raise Unauthorized

        beforeToggleBudgetRelated = self.context.getBudgetRelated()
        # toggle value
        self.context.setBudgetRelated(not beforeToggleBudgetRelated)

        if beforeToggleBudgetRelated:
            filename = 'budgetRelatedNo.png'
            # prefix with 'name' so we can discriminate this label from icon name
            name = 'nameBudgetRelatedYes'
            msgid = 'budget_related_no_edit'
            img_title_msgid = 'budget_related_no_img_title_edit'
        else:
            filename = 'budgetRelatedYes.png'
            name = 'nameBudgetRelatedNo'
            msgid = 'budget_related_yes_edit'
            img_title_msgid = 'budget_related_yes_img_title_edit'

        label = translate(msgid,
                          domain="PloneMeeting",
                          context=self.request)
        img_title = translate(img_title_msgid,
                              domain="PloneMeeting",
                              context=self.request)
        portal_url = self.portal.absolute_url()
        src = "%s/%s" % (portal_url, filename)
        budgetRelatedClass = beforeToggleBudgetRelated and 'notBudgetRelated' or 'budgetRelated'
        html = self.IMG_TEMPLATE % (src, name, img_title, budgetRelatedClass, label)
        # reload the page if current toggle did change adviceIndex
        # indeed, budgetRelated informations often impact automtic advices
        storedAdviceIndex = self.context.adviceIndex
        self.context._update_after_edit()
        if not self.context.adviceIndex == storedAdviceIndex:
            # we set a status reponse of 500 so the jQuery calling this
            # will refresh the page
            self.request.RESPONSE.status = 500
            return
        return html


class AsyncRenderSearchTerm(BrowserView):
    """ """

    def __call___cachekey(method, self):
        '''cachekey method for self.__call__.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        userGroups = tool.get_plone_groups_for_user()
        cfg = tool.getMeetingConfig(self.context)
        cfg_modified = cfg.modified()
        # URL to the annex_type can change if server URL changed
        server_url = self.request.get('SERVER_URL', None)
        # cache until a meeting is modified
        date = get_cachekey_volatile('Products.PloneMeeting.Meeting.modified')
        # return meeting.UID if we are on a meeting or None if not
        # as portlet is highlighting the meeting we are on
        meeting_uid = self.context.meta_type == 'Meeting' and self.context.UID() or None
        collection_uid = self.request.get('collection_uid')
        return (userGroups,
                cfg_modified,
                server_url,
                date,
                meeting_uid,
                collection_uid)

    @ram.cache(__call___cachekey)
    def __call__(self):
        """ """
        self.collection_uid = self.request.get('collection_uid')
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.collection = api.content.find(UID=self.collection_uid)[0].getObject()
        self.brains = self.collection.results(batch=False, brains=True)
        rendered_term = ViewPageTemplateFile("templates/term_searchmeetings.pt")(self)
        return rendered_term


class AsyncLoadLinkedItems(BrowserView):
    """ """

    def __call__(self):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal_url = api.portal.get().absolute_url()
        return self.index()


class AsyncLoadItemAssemblyAndSignatures(BrowserView):
    """ """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()

    def show(self):
        """ """
        return self.meeting is not None

    def vote_counts(self, vote_number=0):
        """Returns an HTML string regarding votes count."""
        res = [u'<span title="{0}">{1}</span>'.format(
            translate('number_of_voters', domain='PloneMeeting', context=self.request),
            len(self.voters))]
        pattern = u'<span class="vote_value_{0}" title="{1}">{2}</span>'
        for usedVoteValue in self.cfg.getUsedVoteValues():
            res.append(pattern.format(
                usedVoteValue,
                translate('vote_value_{0}'.format(usedVoteValue),
                          domain='PloneMeeting',
                          context=self.request),
                self.context.getVoteCount(usedVoteValue, vote_number)))
        votes = u" / ".join(res)
        return votes

    def next_vote_number(self):
        """Return next vote_number."""
        return len(self.itemVotes)

    def __call___cachekey(method, self):
        '''cachekey method for self.__call__.
           Cache is invalidated depending on :
           - current user may edit or not;
           - something is redefined for current item or not.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        cfg_modified = cfg.modified()
        meeting = self.context.getMeeting()
        ordered_contacts = meeting.orderedContacts.items()
        redefined_item_attendees = meeting._get_all_redefined_attendees(only_keys=False)
        item_votes = self.context.getItemVotes(include_vote_number=False)
        context_uid = self.context.UID()
        # if something redefined for context or not
        if context_uid not in str(redefined_item_attendees):
            redefined_item_attendees = []
        may_change_attendees = self.context._mayChangeAttendees()
        return (self.context.UID(),
                cfg_modified,
                ordered_contacts,
                redefined_item_attendees,
                item_votes,
                may_change_attendees)

    @ram.cache(__call___cachekey)
    def __call__(self):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.usedMeetingAttrs = self.cfg.getUsedMeetingAttributes()
        self.meeting = self.context.getMeeting()
        self.showVotes = self.context.showVotes()
        self.voters = self.showVotes and self.context.getItemVoters() or []
        self.itemVotes = self.showVotes and \
            self.context.getItemVotes(include_unexisting=True) or []
        return self.index()


class AsyncLoadMeetingAssemblyAndSignatures(BrowserView):
    """ """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()

    def show(self):
        """ """
        return self.meeting is not None

    def __call___cachekey(method, self):
        '''cachekey method for self.__call__.
           Cache is invalidated depending on :
           - current user may edit or not;
           - something is redefined for current item or not.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        cfg_modified = cfg.modified()
        ordered_contacts = self.context.orderedContacts.items()
        item_votes = self.context.getItemVotes()
        context_uid = self.context.UID()
        return (cfg_modified,
                ordered_contacts,
                item_votes,
                context_uid)

    @ram.cache(__call___cachekey)
    def __call__(self):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.usedAttrs = self.cfg.getUsedMeetingAttributes()
        return self.index()
