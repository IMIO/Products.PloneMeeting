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

from os import path
from datetime import datetime
from DateTime import DateTime
from AccessControl import Unauthorized
from Products.Five import zcml
from zope.i18n import translate
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.statusmessages.interfaces import IStatusMessage

from Products import PloneMeeting as products_plonemeeting
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase

SAMPLE_ERROR_MESSAGE = u'This is the error message!'


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

    def test_pm_CreateItemFromTemplate(self):
        '''
          Test the createItemFromTemplate functionnality triggered from the plonemeeting portlet.
        '''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        self.getMeetingFolder()
        folder = getattr(self.portal.Members.pmCreator1.mymeetings, self.meetingConfig.getId())
        itemTemplateView = folder.restrictedTraverse('createitemfromtemplate')
        # the template we will use
        itemTemplates = cfg.getItemTemplates(filtered=True)
        itemTemplate = itemTemplates[0].getObject()
        self.assertTrue(itemTemplate.portal_type == cfg.getItemTypeName(configType='MeetingItemTemplate'))
        itemTemplateUID = itemTemplate.UID()
        # for now, no items in the user folder
        self.assertTrue(not folder.objectIds('MeetingItem'))
        newItem = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        self.assertTrue(newItem.portal_type == cfg.getItemTypeName())
        # the new item is the itemTemplate clone
        self.assertTrue(newItem.Title() == itemTemplate.Title())
        self.assertTrue(newItem.Description() == itemTemplate.Description())
        self.assertTrue(newItem.getDecision() == itemTemplate.getDecision())
        # and it has been created in the user folder
        self.assertTrue(newItem.getId() in folder.objectIds())
        # now check that the user can use a 'secret' item template if no proposing group is selected on it
        self.changeUser('admin')
        itemTemplate.setPrivacy('secret')
        # an itemTemplate can have no proposingGroup, it does validate
        itemTemplate.setProposingGroup('')
        self.failIf(itemTemplate.validate_proposingGroup(''))
        # use this template
        self.changeUser('pmCreator1')
        newItem2 = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        self.assertTrue(newItem2.portal_type == cfg.getItemTypeName())
        # item has been created with a filled proposing group
        # and privacy is still ok
        self.assertTrue(newItem2.getId() in folder.objectIds())
        userGroups = self.tool.getGroupsForUser(suffixes=['creators'])
        self.assertTrue(newItem2.getProposingGroup() == userGroups[0].getId())
        self.assertTrue(newItem2.getPrivacy() == itemTemplate.getPrivacy())

    def test_pm_ItemTemplateDeletedIfFirstEditCancelled(self):
        '''When creating an item from a template, if the user cancel first edition, the item is removed'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        itemTemplates = cfg.getItemTemplates(filtered=True)
        itemTemplate = itemTemplates[0].getObject()
        self.assertTrue(itemTemplate.portal_type == cfg.getItemTypeName(configType='MeetingItemTemplate'))
        itemTemplateUID = itemTemplate.UID()

        # if we cancel edit, the newItem is deleted
        newItem = view.createItemFromTemplate(itemTemplateUID)
        self.assertTrue(newItem._at_creation_flag)
        newItem.restrictedTraverse('@@at_lifecycle_view').cancel_edit()
        self.assertFalse(newItem.getId() in newItem.getParentNode().objectIds())

        # but if item is saved, it is kept
        newItem2 = view.createItemFromTemplate(itemTemplateUID)
        self.assertTrue(newItem._at_creation_flag)
        newItem2.processForm()
        self.assertFalse(newItem2._at_creation_flag)
        self.assertTrue(newItem.getId() in newItem.getParentNode().objectIds())
        # cancel second edition
        newItem2.restrictedTraverse('@@at_lifecycle_view').cancel_edit()
        self.assertTrue(newItem.getId() in newItem.getParentNode().objectIds())

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

    def test_pm_ChangeListTypeView(self):
        '''Test the item-change-listtype view and relevant methods in MeetingItem.'''
        # only MeetingManager may change listType once item is in a meeting
        self.changeUser('pmManager')
        item = self.create('MeetingItem', title='Item title')
        view = item.restrictedTraverse('@@change-item-listtype')
        self.assertFalse(item.adapted().mayChangeListType())
        self.assertRaises(Unauthorized, view, new_value='late')
        self.create('Meeting', date=DateTime())
        self.presentItem(item)
        # now listType may be changed
        self.assertTrue(item.adapted().mayChangeListType())
        # new_value is verified
        self.assertRaises(KeyError, view, new_value='some_wrong_value')
        # right, change listType value
        self.assertEquals(item.getListType(), u'normal')
        self.assertTrue(self.portal.portal_catalog(UID=item.UID(), listType=u'normal'))
        view('late')
        # value changed and item reindexed
        self.assertEquals(item.getListType(), u'late')
        self.assertTrue(self.portal.portal_catalog(UID=item.UID(), listType=u'late'))
        # a specific subscriber is triggered when listType value changed
        # register a subscriber that will actually change item title
        # and set it to 'old_listType - new_listType'
        zcml.load_config('tests/testing-subscribers.zcml', products_plonemeeting)
        self.assertEquals(item.Title(), 'Item title')
        view('normal')
        self.assertEquals(item.Title(), 'late - normal')
        self.assertEquals(item.getListType(), u'normal')
        self.assertTrue(self.portal.portal_catalog(UID=item.UID(), listType=u'normal'))
        # if title is 'late - normal' call to subscriber will raise an error
        # this way, we test that when an error occur in the event, the listType is not changed
        view('late')
        # not changed and a portal_message is added
        self.assertEquals(item.Title(), 'late - normal')
        self.assertEquals(item.getListType(), u'normal')
        self.assertTrue(self.portal.portal_catalog(UID=item.UID(), listType=u'normal'))
        messages = IStatusMessage(self.request).show()
        self.assertEquals(messages[-1].message,
                          SAMPLE_ERROR_MESSAGE)
        # cleanUp zmcl.load_config because it impact other tests
        zcml.cleanUp()

    def test_pm_UpdateDelayAwareAdvices(self):
        '''
          Test that the maintenance task updating delay-aware advices works...
          This is supposed to update delay-aware advices that are still addable/editable.
        '''
        # this view is only available to Managers (protected by 'Manage portal' permission)
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, '@@update-delay-aware-advices')
        # create different items having relevant advices :
        # item1 : no advice
        # item2 : one optional advice, one automatic advice, none delay-aware
        # item3 : one delay-aware advice
        catalog = api.portal.get_tool('portal_catalog')
        self.changeUser('admin')
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'group': 'vendors',
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'group': 'vendors',
              'gives_auto_advice_on': 'here/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '',
              'delay_label': ''}, ])
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        query['meta_type'] = 'MeetingItem'

        self.changeUser('pmManager')
        # no advice
        self.create('MeetingItem')
        # if we use the query, it will return nothing for now...
        self.assertTrue(not catalog(**query))

        # no delay-aware advice
        itemWithNonDelayAwareAdvices = self.create('MeetingItem')
        itemWithNonDelayAwareAdvices.setBudgetRelated(True)
        itemWithNonDelayAwareAdvices.at_post_edit_script()

        # the automatic advice has been added
        self.assertTrue(itemWithNonDelayAwareAdvices.adviceIndex['vendors']['optional'] is False)
        itemWithNonDelayAwareAdvices.setOptionalAdvisers(('developers', ))
        itemWithNonDelayAwareAdvices.at_post_edit_script()
        self.assertTrue(itemWithNonDelayAwareAdvices.adviceIndex['developers']['optional'] is True)

        # one delay-aware advice addable
        itemWithDelayAwareAdvice = self.create('MeetingItem')
        itemWithDelayAwareAdvice.setOptionalAdvisers(('vendors__rowid__unique_id_123', ))
        itemWithDelayAwareAdvice.at_post_edit_script()
        self.proposeItem(itemWithDelayAwareAdvice)
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_addable'])
        # this time the element is returned
        self.assertTrue(len(catalog(**query)) == 1)
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # if item3 is no more giveable, the query will not return it anymore
        self.validateItem(itemWithDelayAwareAdvice)
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(not catalog(**query))
        # back to proposed, add it
        self.backToState(itemWithDelayAwareAdvice, self.WF_STATE_NAME_MAPPINGS['proposed'])
        createContentInContainer(itemWithDelayAwareAdvice,
                                 'meetingadvice',
                                 **{'advice_group': 'vendors',
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_addable'])
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_editable'])
        # an editable item will found by the query
        self.assertTrue(len(catalog(**query)) == 1)
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even once updated, it will still be found
        itemWithDelayAwareAdvice.updateLocalRoles()
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())

        # makes it no more editable
        self.backToState(itemWithDelayAwareAdvice, self.WF_STATE_NAME_MAPPINGS['itemcreated'])
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex['vendors']['advice_editable'])
        self.assertTrue(not catalog(**query))

        # makes it giveable again and timed_out, it should still be found
        self.proposeItem(itemWithDelayAwareAdvice)
        itemWithDelayAwareAdvice.adviceIndex['vendors']['delay_started_on'] = datetime(2016, 1, 1)
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even if a reindexObject occurs in between, still found
        itemWithDelayAwareAdvice.reindexObject()
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # but once updated, it is not found anymore
        itemWithDelayAwareAdvice.updateLocalRoles()
        self.assertTrue(not catalog(**query))

        # try with an not_given timed_out advice as indexAdvisers behaves differently
        # remove meetingadvice, back to not timed_out, updateLocalRoles then proceed
        self.deleteAsManager(itemWithDelayAwareAdvice.meetingadvice.UID())
        itemWithDelayAwareAdvice.adviceIndex['vendors']['delay_started_on'] = datetime.now()
        itemWithDelayAwareAdvice.updateLocalRoles()
        # found for now
        itemWithDelayAwareAdvice.adviceIndex['vendors']['delay_started_on'] = datetime(2016, 1, 1)
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even if a reindexObject occurs in between, still found
        itemWithDelayAwareAdvice.reindexObject()
        self.assertTrue(catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # but once updated, it is not found anymore
        itemWithDelayAwareAdvice.updateLocalRoles()
        self.assertTrue(not catalog(**query))

    def test_pm_UpdateDelayAwareAdvicesUpdateAllAdvices(self):
        """Test the _updateAllAdvices method that update every advices.
           It is used to update every delay aware advices every night."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(('itemcreated', ))
        cfg.setItemAdviceEditStates(('itemcreated', ))
        # create items and ask advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers(('developers', ))
        item1.at_post_edit_script()
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers(('developers', ))
        self.proposeItem(item2)
        self.assertTrue('developers_advisers' in item1.__ac_local_roles__)
        self.assertFalse('developers_advisers' in item2.__ac_local_roles__)

        # change configuration, _updateAllAdvices then check again
        self.changeUser('siteadmin')
        cfg.setItemAdviceStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        cfg.setItemAdviceEditStates((self.WF_STATE_NAME_MAPPINGS['proposed'], ))
        self.portal.restrictedTraverse('@@update-delay-aware-advices')._updateAllAdvices()
        self.assertFalse('developers_advisers' in item1.__ac_local_roles__)
        self.assertTrue('developers_advisers' in item2.__ac_local_roles__)

    def test_pm_SendPodTemplateToMailingList(self):
        """Send a Pod template to a mailing list."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        template = self.meetingConfig.podtemplates.itemTemplate
        # no mailing lists for now
        self.assertIsNone(template.mailing_lists)
        self.failIf(self.tool.getAvailableMailingLists(item, template.UID()))

        # define mailing_lists
        template.mailing_lists = "list1;python:True;user1@test.be\nlist2;python:False;user1@test.be"
        self.assertEquals(self.tool.getAvailableMailingLists(item, template.UID()),
                          ['list1'])

        # call the document-generation view
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        self.request.set('mailinglist_name', 'unknown_mailing_list')
        view = item.restrictedTraverse('@@document-generation')
        # raises Unauthorized if mailing list no available
        self.assertRaises(Unauthorized, view)

        # use correct mailing list, works as expected
        self.request.set('mailinglist_name', 'list1')
        messages = IStatusMessage(self.request).show()
        msg = translate('pt_mailing_sent', domain='PloneMeeting', context=self.request)
        self.assertNotEquals(messages[-1].message, msg)
        view()
        messages = IStatusMessage(self.request).show()
        self.assertEquals(messages[-1].message, msg)

    def test_pm_ItemMoreInfos(self, ):
        '''Test the @@item-more-infos view, especially getItemsListVisibleFields
           that keeps order of fields, because we need to make sure that it respects
           order defined in the MeetingItem schema.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('@@item-more-infos')
        cfg.setItemsListVisibleFields(('MeetingItem.description',
                                       'MeetingItem.motivation',
                                       'MeetingItem.decision'))
        self.assertEquals(view.getItemsListVisibleFields().keys(),
                          ['description', 'motivation', 'decision'])

    def test_pm_PrintXhtml(self):
        '''Test the method that will ease print of XHTML content into Pod templates.'''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setMotivation('<p>The motivation using UTF-8 characters : \xc3\xa8\xc3\xa0.</p>')
        motivation = item.getMotivation()
        item.setDecision('<p>The d\xc3\xa9cision using UTF-8 characters.</p>')
        decision = item.getDecision()
        template = self.meetingConfig.podtemplates.itemTemplate
        # call the document-generation view
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        self.request.set('mailinglist_name', 'unknown_mailing_list')
        view = item.restrictedTraverse('@@document-generation')
        helper = view.get_generation_context_helper()

        # test with one single xhtmlContent
        self.assertEquals(helper.printXhtml(item, decision),
                          item.getDecision())
        # several xhtmlContent
        self.assertEquals(helper.printXhtml(item, [motivation, decision]),
                          motivation + decision)
        # use 'space'
        self.assertEquals(helper.printXhtml(item, [motivation, 'space', decision]),
                          motivation + '<p>&nbsp;</p>' + decision)
        # use 'space' with a fonctionnal usecase
        self.assertEquals(helper.printXhtml(item, [motivation,
                                                   'space',
                                                   '<p>DECIDE :</p>',
                                                   'space',
                                                   decision]),
                          motivation + '<p>&nbsp;</p><p>DECIDE :</p><p>&nbsp;</p>' + decision)

        # use 'space' and change 'separatorValue', insert 2 empty lines
        self.assertEquals(helper.printXhtml(item,
                                            [motivation, 'space', decision],
                                            separatorValue='<p>&nbsp;</p><p>&nbsp;</p>'),
                          motivation + '<p>&nbsp;</p><p>&nbsp;</p>' + decision)
        # use keepWithNext
        # special characters are turned to HTML entities decimal representation
        self.assertEquals(helper.printXhtml(item,
                                            [motivation, 'space', decision],
                                            keepWithNext=True),
                          """<p class="pmParaKeepWithNext">The motivation using UTF-8 characters : &#232;&#224;.</p>
<p class="pmParaKeepWithNext">&#160;</p>
<p class="pmParaKeepWithNext">The d&#233;cision using UTF-8 characters.</p>
""")

        # use image_src_to_paths
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')
        img_id = item.invokeFactory('Image', id='img', title='Image', file=data.read())
        img = getattr(item, img_id)
        img_blob_path = img.getBlobWrapper().blob._p_blob_committed
        text = "<p>Text with image <img src='{0}'/> and more text.".format(img.absolute_url())
        self.assertEquals(helper.printXhtml(item,
                                            [motivation, 'space', decision, 'space', text],
                                            keepWithNext=True).replace('\n', ''),
                          """<p>The motivation using UTF-8 characters : &#232;&#224;.</p>
<p>&#160;</p>
<p class="pmParaKeepWithNext">The d&#233;cision using UTF-8 characters.</p>
<p class="pmParaKeepWithNext">&#160;</p>
<p class="pmParaKeepWithNext">Text with image <img src="{0}"/> and more text.</p>
""".format(img_blob_path).replace('\n', ''))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testViews, prefix='test_pm_'))
    return suite
