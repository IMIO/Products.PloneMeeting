from zope.component import getMultiAdapter

from AccessControl import getSecurityManager, Unauthorized

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView


IMG_TEMPLATE = u'<img class="toDiscussEditable" src="%s" title="%s" name="%s" />'


class Discuss(BrowserView):

    def available(self):
        return False

    def toggle(self, UID):

        uid_catalog = getToolByName(self.context, 'uid_catalog')
        item = uid_catalog(UID=UID)[0].getObject()
        
        sm = getSecurityManager()
        if sm.checkPermission("Modify portal content", item):

            toDiscuss = not item.getToDiscuss()
            item.setToDiscuss(toDiscuss)

            if toDiscuss:
                filename = 'toDiscussYes.png'
                name = 'discussNo'
                title_msgid = 'to_discuss_yes_edit'
            else:
                filename = 'toDiscussNo.png'
                name = 'discussYes'
                title_msgid = 'to_discuss_no_edit'

            title = item.translate(title_msgid,
                    domain="PloneMeeting")
            
            portal_state = getMultiAdapter((self.context, self.request),
                name=u"plone_portal_state")
            portal_url = portal_state.portal_url()
            src = "%s/%s" % (portal_url, filename)

            html = IMG_TEMPLATE % (src, title, name)
            return html
        else:
            raise Unauthorized("You are not allowed to modify items.")
