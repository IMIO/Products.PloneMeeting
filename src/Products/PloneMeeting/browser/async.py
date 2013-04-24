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

    def available(self):
        return False

    def toggle(self):

        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
        if not member.has_permission('Modify portal content', self.context):
            raise Unauthorized

        toDiscuss = not self.context.getToDiscuss()
        self.context.setToDiscuss(toDiscuss)

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

        annexToPrint = self.context.getToPrint()
        # toggle value
        self.context.setToPrint(not annexToPrint)

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
