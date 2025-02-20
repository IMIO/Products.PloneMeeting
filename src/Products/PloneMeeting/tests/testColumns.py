# -*- coding: utf-8 -*-
#
# File: testAdvices.py
#
# GNU General Public License (GPL)
#

from collective.iconifiedcategory.browser.tabview import CategorizedContent
from collective.iconifiedcategory.config import get_sort_categorized_tab
from collective.iconifiedcategory.config import set_sort_categorized_tab
from collective.iconifiedcategory.utils import get_categorized_elements
from imio.helpers.cache import cleanRamCacheFor
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.columns import ItemLinkedMeetingColumn
from Products.PloneMeeting.columns import PMAnnexActionsColumn
from Products.PloneMeeting.columns import PMPrettyLinkColumn
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.i18n import translate


class testColumns(PloneMeetingTestCase):
    '''Tests various aspects of advices management.
       Advices are enabled for PloneGov Assembly, not for PloneMeeting Assembly.'''

    def test_pm_ItemPrettyLinkColumnWhenNotPrivacyViewable(self):
        """When item is not privacyViewable :
           - no link is rendred, only the title;
           - more infos are not displayed."""
        cfg = self.meetingConfig
        cfg.setRestrictAccessToSecretItems(True)
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=(self._stateMappingFor('itemcreated'), ))
        self.request.cookies['pmShowDescriptions'] = 'true'

        self.changeUser('pmCreator1')
        # create 2 exactly same items, second will be set 'secret'
        publicItem = self.create('MeetingItem',
                                 title='Public item title',
                                 description='Public item description')
        self.addAnnex(publicItem)
        self.addAnnex(publicItem, relatedTo='item_decision')
        publicItem.setPrivacy('public')
        publicItem._update_after_edit()
        publicBrain = self.catalog(UID=publicItem.UID())[0]
        secretItem = self.create('MeetingItem',
                                 title='Secret item title',
                                 description='Secret item description')
        self.addAnnex(secretItem)
        secretItem.setPrivacy('secret')
        secretItem._update_after_edit()
        secretBrain = self.catalog(UID=secretItem.UID())[0]

        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        column = PMPrettyLinkColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        # as a normal user, everything is viewable
        # link to title, more-infos and annexes
        self.assertTrue(publicItem.adapted().isPrivacyViewable())
        self.assertTrue(secretItem.adapted().isPrivacyViewable())
        publicBrainPrettyLinkColumn = column.renderCell(publicBrain)
        secretBrainPrettyLinkColumn = column.renderCell(secretBrain)
        # make sure cache is shared between cell and item view
        self.assertTrue(publicItem.getPrettyLink() in publicBrainPrettyLinkColumn)
        self.assertTrue(secretItem.getPrettyLink() in secretBrainPrettyLinkColumn)
        # link to title
        self.assertTrue("href='{0}'".format(publicBrain.getURL()) in publicBrainPrettyLinkColumn)
        self.assertTrue("href='{0}'".format(secretBrain.getURL()) in secretBrainPrettyLinkColumn)
        # more infos
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        self.assertTrue(' class="pmMoreInfo">' in secretBrainPrettyLinkColumn)
        # annexes
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        self.assertTrue(' class="pmMoreInfo">' in secretBrainPrettyLinkColumn)

        # now as a restricted power observer, secretItem title is only shown (without a link)
        self.changeUser('restrictedpowerobserver1')
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.assertTrue(publicItem.adapted().isPrivacyViewable())
        self.assertFalse(secretItem.adapted().isPrivacyViewable())
        publicBrainPrettyLinkColumn = column.renderCell(publicBrain)
        secretBrainPrettyLinkColumn = column.renderCell(secretBrain)
        # make sure cache is shared between cell and item view
        self.assertTrue(publicItem.getPrettyLink() in publicBrainPrettyLinkColumn)
        self.assertTrue(secretItem.getPrettyLink() in secretBrainPrettyLinkColumn)
        # link to title
        self.assertTrue("href='{0}'".format(publicBrain.getURL()) in publicBrainPrettyLinkColumn)
        # more infos
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        # annexes
        self.assertTrue(' class="pmMoreInfo">' in publicBrainPrettyLinkColumn)
        # the secret item is not accessible
        self.assertEqual(
            secretBrainPrettyLinkColumn,
            u"<div class='pretty_link' title='Secret item title'>"
            u"<span class='pretty_link_icons'>"
            u"<img title='{0}' src='http://nohost/plone/MeetingItem.png' "
            u"style=\"width: 16px; height: 16px;\" /></span>"
            u"<span class='pretty_link_content state-itemcreated'>Secret item title "
            u"<span class='discreet no_access'>(You can not access this element)</span>"
            u"</span></div>".format(self.portal.portal_types[secretItem.portal_type].Title()))

    def test_pm_AnnexActionsColumnShowArrows(self):
        """Arrows are only shown if annex or annexDecision are orderable.
           Only displayed on annexDecisions if only annexDecision addable and no more annex addable."""
        # avoid adding recurring items to created meeting
        self._removeConfigObjectsFor(self.meetingConfig, folders=['recurringitems'])

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision text</p>')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)

        annex1_infos = get_categorized_elements(item, uids=[annex1.UID()])
        annex1_content = CategorizedContent(item, annex1_infos[0])
        annex2_infos = get_categorized_elements(item, uids=[annex2.UID()])
        annex2_content = CategorizedContent(item, annex2_infos[0])

        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        column = PMAnnexActionsColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        renderedColumnAnnex1 = column.renderCell(annex1_content)
        renderedColumnAnnex2 = column.renderCell(annex2_content)
        self.assertTrue(self.hasPermission(AddAnnex, item))
        # sort_categorized_tab must be False to show arrows
        self.assertTrue(get_sort_categorized_tab())
        self.assertFalse('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertFalse('folder_position_typeaware?position=up' in renderedColumnAnnex2)
        set_sort_categorized_tab(False)
        renderedColumnAnnex1 = column.renderCell(annex1_content)
        renderedColumnAnnex2 = column.renderCell(annex2_content)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnAnnex2)

        # now test when both annex and annexDecision may be added
        self.validateItem(item)
        self.assertTrue(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))
        annexDecision1 = self.addAnnex(item, relatedTo='item_decision')
        annexDecision2 = self.addAnnex(item, relatedTo='item_decision')
        annexDecision1_infos = get_categorized_elements(item, uids=[annexDecision1.UID()])
        annexDecision1_content = CategorizedContent(item, annexDecision1_infos[0])
        annexDecision2_infos = get_categorized_elements(item, uids=[annexDecision2.UID()])
        annexDecision2_content = CategorizedContent(item, annexDecision2_infos[0])

        renderedColumnAnnex1 = column.renderCell(annex1_content)
        renderedColumnAnnex2 = column.renderCell(annex2_content)
        renderedColumnDecisionAnnex1 = column.renderCell(annexDecision1_content)
        renderedColumnDecisionAnnex2 = column.renderCell(annexDecision2_content)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnAnnex2)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnDecisionAnnex1)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnDecisionAnnex2)
        # and it works
        item.folder_position_typeaware(position='down', id=annex1.getId())
        item.folder_position_typeaware(position='up', id=annex2.getId())
        item.folder_position_typeaware(position='down', id=annexDecision1.getId())
        item.folder_position_typeaware(position='up', id=annexDecision2.getId())

        # now when only annexDecision are addable
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.closeMeeting(meeting)
        self.assertFalse(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))
        renderedColumnAnnex1 = column.renderCell(annex1_content)
        renderedColumnAnnex2 = column.renderCell(annex2_content)
        renderedColumnDecisionAnnex1 = column.renderCell(annexDecision1_content)
        renderedColumnDecisionAnnex2 = column.renderCell(annexDecision2_content)
        self.assertFalse('folder_position_typeaware?position=down' in renderedColumnAnnex1)
        self.assertFalse('folder_position_typeaware?position=up' in renderedColumnAnnex2)
        self.assertTrue('folder_position_typeaware?position=up' in renderedColumnDecisionAnnex1)
        self.assertTrue('folder_position_typeaware?position=down' in renderedColumnDecisionAnnex2)
        # and it works
        item.folder_position_typeaware(position='up', id=annexDecision1.getId())
        item.folder_position_typeaware(position='down', id=annexDecision2.getId())

    def test_pm_ItemLinkedMeetingColumnWhenMeetingNotViewable(self):
        """Test when link to meeting displayed in the items dashboard."""
        self._setPowerObserverStates(states=('presented', ))
        self._setPowerObserverStates(field_name='meeting_states', states=())
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        self.create('Meeting')
        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        column = ItemLinkedMeetingColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        # item not linked to a meeting
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertEqual(column.renderCell(item_brain), u'-')
        self.presentItem(item)

        # linked and viewable
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertTrue(u"<span class='pretty_link_content state-created'>" in column.renderCell(item_brain))
        # linked but not viewable
        self.changeUser('powerobserver1')
        # column have use_caching=True
        column = ItemLinkedMeetingColumn(meetingFolder, self.portal.REQUEST, faceted_table)
        self.assertTrue(u"<span class='pretty_link_content state-created'>" in column.renderCell(item_brain))

    def test_pm_ItemCategoryColumn(self):
        """Test the column displaying category of MeetingItem."""
        self._enableField('category')
        self._enable_column('getCategory')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        faceted_table.initColumns()
        column = faceted_table.columnByName['getCategory']
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertEqual(column.renderCell(item_brain), u'Development topics')
        self.assertEqual(
            column.getCSSClasses(item_brain),
            {'td': 'td_cell_getCategory td_cell_development',
             'th': 'th_header_getCategory'})
        item.setCategory('')
        item.reindexObject(idxs=['getCategory'])
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertEqual(column.renderCell(item_brain), u'-')
        self.assertEqual(
            column.getCSSClasses(item_brain),
            {'td': 'td_cell_getCategory td_cell_',
             'th': 'th_header_getCategory'})

    def test_pm_MeetingPrettyLinkColumnWithStaticInfos(self):
        """Test the PMPrettyLinkColumn for Meeting, especially when displaying static infos."""
        cfg = self.meetingConfig
        self._enableField('category')
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        faceted_table.initColumns()
        column = faceted_table.columnByName['pretty_link']
        meeting_brain = self.catalog(UID=meeting.UID())[0]
        # header
        faceted_table.batch = []
        self.assertTrue("c0=sortable_title" in column.renderHeadCell())
        self.assertFalse('static-infos' in column.renderCell(meeting_brain))
        # enable static_end_date without enabled in used_attrs
        cfg.setMeetingColumns(('static_end_date', ))
        self.assertFalse('static-infos' in column.renderCell(meeting_brain))
        # now if end_date contains something, it will be displayed
        meeting.end_date = meeting.date
        self.assertTrue('static-infos' in column.renderCell(meeting_brain))

    def test_pm_ReviewStateTitleColumn(self):
        """Will display review_state title by getting the title used
           in the workflow object."""
        cfg = self.meetingConfig
        item_wf = cfg.getItemWorkflow(True)
        self._enable_column('review_state_title')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        faceted_table.initColumns()
        column = faceted_table.columnByName['review_state_title']
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertEqual(column.renderCell(item_brain),
                         translate(safe_unicode(item_wf.states['itemcreated'].title),
                                   domain="plone", context=self.request))
        item_wf.states['itemcreated'].title = 'proposed'
        self.assertEqual(column.renderCell(item_brain), u'Proposed')

    def test_pm_ItemNumberColumn(self):
        """Will display the item number on the meeting_view."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        item = meeting.get_items(ordered=True)[0]
        faceted_table = meeting.restrictedTraverse('faceted-table-view')
        faceted_table.initColumns()
        column = faceted_table.columnByName['getItemNumber']
        item_brain = self.catalog(UID=item.UID())[0]
        # moveable for MeetingManagers
        self.assertTrue(u"\u28ff" in column.renderCell(item_brain))
        self.assertTrue(u"data-item_number='100'" in column.renderCell(item_brain))
        self.assertTrue('onclick="moveItem(baseUrl' in column.renderCell(item_brain))
        # header and CSS
        self.assertEqual(
            column.getCSSClasses(item_brain),
            {'td': 'draggable',
             'th': 'th_header_draggable'})
        self.assertEqual(
            column.renderHeadCell(),
            u'</th><th class="th_header_getItemNumber"><script '
            u'type="text/javascript">initializeMeetingItemsDND();</script> ')

        # simplified for non MeetingManagers
        self.changeUser('pmCreator1')
        faceted_table = meeting.restrictedTraverse('faceted-table-view')
        faceted_table.initColumns()
        column = faceted_table.columnByName['getItemNumber']
        self.assertEqual(column.renderCell(item_brain).strip(),
                         u'<span class="itemnumber">1</span>')
        # header and CSS
        self.assertEqual(
            column.getCSSClasses(item_brain),
            {'td': 'td_cell_getItemNumber', 'th': 'th_header_getItemNumber'})
        # no header to avoid init table DND uselessly
        self.assertEqual(column.renderHeadCell(), u' ')

    def test_pm_CopyGroupsColumn(self):
        """Will display the item copyGroups.
           Also because it uses the PMGroups vocabulary."""
        self._enable_column('copyGroups')
        self.changeUser('pmManager')
        item = self.create('MeetingItem', copyGroups=(self.vendors_reviewers, ))
        meetingFolder = self.getMeetingFolder()
        faceted_table = meetingFolder.restrictedTraverse('faceted-table-view')
        faceted_table.initColumns()
        column = faceted_table.columnByName['copyGroups']
        item_brain = self.catalog(UID=item.UID())[0]
        self.assertEqual(column.renderCell(item_brain), u'Vendors (Reviewers)')
        # value is correct without reindex as we use object stored attr
        item.setCopyGroups((self.developers_reviewers, self.vendors_reviewers, ))
        self.assertEqual(column.renderCell(item_brain), u'Developers (Reviewers), Vendors (Reviewers)')


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testColumns, prefix='test_pm_'))
    return suite
