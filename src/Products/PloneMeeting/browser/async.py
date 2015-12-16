# -*- coding: utf-8 -*-

from zope.component import getMultiAdapter
from zope.i18n import translate
from AccessControl import Unauthorized
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.interfaces import IAnnexable


class Discuss(BrowserView):

    IMG_TEMPLATE = u'<img class="toDiscussEditable" src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

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
        member = self.portal_state.member()
        if not member.has_permission('Modify portal content', self.context):
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

        portal_url = self.portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)

        html = self.IMG_TEMPLATE % (src, title, name)
        self.context.at_post_edit_script()
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
            sendMailEnabled = item.sendMailIfRelevant('askDiscussItem', 'MeetingManager', isRole=True)
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
        self.context.at_post_edit_script()
        return self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])


class AnnexToPrint(BrowserView):
    """
      View that switch the annex 'toPrint' attribute using an ajax call.
    """
    IMG_TEMPLATE = u'<img class="annexToPrintEditable" src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def toggle(self):
        if not self.context.adapted().mayChangeToPrint():
            raise Unauthorized

        try:
            annexToPrint = self.context.getToPrint()
            # toggle value
            self.context.setToPrint(not annexToPrint)

            # check that this annex is printable
            # in case last conversion failed, we should not let the user
            # specify that the annex is toPrint
            if IAnnexable(self.context).conversionFailed():
                raise Exception('This annex can not be printed because the conversion to a printable format failed!')

            if annexToPrint:
                filename = 'annexToPrintNo.png'
                name = 'annexToPrintYes'
                title_msgid = 'annex_to_print_no_edit'
            else:
                filename = 'annexToPrintYes.png'
                name = 'annexToPrintNo'
                title_msgid = 'annex_to_print_yes_edit'

            title = translate(title_msgid,
                              domain="PloneMeeting",
                              context=self.request)
            portal_url = self.portal_state.portal_url()
            src = "%s/%s" % (portal_url, filename)
            html = self.IMG_TEMPLATE % (src, title, name)
            self.context.at_post_edit_script()
            return html
        except Exception, exc:
            # set an error status in request.RESPONSE so the ajax call knows
            # that something wrong happened and redirect the page so portalMessages are displayed
            plone_utils = getToolByName(self.context, 'plone_utils')
            plone_utils.addPortalMessage(
                self.context.translate("There was an error while trying to set this annex to printable. "
                                       "The error message was : ${error}. Please contact system administrator.",
                                       mapping={'error': str(exc)},
                                       domain="PloneMeeting"),
                type='error')
            self.request.RESPONSE.status = 500
            return


class TakenOverBy(BrowserView):
    """
      View that switch the item 'takenOverBy' from None to current user and from current user to None.
    """
    IMG_TEMPLATE = u'<span class="takenOverByEditable %s" title="%s" name="%s">\n%s\n</span>'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def toggle(self, takenOverByFrom):
        member = self.portal_state.member()
        if not self.context.adapted().mayTakeOver():
            raise Unauthorized

        memberId = member.getId()

        tool = getToolByName(self.context, 'portal_plonemeeting')
        currentlyTakenOverBy = self.context.getTakenOverBy()
        if currentlyTakenOverBy and \
           not currentlyTakenOverBy == takenOverByFrom and \
           not currentlyTakenOverBy == memberId:
            plone_utils = getToolByName(self.context, 'plone_utils')
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
            if self.request['AUTHENTICATED_USER'].getId() == newlyTakenOverBy:
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
                                      mapping={'fullname': unicode(tool.getUserName(member.getId()),
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
        self.context.reindexObject(idxs=['getTakenOverBy', ])
        return html


class AnnexIsConfidential(BrowserView):
    """
      View that switch the annex 'isConfidential' attribute using an ajax call.
    """
    IMG_TEMPLATE = u'<img class="annexIsConfidentialEditable" src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def toggle(self):
        if not self.context.adapted().mayChangeConfidentiality():
            raise Unauthorized

        isConfidential = self.context.getIsConfidential()
        # toggle value
        self.context.setIsConfidential(not isConfidential)
        # update parent item's annexIndex
        item = self.context.getParentNode()
        IAnnexable(item).updateAnnexIndex()

        if isConfidential:
            filename = 'isConfidentialNo.png'
            name = 'isConfidentialYes'
            title_msgid = 'annex_is_confidential_no_edit'
        else:
            filename = 'isConfidentialYes.png'
            name = 'isConfidentialNo'
            title_msgid = 'annex_is_confidential_yes_edit'

        title = translate(title_msgid,
                          domain="PloneMeeting",
                          context=self.request)
        portal_url = self.portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)
        html = self.IMG_TEMPLATE % (src, title, name)
        self.context.at_post_edit_script()
        return html


class AdviceIsConfidential(BrowserView):
    """
      View that switch an advice 'isConfidential' attribute using an ajax call.
    """
    IMG_TEMPLATE = u'<img src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def toggle(self, UID):
        # check if current user may edit advice confidentiality
        if not self.context.adapted().mayEditAdviceConfidentiality():
            raise Unauthorized

        # get the adviceInfo
        adviceId = UID.split('__')[1]

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
        portal_url = self.portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)
        html = self.IMG_TEMPLATE % (src, title, name)
        self.context.at_post_edit_script()
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
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def toggle(self):
        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
        if not member.has_permission('PloneMeeting: Write budget infos', self.context):
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
        portal_url = self.portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)
        budgetRelatedClass = beforeToggleBudgetRelated and 'notBudgetRelated' or 'budgetRelated'
        html = self.IMG_TEMPLATE % (src, name, img_title, budgetRelatedClass, label)
        # reload the page if current toggle did change adviceIndex
        # indeed, budgetRelated informations often impact automtic advices
        storedAdviceIndex = self.context.adviceIndex
        self.context.at_post_edit_script()
        if not self.context.adviceIndex == storedAdviceIndex:
            # we set a status reponse of 500 so the jQuery calling this
            # will refresh the page
            self.request.RESPONSE.status = 500
            return
        return html
