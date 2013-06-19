from zope.component import getMultiAdapter
from AccessControl import Unauthorized
from Products.Five import BrowserView


class Discuss(BrowserView):

    IMG_TEMPLATE = u'<img class="toDiscussEditable" src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def isAsynchToggleEnabled(self):
        """
          Return True if the asynchronous call is enabled.
          Indeed, in some case, it can be necessary to deactivate to asynchronous call
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
        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
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

        portal_state = getMultiAdapter((self.context, self.request),
                                       name=u"plone_portal_state")
        portal_url = portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)

        html = self.IMG_TEMPLATE % (src, title, name)
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
        return self.context.portal_plonemeeting.gotoReferer()


class AnnexToPrint(BrowserView):
    """
      View that switch the annex 'toPrint' attribute using an ajax call.
    """
    IMG_TEMPLATE = u'<img class="annexToPrintEditable" src="%s" title="%s" name="%s" />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def toggle(self):
        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
        if not member.has_permission('Modify portal content', self.context):
            raise Unauthorized

        try:
            annexToPrint = self.context.getToPrint()
            # toggle value
            self.context.setToPrint(not annexToPrint)

            # check that this annex is printable
            # in case last conversion failed, we should not let the user
            # specify that the annex is toPrint
            if self.context.conversionFailed():
                raise Exception, \
                    'This annex can not be printed because the conversion to a printable format failed!'

            if annexToPrint:
                filename = 'annexToPrintNo.png'
                name = 'annexToPrintYes'
                title_msgid = 'annex_to_print_no_edit'
            else:
                filename = 'annexToPrintYes.png'
                name = 'annexToPrintNo'
                title_msgid = 'annex_to_print_yes_edit'

            title = self.context.utranslate(title_msgid,
                                            domain="PloneMeeting")
            portal_state = getMultiAdapter((self.context, self.request), name=u"plone_portal_state")
            portal_url = portal_state.portal_url()
            src = "%s/%s" % (portal_url, filename)
            html = self.IMG_TEMPLATE % (src, title, name)
            return html
        except Exception, exc:
            # set an error status in request.RESPONSE so the ajax call knows
            # that something wrong happened and redirect the page so portalMessages are displayed
            self.portal.plone_utils.addPortalMessage(
                self.context.translate("There was an error while trying to set this annex to printable. "
                                       "The error message was : ${error}. Please contact system administrator.",
                                       mapping={'error': str(exc)},
                                       domain="PloneMeeting"),
                type='error')
            self.request.RESPONSE.status = 500
            return
