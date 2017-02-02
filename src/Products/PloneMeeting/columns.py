# encoding: utf-8
from DateTime import DateTime
from zope.i18n import translate

from plone import api

from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.interfaces import IMeeting

from collective.eeafaceted.z3ctable.columns import AbbrColumn
from collective.eeafaceted.z3ctable.columns import BaseColumn
from collective.eeafaceted.z3ctable.columns import BrowserViewCallColumn
from collective.eeafaceted.z3ctable.columns import CheckBoxColumn
from collective.eeafaceted.z3ctable.columns import ColorColumn
from collective.eeafaceted.z3ctable.columns import I18nColumn
from collective.eeafaceted.z3ctable.columns import VocabularyColumn
from imio.annex.columns import ActionsColumn as AnnexActionsColumn
from imio.dashboard.columns import ActionsColumn
from imio.dashboard.columns import PrettyLinkColumn
from imio.prettylink.interfaces import IPrettyLink


class ItemCategoryColumn(VocabularyColumn):
    """A column that display the MeetingItem.category."""
    vocabulary = u'Products.PloneMeeting.vocabularies.categoriesvocabulary'

    def getCSSClasses(self, item):
        """Add a class with category id so we can skin particular categories."""
        css_classes = self.cssClasses
        css_classes['td'] = css_classes['td'] + ' td_cell_{0}'.format(item.getCategory)
        return css_classes


class ItemProposingGroupColumn(VocabularyColumn):
    """A column that display the MeetingItem.proposingGroup."""
    vocabulary = u'Products.PloneMeeting.vocabularies.proposinggroupsvocabulary'


class ItemProposingGroupAcronymColumn(AbbrColumn):
    """A column that display the MeetingItem.proposingGroup acronym."""
    attrName = 'getProposingGroup'
    vocabulary = u'Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary'
    full_vocabulary = u'Products.PloneMeeting.vocabularies.proposinggroupsvocabulary'


class ItemGroupInChargeColumn(VocabularyColumn):
    """A column that display the proposingGroup.groupInCharge
    taking into account meeting date."""
    attrName = 'getGroupInCharge'
    vocabulary = u'Products.PloneMeeting.vocabularies.proposinggroupsvocabulary'


class ItemGroupInChargeAcronymColumn(AbbrColumn):
    """A column that display the proposingGroup.groupInCharge
    acronym taking into account meeting date."""
    attrName = 'getGroupInCharge'
    vocabulary = u'Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary'
    full_vocabulary = u'Products.PloneMeeting.vocabularies.proposinggroupsvocabulary'


class ItemAdvicesColumn(BrowserViewCallColumn):
    """A column that display the MeetingItem advices."""
    view_name = 'advices-icons'


class ItemToDiscussColumn(BrowserViewCallColumn):
    """A column that display the MeetingItem.toDiscuss as an icon."""
    view_name = 'item-to-discuss'
    header_image = 'toDiscussYes.png'


class ItemIsSignedColumn(BrowserViewCallColumn):
    """A column that display the MeetingItem.toDiscuss as an icon."""
    view_name = 'item-is-signed'
    header_image = 'itemIsSignedYes.png'


class ItemPrivacyColumn(I18nColumn):
    """A column that display the translated MeetingItem.privacy."""
    i18n_domain = 'PloneMeeting'


class ItemPollTypeColumn(VocabularyColumn):
    """A column that display the MeetingItem.pollType."""
    vocabulary = u'Products.PloneMeeting.vocabularies.polltypesvocabulary'


class PMPrettyLinkColumn(PrettyLinkColumn):
    """A column that display the IPrettyLink.getLink column."""

    def renderHeadCell(self):
        """Override rendering of head of the cell to include jQuery
           call to initialize annexes menu and to show the 'more/less details' if we are listing items."""

        if not self.header_js:
            # avoid problems while concataining None and unicode
            self.header_js = u''
        self.header_js += u'<script type="text/javascript">jQuery(document).ready' + \
            u'(initializeMenusAXStartingAt($("#content")));initializePMOverlays();' + \
            u'initializeIconifiedCategoryWidget();</script>'

        if self.table.batch and self.table.batch[0].meta_type == 'MeetingItem':
            # change header title to "Purpose"
            self.header = "header_purpose"
            # activate necessary javascripts
            if not self.header_js:
                # avoid problems while concataining None and unicode
                self.header_js = u''
            self.header_js += u'<script type="text/javascript">jQuery(document).ready' + \
                u'(initializeMenusAXStartingAt($("#content")));initializePMOverlays();' + \
                u'initializeIconifiedCategoryWidget();</script>'
            showHideMsg = translate("show_or_hide_details",
                                    domain="PloneMeeting",
                                    context=self.request,
                                    default="Show/hide details")
            header = \
                u'<span class="showHideDetails" onclick="javascript:toggleMeetingDescriptions()">' + \
                u'<img src="{0}/more_less_details.png" title="{1}" /></span>'.format(self.table.portal_url, showHideMsg)
            return super(PMPrettyLinkColumn, self).renderHeadCell() + header
        return super(PMPrettyLinkColumn, self).renderHeadCell()

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        prettyLinker = IPrettyLink(obj)
        prettyLinker.target = '_parent'

        annexes = staticInfos = moreInfos = ''

        tool = api.portal.get_tool('portal_plonemeeting')
        if obj.meta_type == 'MeetingItem':
            cfg = tool.getMeetingConfig(self.context)
            isPrivacyViewable = obj.adapted().isPrivacyViewable()
            prettyLinker.isViewable = isPrivacyViewable
            # display annexes and infos if item and item isPrivacyViewable
            if isPrivacyViewable:
                # display moreInfos about item
                # visible columns are one define for items listings or when the meeting is displayed
                # so check where we are
                if IMeeting.providedBy(self.context):
                    # on the meeting
                    visibleColumns = cfg.getItemsListVisibleColumns()
                else:
                    visibleColumns = cfg.getItemColumns()
                staticInfos = obj.restrictedTraverse('@@item-static-infos')(visibleColumns=visibleColumns)
                moreInfos = obj.restrictedTraverse('@@item-more-infos')(visibleColumns=visibleColumns)

                # display annexes
                annexes += obj.restrictedTraverse('categorized-childs')(portal_type='annex', show_nothing=False)
                if tool.hasAnnexes(obj, portal_type='annexDecision'):
                    decision_term = translate("AnnexesDecisionShort",
                                              domain='PloneMeeting',
                                              context=obj.REQUEST)
                    annexes += u"<span class='discreet'>{0}&nbsp;:&nbsp;</span>".format(decision_term)
                    annexes += obj.restrictedTraverse('categorized-childs')(portal_type='annexDecision')
        elif obj.meta_type == 'Meeting':
            annexes += obj.restrictedTraverse('categorized-childs')(portal_type='annex', show_nothing=False)
        if annexes:
            annexes = u"<div class='dashboard_annexes'>{0}</div>".format(annexes)

        pretty_link = prettyLinker.getLink()
        return pretty_link + staticInfos + moreInfos + annexes


class PMActionsColumn(ActionsColumn):
    """A column displaying available actions of the listed item."""

    def renderCell(self, item):
        # activate arrows while displaying meeting presented items
        if self.context.meta_type == 'Meeting' and not self.context._displayingAvailableItems():
            self.params['showArrows'] = True
            self.params['lastItemUID'] = self.context.getItems(ordered=True, useCatalog=True)[-1].UID
            self.params['totalNbOfItems'] = self.context.numberOfItems()
        else:
            self.params['showArrows'] = False
            self.params['lastItemUID'] = 0
        return super(ActionsColumn, self).renderCell(item)


class ItemLinkedMeetingColumn(BaseColumn):
    """
      Display the formatted date and a link to the linked meeting if any.
    """
    meeting_uid_attr = 'linkedMeetingUID'

    def renderCell(self, item):
        """Display right icon depending on toDiscuss or not."""
        value = self.getValue(item)
        if not value or value == DateTime('1950/01/01'):
            return u'-'
        else:
            catalog = api.portal.get_tool('uid_catalog')
            meeting = catalog(UID=getattr(item, self.meeting_uid_attr))[0].getObject()
            prettyLinker = IPrettyLink(meeting)
            pretty_link = prettyLinker.getLink()
            return pretty_link


class ItemPreferredMeetingColumn(ItemLinkedMeetingColumn):
    """
      Display the formatted date and a link to the preferred meeting if any.
    """
    meeting_uid_attr = 'getPreferredMeeting'


class ItemListTypeColumn(VocabularyColumn, ColorColumn):
    """A column that display the MeetingItem.listType as a color.
       We use a mix of VocabularyColumn and ColorColumn."""
    i18n_domain = "PloneMeeting"
    cssClassPrefix = 'meeting_item'
    vocabulary = u'Products.PloneMeeting.vocabularies.listtypesvocabulary'

    def renderCell(self, item):
        """Display a message."""
        term_value = super(ItemListTypeColumn, self).renderCell(item)
        # display the menu to change listType if current user may edit the meeting
        if _checkPermission(ModifyPortalContent, self.context):
            obj = self._getObject(item)
            renderedChangeListTypeView = obj.restrictedTraverse('@@item-listtype').index()
            return u'<div title="{0}" style="display: inline-block;">{1}</div>'.format(term_value,
                                                                                       renderedChangeListTypeView)
        else:
            return u'<div title="{0}" style="display: inline-block;"></div>'.format(term_value)


class ItemNumberColumn(BrowserViewCallColumn):
    """
      Display the itemNumber column, used on meetings.
    """
    view_name = 'item-number'

    def getCSSClasses(self, item):
        """Apply a particular class on the table row depending on the item's privacy."""
        self.table.sorting_criterion_name = None
        # for TR
        trCSSClasses = []
        trCSSClasses.append('meeting_item_privacy_{0}'.format(item.privacy))
        return {'tr': ' '.join(trCSSClasses),
                'td': 'itemnumber'}


class ItemCheckBoxColumn(CheckBoxColumn):
    """ """

    def renderHeadCell(self):
        """Display the '(un)present every selected items' action depending
           on the faceted we are on, available or presented items."""
        head = super(ItemCheckBoxColumn, self).renderHeadCell()
        if self.context.meta_type == 'Meeting':
            if self.context._displayingAvailableItems():
                    present_msg = translate('present_several_items',
                                            domain='PloneMeeting',
                                            context=self.request)
                    head = u'''<table class="actionspanel-no-style-table nosort">
    <tr><td>{0}</td><td><button onclick="presentSelectedItems('{1}')" title="{2}" class="present_several" type="button">
    <img src="{3}/presentSeveral.png">
    </button></td></tr></table>'''.format(head, self.context.absolute_url(), present_msg, self.table.portal_url)
            else:
                if self.context.adapted().showRemoveSelectedItemsAction():
                    unpresent_msg = translate('remove_several_items',
                                              domain='PloneMeeting',
                                              context=self.request)
                    head = u'''<table class="actionspanel-no-style-table nosort">
    <tr><td>{0}</td><td><button onclick="removeSelectedItems('{1}')" title="{2}" class="remove_several" type="button">
    <img src="{3}/removeSeveral.png">
    </button></td></tr></table>'''.format(head, self.context.absolute_url(), unpresent_msg, self.table.portal_url)
        return head


class PMAnnexActionsColumn(AnnexActionsColumn):
    """ """
    params = AnnexActionsColumn.params.copy()
    params.update({'edit_action_class': 'link-overlay-pm-annex'})
    params.update({'arrowsPortalTypeAware': True})

    def renderCell(self, item):
        # display arrows for annex and/or annexDecision depending on relevant add permissions
        obj = self._getObject(item)
        parent = obj.aq_parent
        if not self._showArrows() or \
           (obj.portal_type == 'annex' and not _checkPermission(AddAnnex, parent)):
            self.params['showArrows'] = False
        elif not self._showArrows() or \
                (obj.portal_type == 'annexDecision' and not _checkPermission(AddAnnexDecision, parent)):
            self.params['showArrows'] = False
        else:
            self.params['showArrows'] = True
        return super(AnnexActionsColumn, self).renderCell(item)
