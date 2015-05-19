# encoding: utf-8
from imio.dashboard.columns import PrettyLinkColumn
from imio.prettylink.interfaces import IPrettyLink


class PMPrettyLinkColumn(PrettyLinkColumn):
    """A column that display the IPrettyLink.getLink column."""

    def renderHeadCell(self):
        """Override rendering of head of the cell to include jQuery
           call to initialize annexes menu."""
        header = '<script type="text/javascript">jQuery(document).ready(initializeMenusAXStartingAt($("#content")));</script>'
        return header.format(super(PMPrettyLinkColumn, self).renderHeadCell())

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        pretty_link = IPrettyLink(obj).getLink()
        # display annexes if item isPrivacyViewable
        annexes = ''
        if obj.adapted().isPrivacyViewable():
            annexes = obj.restrictedTraverse('@@annexes-icons')(relatedTo='item')
        return pretty_link + annexes
