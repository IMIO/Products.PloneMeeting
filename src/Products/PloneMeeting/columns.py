# encoding: utf-8
from zope.i18n import translate

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.interfaces import IMeeting

from collective.eeafaceted.z3ctable.columns import BaseColumn
from collective.eeafaceted.z3ctable.columns import BrowserViewCallColumn
from collective.eeafaceted.z3ctable.columns import CheckBoxColumn
from imio.dashboard.columns import PrettyLinkColumn
from imio.prettylink.interfaces import IPrettyLink


class PMPrettyLinkColumn(PrettyLinkColumn):
    """A column that display the IPrettyLink.getLink column."""

    def renderHeadCell(self):
        """Override rendering of head of the cell to include jQuery
           call to initialize annexes menu and to show the 'more/less details' if we are listing items."""
        if self.table.batch[0].meta_type == 'MeetingItem':
            # change header title to "Purpose"
            self.header = translate("header_purpose",
                                    domain="collective.eeafaceted.z3ctable",
                                    context=self.request)
            # activate necessary javascripts
            header = u'<script type="text/javascript">jQuery(document).ready(initializeMenusAXStartingAt($("#content")));initializePMOverlays()</script>{0}'
            showHideMsg = translate("show_or_hide_details",
                                    domain="PloneMeeting",
                                    context=self.request,
                                    default="Show/hide details")
            header += u'<span class="showHideDetails" onclick="javascript:toggleMeetingDescriptions()">({0})</span>'.format(showHideMsg)
            return header.format(super(PMPrettyLinkColumn, self).renderHeadCell())
        return super(PMPrettyLinkColumn, self).renderHeadCell()

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        pretty_link = IPrettyLink(obj).getLink()

        annexes = moreInfos = ''

        if obj.meta_type == 'MeetingItem':
            tool = getToolByName(self.context, 'portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            # display annexes if item and item isPrivacyViewable
            annexes = ''
            if obj.adapted().isPrivacyViewable():
                annexes = obj.restrictedTraverse('@@annexes-icons')(relatedTo='item')
                # display moreInfos about item
                # visible columns are one define for items listings or when the meeting is displayed
                # so check where we are
                if IMeeting.providedBy(self.context):
                    # on the meeting
                    visibleColumns = cfg.getItemsListVisibleColumns()
                else:
                    visibleColumns = cfg.getItemColumns()
                moreInfos = obj.restrictedTraverse('@@item-more-infos')(visibleColumns=visibleColumns)
        return pretty_link + annexes + moreInfos


class ItemLinkedMeetingColumn(BaseColumn):
    """
      Display the formatted date and a link to the linked meeting if any.
      This column is used for 'linkedMeetingDate' and 'getPreferredMeetingDate'.
    """

    meeting_uid_attr = 'linkedMeetingUID'

    def renderCell(self, item):
        """Display right icon depending on toDiscuss or not."""
        if not self.getValue(item):
            return u'-'
        else:
            catalog = getToolByName(item, 'portal_catalog')
            tool = getToolByName(item, 'portal_plonemeeting')
            meeting = catalog(UID=getattr(item, self.meeting_uid_attr))[0]
            formattedMeetingDate = tool.formatMeetingDate(meeting, withHour=True)
            return u'<a href="{0}">{1}</a>'.format(meeting.getURL(), formattedMeetingDate)


class ItemNumberColumn(BrowserViewCallColumn):
    """
      Display the itemNumber column, used on meetings.
    """
    def getCSSClasses(self, item):
        """Apply a particular class on the table row depending on the item's privacy."""
        # for TR
        trCSSClasses = []
        trCSSClasses.append('meeting_item_privacy_{0}'.format(item.privacy))
        return {'tr': ' '.join(trCSSClasses)}


class MeetingCheckBoxColumn(CheckBoxColumn):
    """ """

    def renderHeadCell(self):
        """Display the 'unpresent every selected items' action."""
        head = super(MeetingCheckBoxColumn, self).renderHeadCell()
        if self.context.adapted().showRemoveSelectedItemsAction():
            unpresent_msg = translate('remove_several_items',
                                      domain='PloneMeeting',
                                      context=self.request)
            head = u'''<table class="actionspanel-no-style-table nosort"><tr><td>{0}</td><td><button onclick="removeSelectedItems()" title="{1}" class="noborder" type="button">
    <img src="{2}/removeSeveral.png">
</button></td></tr></table>'''.format(head, unpresent_msg, self.table.portal_url)
        return head
