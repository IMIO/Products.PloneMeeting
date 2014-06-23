from AccessControl import Unauthorized
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityManagement import setSecurityManager

from zope.component import getMultiAdapter
from zope.i18n import translate

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from plone.memoize.view import memoize

from imio.actionspanel.utils import APOmnipotentUser


class UnrestrictedMethodsView(BrowserView):
    """
      This class contains every methods behaving as unrestricted.
      These methods were formerly Manager proxy roled python Scripts.
    """
    def getLinkedMeetingTitle(self):
        """
          Return the title of the linked meeting in case current user can not access the meeting.
        """
        meeting = self.context.getMeeting()
        if meeting:
            return meeting.portal_plonemeeting.formatDate(meeting.getDate(), prefixed=True)

    def getLinkedMeetingDate(self):
        """
          Return the date of the linked meeting in case current user can not access the meeting.
        """
        meeting = self.context.getMeeting()
        if meeting:
            return meeting.getDate()

    @memoize
    def findFirstItemNumberForMeeting(self, meeting):
        """
          Return the base number to take into account while computing an item number.
          This is used when given p_meeting firstItemNumber is -1, we need to look in previous
          meetings for a defined firstItemNumber and compute number of items since that...
        """
        # Look for every meetings that take place before the given p_meeting
        # and find a relevant firstItemNumber to base our count on
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        catalog = getToolByName(self, 'portal_catalog')
        # previous meetings
        # we need to make an unrestricted search because previous meetings
        # could be unaccessible to the current user, for example by default a
        # meeting in state 'created' is not viewable by items creators
        brains = catalog.unrestrictedSearchResults(Type=cfg.getMeetingTypeName(),
                                                   getDate={'query': meeting.getDate(),
                                                            'range': 'max'},
                                                   sort_on='getDate',
                                                   sort_order='reverse')
        # while looking for previous meetings, the current meeting is
        # also returned so removes it from the brains
        brains = brains[1:]
        numberOfItemsBefore = 0
        # if we found no defined firstItemNumber on meetings we will loop on, then
        # we went up to the first meeting and his theorical default firstItemNumber is 1
        previousFirstItemNumber = 1
        for brain in brains:
            # as we did an unrestrictedSearchResults in the portal_catalog
            # we need to do a _unrestrictedGetObject to get the object from the brain
            meetingObj = brain._unrestrictedGetObject()
            # either we have a firstItemNumber defined on the meeting
            # or -1, in this last case, we save number of items of the meeting
            # and we continue to the previous meeting
            numberOfItemsBefore += meetingObj.getItemsCount()
            if not meetingObj.getFirstItemNumber() == -1:
                previousFirstItemNumber = meetingObj.getFirstItemNumber()
                break
        # we return a number that would be the given p_meeting firstItemNumber
        return (previousFirstItemNumber + numberOfItemsBefore)


class ItemSign(BrowserView):
    """
      Item is signed after it has been closed and so, user has no more "Modify portal content" permission.
      We use maySignItem to check if the current user can actually sign/unsignItem.
    """
    IMG_TEMPLATE = u'<img class="%s" src="%s" title="%s" name="%s" %s />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def toggle(self, UID):
        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
        if not self.context.adapted().maySignItem(member):
            raise Unauthorized

        # save current SecurityManager to fall back to it after deletion
        oldsm = getSecurityManager()
        # login as an omnipotent user
        newSecurityManager(None, APOmnipotentUser().__of__(self.portal.aq_inner.aq_parent.acl_users))
        uid_catalog = getToolByName(self.context, 'uid_catalog')
        item = uid_catalog(UID=UID)[0].getObject()
        itemIsSigned = not item.getItemIsSigned()
        item.setItemIsSigned(itemIsSigned)
        item.reindexObject(idxs=('getItemIsSigned',))
        setSecurityManager(oldsm)

        # check again if member can signItem now that it has been signed
        # by default, when an item is signed, it can not be unsigned
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

        title = translate(msgid=title_msgid,
                          domain="PloneMeeting",
                          context=self.request)
        portal_state = getMultiAdapter((self.context, self.request), name=u"plone_portal_state")
        portal_url = portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)
        # manage the onclick if the user still may change the value
        # let onclick be managed by the jQuery method if we do not need to change it
        # just redefines it to "" if we really want to specify that we do not want an onclick
        onclick = not maySignItem and 'onclick=""' or ''
        # manage the applied css_class : if the user still may edit the value, use 'itemIsSignedEditable'
        # if he can no more change the value, do not use a css_class
        css_class = maySignItem and 'itemIsSignedEditable' or ''
        html = self.IMG_TEMPLATE % (css_class, src, title, name, onclick)
        return html
