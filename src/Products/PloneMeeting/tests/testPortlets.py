# -*- coding: utf-8 -*-
#
# File: testPortlets.py
#
# Copyright (c) 2017 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from imio.helpers.cache import cleanRamCacheFor
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletRenderer
from Products.PloneMeeting.browser import portlet_plonemeeting
from Products.PloneMeeting.browser import portlet_todo
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
        self.assertTrue(itemsCategory.templateItems())
        # pmCreator2 is member of 'vendors'
        self.changeUser('pmCreator2')
        pmFolder2 = self.getMeetingFolder()
        itemsCategory = pmFolder2.restrictedTraverse('@@render_collection_widget_category')
        itemsCategory(widget=None)
        self.assertTrue(itemsCategory.templateItems())
        # no matter actually there are no itemTemplates available for him...
        self.assertFalse(cfg.getItemTemplates(as_brains=True, onlyActive=True, filtered=True))

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
        cleanRamCacheFor('Products.PloneMeeting.adapters.compute_criteria')
        self.assertTrue(searchAllItemsUID in self.portlet_pm_renderer.render())
        # and viewable in portlet_todo
        self.request.set('load_portlet_todo', True)
        self.assertTrue(searchAllItemsUID in self.portlet_todo_renderer.render())

        # set 'python: fromPortletTodo' as condition for a search, it will be displayed
        # in the portlet_todo but not in the portlet_plonemeeting
        searchAllItems.tal_condition = 'python: fromPortletTodo'
        notify(ObjectModifiedEvent(searchAllItems))
        self._setup_portlets()
        # not viewable in portlet_plonemeeting
        self.assertFalse(searchAllItemsUID in self.portlet_pm_renderer.render())
        # but viewable in portlet_todo
        self.assertTrue(searchAllItemsUID in self.portlet_todo_renderer.render())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testPortlets, prefix='test_pm_'))
    return suite
