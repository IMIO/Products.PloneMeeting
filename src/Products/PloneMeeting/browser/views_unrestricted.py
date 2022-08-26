# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from plone import api
from Products.Five import BrowserView
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from zope.component import getMultiAdapter
from zope.i18n import translate


class ItemUnrestrictedMethodsView(BrowserView):
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
            tool = api.portal.get_tool('portal_plonemeeting')
            return tool.format_date(meeting.date, prefixed=True)

    def getLinkedMeetingDate(self):
        """
          Return the date of the linked meeting in case current user can not access the meeting.
        """
        meeting = self.context.getMeeting()
        if meeting:
            return meeting.date


class MeetingUnrestrictedMethodsView(BrowserView):

    def findFirstItemNumber(self, get_items_additional_catalog_query={}):
        """
          Return the base number to take into account while computing an item number.
          This is used when given p_meeting firstItemNumber is -1, we need to look in previous
          meetings for a defined firstItemNumber and compute number of items since that...
        """
        # Look for every meetings that take place before the given p_meeting
        # and find a relevant firstItemNumber to base our count on
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        catalog = api.portal.get_tool('portal_catalog')
        # previous meetings
        # we need to make an unrestricted search because previous meetings
        # could be unaccessible to the current user, for example by default a
        # meeting in state 'created' is not viewable by items creators
        brains = catalog.unrestrictedSearchResults(portal_type=cfg.getMeetingTypeName(),
                                                   meeting_date={'query': self.context.date,
                                                                 'range': 'max'},
                                                   sort_on='meeting_date',
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
            meeting = brain._unrestrictedGetObject()
            # either we have a firstItemNumber defined on the meeting
            # or -1, in this last case, we save number of items of the meeting
            # and we continue to the previous meeting
            # divide lastItem itemNumber by 100 so we are sure to ignore subnumbers
            # 308 will become 3 or 1400 will become 14
            items = meeting.get_items(
                the_objects=True,
                ordered=True,
                unrestricted=True,
                additional_catalog_query=get_items_additional_catalog_query)
            # compute number of items ignoring items with a subnumber
            lastItemNumber = len([item for item in items if _is_integer(item.getItemNumber())])
            numberOfItemsBefore += lastItemNumber
            if not meeting.first_item_number == -1:
                previousFirstItemNumber = meeting.first_item_number
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
        if not self.context.adapted().maySignItem():
            raise Unauthorized

        # do this as Manager
        with api.env.adopt_roles(['Manager', ]):
            itemIsSigned = not self.context.getItemIsSigned()
            self.context.setItemIsSigned(itemIsSigned)
            notifyModifiedAndReindex(self.context, extra_idxs=['item_is_signed'])

        # check again if member can signItem now that it has been signed
        # by default, when an item is signed, it can not be unsigned
        maySignItem = self.context.adapted().maySignItem()
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
