# -*- coding: utf-8 -*-
#
# File: columns.py
#
# GNU General Public License (GPL)
#

from collective.contact.plonegroup.browser.tables import OrgaPrettyLinkWithAdditionalInfosColumn
from collective.eeafaceted.z3ctable.columns import AbbrColumn
from collective.eeafaceted.z3ctable.columns import ActionsColumn
from collective.eeafaceted.z3ctable.columns import BaseColumn
from collective.eeafaceted.z3ctable.columns import BrowserViewCallColumn
from collective.eeafaceted.z3ctable.columns import CheckBoxColumn
from collective.eeafaceted.z3ctable.columns import ColorColumn
from collective.eeafaceted.z3ctable.columns import DateColumn
from collective.eeafaceted.z3ctable.columns import I18nColumn
from collective.eeafaceted.z3ctable.columns import PrettyLinkColumn
from collective.eeafaceted.z3ctable.columns import VocabularyColumn
from imio.annex.columns import ActionsColumn as AnnexActionsColumn
from imio.dashboard.interfaces import IContactsDashboard
from imio.prettylink.interfaces import IPrettyLink
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.utils import displaying_available_items
from zope.i18n import translate


class ItemCategoryColumn(VocabularyColumn):
    """A column that display the MeetingItem.category."""
    vocabulary = u'Products.PloneMeeting.vocabularies.categoriesvocabulary'

    def getCSSClasses(self, item):
        """Add a class with category id so we can skin particular categories."""
        css_classes = self.cssClasses
        css_classes['td'] = css_classes['td'] + ' td_cell_{0}'.format(item.getCategory)
        return css_classes


class MeetingCategoryColumn(ItemCategoryColumn):
    """A column that display the Meeting.category."""
    attrName = 'getCategory'
    vocabulary = u'Products.PloneMeeting.vocabularies.meeting_categories_vocabulary'


class ItemClassifierColumn(VocabularyColumn):
    """A column that display the MeetingItem.classifier."""
    vocabulary = u'Products.PloneMeeting.vocabularies.classifiersvocabulary'


class ItemProposingGroupColumn(VocabularyColumn):
    """A column that display the MeetingItem.proposingGroup."""
    vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary'
    header_help = u'header_getProposingGroup_help'


class ItemProposingGroupAcronymColumn(AbbrColumn):
    """A column that display the MeetingItem.proposingGroup acronym."""
    attrName = 'getProposingGroup'
    vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary'
    full_vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary'
    header_help = u'header_proposing_group_acronym_help'


class ItemGroupsInChargeColumn(VocabularyColumn):
    """A column that display the groupsInCharge."""
    attrName = 'getGroupsInCharge'
    vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary'


class ItemGroupsInChargeAcronymColumn(AbbrColumn):
    """A column that display the groupsInCharge acronym."""
    attrName = 'getGroupsInCharge'
    vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary'
    full_vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary'
    header_help = u"header_groups_in_charge_acronym_help"


class ItemCopyGroupsColumn(VocabularyColumn):
    """A column that display the copyGroups."""
    attrName = 'getAllBothCopyGroups'
    vocabulary = u'Products.PloneMeeting.Groups'
    the_object = True


class ItemAssociatedGroupsColumn(VocabularyColumn):
    """A column that display the associatedGroups."""
    attrName = 'getAssociatedGroups'
    vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary'
    header_help = u"header_getAssociatedGroups_help"


class ItemAssociatedGroupsAcronymColumn(AbbrColumn):
    """A column that display the associatedGroups acronym."""
    attrName = 'getAssociatedGroups'
    vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsacronymsvocabulary'
    full_vocabulary = u'Products.PloneMeeting.vocabularies.everyorganizationsvocabulary'
    header_help = u"header_associated_groups_acronym_help"


class ItemCommitteesColumn(VocabularyColumn):
    """A column that display the MeetingItem.committees."""
    attrName = 'committees_index'
    vocabulary = u'Products.PloneMeeting.vocabularies.selectable_committees_vocabulary'


class ItemCommitteesAcronymColumn(AbbrColumn):
    """A column that display the MeetingItem.committees acronym."""
    attrName = 'committees_index'
    vocabulary = u'Products.PloneMeeting.vocabularies.selectable_committees_acronyms_vocabulary'
    full_vocabulary = u'Products.PloneMeeting.vocabularies.selectable_committees_vocabulary'
    header_help = u"header_committees_index_acronym_help"


class ItemAdvicesColumn(BrowserViewCallColumn):
    """A column that display the MeetingItem advices."""
    view_name = 'advices-icons'
    escape = False


class ItemToDiscussColumn(BrowserViewCallColumn):
    """A column that display the MeetingItem.toDiscuss as an icon."""
    view_name = 'item-to-discuss'
    header_image = 'toDiscussYes.png'
    escape = False


class ItemIsSignedColumn(BrowserViewCallColumn):
    """A column that display the MeetingItem.toDiscuss as an icon."""
    view_name = 'item-is-signed'
    header_image = 'itemIsSignedYes.png'
    escape = False


class ItemPrivacyColumn(I18nColumn):
    """A column that display the translated MeetingItem.privacy."""
    i18n_domain = 'PloneMeeting'
    header_help = u'header_privacy_help'
    escape = False


class ItemPollTypeColumn(VocabularyColumn):
    """A column that display the MeetingItem.pollType."""
    vocabulary = u'Products.PloneMeeting.vocabularies.polltypesvocabulary'
    header_help = u'header_pollType_help'
    escape = False


def render_item_annexes(item, tool, show_nothing=False, check_can_view=False):
    """ """
    annexes = ''
    annexes += item.restrictedTraverse('@@categorized-childs')(
        portal_type='annex', show_nothing=show_nothing, check_can_view=check_can_view)
    decision_annexes = item.restrictedTraverse('@@categorized-childs')(
        portal_type='annexDecision', show_nothing=show_nothing, check_can_view=check_can_view)
    if decision_annexes.strip():
        decision_term = translate("AnnexesDecisionShort",
                                  domain='PloneMeeting',
                                  context=item.REQUEST)
        annexes += u"<span class='discreet'>{0}&nbsp;:&nbsp;</span>".format(decision_term)
        annexes += decision_annexes
    return annexes


class PMPrettyLinkColumn(PrettyLinkColumn):
    """A column that display the IPrettyLink.getLink column."""

    def renderHeadCell(self):
        """Override rendering of head of the cell to include jQuery
           call to initialize annexes menu and to show the 'more/less details' if we are listing items."""

        if not self.header_js:
            # avoid problems while concataining None and unicode
            self.header_js = u''
        # activate necessary javascripts
        self.header_js += u'<script type="text/javascript">initializeDashboard();' + \
            u'initializeIconifiedCategoryWidget();</script>'

        if self.table.batch and self.table.batch[0].meta_type == 'MeetingItem':
            # change header title to "Purpose"
            self.header = "header_purpose"
            showHideMsg = translate("show_or_hide_details",
                                    domain="PloneMeeting",
                                    context=self.request,
                                    default="Show/hide details")
            header = \
                u'<span class="showHideDetails" onclick="javascript:toggleMeetingDescriptions()">' + \
                u'<img src="{0}/more_less_details.png" title="{1}" /></span>'.format(
                    self.table.portal_url, showHideMsg)
            return super(PMPrettyLinkColumn, self).renderHeadCell() + header
        return super(PMPrettyLinkColumn, self).renderHeadCell()

    def renderCell(self, item):
        """ """
        obj = self._getObject(item)
        prettyLinker = IPrettyLink(obj)
        prettyLinker.target = '_parent'
        prettyLinker.showContentIcon = True

        annexes = staticInfos = moreInfos = ''

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if obj.meta_type == 'MeetingItem':
            isPrivacyViewable = obj.adapted().isPrivacyViewable()
            prettyLinker.isViewable = isPrivacyViewable
            # display annexes and infos if item and item isPrivacyViewable
            if isPrivacyViewable:
                # display moreInfos about item
                # visible columns are one define for items listings or when the meeting is displayed
                # so check where we are
                if IMeeting.providedBy(self.context):
                    # on the meeting
                    if displaying_available_items(self.context):
                        visibleColumns = cfg.getAvailableItemsListVisibleColumns()
                    else:
                        visibleColumns = cfg.getItemsListVisibleColumns()
                else:
                    visibleColumns = cfg.getItemColumns()
                staticInfos = obj.restrictedTraverse('@@static-infos')(
                    visibleColumns=visibleColumns)
                if self.showMoreInfos:
                    moreInfos = obj.restrictedTraverse('@@item-more-infos')()

                # display annexes
                annexes = render_item_annexes(obj, tool)
        elif obj.getTagName() == 'Meeting':
            staticInfos = obj.restrictedTraverse('@@static-infos')(
                visibleColumns=cfg.getMeetingColumns())
            # check_can_view=True because permission check is not enough
            annexes += obj.restrictedTraverse('@@categorized-childs')(
                portal_type='annex', check_can_view=True)
            # display number of items in meeting title
            contentValue = "{0} [{1}]".format(
                obj.Title(), obj.number_of_items())
            prettyLinker.contentValue = contentValue

        if annexes:
            annexes = u"<div class='dashboard_annexes'>{0}</div>".format(annexes)

        pretty_link = prettyLinker.getLink()
        return pretty_link + staticInfos + moreInfos + annexes

    @property
    def showMoreInfos(self):
        """ """
        return self.request.cookies.get('pmShowDescriptions', 'false') == 'true' and True or False

    def getCSSClasses(self, item):
        """Apply a particular class on the table row depending on the item's privacy
           if item is displayed in a meeting."""
        css_classes = super(PMPrettyLinkColumn, self).getCSSClasses(item)
        if self.context.getTagName() == 'Meeting':
            # for TR
            trCSSClasses = []
            trCSSClasses.append('meeting_item_privacy_{0}'.format(item.privacy))
            css_classes.update({'tr': ' '.join(trCSSClasses), })
        return css_classes


class PMActionsColumn(ActionsColumn):
    """A column displaying available actions of the listed item."""

    def renderCell(self, item):
        # dashboard displaying contacts
        if IContactsDashboard.providedBy(self.context):
            self.params['showActions'] = False
        return super(ActionsColumn, self).renderCell(item)


class PMAsyncActionsColumn(BaseColumn):
    """A column that displays an icon that will on hover display a tooltipster
       with actions availble to current user."""

    sort_index = -1
    escape = False

    def renderCell(self, item):
        tag = """<div class="async-actions-panel-icon-container">""" \
            """<a href="#" title="Actions" onclick="event.preventDefault();;">""" \
            """<span class="fa async-actions-panel-icon link-action tooltipster-actions-panel" data-base_url="{}" """ \
            """data-showHistory:boolean="1" /></a></div>""".format(item.getURL())
        return tag


class ItemLinkedMeetingColumn(BaseColumn):
    """
      Display the formatted date and a link to the linked meeting if any.
    """
    meeting_uid_attr = 'meeting_uid'
    attrName = 'meeting_date'
    use_caching = True
    escape = False

    def renderCell(self, item):
        """ """
        value = self.getValue(item)
        if self.use_caching:
            res = self._get_cached_result(value)
            if res:
                return res

        if not value or value.year <= 1950:
            res = u'-'
        else:
            catalog = self.table.portal.portal_catalog
            # done unrestricted because can be used to display meeting date
            # in dashboard when current user may not see the meeting
            brains = catalog.unrestrictedSearchResults(
                UID=getattr(item, self.meeting_uid_attr))
            meeting = brains[0]._unrestrictedGetObject()
            res = meeting.get_pretty_link()

        if self.use_caching:
            self._store_cached_result(value, res)
        return res


class ItemPreferredMeetingColumn(ItemLinkedMeetingColumn):
    """
      Display the formatted date and a link to the preferred meeting if any.
    """
    meeting_uid_attr = 'preferred_meeting_uid'
    attrName = 'preferred_meeting_date'
    header_help = u'header_preferred_meeting_date_help'
    escape = False


class ItemListTypeColumn(VocabularyColumn, ColorColumn):
    """A column that display the MeetingItem.listType as a color.
       We use a mix of VocabularyColumn and ColorColumn."""
    i18n_domain = "PloneMeeting"
    cssClassPrefix = 'meeting_item'
    vocabulary = u'Products.PloneMeeting.vocabularies.listtypesvocabulary'
    # VocabularyColumn and ColorColumn manage escape manually
    escape = False

    def renderCell(self, item):
        """Display a message."""
        term_value = super(ItemListTypeColumn, self).renderCell(item)
        # display the menu to change listType if current user may edit the meeting
        if _checkPermission(ModifyPortalContent, self.context):
            obj = self._getObject(item)
            return u'<div title="{0}" class="item_listType_container">' \
                u'<div class="item_listType Editable pmAction tooltipster-item-listtype-change" ' \
                u'data-base_url="{1}"></div></div>'.format(
                    term_value, obj.absolute_url())
        else:
            return u'<div title="{0}" class="item_listType_container"></div>'.format(term_value)


class ItemNumberColumn(BrowserViewCallColumn):
    """
      Display the itemNumber column, used on meetings.
    """
    view_name = 'item-number'
    header_js = u'<script type="text/javascript">initializeMeetingItemsDND();</script>'
    escape = False

    @property
    def cssClasses(self):
        """ """
        cssClasses = super(ItemNumberColumn, self).cssClasses
        if self.may_change_items_order(self.context):
            cssClasses['th'] = 'th_header_draggable'
            cssClasses['td'] = 'draggable'
        return cssClasses

    def may_change_items_order(self, meeting):
        """ """
        _may_change_items_order = getattr(self.table, '_may_change_items_order', None)
        if _may_change_items_order is None:
            self.table._may_change_items_order = meeting.wfConditions().may_change_items_order()
            if not self.table._may_change_items_order:
                # avoid init table DND, would slow browser for nothing
                self.header_js = u''
        return self.table._may_change_items_order

    def renderHeadCell(self):
        """ """
        cell = super(ItemNumberColumn, self).renderHeadCell()
        if self.may_change_items_order(self.context):
            cell = u'</th><th class="th_header_getItemNumber">' + cell
        return cell

    def renderCell(self, item):
        """ """
        may_change_items_order = self.may_change_items_order(self.context)
        self.params = {'may_change_items_order': may_change_items_order}
        cell = super(ItemNumberColumn, self).renderCell(item)
        if may_change_items_order:
            obj = self._getObject(item)
            cell = u"⣿</td><td td_cell_getItemNumber data-item_number='{0}'>".format(
                obj.getItemNumber()) + cell
        return cell


class ItemCheckBoxColumn(CheckBoxColumn):
    """ """

    def show_insert_or_remove_selected_items_action(self):
        '''Return True/False if the 'Remove selected items' or 'Present selected items'
           action must be displayed on the meeting view displaying presented items.'''
        return bool(_checkPermission(ModifyPortalContent, self.context) and
                    not self.context.query_state() in self.context.MEETINGCLOSEDSTATES)

    def renderHeadCell(self):
        """Display the '(un)present every selected items' action depending
           on the faceted we are on, available or presented items."""
        head = super(ItemCheckBoxColumn, self).renderHeadCell()
        if self.context.getTagName() == 'Meeting':
            if self.show_insert_or_remove_selected_items_action():
                if displaying_available_items(self.context):
                    present_msg = translate('present_several_items',
                                            domain='PloneMeeting',
                                            context=self.request)
                    head = u'''<table class="actionspanel-no-style-table nosort">
<tr><td>{0}</td><td><button onclick="presentSelectedItems('{1}')" title="{2}" class="present_several" type="button">
<img src="{3}/presentSeveral.png">
</button></td></tr></table>'''.format(head, self.context.absolute_url(), present_msg, self.table.portal_url)
                else:
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


class ReviewStateTitle(I18nColumn):
    """Translate the review_state title and not the id."""

    def _get_workflow(self, item):
        ''' '''
        if not hasattr(self, '_cached_wf'):
            wfTool = api.portal.get_tool('portal_workflow')
            wf = wfTool.getWorkflowsFor(item.portal_type)[0]
            self._cached_wf = wf
        return self._cached_wf

    def getValue(self, item):
        """ """
        wf = self._get_workflow(item)
        return wf.states.get(item.review_state).title


class PMOrgaPrettyLinkWithAdditionalInfosColumn(OrgaPrettyLinkWithAdditionalInfosColumn):
    """ """

    ai_reloaded_fields = ['position_type']


class ItemMeetingDeadlineDateColumn(DateColumn):
    """ """
    sort_index = -1
    attrName = "meetingDeadlineDate"
    long_format = True
    the_object = True
