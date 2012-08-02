from zope.component import getMultiAdapter

from AccessControl import getSecurityManager, Unauthorized

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView


#IMG_TEMPLATE = u'<img class="itemIsSignedEditable" style="cursor:pointer" src="%s" title="%s" name="%s" />'
IMG_TEMPLATE = u'<img src="%s" title="%s" name="%s" %s />'


class ItemSign(BrowserView):

    def toggle(self, UID):

        uid_catalog = getToolByName(self.context, 'uid_catalog')
        item = uid_catalog(UID=UID)[0].getObject()

        sm = getSecurityManager()
        if sm.checkPermission("Modify portal content", item):

            itemIsSigned = not item.getItemIsSigned()
            item.setItemIsSigned(itemIsSigned)
            item.reindexObject(idxs=('getItemIsSigned',))

            member = getToolByName(self.context, 'portal_membership').getAuthenticatedMember()
            maySignItem = item.maySignItem(member) 
            if itemIsSigned:
                filename = 'itemIsSignedYes.png'
                name = 'itemIsSignedNo'
                if maySignItem:
                    title_msgid = 'item_is_signed_yes_edit'
                else:
                    title_msgid = 'item_is_signed_yes'
            else:
                filename = 'itemIsSignedNo.png'
                name = 'itemIsSignedYes'
                if maySignItem:
                    title_msgid = 'item_is_signed_no_edit'
                else:
                    title_msgid = 'item_is_signed_no'

            title = item.utranslate(title_msgid,
                    domain="PloneMeeting")
            
            portal_state = getMultiAdapter((self.context, self.request),
                name=u"plone_portal_state")
            portal_url = portal_state.portal_url()
            src = "%s/%s" % (portal_url, filename)
            #manage the onclick if the user still may change the value
            onclick = maySignItem and u'class="itemIsSignedEditable" onclick="asyncItemIsSigned(\'%s\', baseUrl=\'%s\')"' % (UID, item.absolute_url()) or ''
            html = IMG_TEMPLATE % (src, title, name, onclick)
            #html = IMG_TEMPLATE % (src, title, name)
            return html
        else:
            raise Unauthorized("You are not allowed to modify items.")
