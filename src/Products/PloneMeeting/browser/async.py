# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.content import get_vocab
from imio.helpers.content import uuidToObject
from plone import api
from plone.memoize import ram
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.browser.itemvotes import _get_linked_item_vote_numbers
from Products.PloneMeeting.browser.meeting import BaseMeetingView
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import WriteBudgetInfos
from Products.PloneMeeting.content.meeting import get_all_used_held_positions
from Products.PloneMeeting.utils import get_current_user_id
from Products.PloneMeeting.utils import reindex_object
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
        self.context._update_after_edit(idxs=['to_discuss'])
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
        self.context._update_after_edit(idxs=['to_discuss'])
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

        memberId = get_current_user_id()

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
        # when it is decided, by members of the proposingGroup
        # and in this case item must not be modified
        # cache will be invalidated because we check for modified and _p_mtime
        reindex_object(self.context, idxs=['getTakenOverBy'], update_metadata=False)
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
        self.context._update_after_edit(idxs=[])
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
        self.context._update_after_edit(idxs=[])
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
        meeting_uid = self.context.__class__.__name__ == 'Meeting' and self.context.UID() or None
        collection_uid = self.request.get('collection_uid')
        return (userGroups,
                cfg_modified,
                server_url,
                date,
                meeting_uid,
                collection_uid)

    @ram.cache(__call___cachekey)
    def AsyncRenderSearchTerm__call__(self):
        """ """
        self.collection_uid = self.request.get('collection_uid')
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.collection = uuidToObject(self.collection_uid, unrestricted=True)
        self.brains = self.collection.results(batch=False, brains=True)
        rendered_term = ViewPageTemplateFile("templates/term_searchmeetings.pt")(self)
        return rendered_term

    # do ram.cache have a different key name
    __call__ = AsyncRenderSearchTerm__call__


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

    def vote_counts(self):
        """Returns informations regarding votes count."""
        data = []
        counts = []
        for vote_number in range(len(self.item_votes)):
            sub_counts = []
            total_votes = self.context.getVoteCount('any_votable', vote_number)
            number_of_votes_msg = translate(
                'number_of_voters', domain='PloneMeeting', context=self.request)
            res = [u'<span title="{0}">{1}</span>'.format(
                number_of_votes_msg,
                total_votes)]
            formated_total_votes = total_votes
            pattern = u'<span class="vote_value_{0}" title="{1}">{2}</span>'

            # specify how much voted for this vote if secret
            if self.votesAreSecret:
                voted = self.context.getVoteCount('any_voted', vote_number)
                formated_total_votes = "{0} / {1}".format(voted, total_votes)
            sub_counts.append((number_of_votes_msg,
                               formated_total_votes,
                               'vote_value_number_of_voters'))

            # compute votes not encoded for first secret vote
            # taking into account linked votes
            if self.votesAreSecret:
                linked_vote_numbers = _get_linked_item_vote_numbers(
                    self.context, self.meeting, vote_number)
                if not linked_vote_numbers or vote_number == min(linked_vote_numbers):
                    total_voted = 0
                    for linked_vote_number in linked_vote_numbers:
                        total_voted += self.context.getVoteCount('any_voted', linked_vote_number)
                    translated_used_vote_value = translate(
                        'vote_value_not_yet',
                        domain='PloneMeeting',
                        context=self.request)
                    count = total_votes - total_voted
                    res.append(pattern.format(
                        "not_yet",
                        translated_used_vote_value,
                        count))
                    sub_counts.append((translated_used_vote_value,
                                       count,
                                       'vote_value_not_yet'))

            used_vote_terms = get_vocab(
                self.context,
                "Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary",
                vote_number=vote_number)
            usedVoteValues = [term.token for term in used_vote_terms._terms]
            for usedVoteValue in usedVoteValues:
                translated_used_vote_value = translate(
                    'vote_value_{0}'.format(usedVoteValue),
                    domain='PloneMeeting',
                    context=self.request)
                count = self.context.getVoteCount(usedVoteValue, vote_number)
                res.append(pattern.format(
                    usedVoteValue,
                    translated_used_vote_value,
                    count))
                sub_counts.append((translated_used_vote_value, count, 'vote_value_' + usedVoteValue))
            votes = u" / ".join(res)
            data.append(votes)
            counts.append(sub_counts)
        return data, counts

    def compute_next_vote_number(self):
        """Return next vote_number."""
        return len(self.item_votes)

    def show_add_vote_linked_to_previous_icon(self, vote_number):
        """Show add linked_to_previous icon only on last element.
           More over, may only add linked_to_previous if :
           - already a linked_to_previous element;
           - not linked_to_previous element does not use forbidden vote_values,
             aka vote_values not in MeetingConfig.firstLinkedVoteUsedVoteValues."""
        res = False
        vote_infos = self.item_votes[vote_number]
        if (vote_infos['vote_number'] + 1 == self.next_vote_number):
            if vote_infos['linked_to_previous']:
                res = True
            else:
                # check vote_values not out of MeetingConfig.firstLinkedVoteUsedVoteValues
                if self.votesAreSecret:
                    vote_values = [vote_value for vote_value, vote_count
                                   in vote_infos['votes'].items()
                                   if vote_count and vote_value in self.cfg.getUsedVoteValues()]
                else:
                    vote_values = [vote_value for vote_value in vote_infos['voters'].values()]
                if not set(vote_values).difference(
                    self.cfg.getUsedVoteValues(
                        used_values_attr='firstLinkedVoteUsedVoteValues',
                        include_not_encoded=True)):
                    res = True
        return res

    def __call___cachekey(method, self):
        '''cachekey method for self.__call__.
           Cache is invalidated depending on :
           - current user may edit or not;
           - something is redefined for current item or not.'''
        # when using raw fields (assembly, absents, signatures, ...)
        # we invalidate if a raw value changed
        date = get_cachekey_volatile(
            'Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        cfg_modified = cfg.modified()
        meeting = self.context.getMeeting()
        ordered_contacts = meeting.ordered_contacts.items()
        redefined_item_attendees = meeting._get_all_redefined_attendees(only_keys=False)
        show_votes = self.context.show_votes()
        item_votes = self.context.get_item_votes(include_vote_number=False)
        context_uid = self.context.UID()
        # if something redefined for context or not
        if context_uid not in str(redefined_item_attendees):
            redefined_item_attendees = []
        may_change_attendees = self.context._mayChangeAttendees()
        poll_type = self.context.getPollType()
        cache_date = self.request.get('cache_date', None)
        return (date,
                context_uid,
                cfg_modified,
                ordered_contacts,
                redefined_item_attendees,
                show_votes,
                item_votes,
                may_change_attendees,
                poll_type,
                cache_date)

    def _update(self):
        """ """
        self.error_msg = self.request.get('attendees_error_msg')
        self.context_uid = self.context.UID()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.usedMeetingAttrs = self.cfg.getUsedMeetingAttributes()
        self.meeting = self.context.getMeeting()
        self.show_votes = self.context.show_votes()
        if self.show_votes:
            self.votesAreSecret = self.context.get_votes_are_secret()
            self.voters = self.context.get_item_voters() or []
            self.item_votes = self.context.get_item_votes(
                include_unexisting=True,
                ignored_vote_values=[NOT_VOTABLE_LINKED_TO_VALUE]) or []
            self.voted_voters = ()
            if not self.votesAreSecret:
                self.voted_voters = self.context.get_voted_voters()
            self.next_vote_number = self.compute_next_vote_number()
            vote_counts = self.vote_counts()
            self.displayable_counts = vote_counts[0]
            self.counts = vote_counts[1]
        else:
            self.votesAreSecret = False
            self.voters = []
            self.item_votes = []
            self.voted_voters = []
            self.next_vote_number = None
            self.counts = None

    @ram.cache(__call___cachekey)
    def AsyncLoadItemAssemblyAndSignatures__call__(self):
        """ """
        self._update()
        return self.index()

    # do ram.cache have a different key name
    __call__ = AsyncLoadItemAssemblyAndSignatures__call__

    def get_all_used_held_positions(self):
        """ """
        return get_all_used_held_positions(self.meeting)


class AsyncLoadMeetingAssemblyAndSignatures(BrowserView, BaseMeetingView):
    """ """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()

    def __call___cachekey(method, self):
        '''cachekey method for self.__call__.
           Cache is invalidated depending on :
           - current user may edit or not;
           - something is redefined for current item or not.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.browser.async.AsyncLoadMeetingAssemblyAndSignatures')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        is_manager = tool.isManager(cfg)
        cfg_modified = cfg.modified()
        ordered_contacts = self.context.ordered_contacts.items()
        item_votes = sorted(self.context.get_item_votes().items())
        cache_date = self.request.get('cache_date', None)
        return (date,
                is_manager,
                cfg_modified,
                ordered_contacts,
                item_votes,
                repr(self.context),
                cache_date)

    def get_all_used_held_positions(self):
        """ """
        return get_all_used_held_positions(self.context)

    def _update(self):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.used_attrs = self.cfg.getUsedMeetingAttributes()
        self.show_voters = self.cfg.getUseVotes()
        self.voters = self.context.get_voters()
        view = self.context.restrictedTraverse('@@view')
        view.update()
        self.meeting_view = view

    @ram.cache(__call___cachekey)
    def AsyncLoadMeetingAssemblyAndSignatures__call__(self):
        """ """
        self._update()
        return self.index()

    # do ram.cache have a different key name
    __call__ = AsyncLoadMeetingAssemblyAndSignatures__call__
