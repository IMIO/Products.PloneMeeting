# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_user_fullname
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
from Products.PloneMeeting.config import NOT_ENCODED_VOTE_VALUE
from Products.PloneMeeting.config import NOT_VOTABLE_LINKED_TO_VALUE
from Products.PloneMeeting.config import WriteBudgetInfos
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
        item = uuidToObject(itemUid, unrestricted=True)
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
        return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])


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

        currentlyTakenOverBy = self.context.getTakenOverBy()
        if currentlyTakenOverBy and \
           not currentlyTakenOverBy == takenOverByFrom and \
           not currentlyTakenOverBy == memberId:
            plone_utils = api.portal.get_tool('plone_utils')
            plone_utils.addPortalMessage(
                self.context.translate("The item you tried to take over was already taken "
                                       "over in between by ${fullname}. You can take it over "
                                       "now if you are sure that the other user do not handle it.",
                                       mapping={'fullname': get_user_fullname(currentlyTakenOverBy)},
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
                                      mapping={'fullname': get_user_fullname(memberId)},
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
        return (get_plone_groups_for_user(),
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


class AsyncLoadLinkedItemsInfos(BrowserView):

    def __call__(self, fieldsConfigAttr, currentCfgId):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal_url = api.portal.get().absolute_url()
        # more infos, compute it first to have fields/static fields to show
        more_infos_view = self.context.restrictedTraverse('@@item-more-infos')
        more_infos = more_infos_view(fieldsConfigAttr, currentCfgId)
        # static infos
        static_infos = ''
        visibleColumns = [field for field in more_infos_view.visibleFields
                          if field.startswith('static_')]
        if visibleColumns:
            static_infos = self.context.restrictedTraverse('@@static-infos')(
                visibleColumns=visibleColumns)
        return static_infos + more_infos


class AsyncLoadItemAssemblyAndSignatures(BrowserView):
    """ """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self._cached_vote_is_secret = {}

    def show(self):
        """ """
        return self.meeting is not None

    def get_cached_vote_is_secret(self, vote_number):
        """ """
        if vote_number not in self._cached_vote_is_secret:
            self._cached_vote_is_secret[vote_number] = self.context.get_vote_is_secret(self.meeting, vote_number)
        return self._cached_vote_is_secret[vote_number]

    def vote_counts(self):
        """Returns informations regarding votes count."""
        data = []
        counts = []
        total_count = 0
        for vote_number in range(len(self.item_votes)):
            sub_counts = []
            total_votes = self.context.get_vote_count(self.meeting, 'any_votable', vote_number)
            number_of_votes_msg = translate(
                'number_of_voters', domain='PloneMeeting', context=self.request)
            res = [u'<span title="{0}">{1}</span>'.format(
                number_of_votes_msg,
                total_votes)]
            formated_total_votes = total_votes
            pattern = u'<span class="vote_value_{0}" title="{1}">{2}</span>'

            # specify how much voted for this vote if secret
            vote_is_secret = self.get_cached_vote_is_secret(vote_number)
            if vote_is_secret:
                voted = self.context.get_vote_count(self.meeting, 'any_voted', vote_number)
                formated_total_votes = "{0} / {1}".format(voted, total_votes)
            sub_counts.append((number_of_votes_msg,
                               formated_total_votes,
                               'vote_value_number_of_voters'))

            # compute votes not encoded for first secret vote
            # taking into account linked votes
            if vote_is_secret:
                linked_vote_numbers = _get_linked_item_vote_numbers(
                    self.context, self.meeting, vote_number) or [0]
                if not linked_vote_numbers or vote_number == min(linked_vote_numbers):
                    total_voted = 0
                    for linked_vote_number in linked_vote_numbers:
                        total_voted += self.context.get_vote_count(self.meeting, 'any_voted', linked_vote_number)
                    translated_not_yet_vote_value = translate(
                        'vote_value_not_yet',
                        domain='PloneMeeting',
                        context=self.request)
                    count = total_votes - total_voted
                    res.append(pattern.format(
                        NOT_ENCODED_VOTE_VALUE,
                        translated_not_yet_vote_value,
                        count))
                    sub_counts.append((translated_not_yet_vote_value,
                                       count,
                                       'vote_value_not_yet'))

            used_vote_terms = get_vocab(
                self.context,
                "Products.PloneMeeting.vocabularies.usedvotevaluesvocabulary",
                vote_number=vote_number)
            for term in used_vote_terms._terms:
                count = self.context.get_vote_count(self.meeting, term.token, vote_number)
                res.append(pattern.format(
                    term.token,
                    term.title,
                    count))
                if term.token != NOT_ENCODED_VOTE_VALUE:
                    total_count += count
                sub_counts.append((term.title, count, 'vote_value_' + term.token))
            votes = u" / ".join(res)
            data.append(votes)
            counts.append(sub_counts)
        return data, counts, total_count

    def compute_next_vote_number(self):
        """Return next vote_number."""
        return len(self.item_votes)

    def show_add_vote_linked_to_previous_icon(self, vote_number):
        """Show add linked_to_previous icon only on last element.
           More over, may only add linked_to_previous if :
           - already a linked_to_previous element;
           - not linked_to_previous element does not use forbidden vote_values,
             aka vote_values not in MeetingConfig.firstLinkedVoteUsedVoteValues;
           - vote poll_type was not redefined."""
        res = False
        vote_infos = self.item_votes[vote_number]
        if (vote_infos['vote_number'] + 1 == self.next_vote_number):
            if vote_infos['linked_to_previous']:
                res = True
            elif vote_infos.get('poll_type') == self.context.getPollType():
                # check vote_values not out of MeetingConfig.firstLinkedVoteUsedVoteValues
                if self.get_cached_vote_is_secret(vote_number):
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
        # cache will be invalidated if something changed about attendees on meeting
        meeting = self.context.getMeeting()
        ordered_contacts = meeting.ordered_contacts.items()
        redefined_item_attendees = meeting._get_all_redefined_attendees(only_keys=False)
        show_votes = self.context.show_votes()
        context_uid = self.context.UID()
        item_votes_modified = context_uid in meeting.item_votes and meeting.item_votes[context_uid]._p_mtime
        item_attendees_order = meeting._get_item_attendees_order(context_uid)
        # if something redefined for context or not
        if context_uid not in str(redefined_item_attendees):
            redefined_item_attendees = []
        may_change_attendees = self.context._mayChangeAttendees()
        poll_type = self.context.getPollType()
        cache_date = self.request.get('cache_date', None)
        # when using a cache_date, make sure cache is invalidated
        if cache_date:
            date = invalidate_cachekey_volatile_for(
                'Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields',
                get_again=True)
        else:
            date = get_cachekey_volatile(
                'Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields')
        # when using votesResult, invalidate cache if field content changed
        votesResult = None
        if self.context.attribute_is_used('votesResult'):
            votesResult = self.context.getRawVotesResult(real=True)
        return (date,
                context_uid,
                cfg_modified,
                ordered_contacts,
                redefined_item_attendees,
                item_attendees_order,
                show_votes,
                item_votes_modified,
                may_change_attendees,
                poll_type,
                cache_date,
                votesResult)

    def _update(self):
        """ """
        self.error_msg = self.request.get('attendees_error_msg')
        self.context_uid = self.context.UID()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        # necessary for the @@pm-macros/viewContentField
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.used_item_attrs = self.cfg.getUsedItemAttributes()
        self.member = api.user.get_current()
        self.used_meeting_attrs = self.cfg.getUsedMeetingAttributes()
        self.meeting = self.context.getMeeting()
        self.show_votes = self.context.show_votes()
        if self.show_votes:
            self.voters = self.context.get_item_voters() or []
            self.item_votes = self.context.get_item_votes(
                include_unexisting=True,
                ignored_vote_values=[NOT_VOTABLE_LINKED_TO_VALUE]) or []
            self.voted_voters = self.context.get_voted_voters()
            self.next_vote_number = self.compute_next_vote_number()
            self.displayable_counts, self.counts, self.total_count = self.vote_counts()
        else:
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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        is_manager = tool.isManager(cfg)
        cfg_modified = cfg.modified()
        ordered_contacts = self.context.ordered_contacts.items()
        item_votes = sorted(self.context.get_item_votes().items())
        cache_date = self.request.get('cache_date', None)
        # when using a cache_date, make sure cache is invalidated
        if cache_date:
            date = invalidate_cachekey_volatile_for(
                'Products.PloneMeeting.browser.async.AsyncLoadMeetingAssemblyAndSignatures',
                get_again=True)
        else:
            date = get_cachekey_volatile(
                'Products.PloneMeeting.browser.async.AsyncLoadMeetingAssemblyAndSignatures')
        return (date,
                is_manager,
                cfg_modified,
                ordered_contacts,
                item_votes,
                repr(self.context),
                cache_date)

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
