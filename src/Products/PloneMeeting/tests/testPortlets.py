# -*- coding: utf-8 -*-
#
# File: testPortlets.py
#
# GNU General Public License (GPL)
#

from imio.helpers.cache import cleanRamCacheFor
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletRenderer
from Products.Archetypes.event import ObjectEditedEvent
from Products.PloneMeeting.browser import portlet_plonemeeting
from Products.PloneMeeting.browser import portlet_todo
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


class testPortlets(PloneMeetingTestCase):
    '''Tests the MeetingItem class methods.'''

    def _setup_portlets(self):
        """ """
        self.changeUser('pmCreator1')
        searches_items = self.getMeetingFolder(self.meetingConfig).searches_items
        self.view = self.portal.restrictedTraverse('@@plone')
        self.manager = getUtility(IPortletManager,
                                  name='plone.leftcolumn',
                                  context=self.portal)
        self.portlet_pm_assignment = portlet_plonemeeting.Assignment()
        self.portlet_pm_renderer = getMultiAdapter(
            (searches_items,
             self.request,
             self.view,
             self.manager,
             self.portlet_pm_assignment),
            IPortletRenderer)
        self.portlet_todo_assignment = portlet_todo.Assignment(batch_size=5,
                                                               title_length=100)
        self.portlet_todo_renderer = getMultiAdapter(
            (searches_items,
             self.request,
             self.view,
             self.manager,
             self.portlet_todo_assignment),
            IPortletRenderer)

    def test_pm_PortletPMAvailableTemplates(self):
        '''Test the portlet_plonemeeting itemTemplates icon that is shown if item templates
           are defined in the configuration, no matter current user have item templates or not,
           this way we have something coherent between users, even for users without itemTemplates.'''
        cfg = self.meetingConfig
        # remove every templates and add one restricted to 'developers'
        self.changeUser('siteadmin')
        self._removeConfigObjectsFor(cfg, folders=['recurringitems', 'itemtemplates'])
        itemTemplate = self.create('MeetingItemTemplate')
        itemTemplate.setTemplateUsingGroups(('developers', ))
        itemTemplate.reindexObject(idxs=['templateUsingGroups', ])
        # pmCreator1 is member of 'developers'
        self.changeUser('pmCreator1')
        pmFolder1 = self.getMeetingFolder()
        itemsCategory = pmFolder1.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertTrue(itemsCategory.hasTemplateItems())
        # pmCreator2 is member of 'vendors'
        self.changeUser('pmCreator2')
        pmFolder2 = self.getMeetingFolder()
        itemsCategory = pmFolder2.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        # clean ram.cache even if cache is still correct because the same for every users
        notify(ObjectEditedEvent(cfg))
        self.assertTrue(itemsCategory.hasTemplateItems())
        # no matter actually there are no itemTemplates available for him...
        self.assertFalse(cfg.getItemTemplates(as_brains=True, onlyActive=True, filtered=True))

    def test_pm_PortletPMRestrictCreateItemFromEmptyTemplate(self):
        '''Test that the "Crate item from empty template" may be restricted
           to some groups, this let's make the link "Create empty item" available
           to only some groups.'''
        cfg = self.meetingConfig
        empty_item_template = cfg.itemtemplates.get(ITEM_DEFAULT_TEMPLATE_ID)
        empty_item_template_uid = empty_item_template.UID()
        # by default template is not restricted so available to everybody
        self.changeUser('pmCreator1')
        pmFolder1 = self.getMeetingFolder()
        itemsCategory = pmFolder1.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertEqual(itemsCategory._get_default_item_template_UID(), empty_item_template_uid)
        self.changeUser('pmCreator2')
        pmFolder2 = self.getMeetingFolder()
        itemsCategory = pmFolder2.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertEqual(itemsCategory._get_default_item_template_UID(), empty_item_template_uid)
        # restrict it to developers
        self.changeUser('siteadmin')
        empty_item_template.setTemplateUsingGroups([self.developers_uid])
        empty_item_template.reindexObject(idxs=['templateUsingGroups', ])
        # available for pmCreator1 that is member of developers
        self.changeUser('pmCreator1')
        itemsCategory = pmFolder1.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertEqual(itemsCategory._get_default_item_template_UID(), empty_item_template_uid)
        # not available for pmCreator2 that is not member of developers
        self.changeUser('pmCreator2')
        itemsCategory = pmFolder2.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertIsNone(itemsCategory._get_default_item_template_UID())

    def test_pm_FromPortletTodo(self):
        """While getting searches in portlet_todo, the TAL condition for searches have
           a 'fromPortletTodo=True', it is not the case in the portlet_plonemeeting, this way
           we may know that we are in portlet_todo or portlet_plonemeeting and display
           searches using a different condition."""
        cfg = self.meetingConfig
        self._setup_portlets()
        # by default, no condition, viewable in both portlets
        searches = cfg.searches
        searchAllItems = searches.searches_items.searchallitems
        searchAllItems.tal_condition = ''
        searchAllItemsUID = searchAllItems.UID()
        # select 'searchallitems' in the MeetingConfig.toDoListSearches
        cfg.setToDoListSearches([searchAllItemsUID])

        # viewable in portlet_plonemeeting
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item_url = item.absolute_url()
        cleanRamCacheFor('Products.PloneMeeting.adapters.compute_criteria')
        self.assertTrue(searchAllItemsUID in self.portlet_pm_renderer.render())
        # and viewable in portlet_todo
        self.request.set('load_portlet_todo', True)
        self.assertTrue(searchAllItemsUID in self.portlet_todo_renderer.render())
        self.assertTrue(item_url in self.portlet_todo_renderer.render())

        # set 'python: fromPortletTodo' as condition for a search, it will be displayed
        # in the portlet_todo but not in the portlet_plonemeeting
        searchAllItems.tal_condition = 'python: fromPortletTodo'
        notify(ObjectModifiedEvent(searchAllItems))
        self._setup_portlets()
        # not viewable in portlet_plonemeeting
        self.assertFalse(searchAllItemsUID in self.portlet_pm_renderer.render())
        # but viewable in portlet_todo
        self.assertTrue(searchAllItemsUID in self.portlet_todo_renderer.render())
        self.assertTrue(item_url in self.portlet_todo_renderer.render())

    def test_pm_PortletTodoCaching(self):
        """Results updated when item modified or MeetingConfig changed."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        self._setup_portlets()
        # select 'searchallitems' in the MeetingConfig.toDoListSearches
        searchAllItemsUID = cfg.searches.searches_items.searchallitems.UID()
        cfg.setToDoListSearches([searchAllItemsUID])
        searchAllItemsUID = cfg2.searches.searches_items.searchallitems.UID()
        cfg2.setToDoListSearches([searchAllItemsUID])
        # enable rendering of portlet_todo, updated thru external view
        self.request.set('load_portlet_todo', True)

        # create items, one in each MeetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item_url = item.absolute_url()
        self.setMeetingConfig(cfg2.getId())
        item2 = self.create('MeetingItem')
        item2_url = item2.absolute_url()

        # MeetingConfig1
        self.assertTrue(item_url in self.portlet_todo_renderer.render())
        self.assertTrue(item.query_state() in self.portlet_todo_renderer.render())
        self.proposeItem(item)
        self.assertTrue(item_url in self.portlet_todo_renderer.render())
        self.assertTrue(item.query_state() in self.portlet_todo_renderer.render())

        # MeetingConfig1
        self.portlet_todo_renderer.cfg = cfg2
        self.assertTrue(item2_url in self.portlet_todo_renderer.render())
        self.assertTrue(item2.query_state() in self.portlet_todo_renderer.render())
        self.proposeItem(item2)
        self.assertTrue(item2_url in self.portlet_todo_renderer.render())
        self.assertTrue(item2.query_state() in self.portlet_todo_renderer.render())


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPortlets, prefix='test_pm_'))
    return suite
