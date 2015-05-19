# encoding: utf-8
import urllib2

from Products.CMFCore.utils import getToolByName

from imio.dashboard.columns import PrettyLinkColumn
from imio.prettylink.interfaces import IPrettyLink


class PMPrettyLinkColumn(PrettyLinkColumn):
    """A column that display the IPrettyLink.getLink column."""

    def renderHeadCell(self):
        """Override rendering of head of the cell to include jQuery
           call to initialize annexes menu and to show the 'more/less details' if we are listing items."""
        header = u'<script type="text/javascript">jQuery(document).ready(initializeMenusAXStartingAt($("#content")));</script>{0}'
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
            header += u'<a class="showHideDetails" onclick="javascript:toggleMeetingDescriptions(); document.location(this.href);" href="{0}">({1})</a>'.format(url, showHideMsg)
        return header.format(super(PMPrettyLinkColumn, self).renderHeadCell())

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        pretty_link = IPrettyLink(obj).getLink()

        annexes = moreInfos = ''

        if obj.meta_type == 'MeetingItem':
            # display annexes if item and item isPrivacyViewable
            annexes = ''
            if obj.adapted().isPrivacyViewable():
                annexes = obj.restrictedTraverse('@@annexes-icons')(relatedTo='item')
                # display moreInfos about item
                visibleColumns = [col.attrName for col in self.table.columns]
                moreInfos = obj.restrictedTraverse('@@item-more-infos')(visibleColumns=visibleColumns)

        return pretty_link + annexes + moreInfos
