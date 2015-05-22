# encoding: utf-8
import urllib2

from zope.i18n import translate

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.interfaces import IMeeting

from collective.eeafaceted.z3ctable.columns import BaseColumn
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
            # manage link around 'Show/hide details' for listing of items
            # if shown, we render javascript that show/hide it, but if hidden, we render
            # a link that will reload current page of the listing if we activate the details
            tool = getToolByName(self.context, 'portal_plonemeeting')
            showDetails = tool.readCookie('pmShowDescriptions') == 'true' and True or False
            showHideMsg = u'Afficher/cacher les détails'
            if showDetails:
                header += u'<span class="showHideDetails" onclick="javascript:toggleMeetingDescriptions()">({0})</span>'.format(showHideMsg)
            else:
                # we use method imio.actionspanel.views.ActionsPanelView.buildBackURL that build the url we want
                url = urllib2.unquote(self.context.restrictedTraverse('@@actions_panel').buildBackURL())
                header += u'<a class="showHideDetails" onclick="javascript:toggleMeetingDescriptions();" href="{0}">({1})</a>'.format(url, showHideMsg)
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
        return unicode(pretty_link, 'utf-8') + annexes + moreInfos


class ToDiscussColumn(BaseColumn):
    """Display an icon to represent if item is toDiscuss or not."""

    header_image = 'toDiscussYes.png'

    def renderCell(self, item):
        """Display right icon depending on toDiscuss or not."""
        if self.getValue(item):
            return u"<img  title='{0}' src='{1}/toDiscussYes.png' />".format(translate('to_discuss_yes',
                                                                                       domain='PloneMeeting',
                                                                                       context=self.request),
                                                                             self.table.portal_url)
        else:
            return u"<img  title='{0}' src='{1}/toDiscussNo.png' />".format(translate('to_discuss_no',
                                                                                      domain='PloneMeeting',
                                                                                      context=self.request),
                                                                            self.table.portal_url)


class LinkedMeetingColumn(BaseColumn):
    """Display the formatted date and a link to the linked meeting if any."""

    def renderCell(self, item):
        """Display right icon depending on toDiscuss or not."""
        if not item.linkedMeetingDate:
            return u'-'
        else:
            catalog = getToolByName(item, 'portal_catalog')
            tool = getToolByName(item, 'portal_plonemeeting')
            meeting = catalog(UID=item.linkedMeetingUID)[0]
            formattedMeetingDate = tool.formatMeetingDate(meeting, withHour=True)
            return u'<a href="{0}">{1}</a>'.format(meeting.getURL(), formattedMeetingDate)
