# -*- coding: utf-8 -*-
#
# File: testViews.py
#
# Copyright (c) 2015 by Imio.be
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

from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase


class testViews(PloneMeetingTestCase):
    '''Tests various views.'''

    def test_pm_ItemTemplates(self):
        '''Test the view showing itemTemplates to select to create an new item.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        # only one itemTemplate available to 'pmCreator1'
        self.assertTrue(len(cfg.getItemTemplates(filtered=True)) == 1)
        self.assertTrue(len(view.templatesTree['children']) == 1)
        # no sub children
        self.assertFalse(view.templatesTree['children'][0]['children'])
        self.assertFalse(view.displayShowHideAllLinks())
        # as pmCreator2, 2 templates available
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        self.assertTrue(len(cfg.getItemTemplates(filtered=True)) == 2)
        self.assertTrue(len(view.templatesTree['children']) == 2)
        # no sub children
        self.assertFalse(view.templatesTree['children'][0]['children'])
        self.assertFalse(view.templatesTree['children'][1]['children'])
        self.assertFalse(view.displayShowHideAllLinks())

        # user may cancel action
        self.request.RESPONSE.setStatus(200)
        self.request.form['form.HTTP_REFERER'] = self.request.RESPONSE.getHeader('location')
        self.request.form['form.buttons.cancel'] = True
        view()
        self.assertEquals(self.request.RESPONSE.status, 302)
        self.assertEquals(self.request.RESPONSE.getHeader('location'),
                          self.request.form.get('form.HTTP_REFERER'))

        # create an item from an itemTemplate
        self.request.RESPONSE.setStatus(200)
        self.request.RESPONSE.setHeader('location', '')
        self.assertEquals(self.request.RESPONSE.status, 200)
        itemTemplate = view.templatesTree['children'][0]['item']
        self.request.form['templateUID'] = itemTemplate.UID
        view()
        # user was redirected to the new created item edit form
        self.assertEquals(self.request.RESPONSE.status, 302)
        self.assertEquals(self.request.RESPONSE.getHeader('location'),
                          '{0}/{1}/edit'.format(pmFolder.absolute_url(),
                                                itemTemplate.getId))
        # one item created in the user pmFolder
        self.assertTrue(len(pmFolder.objectValues('MeetingItem')) == 1)
        self.assertTrue(pmFolder.objectValues('MeetingItem')[0].getId() == itemTemplate.getId)

    def test_pm_ItemTemplatesWithSubFolders(self):
        '''Test when we have subFolders containing item templates in the configuration.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        # one element, and it is an item
        self.assertTrue(len(view.templatesTree['children']) == 1)
        self.assertTrue(view.templatesTree['children'][0]['item'].meta_type == 'MeetingItem')
        self.assertFalse(view.displayShowHideAllLinks())

        # add an itemTemplate in a subFolder
        self.changeUser('siteadmin')
        cfg.itemtemplates.invokeFactory('Folder', id='subfolder', title="Sub folder")
        subFolder = cfg.itemtemplates.subfolder
        self.create('MeetingItemTemplate', folder=subFolder)

        # we have the subfolder and item under it
        self.changeUser('pmCreator1')
        view()
        self.assertTrue(len(view.templatesTree['children']) == 2)
        self.assertTrue(view.templatesTree['children'][0]['item'].meta_type == 'MeetingItem')
        self.assertTrue(view.templatesTree['children'][1]['item'].meta_type == 'ATFolder')
        self.assertTrue(view.templatesTree['children'][1]['children'][0]['item'].meta_type == 'MeetingItem')
        self.assertTrue(view.displayShowHideAllLinks())

        # an empty folder is not shown
        self.changeUser('siteadmin')
        cfg.itemtemplates.invokeFactory('Folder', id='subfolder1', title="Sub folder 1")
        subFolder1 = cfg.itemtemplates.subfolder1
        newItemTemplate = self.create('MeetingItemTemplate', folder=subFolder1)
        # hide it to pmCreator1
        newItemTemplate.setTemplateUsingGroups(('vendors', ))
        newItemTemplate.reindexObject()
        self.changeUser('pmCreator1')
        view()
        self.assertTrue(len(view.templatesTree['children']) == 2)
        # but available to 'pmCreator2'
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        self.assertTrue(len(view.templatesTree['children']) == 4)
        self.assertTrue(view.templatesTree['children'][3]['item'].id == 'subfolder1')

    def test_pm_ItemTemplatesWithSubFoldersContainedInEmptyFolders(self):
        """This test that if a template is in a sub/subFolder and no other template in parent folders,
           it works, so we have something like :
           - itemtemplates/subfolder/subsubfolder/a-template;
           And subfolder Folder does not contains itemtemplate..."""
        cfg = self.meetingConfig
        # add an itemTemplate in a subSubFolder
        self.changeUser('siteadmin')
        cfg.itemtemplates.invokeFactory('Folder', id='subfolder', title="Sub folder")
        subFolder = cfg.itemtemplates.subfolder
        subFolder.invokeFactory('Folder', id='subsubfolder', title="Sub sub folder")
        subSubFolder = subFolder.subsubfolder

        self.create('MeetingItemTemplate', folder=subSubFolder)
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        # we have one isolated itemtemplate and complete path the itemtemplate in subsubfolder
        self.assertEquals(len(view.templatesTree['children']),
                          2)
        self.assertEquals(view.templatesTree['children'][0]['item'].id,
                          'template1')
        self.assertEquals(view.templatesTree['children'][1]['item'].id,
                          'subfolder')
        self.assertEquals(view.templatesTree['children'][1]['children'][0]['item'].id,
                          'subsubfolder')
        self.assertEquals(view.templatesTree['children'][1]['children'][0]['children'][0]['item'].id,
                          'o1')
        self.assertTrue(view.displayShowHideAllLinks())

    def test_pm_JSVariables(self):
        """Test the view producing plonemeeting_javascript_variables.js."""
        self.changeUser('pmCreator1')
        view = self.portal.restrictedTraverse('plonemeeting_javascript_variables.js')
        # calling the view will produce a unicode string containing javascript...
        self.assertTrue(isinstance(view(), unicode))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testViews, prefix='test_pm_'))
    return suite
