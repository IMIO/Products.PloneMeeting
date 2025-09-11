# -*- coding: utf-8 -*-
#
# File: testViews.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_own_organization
from collective.documentgenerator.interfaces import IGenerablePODTemplates
from collective.eeafaceted.dashboard.interfaces import IDashboardGenerablePODTemplates
from datetime import datetime
from ftw.labels.interfaces import ILabeling
from ftw.labels.interfaces import ILabelJar
from imio.helpers.cache import cleanRamCacheFor
from imio.helpers.content import richtextval
from imio.history.utils import getLastWFAction
from imio.zamqp.pm.tests.base import DEFAULT_SCAN_ID
from os import path
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.testing import logout
from plone.dexterity.utils import createContentInContainer
from plone.locking.interfaces import ILockable
from plone.testing.z2 import Browser
from Products import PloneMeeting as products_plonemeeting
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.ActionInformation import Action
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFPlone.utils import safe_unicode
from Products.Five import zcml
from Products.PloneMeeting.browser.views import SEVERAL_SAME_BARCODE_ERROR
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.content.meeting import PLACE_OTHER
from Products.PloneMeeting.etags import ConfigModified
from Products.PloneMeeting.etags import ContextModified
from Products.PloneMeeting.etags import LinkedMeetingModified
from Products.PloneMeeting.etags import ToolModified
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.tests.PloneMeetingTestCase import IMG_BASE64_DATA
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import extract_recipients
from Products.PloneMeeting.utils import get_advice_alive_states
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_dx_widget
from Products.PloneMeeting.utils import getAvailableMailingLists
from Products.PloneMeeting.utils import set_field_from_ajax
from Products.statusmessages.interfaces import IStatusMessage
from z3c.form.interfaces import DISPLAY_MODE
from z3c.form.interfaces import INPUT_MODE
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.event import notify
from zope.i18n import translate

import magic
import transaction


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
        # only 2 itemTemplates available to 'pmCreator1'
        self.assertEqual(len(cfg.getItemTemplates(filtered=True)), 2)
        templatesTree = view._getTemplatesTree()
        self.assertEqual(len(templatesTree['children']), 2)
        # no sub children
        self.assertFalse(templatesTree['children'][0]['children'])
        self.assertFalse(view.displayShowHideAllLinks())
        # as pmCreator2, 3 templates available
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        self.assertEqual(len(cfg.getItemTemplates(filtered=True)), 3)
        self.assertEqual(len(view._getTemplatesTree()['children']), 3)
        # no sub children
        templatesTree = view._getTemplatesTree()
        self.assertFalse(templatesTree['children'][0]['children'])
        self.assertFalse(templatesTree['children'][1]['children'])
        self.assertFalse(templatesTree['children'][2]['children'])
        self.assertFalse(view.displayShowHideAllLinks())

        # user may cancel action
        self.request.RESPONSE.setStatus(200)
        self.request.form['form.HTTP_REFERER'] = self.request.RESPONSE.getHeader('location')
        self.request.form['form.buttons.cancel'] = True
        view()
        self.assertEqual(self.request.RESPONSE.status, 302)
        self.assertEqual(self.request.RESPONSE.getHeader('location'),
                         self.request.form.get('form.HTTP_REFERER'))

        # create an item from an itemTemplate
        self.request.RESPONSE.setStatus(200)
        self.request.RESPONSE.setHeader('location', '')
        self.assertEqual(self.request.RESPONSE.status, 200)
        # the default item template
        templatesTree = view._getTemplatesTree()
        itemTemplate = templatesTree['children'][0]['item']
        self.request.form['templateUID'] = itemTemplate.UID
        view()
        # user was redirected to the new created item edit form
        self.assertEqual(self.request.RESPONSE.status, 302)
        # with default template, we remove the title
        self.assertEqual(self.request.RESPONSE.getHeader('location'),
                         '{0}/{1}/edit?title='.format(
                         pmFolder.absolute_url(), itemTemplate.getId))
        # one item created in the user pmFolder
        self.assertEqual(len(pmFolder.objectValues('MeetingItem')), 1)
        self.assertEqual(pmFolder.objectValues('MeetingItem')[-1].getId(), itemTemplate.getId)
        # with another template
        templatesTree = view._getTemplatesTree()
        itemTemplate = templatesTree['children'][1]['item']
        self.request.form['templateUID'] = itemTemplate.UID
        view()
        # user was redirected to the new created item edit form
        self.assertEqual(self.request.RESPONSE.status, 302)
        # with default template, we remove the title
        self.assertEqual(self.request.RESPONSE.getHeader('location'),
                         '{0}/{1}/edit'.format(
                         pmFolder.absolute_url(), itemTemplate.getId))
        # one item created in the user pmFolder
        self.assertEqual(len(pmFolder.objectValues('MeetingItem')), 2)
        self.assertEqual(pmFolder.objectValues('MeetingItem')[-1].getId(), itemTemplate.getId)

    def test_pm_ItemTemplatesCaching(self):
        '''ItemTemplateView.createTemplatesTree uses ram.cache.'''
        # main_template is taking ajax_load into account
        self.request['ajax_load'] = '123456789'
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        pmCreator1_rendered_view = view()
        pmCreator1_groups = self.member.getGroups()
        self.assertTrue('/pmCreator1/' in pmCreator1_rendered_view)
        self.assertFalse('/pmCreator1b/' in pmCreator1_rendered_view)
        # template2 is restricted to vendors, it is not useable by developers creators
        template2_uid = self.meetingConfig.itemtemplates.template2.UID()
        self.assertFalse(template2_uid in pmCreator1_rendered_view)

        # with a user with same groups, the cache is used but the result is patched
        self.changeUser('pmCreator1b')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        pmCreator1b_rendered_view = view()
        self.assertEqual(pmCreator1_groups, self.member.getGroups())
        self.assertNotEqual(pmCreator1_rendered_view, pmCreator1b_rendered_view)
        self.assertFalse('/pmCreator1/' in pmCreator1b_rendered_view)
        self.assertTrue('/pmCreator1b/' in pmCreator1b_rendered_view)
        self.assertFalse(template2_uid in pmCreator1b_rendered_view)

        # another user having other Plone groups
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        pmCreator2_rendered_view = view()
        self.assertNotEqual(pmCreator1_groups, self.member.getGroups())
        self.assertNotEqual(pmCreator1_rendered_view, pmCreator2_rendered_view)
        self.assertTrue('/pmCreator2/' in pmCreator2_rendered_view)
        self.assertTrue(template2_uid in pmCreator2_rendered_view)

    def test_pm_ItemTemplateView(self):
        '''As some fields behaves differently on an item template,
           check that the view is still working correctly, for example if 'proposingGroup' is empty
           (possible on an item template but not on a item in the application).'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        itemTemplates = self.catalog(
            portal_type=cfg.getItemTypeName(configType='MeetingItemTemplate'))
        for brain in itemTemplates:
            itemTemplate = brain.getObject()
            itemTemplate()
        # test when 'proposingGroupWithGroupInCharge' is used
        usedItemAttrs = cfg.getUsedItemAttributes()
        if 'proposingGroupWithGroupInCharge' not in usedItemAttrs:
            cfg.setUsedItemAttributes(usedItemAttrs + ('proposingGroupWithGroupInCharge', ))
        for brain in itemTemplates:
            itemTemplate = brain.getObject()
            itemTemplate()

    def test_pm_CreateItemFromTemplate(self):
        '''Test the createItemFromTemplate functionnality triggered from the plonemeeting portlet.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        self.getMeetingFolder()
        folder = self.getMeetingFolder()
        itemTemplateView = folder.restrictedTraverse('createitemfromtemplate')
        # the template we will use
        itemTemplates = cfg.getItemTemplates(filtered=True)
        itemTemplate = itemTemplates[0].getObject()
        self.assertEqual(itemTemplate.portal_type, cfg.getItemTypeName(configType='MeetingItemTemplate'))
        itemTemplateUID = itemTemplate.UID()
        # add a ftw label as it is kept when item created from item template
        self.changeUser('siteadmin')
        labelingview = itemTemplate.restrictedTraverse('@@labeling')
        self.request.form['activate_labels'] = ['label']
        labelingview.update()
        item_labeling = ILabeling(itemTemplate)
        self.assertEqual(item_labeling.storage, {'label': []})
        self.changeUser('pmCreator1')
        # for now, no items in the user folder
        self.assertFalse(folder.objectIds('MeetingItem'))
        newItem = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        self.assertEqual(newItem.portal_type, cfg.getItemTypeName())
        # the new item is the itemTemplate clone
        self.assertEqual(newItem.Title(), itemTemplate.Title())
        self.assertEqual(newItem.Description(), itemTemplate.Description())
        self.assertEqual(newItem.getDecision(), itemTemplate.getDecision())
        # and it has been created in the user folder
        self.assertTrue(newItem.getId() in folder.objectIds())
        # labels are kept
        newItem_labeling = ILabeling(newItem)
        self.assertEqual(item_labeling.storage, newItem_labeling.storage)
        # now check that the user can use a 'secret' item template if no proposing group is selected on it
        self.changeUser('admin')
        itemTemplate.setPrivacy('secret')
        # an itemTemplate can have no proposingGroup, it does validate
        itemTemplate.setProposingGroup('')
        self.failIf(itemTemplate.validate_proposingGroup(''))
        # use this template
        self.changeUser('pmCreator1')
        newItem2 = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        # _at_rename_after_creation is correct
        self.assertEqual(newItem2._at_rename_after_creation, MeetingItem._at_rename_after_creation)
        self.assertEqual(newItem2.portal_type, cfg.getItemTypeName())
        # item has been created with a filled proposing group
        # and privacy is still ok
        self.assertTrue(newItem2.getId() in folder.objectIds())
        userGroupUids = self.tool.get_orgs_for_user(suffixes=['creators'])
        self.assertEqual(newItem2.getProposingGroup(), userGroupUids[0])
        self.assertEqual(newItem2.getPrivacy(), itemTemplate.getPrivacy())

    def test_pm_CreateItemFromTemplateInSubfolderWithSpecialChars(self):
        '''Test the createItemFromTemplate functionnality with subfolder when
           subfolder title and itemTemplate title use special chars as it is used
           to build the WF comments.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        folder = api.content.create(cfg.itemtemplates, type='Folder', id='folder', title='Conténer')
        itemTemplate = self.create('MeetingItemTemplate', folder=folder)
        itemTemplate.setTitle('Titlé')
        itemTemplate.reindexObject(idxs=['Title'])
        self.changeUser('pmCreator1')
        mFolder = self.getMeetingFolder()
        itemTemplateView = mFolder.restrictedTraverse('createitemfromtemplate')
        newItem = itemTemplateView.createItemFromTemplate(itemTemplate.UID())
        last_wf_comments = getLastWFAction(newItem)['comments']
        self.assertEqual(
            last_wf_comments,
            u'This item has been created from item template "Cont\xe9ner / Titl\xe9".')

    def test_pm_CreateItemFromTemplateIsPrivacyViewable(self):
        '''Test the createItemFromTemplate functionnality when creating an item
           with privacy "secret" and MeetingConfig.restrictAccessToSecretItems is True.'''
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        self._enableField('privacy')
        cfg.setRestrictAccessToSecretItems(True)
        itemTemplates = cfg.getItemTemplates(filtered=True)
        itemTemplate = itemTemplates[0].getObject()
        itemTemplate.setPrivacy('secret')
        itemTemplate.setProposingGroup(self.developers_uid)
        itemTemplateUID = itemTemplate.UID()

        # create item
        self.changeUser('pmCreator1')
        self.getMeetingFolder()
        folder = self.getMeetingFolder()
        itemTemplateView = folder.restrictedTraverse('createitemfromtemplate')
        # creating an item from such template does not raise Unauthorized
        itemTemplateView.createItemFromTemplate(itemTemplateUID)

    def test_pm_CreateItemFromTemplateKeepsProposingGroup(self):
        '''When item create from itemTemplate, if proposingGroup defined on itemTemplate,
           it is kept if current user is creator for this proposingGroup.'''
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        self.getMeetingFolder()
        folder = self.getMeetingFolder()
        itemTemplateView = folder.restrictedTraverse('createitemfromtemplate')
        itemTemplates = cfg.getItemTemplates(filtered=True)
        itemTemplate = itemTemplates[0].getObject()
        itemTemplateUID = itemTemplate.UID()

        # itemTemplate created without proposingGroup,
        # first proposingGroup of user is used
        self.assertEqual(itemTemplate.getProposingGroup(), '')
        newItem = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        self.assertEqual(newItem.getProposingGroup(), self.developers_uid)
        # use vendors as proposingGroup, if user is not creator for it,
        # it's first proposingGroup is used, even if member 'advisers' for proposingGroup
        itemTemplate.setProposingGroup(self.vendors_uid)
        self.assertTrue(self.developers_creators in self.member.getGroups())
        self.assertTrue(self.vendors_advisers in self.member.getGroups())
        self.assertFalse(self.vendors_creators in self.member.getGroups())
        newItem = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        self.assertEqual(newItem.getProposingGroup(), self.developers_uid)
        # when current member is creator for it, then it is kept
        itemTemplate.setProposingGroup(self.vendors_uid)
        self._addPrincipalToGroup(self.member.getId(), self.vendors_creators)
        self.assertTrue(self.developers_creators in self.member.getGroups())
        self.assertTrue(self.vendors_creators in self.member.getGroups())
        newItem = itemTemplateView.createItemFromTemplate(itemTemplateUID)
        self.assertEqual(newItem.getProposingGroup(), self.vendors_uid)

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
        self.assertTrue(newItem2.getId() in newItem2.getParentNode().objectIds())
        # cancel second edition
        newItem2.restrictedTraverse('@@at_lifecycle_view').cancel_edit()
        self.assertTrue(newItem2.getId() in newItem2.getParentNode().objectIds())

    def test_pm_ItemTemplatesWithSubFolders(self):
        '''Test when we have subFolders containing item templates in the configuration.'''
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        # 2 elements, and it is items
        templatesTree = view._getTemplatesTree()
        self.assertEqual(len(templatesTree['children']), 2)
        self.assertEqual(templatesTree['children'][0]['item'].meta_type, 'MeetingItem')
        self.assertEqual(templatesTree['children'][1]['item'].meta_type, 'MeetingItem')
        self.assertFalse(view.displayShowHideAllLinks())

        # add an itemTemplate in a subFolder
        self.changeUser('siteadmin')
        cfg.itemtemplates.invokeFactory('Folder', id='subfolder', title="Sub folder")
        subFolder = cfg.itemtemplates.subfolder
        self.create('MeetingItemTemplate', folder=subFolder)

        # we have the subfolder and item under it
        self.changeUser('pmCreator1')
        view()
        templatesTree = view._getTemplatesTree()
        self.assertEqual(len(templatesTree['children']), 3)
        self.assertEqual(templatesTree['children'][0]['item'].meta_type, 'MeetingItem')
        self.assertEqual(templatesTree['children'][1]['item'].meta_type, 'MeetingItem')
        self.assertEqual(templatesTree['children'][2]['item'].meta_type, 'ATFolder')
        self.assertEqual(templatesTree['children'][2]['children'][0]['item'].meta_type, 'MeetingItem')
        self.assertTrue(view.displayShowHideAllLinks())

        # an empty folder is not shown
        self.changeUser('siteadmin')
        cfg.itemtemplates.invokeFactory('Folder', id='subfolder1', title="Sub folder 1")
        subFolder1 = cfg.itemtemplates.subfolder1
        newItemTemplate = self.create('MeetingItemTemplate', folder=subFolder1)
        # hide it to pmCreator1
        newItemTemplate.setTemplateUsingGroups((self.vendors_uid,))
        newItemTemplate.reindexObject()
        self.changeUser('pmCreator1')
        view()
        templatesTree = view._getTemplatesTree()
        self.assertEqual(len(templatesTree['children']), 3)
        # but available to 'pmCreator2'
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        templatesTree = view._getTemplatesTree()
        self.assertEqual(len(templatesTree['children']), 5)
        self.assertEqual(templatesTree['children'][4]['item'].id, 'subfolder1')

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
        templatesTree = view._getTemplatesTree()
        self.assertEqual(len(templatesTree['children']), 3)
        self.assertEqual(templatesTree['children'][0]['item'].id, ITEM_DEFAULT_TEMPLATE_ID)
        self.assertEqual(templatesTree['children'][1]['item'].id, 'template1')
        self.assertEqual(templatesTree['children'][2]['item'].id, 'subfolder')
        self.assertEqual(templatesTree['children'][2]['children'][0]['item'].id, 'subsubfolder')
        self.assertEqual(templatesTree['children'][2]['children'][0]['children'][0]['item'].id, 'o1')
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
        # @@change-item-listtype
        view = item.restrictedTraverse('@@change-item-listtype')
        self.assertFalse(item.adapted().mayChangeListType())
        self.assertRaises(Unauthorized, view, new_value='late')
        self.create('Meeting')
        self.presentItem(item)
        # @@item-listtype
        view = item.restrictedTraverse('@@item-listtype')
        res = view()
        self.assertTrue("item_listType_normal" in res)
        self.assertTrue("item_listType_late" in res)
        # @@change-item-listtype
        view = item.restrictedTraverse('@@change-item-listtype')
        # now listType may be changed
        self.assertTrue(item.adapted().mayChangeListType())
        # new_value is verified
        self.assertRaises(KeyError, view, new_value='some_wrong_value')
        # right, change listType value
        self.assertEqual(item.getListType(), u'normal')
        self.assertTrue(self.catalog(UID=item.UID(), listType=u'normal'))
        view('late')
        # value changed and item reindexed
        self.assertEqual(item.getListType(), u'late')
        self.assertTrue(self.catalog(UID=item.UID(), listType=u'late'))
        # a specific subscriber is triggered when listType value changed
        # register a subscriber (onItemListTypeChanged) that will actually change item title
        # and set it to 'old_listType - new_listType'
        zcml.load_config('tests/events.zcml', products_plonemeeting)
        self.assertEqual(item.Title(), 'Item title')
        view('normal')
        self.assertEqual(item.Title(), 'late - normal')
        self.assertEqual(item.getListType(), u'normal')
        self.assertTrue(self.catalog(UID=item.UID(), listType=u'normal'))
        # if title is 'late - normal' call to subscriber will raise an error
        # this way, we test that when an error occur in the event, the listType is not changed
        view('late')
        # not changed and a portal_message is added
        self.assertEqual(item.Title(), 'late - normal')
        self.assertEqual(item.getListType(), u'normal')
        self.assertTrue(self.catalog(UID=item.UID(), listType=u'normal'))
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[-1].message, SAMPLE_ERROR_MESSAGE)
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
        self.changeUser('admin')
        self.meetingConfig.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': self.vendors_uid,
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
        self.assertFalse(self.catalog(**query))

        # no delay-aware advice
        itemWithNonDelayAwareAdvices = self.create('MeetingItem')
        itemWithNonDelayAwareAdvices.setBudgetRelated(True)
        itemWithNonDelayAwareAdvices._update_after_edit()

        # the automatic advice has been added
        self.assertTrue(itemWithNonDelayAwareAdvices.adviceIndex[self.vendors_uid]['optional'] is False)
        itemWithNonDelayAwareAdvices.setOptionalAdvisers((self.developers_uid,))
        itemWithNonDelayAwareAdvices._update_after_edit()
        self.assertTrue(itemWithNonDelayAwareAdvices.adviceIndex[self.developers_uid]['optional'] is True)

        # one delay-aware advice addable
        itemWithDelayAwareAdvice = self.create('MeetingItem')
        itemWithDelayAwareAdvice.setOptionalAdvisers(
            ('{0}__rowid__unique_id_123'.format(self.vendors_uid),))
        itemWithDelayAwareAdvice._update_after_edit()
        self.proposeItem(itemWithDelayAwareAdvice)
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_addable'])
        # this time the element is returned
        self.assertTrue(len(self.catalog(**query)) == 1)
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # if item3 is no more giveable, the query will not return it anymore
        self.validateItem(itemWithDelayAwareAdvice)
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertTrue(not self.catalog(**query))
        # back to proposed, add it
        self.backToState(itemWithDelayAwareAdvice, self._stateMappingFor('proposed'))
        createContentInContainer(itemWithDelayAwareAdvice,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_editable'])
        # an editable item will found by the query
        self.assertTrue(len(self.catalog(**query)) == 1)
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even once updated, it will still be found
        itemWithDelayAwareAdvice.update_local_roles()
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())

        # makes it no more editable
        self.backToState(itemWithDelayAwareAdvice, self._stateMappingFor('itemcreated'))
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_editable'])
        self.assertTrue(not self.catalog(**query))

        # makes it giveable again and timed_out, it should still be found
        self.proposeItem(itemWithDelayAwareAdvice)
        itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2016, 1, 1)
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even if a reindexObject occurs in between, still found
        itemWithDelayAwareAdvice.reindexObject()
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # but once updated, it is not found anymore
        itemWithDelayAwareAdvice.update_local_roles()
        self.assertTrue(not self.catalog(**query))

        # try with an not_given timed_out advice as indexAdvisers behaves differently
        # remove meetingadvice, back to not timed_out,.update_local_roles then proceed
        self.deleteAsManager(itemWithDelayAwareAdvice.meetingadvice.UID())
        itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now()
        itemWithDelayAwareAdvice.update_local_roles()
        # found for now
        itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2016, 1, 1)
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even if a reindexObject occurs in between, still found
        itemWithDelayAwareAdvice.reindexObject()
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # but once updated, it is not found anymore
        itemWithDelayAwareAdvice.update_local_roles()
        self.assertTrue(not self.catalog(**query))

    def test_pm_UpdateDelayAwareAdvicesComputeQuery(self):
        '''
          The computed query only consider organizations for which a delay aware advice is configured.
        '''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        advice_alive_states = get_advice_alive_states()
        self.changeUser('admin')
        # for now, no customAdvisers
        for mc in self.tool.objectValues('MeetingConfig'):
            self.assertFalse(mc.getCustomAdvisers())
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        self.assertEqual(query, {'indexAdvisers': ['dummy']})
        # define customAdvisers in cfg1, only one delay aware for vendors
        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '5',
              'delay_label': '5 days'},
             {'row_id': 'unique_id_456',
              'org': self.vendors_uid,
              'gives_auto_advice_on': 'here/getBudgetRelated',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '',
              'delay_label': ''}, ])
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        self.assertEqual(
            query,
            {'indexAdvisers': ['delay__{0}_{1}'.format(self.vendors_uid, advice_state)
                               for advice_state in ('advice_not_given', ) + advice_alive_states]})
        # define customAdvisers in cfg2, also for vendors
        cfg2.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': 'python:True',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': self.vendors_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': '10 days'}, ])
        # the query is the same when vendors defined in cfg alone or cfg and cfg2
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        self.assertEqual(
            sorted(query),
            sorted({'indexAdvisers':
                   ['delay__{0}_{1}'.format(self.vendors_uid, advice_state)
                    for advice_state in ('advice_not_given', ) + advice_alive_states]}))
        # now define customAdvisers for developers
        cfg2.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': 'python:True',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '',
              'delay_label': ''},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': '10 days'}, ])
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        # check len because sorted removes duplicates
        self.assertEqual(len(query['indexAdvisers']), 2 * (1 + len(advice_alive_states)))
        self.assertEqual(
            sorted(query),
            sorted({'indexAdvisers':
                    ['delay__{0}_{1}'.format(self.vendors_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + advice_alive_states] +
                    ['delay__{0}_{1}'.format(self.developers_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + advice_alive_states]}))
        # if org delay aware in several MeetingConfigs, line is only shown one time
        cfg2.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.vendors_uid,
              'gives_auto_advice_on': 'python:True',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '3',
              'delay_label': '3 days'},
             {'row_id': 'unique_id_456',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2012/01/01',
              'for_item_created_until': '',
              'delay': '10',
              'delay_label': '10 days'}, ])
        query = self.portal.restrictedTraverse('@@update-delay-aware-advices')._computeQuery()
        self.assertEqual(len(query['indexAdvisers']), 2 * (1 + len(advice_alive_states)))
        self.assertEqual(
            sorted(query),
            sorted({'indexAdvisers':
                    ['delay__{0}_{1}'.format(self.vendors_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + advice_alive_states] +
                    ['delay__{0}_{1}'.format(self.developers_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + advice_alive_states]}))

    def test_pm_UpdateDelayAwareAdvicesUpdateAllAdvices(self):
        """Test the _updateAllAdvices method that update every advices.
           It is used to update every delay aware advices every night."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(('itemcreated',))
        cfg.setItemAdviceEditStates(('itemcreated',))
        # create items and ask advice
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item1.setOptionalAdvisers((self.developers_uid,))
        item1._update_after_edit()
        item2 = self.create('MeetingItem')
        item2.setOptionalAdvisers((self.developers_uid,))
        self.proposeItem(item2)
        self.assertTrue(self.developers_advisers in item1.__ac_local_roles__)
        self.assertFalse(self.developers_advisers in item2.__ac_local_roles__)

        # change configuration, _updateAllAdvices then check again
        self.changeUser('siteadmin')
        cfg.setItemAdviceStates((self._stateMappingFor('proposed'),))
        cfg.setItemAdviceEditStates((self._stateMappingFor('proposed'),))
        # check that item modified is not changed when advice updated
        item1_original_modified = item1.modified()
        item2_original_modified = item2.modified()
        # _updateAllAdvices called with query={} (default)
        self.portal.restrictedTraverse('@@update-delay-aware-advices')._updateAllAdvices()
        self.assertFalse(self.developers_advisers in item1.__ac_local_roles__)
        self.assertTrue(self.developers_advisers in item2.__ac_local_roles__)
        self.assertEqual(item1.modified(), item1_original_modified)
        self.assertEqual(item2.modified(), item2_original_modified)

    def test_pm_UpdateItemsToReindex(self):
        """The @@update-items-to-reindex called by @@pm-night-tasks."""
        # create item with annexes, annexes not found in catalog
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem', title="Classic item1 title")
        item2 = self.create('MeetingItem', title="Classic item2 title")
        item3 = self.create('MeetingItem', title="Classic item3 title")
        self.tool.setDeferParentReindex(['annex'])
        self.addAnnex(item1, annexTitle="Special annex1 title")
        self.addAnnex(item2, annexTitle="Special annex2 title")
        self.addAnnex(item3, annexTitle="Special annex3 title")
        self.assertEqual(len(self.catalog(SearchableText="Classic")), 3)
        self.assertFalse(self.catalog(SearchableText="Special"))
        # will check that modified is not changed
        item1_modified = item1.modified()
        item2_modified = item2.modified()
        item3_modified = item3.modified()
        self.changeUser('siteadmin')
        # @@update-items-to-reindex is called by @@pm-night-tasks
        self.portal.restrictedTraverse('@@pm-night-tasks')()
        self.assertEqual(len(self.catalog(SearchableText="Classic")), 3)
        self.assertEqual(len(self.catalog(SearchableText="Special")), 3)
        self.changeUser('pmCreator1')
        self.assertEqual(len(self.catalog(SearchableText="Classic")), 3)
        self.assertEqual(len(self.catalog(SearchableText="Special")), 3)
        # items are not modified
        self.assertEqual(item1.modified(), item1_modified)
        self.assertEqual(item2.modified(), item2_modified)
        self.assertEqual(item3.modified(), item3_modified)

    def test_pm_SendPodTemplateToMailingList(self):
        """Send a Pod template to a mailing list."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        template = self.meetingConfig.podtemplates.itemTemplate
        # no mailing lists for now
        self.assertEqual(template.mailing_lists, u'')
        self.failIf(getAvailableMailingLists(item, template))

        # define mailing_lists
        # False condition
        template.mailing_lists = "list1;python:False;user1@test.be\nlist2;python:False;user1@test.be"
        self.assertEqual(getAvailableMailingLists(item, template), [])
        # wrong TAL condition, the list is there with error
        template.mailing_lists = "list1;python:wrong_expression;user1@test.be\nlist2;python:False;user1@test.be"
        error_msg = translate('Mailing lists are not correctly defined, original error is \"${error}\"',
                              mapping={'error': u'name \'wrong_expression\' is not defined', },
                              context=self.request)
        self.assertEqual(getAvailableMailingLists(item, template), [error_msg])
        # correct and True condition
        template.mailing_lists = "list1;python:True;user1@test.be\nlist2;python:False;user1@test.be"
        self.assertEqual(getAvailableMailingLists(item, template), ['list1'])

        # call the document-generation view
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        self.request.set('mailinglist_name', 'unknown_mailing_list')
        view = item.restrictedTraverse('@@document-generation')
        # raises Unauthorized if mailing list no available
        self.assertRaises(Unauthorized, view)

        # use correct mailing list
        self.request.set('mailinglist_name', 'list1')
        # but without defined recipients
        template.mailing_lists = "list1;python:True;"
        with self.assertRaises(Exception) as cm:
            view()
        self.assertEqual(cm.exception.message, view.MAILINGLIST_NO_RECIPIENTS)
        self.assertRaises(Exception, view)

        # now when working as expected
        template.mailing_lists = "list1;python:True;user1@test.be,pmCreator1,pmCreator2\nlist2;python:False;user1@test.be"
        messages = IStatusMessage(self.request).show()
        msg = translate(
            'pt_mailing_sent',
            domain='PloneMeeting',
            mapping={'recipients': "user1@test.be, "
                     "M. PMCreator One <pmcreator1@plonemeeting.org>, "
                     "M. PMCreator Two <pmcreator2@plonemeeting.org>"},
            context=self.request)
        self.assertNotEquals(messages[-1].message, msg)
        view()
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[-1].message, msg)

    def test_pm_SendPodTemplateToMailingListRecipients(self):
        """Recipients may be defined using several ways :
           - python script;
           - userid;
           - email;
           - Plone group."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')

        # script
        self.assertEqual(extract_recipients(item, "python:['pmCreator1']"),
                         [u'M. PMCreator One <pmcreator1@plonemeeting.org>'])
        # userid
        self.assertEqual(extract_recipients(item, "pmCreator1"),
                         [u'M. PMCreator One <pmcreator1@plonemeeting.org>'])
        # email
        self.assertEqual(extract_recipients(item, "pmcreator1@plonemeeting.org"),
                         ['pmcreator1@plonemeeting.org'])
        # group
        group_dev_creators = "group:{0}".format(self.developers_creators)
        self.assertEqual(sorted(extract_recipients(item, group_dev_creators)),
                         [u'M. PMCreator One <pmcreator1@plonemeeting.org>',
                          u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
                          u'M. PMManager <pmmanager@plonemeeting.org>'])

        # mixed
        self.assertEqual(sorted(extract_recipients(
            item,
            "python:['pmCreator1'],pmCreator1,pmCreator2,{0},new@example.com".format(
                group_dev_creators))),
            [u'M. PMCreator One <pmcreator1@plonemeeting.org>',
             u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
             u'M. PMCreator Two <pmcreator2@plonemeeting.org>',
             u'M. PMManager <pmmanager@plonemeeting.org>',
             'new@example.com'])

    def test_pm_StorePodTemplateAsAnnex(self):
        """Store a Pod template as an annex."""
        self.changeUser('pmCreator1')
        pod_template, annex_type, item = self._setupStorePodAsAnnex()
        # remove defined store_as_annex for now
        pod_template.store_as_annex = None

        # the document-generation view
        self.request.set('HTTP_REFERER', item.absolute_url())
        view = item.restrictedTraverse('@@document-generation')

        # raises Unauthorized if trying to store_as_annex, as no store_as_annex
        # defined and need to be a (Meeting)Manager also
        self.assertRaises(Unauthorized, view)

        # check as MeetingManager
        self.changeUser('pmManager')
        self.assertRaises(Unauthorized, view)

        # now correctly define template.store_as_annex and try to store
        pod_template.store_as_annex = annex_type.UID()
        self.assertEqual(get_annexes(item), [])
        url = view()
        # after call to view(), user is redirected to the item view
        self.assertEqual(url, item.absolute_url())
        # now we have an annex
        annex = get_annexes(item)[0]
        self.assertEqual(annex.used_pod_template_id, pod_template.getId())
        # we can not store an annex using a POD template several times, we get a status message
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 3)
        view()
        # no extra annex
        self.assertEqual(get_annexes(item), [annex])
        messages = IStatusMessage(self.request).show()
        self.assertEqual(len(messages), 4)
        last_msg = messages[-1].message
        can_not_store_several_times_msg = translate(
            u'store_podtemplate_as_annex_can_not_store_several_times',
            domain='PloneMeeting',
            context=self.request)
        self.assertEqual(last_msg, can_not_store_several_times_msg)

        # scan_id : if found in the REQUEST during storage, it is set
        self.assertIsNone(annex.scan_id)
        self.request.set(ITEM_SCAN_ID_NAME, DEFAULT_SCAN_ID)
        self.deleteAsManager(annex.UID())
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.scan_id, DEFAULT_SCAN_ID)

    def test_pm_StorePodTemplateAsAnnexTitle(self):
        """Title of stored annex may be customized depending on
           pod_template.store_as_annex_title_expr."""
        pod_template, annex_type, item = self._setupStorePodAsAnnex()

        self.changeUser('pmManager')

        # the document-generation view
        view = item.restrictedTraverse('@@document-generation')

        # by default, template Title is used if nothing define on
        # pod_template.store_as_annex_title_expr
        self.assertEqual(pod_template.store_as_annex_title_expr, u'')
        # set store_as_annex_title_expr to None to check, it is the case when
        # field is empty and saved in the UI
        pod_template.store_as_annex_title_expr = None
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.Title(), pod_template.Title())

        # now define a pod_template.store_as_annex_title_expr, append annex creator
        pod_template.store_as_annex_title_expr = \
            u'python: "{0} - generated by {1} héhé".format(pod_template.Title(), member.getId())'
        self.deleteAsManager(annex.UID())
        # set a scan_id
        self.request.set(ITEM_SCAN_ID_NAME, DEFAULT_SCAN_ID)
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.Title(), 'Meeting item - generated by pmManager héhé')

        # when using the functionnality, the title and the scan_id are searchable
        # item title/scan_id indexed in SearchableText is deferred to next
        # SearchableText reindexing
        item.reindexObject(idxs=['SearchableText'])
        item_uid = item.UID()
        res = self.catalog(SearchableText=annex.Title())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].UID, item_uid)
        res = self.catalog(SearchableText=annex.scan_id)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].UID, item_uid)

    def test_pm_StorePodTemplateAsAnnexEmptyFile(self):
        """When pod_template.store_as_annex_empty_file is True,
           an empty file is stored instead the generated POD template,
           this for performance reason when stored annex is not used for any
           other purpose than being replaced by the AMQP process."""
        pod_template, annex_type, item = self._setupStorePodAsAnnex()

        self.changeUser('pmManager')

        # by default, the POD template is generated
        view = item.restrictedTraverse('@@document-generation')
        self.assertFalse(pod_template.store_as_annex_empty_file)
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.file.contentType, 'application/vnd.oasis.opendocument.text')
        self.assertEqual(annex.file.filename, u'Meeting item.odt')
        self.assertIsNone(annex.scan_id)

        # now when pod_template.store_as_annex_empty_file is True
        pod_template.store_as_annex_empty_file = True
        self.deleteAsManager(annex.UID())
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.file.contentType, 'text/plain')
        self.assertEqual(annex.file.data, 'This file will be replaced by the scan process')
        self.assertEqual(annex.file.filename, u'empty_file.txt')
        self.assertEqual(annex.scan_id, DEFAULT_SCAN_ID)

    def test_pm_StorePodTemplateAsAnnexWrongConfig(self):
        """As we can not validate field ConfigurablePODTemplate.store_as_annex to
           select an annex_type of a POD template that will be generated on correct portal_type,
           so we can select an item annex_type for a POD template that will be generated
           on an advice for example, we manage this while storing the annex with a clear message."""
        cfg = self.meetingConfig
        pod_template, annex_type, item = self._setupStorePodAsAnnex()
        # change pod_template.store_as_annex to use a meeting related annex_type
        meeting_annex_type = cfg.annexes_types.meeting_annexes.get(self.annexFileTypeMeeting)
        pod_template.store_as_annex = meeting_annex_type.UID()
        # clear portal messages
        IStatusMessage(self.request).show()
        self.assertEqual(IStatusMessage(self.request).show(), [])
        self.changeUser('pmManager')
        # the document-generation view
        view = item.restrictedTraverse('@@document-generation')
        # does not break but do nothing but adding a portal message
        store_podtemplate_as_annex_wrong_annex_type_on_pod_template = translate(
            u'store_podtemplate_as_annex_wrong_annex_type_on_pod_template',
            domain='PloneMeeting',
            context=self.request)
        view()
        messages = IStatusMessage(self.request).show()
        self.assertEqual(
            messages[0].message,
            store_podtemplate_as_annex_wrong_annex_type_on_pod_template)

    def test_pm_ItemMoreInfos(self):
        '''Test the @@item-more-infos view, especially getItemsListVisibleFields
           for which order of fields may be defined and displayed data may not
           respect MeetingItem schema order.'''
        cfg = self.meetingConfig
        cfg.setItemsListVisibleFields(('MeetingItem.description',
                                       'MeetingItem.decision',
                                       'MeetingItem.motivation'))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('@@item-more-infos')
        view()
        self.assertEqual(view.getVisibleFields().keys(),
                         ['description', 'decision', 'motivation'])

    def test_pm_ItemMoreInfosItemsVisibleFields(self):
        '''Test the @@item-more-infos view when using MeetingConfig.ItemsVisibleFields
           instead MeetingConfig.itemsListVisibleFields.'''
        cfg = self.meetingConfig
        # not used
        cfg.setItemsListVisibleFields(('MeetingItem.description',
                                       'MeetingItem.decision'))
        cfg.setItemsVisibleFields(('MeetingItem.annexes',
                                   'MeetingItem.advices',
                                   'MeetingItem.description',
                                   'MeetingItem.motivation',
                                   'MeetingItem.decision',
                                   'MeetingItem.privacy'))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('@@item-more-infos')
        view(fieldsConfigAttr='itemsVisibleFields')
        self.assertEqual(view.getVisibleFields().keys(),
                         ['annexes', 'advices', 'description', 'motivation', 'decision', 'privacy'])

    def test_pm_ItemMoreInfosNotViewableItem(self):
        '''When displaying more infos on a not viewable item, configuration
           defined in MeetingConfig.itemsNotViewableVisibleFields will be used.'''
        cfg = self.meetingConfig
        cfg_id = cfg.getId()
        self.changeUser('pmCreator1')
        linked_item = self.create('MeetingItem')
        linked_item_uid = linked_item.UID()
        annex = self.addAnnex(linked_item)
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(View, linked_item))
        item = self.create('MeetingItem')
        item.setManuallyLinkedItems((linked_item_uid, ))
        view = item.restrictedTraverse('@@load-linked-items')
        self.assertTrue(linked_item_uid in view())
        self.assertTrue("@@load-linked-items-infos?fieldsConfigAttr=itemsVisibleFields" in view())
        infos_view = linked_item.restrictedTraverse('@@load-linked-items-infos')
        infos_view("itemsNotViewableVisibleFields", cfg_id)
        self.assertEqual(cfg.getItemsNotViewableVisibleFields(), ())
        cfg.setItemsNotViewableVisibleFields(('MeetingItem.description', ))
        self.cleanMemoize()
        # when field is empty, it is not displayed
        self.assertTrue("Nothing to display." in infos_view("itemsNotViewableVisibleFields", cfg_id))
        self.assertFalse(self.descriptionText in infos_view("itemsNotViewableVisibleFields", cfg_id))
        linked_item.setDescription(self.descriptionText)
        self.assertTrue(self.descriptionText in infos_view("itemsNotViewableVisibleFields", cfg_id))
        # view annexes, not viewable for now
        category_uid = linked_item.categorized_elements.get(annex.UID())['category_uid']
        # not viewable because there is no back referenced item to which user has View access
        infos = linked_item.restrictedTraverse('@@categorized-childs-infos')(
            category_uid=category_uid, filters={}).strip()
        # not viewable
        self.assertFalse(infos)
        # not downloadable
        download_view = annex.restrictedTraverse('@@download')
        self.assertRaises(Unauthorized, download_view)
        # make it viewable
        cfg.setItemsNotViewableVisibleFields(('MeetingItem.description', 'MeetingItem.annexes', ))
        self.cleanMemoize()
        infos = linked_item.restrictedTraverse('@@categorized-childs-infos')(
            category_uid=category_uid, filters={}).strip()
        # viewable
        self.assertTrue(infos)
        # downloadable
        self.assertTrue(download_view())
        # remove manually linked item, no more viewable
        self.deleteAsManager(item.UID())
        infos = linked_item.restrictedTraverse('@@categorized-childs-infos')(
            category_uid=category_uid, filters={}).strip()
        self.assertFalse(infos)
        self.assertRaises(Unauthorized, download_view)
        auto_linked_item = self.create('MeetingItem')
        linked_item._update_predecessor(auto_linked_item)
        # with viewable predecessor, annex is viewable
        infos = linked_item.restrictedTraverse('@@categorized-childs-infos')(
            category_uid=category_uid, filters={}).strip()
        self.assertTrue(infos)
        self.assertTrue(download_view())

    def test_pm_ItemMoreInfosNotViewableItemTALExpr(self):
        '''When displaying more infos on a not viewable item, configuration
           defined in MeetingConfig.itemsNotViewableVisibleFields will be used,
           it is possible to complete access with a TAL expression so for example
           not viewable items fields are only shown when item is decided.'''
        cfg = self.meetingConfig
        cfg.setItemsNotViewableVisibleFields(('MeetingItem.description', ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(View, item))
        view = item.restrictedTraverse('@@item-more-infos')
        view()
        self.assertEqual(view.getVisibleFields().keys(), ['description'])
        # define TAL expression
        cfg.setItemsNotViewableVisibleFieldsTALExpr("python: item.query_state() != 'itemcreated'")
        self.cleanMemoize()
        view()
        self.assertEqual(view.getVisibleFields().keys(), [])
        self.proposeItem(item)
        cfg.setItemsNotViewableVisibleFields(('MeetingItem.description', ))

    def _setupPrintXhtml(self):
        """ """
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
        view = item.restrictedTraverse('@@document-generation')
        view()
        helper = view.get_generation_context_helper()
        return item, motivation, decision, helper

    def test_pm_PrintXhtmlContents(self):
        '''Test the method that will ease print of XHTML content into Pod templates.'''
        item, motivation, decision, helper = self._setupPrintXhtml()
        # test with one single xhtmlContent
        self.assertEqual(helper.printXhtml(item, decision),
                         item.getDecision())
        # several xhtmlContent
        self.assertEqual(helper.printXhtml(item, [motivation, decision]),
                         motivation + decision)
        # xhtmlContents is None
        self.assertEqual(helper.printXhtml(item, None), '')
        # use 'separator'
        self.assertEqual(helper.printXhtml(item, [motivation, 'separator', decision]),
                         motivation + '<p>&nbsp;</p>' + decision)
        # use 'separator' with a fonctionnal usecase
        self.assertEqual(helper.printXhtml(item, [motivation,
                                                  'separator',
                                                  '<p>DECIDE :</p>',
                                                  'separator',
                                                  decision]),
                         motivation + '<p>&nbsp;</p><p>DECIDE :</p><p>&nbsp;</p>' + decision)

    def test_pm_PrintXhtmlSeparator(self):
        ''' '''
        item, motivation, decision, helper = self._setupPrintXhtml()

        # use 'separator' and change 'separatorValue', insert 2 empty lines
        self.assertEqual(helper.printXhtml(item,
                                           [motivation, 'separator', decision],
                                           separatorValue='<p>&nbsp;</p><p>&nbsp;</p>'),
                         motivation + '<p>&nbsp;</p><p>&nbsp;</p>' + decision)
        # use keepWithNext
        # special characters are turned to HTML entities decimal representation
        self.assertEqual(helper.printXhtml(item,
                                           [motivation, 'separator', decision],
                                           keepWithNext=True),
                         '<p class="ParaKWN">The motivation using UTF-8 characters : &#232;&#224;.</p>'
                         '<p class="ParaKWN">&#160;</p>'
                         '<p class="ParaKWN">The d&#233;cision using UTF-8 characters.</p>')

    def test_pm_PrintXhtmlImageSrcToPaths(self):
        ''' '''
        item, motivation, decision, helper = self._setupPrintXhtml()

        # use image_src_to_paths
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')
        img_id = item.invokeFactory('Image', id='img', title='Image', file=data.read())
        img = getattr(item, img_id)
        img_blob_path = img.getBlobWrapper().blob._p_blob_committed
        text = "<p>Text with image <img src='{0}'/> and more text.".format(img.absolute_url())
        # res is parsed by XhtmlPreprocessor.html2xhtml in appy.pod
        res = helper.printXhtml(
            item,
            [motivation, 'separator', decision, 'separator', text],
            image_src_to_paths=True,
            keepWithNext=True,
            keepWithNextNumberOfChars=60,
            use_appy_pod_preprocessor=True)
        self.assertEqual(res,
                         '<p>The motivation using UTF-8 characters : &#232;&#224;.</p>'
                         '<p>&#160;</p>'
                         '<p class="ParaKWN">The d&#233;cision using UTF-8 characters.</p>'
                         '<p class="ParaKWN">&#160;</p>'
                         '<p class="ParaKWN">Text with image <img src="{0}"/> and more text.</p>'
                         .format(img_blob_path))

    def test_pm_PrintXhtmlImageSrcToData(self):
        ''' '''
        item, motivation, decision, helper = self._setupPrintXhtml()

        # use image_src_to_data
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')
        img_id = item.invokeFactory('Image', id='img', title='Image', file=data.read())
        img = getattr(item, img_id)
        pattern = '<p>Text with image <img src="{0}"/> and more text.</p>'
        text = pattern.format(img.absolute_url())
        # in tests the monkeypatch for safe_html.hasScript does not seem to be applied...
        # so disable remove_javascript from safe_html
        self.portal.portal_transforms.safe_html._v_transform.config['remove_javascript'] = 0
        # res is parsed by XhtmlPreprocessor.html2xhtml in appy.pod
        res = helper.printXhtml(
            item,
            text,
            image_src_to_paths=False,
            image_src_to_data=True,
            use_appy_pod_preprocessor=True)
        self.assertEqual(res,
                         pattern.format(IMG_BASE64_DATA))
        self.portal.portal_transforms.safe_html._v_transform.config['remove_javascript'] = 1

    def test_pm_PrintXhtmlAddCSSClass(self):
        ''' '''
        item, motivation, decision, helper = self._setupPrintXhtml()
        # use 'addCSSClass'
        self.assertEqual(helper.printXhtml(item,
                                           [motivation,
                                            'separator',
                                            '<p>DECIDE :</p>',
                                            'separator',
                                            decision],
                                           addCSSClass='sample'),
                         '<p class="sample">The motivation using UTF-8 characters : &#232;&#224;.</p>'
                         '<p class="sample">&#160;</p>'
                         '<p class="sample">DECIDE :</p>'
                         '<p class="sample">&#160;</p>'
                         '<p class="sample">The d&#233;cision using UTF-8 characters.</p>')

    def test_pm_PrintXhtmlUseSafeHTML(self):
        '''safe_html will do result XHTML compliant (no more used by default).'''
        item, motivation, decision, helper = self._setupPrintXhtml()
        # use_safe_html is True by default
        self.assertEqual(
            helper.printXhtml(item, [motivation, '<br>'], use_safe_html=True),
            motivation + '<br />')
        self.assertEqual(
            helper.printXhtml(item, [motivation, '<br>']),
            motivation + '<br>')

    def test_pm_PrintXhtmlClean(self):
        '''clean=True will use separate_images from imio.helpers.xhtlm.'''
        item, motivation, decision, helper = self._setupPrintXhtml()
        text = '<p>Text1</p><p><img src="http://plone/nohost/img1.png"/>' \
            '<img src="http://plone/nohost/img2.png"/></p>' \
            '<p>Text2</p><p><img src="http://plone/nohost/img3.png"/></p>'
        # True by default
        # res is parsed by XhtmlPreprocessor.html2xhtml in appy.pod
        res = helper.printXhtml(item, text, clean=False, use_appy_pod_preprocessor=True)
        self.assertEqual(res, text)
        # when used, images are moved in their own <p> when necessary
        res = helper.printXhtml(item, text, use_appy_pod_preprocessor=True)
        self.assertEqual(res,
                         '<p>Text1</p>'
                         '<p><img src="http://plone/nohost/img1.png"/></p>'
                         '<p><img src="http://plone/nohost/img2.png"/></p>'
                         '<p>Text2</p>'
                         '<p><img src="http://plone/nohost/img3.png"/></p>')

    def test_pm_PrintXhtmlAnonymize(self):
        '''Elements using class "pm-anonymize" will be anonymized if anonymize=True.'''
        item, motivation, decision, helper = self._setupPrintXhtml()

        # do nothing if nothing to do
        self.assertEqual(helper.printXhtml(item, motivation, anonymize=True),
                         '<p>The motivation using UTF-8 characters : &#232;&#224;.</p>')
        # anonymize=True
        motivation += '<p>The motivation <span class="pm-anonymize">chars \xc3\xa8\xc3\xa0</span>.</p>'
        self.assertEqual(helper.printXhtml(item, motivation, anonymize=True),
                         '<p>The motivation using UTF-8 characters : &#232;&#224;.</p>'
                         '<p>The motivation <span class="pm-anonymize"></span>.</p>')

        # anonymize may be a dict with some more config
        anonymize = {"css_class": "pm-hide", "new_content": "[Hidden]"}
        motivation += '<p>The motivation <span class="pm-hide">chars \xc3\xa8\xc3\xa0</span>.</p>'
        self.assertEqual(
            helper.printXhtml(item, motivation, anonymize=anonymize),
            '<p>The motivation using UTF-8 characters : &#232;&#224;.</p>'
            '<p>The motivation <span class="pm-anonymize">chars &#232;&#224;</span>.</p>'
            '<p>The motivation <span class="pm-hide">[Hidden]</span>.</p>')

    def test_pm_print_advices_infos(self):
        """Test the print_advices_infos method."""
        cfg = self.meetingConfig
        cfg.setSelectableAdvisers((self.developers_uid, self.vendors_uid))
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'),))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'),))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'),))
        notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid, self.vendors_uid), )
        item._update_after_edit()
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()

        # advices not given
        self.assertEqual(
            helper.print_advices_infos(item),
            "<p class='pmAdvices'><u><b>Advices :</b></u></p>"
            "<p class='pmAdvices'><u>Developers:</u><br /><u>Advice type :</u> "
            "<i>Not given yet</i></p><p class='pmAdvices'><u>Vendors:</u><br />"
            "<u>Advice type :</u> <i>Not given yet</i></p>")
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        # mixes advice given and not given
        self.assertEqual(
            helper.print_advices_infos(item),
            "<p class='pmAdvices'><u><b>Advices :</b></u></p>"
            "<p class='pmAdvices'><u>Vendors:</u><br /><u>Advice type :</u> "
            "<i>Not given yet</i></p><p class='pmAdvices'><u>Developers:</u><br />"
            "<u>Advice type :</u> <i>Positive</i><br /><u>Advice given by :</u> "
            "<i>M. PMAdviser One (H\xc3\xa9)</i><br /><u>Advice comment :</u> My comment<p></p></p>")

        # every advices given
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'negative'})
        self.changeUser('pmCreator1')
        self.assertEqual(
            helper.print_advices_infos(item),
            "<p class='pmAdvices'><u><b>Advices :</b></u></p><p class='pmAdvices'>"
            "<u>Vendors:</u><br /><u>Advice type :</u> <i>Negative</i><br />"
            "<u>Advice given by :</u> <i>M. PMReviewer Two</i><br />"
            "<u>Advice comment :</u> -<p></p></p><p class='pmAdvices'><u>Developers:</u><br />"
            "<u>Advice type :</u> <i>Positive</i><br /><u>Advice given by :</u> "
            "<i>M. PMAdviser One (H\xc3\xa9)</i><br /><u>Advice comment :</u> My comment<p></p></p>")

    def test_pm_print_meeting_date(self):
        # Setup
        cfg = self.meetingConfig
        cfg.setPowerObservers([
            {'item_access_on': '',
             'item_states': ['validated',
                             'presented',
                             'itemfrozen',
                             'returned_to_proposing_group',
                             'pre_accepted'
                             'accepted',
                             'accepted_but_modified',
                             'delayed',
                             'refused'],
             'label': 'testSuperObservers',
             'meeting_access_on': '',
             'meeting_states': [],
             'row_id': 'powerobservers'}])

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2019, 1, 1))
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()

        self.assertListEqual(  # item is not in a meeting so noMeetingMarker is expected
            [helper.print_meeting_date(), helper.print_meeting_date(noMeetingMarker='xxx')],
            ['-', 'xxx']
        )
        self.presentItem(item)

        self.changeUser('powerobserver1')
        # standard case, item in a meeting, no access restriction
        self.assertListEqual(
            [helper.print_meeting_date(), helper.print_meeting_date(returnDateTime=True)],
            ['1 january 2019', meeting.date]
        )
        # powerobserver1 can't see the meeting so noMeetingMarker is expected when unrestricted=False
        self.assertListEqual(
            [helper.print_meeting_date(unrestricted=False, noMeetingMarker=''),
             helper.print_meeting_date(returnDateTime=True, unrestricted=False, noMeetingMarker=None)],
            ['', None]
        )

    def test_pm_Print_preferred_meeting_date(self):
        cfg = self.meetingConfig
        cfg.setPowerObservers([
            {'item_access_on': '',
             'item_states': ['validated',
                             'presented',
                             'itemfrozen',
                             'returned_to_proposing_group',
                             'pre_accepted'
                             'accepted',
                             'accepted_but_modified',
                             'delayed',
                             'refused'],
             'label': 'testSuperObservers',
             'meeting_access_on': '',
             'meeting_states': [],
             'row_id': 'powerobservers'}])

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=datetime(2019, 1, 1))
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()

        self.assertListEqual(  # item has not preferred meeting so noMeetingMarker is expected
            [helper.print_preferred_meeting_date(), helper.print_preferred_meeting_date(noMeetingMarker='xxx')],
            ['-', 'xxx']
        )

        item.setPreferredMeeting(meeting.UID())
        self.assertListEqual(  # standard case, a preferred meeting date is expected
            [helper.print_preferred_meeting_date(), helper.print_preferred_meeting_date(returnDateTime=True)],
            ['1 january 2019', meeting.date]
        )

        self.changeUser('powerobserver1')
        self.assertListEqual(
            # powerobserver1 can't see the meeting so noMeetingMarker is expected when unrestricted=False
            [helper.print_preferred_meeting_date(unrestricted=False, noMeetingMarker=''),
             helper.print_preferred_meeting_date(returnDateTime=True, unrestricted=False, noMeetingMarker=None)],
            ['', None],
        )

    def test_pm_print_value(self):
        """Test the BaseDGHV.print_value that will print almost everything...
           For now, only working for DX elements (Meeting, MeetingAdvice)."""
        cfg = self.meetingConfig
        cfg.setPlaces('Place1\r\nPlace2\r\nPlace3\r\nSp\xc3\xa9cial place\r\n')
        self._enableField(
            ["convocation_date", "place", "notes", ],
            related_to='Meeting')
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2021, 5, 4))
        view = meeting.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        # Datetime
        self.assertEqual(helper.print_value("date"), u'4 may 2021')
        self.assertEqual(helper.print_value("date", target_language='fr'), u'4 mai 2021')
        self.assertEqual(helper.print_value("convocation_date"), u'')
        self.assertEqual(helper.print_value("convocation_date", empty_marker=u'???'), u'???')
        # RichText
        self.assertIsNone(meeting.observations)
        self.assertEqual(helper.print_value("observations"), u'')
        self.assertEqual(helper.print_value("observations", empty_marker=u'???'), u'???')
        text = '<p>Observations <img src="%s" alt="22-400x400.jpg" title="22-400x400.jpg"/>.</p>' \
            % self.external_image1
        set_field_from_ajax(meeting, "observations", text)
        image = meeting.objectValues()[0]
        img_path = image.getFile().blob._p_blob_committed
        # when using printXhtml, img url are turned to blob path
        text = text.replace(self.external_image1, img_path)
        self.assertEqual(helper.print_value("observations", use_appy_pod_preprocessor=True),
                         text)
        # raw_xhtml=True
        self.assertIn("resolveuid/%s" % image.UID(),
                      helper.print_value("observations", raw_xhtml=True))
        # Boolean
        self.assertFalse(meeting.extraordinary_session)
        self.assertEqual(helper.print_value("extraordinary_session"), u'No')
        meeting.extraordinary_session = None
        self.assertEqual(helper.print_value("extraordinary_session"), u'No')
        meeting.extraordinary_session = True
        self.assertEqual(helper.print_value("extraordinary_session"), u'Yes')
        # special case for place, default value is u"other"
        self.assertEqual(helper.print_value("place"), u'Other')
        meeting.place = u'Place1'
        self.assertEqual(helper.print_value("place"), u'Place1')
        meeting.place = PLACE_OTHER
        meeting.place_other = unicode('Spécial place', 'utf-8')
        self.assertEqual(helper.print_value("place"), u'Sp\xe9cial place')

    def test_pm_MeetingUpdateItemReferences(self):
        """Test call to @@update-item-references from the meeting that will update
           every references of items of a meeting."""
        cfg = self.meetingConfig
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=datetime(2017, 3, 3))
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.assertEqual(item.getItemReference(), 'Ref. 20170303/1')
        # change itemReferenceFormat
        # change itemReferenceFormat to include an item data (Title)
        cfg.setItemReferenceFormat(
            "python: here.getMeeting().date.strftime('%Y%m%d') + '/' + "
            "here.getItemNumber(for_display=True)")
        view = meeting.restrictedTraverse('@@update-item-references')
        view()
        self.assertEqual(item.getItemReference(), '20170303/1')

        # the view is not available to other users
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertRaises(Unauthorized,
                          meeting.restrictedTraverse,
                          '@@update-item-references')

    def test_pm_MeetingReorderItems(self):
        """Test call to @@reorder-items from the meeting that will reorder
           items based on configured MeetingConfig.insertingMethodsOnAddItem."""
        cfg = self.meetingConfig
        # setup
        # remove recurring items in self.meetingConfig
        self.changeUser('siteadmin')
        self._removeConfigObjectsFor(cfg)
        self._enableField('category')
        cfg.setInsertingMethodsOnAddItem((
            {'insertingMethod': 'on_list_type',
             'reverse': '0'},
            {'insertingMethod': 'on_categories',
             'reverse': '0'},
            {'insertingMethod': 'on_proposing_groups',
             'reverse': '0'},)
        )
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=datetime(2019, 1, 18))
        item1 = self.create('MeetingItem', proposingGroup=self.developers_uid, category='development')
        item2 = self.create('MeetingItem', proposingGroup=self.developers_uid, category='development')
        item3 = self.create('MeetingItem', proposingGroup=self.developers_uid, category='development')
        item4 = self.create('MeetingItem', proposingGroup=self.vendors_uid, category='development')
        item5 = self.create('MeetingItem', proposingGroup=self.developers_uid, category='research')
        item6 = self.create('MeetingItem', proposingGroup=self.vendors_uid, category='research')
        item7 = self.create('MeetingItem', proposingGroup=self.developers_uid, category='events')
        item8 = self.create('MeetingItem', proposingGroup=self.vendors_uid, category='events')
        right_ordered_items = [item1, item2, item3, item4, item5, item6, item7, item8]
        for item in right_ordered_items:
            self.presentItem(item)
        # present 2 late items
        self.freezeMeeting(meeting)
        meeting_uid = meeting.UID()
        item9 = self.create('MeetingItem', proposingGroup=self.developers_uid,
                            category='development', preferredMeeting=meeting_uid)
        item10 = self.create('MeetingItem', proposingGroup=self.vendors_uid,
                             category='events', preferredMeeting=meeting_uid)
        self.presentItem(item9)
        self.presentItem(item10)
        right_ordered_items.append(item9)
        right_ordered_items.append(item10)
        right_item_references = [
            'Ref. 20190118/1', 'Ref. 20190118/2', 'Ref. 20190118/3', 'Ref. 20190118/4', 'Ref. 20190118/5',
            'Ref. 20190118/6', 'Ref. 20190118/7', 'Ref. 20190118/8', 'Ref. 20190118/9', 'Ref. 20190118/10']
        self.assertEqual(right_ordered_items,
                         [item1, item2, item3, item4, item5, item6, item7, item8, item9, item10])
        self.assertEqual(meeting.get_items(ordered=True), right_ordered_items)
        self.assertEqual([item.getItemReference() for item in right_ordered_items], right_item_references)

        # change some items order using the @@change-item-order
        view = item1.restrictedTraverse('@@change-item-order')
        view('number', '6')
        view = item2.restrictedTraverse('@@change-item-order')
        view('number', '4')
        view = item7.restrictedTraverse('@@change-item-order')
        view('number', '1')
        view = item8.restrictedTraverse('@@change-item-order')
        view('number', '2')
        view = item10.restrictedTraverse('@@change-item-order')
        view('number', '7')
        mixed_items = meeting.get_items(ordered=True)
        self.assertEqual(mixed_items,
                         [item7, item8, item3, item4, item5, item2, item10, item6, item1, item9])
        # references are correct
        self.assertEqual([item.getItemReference() for item in mixed_items], right_item_references)
        # reorder items
        view = meeting.restrictedTraverse('@@reorder-items')
        view()
        # order and references are correct
        self.assertEqual(meeting.get_items(ordered=True), right_ordered_items)
        self.assertEqual([item.getItemReference() for item in right_ordered_items], right_item_references)

    def test_pm_DisplayGroupUsersView(self):
        """This view returns member of a group but not 'Not found' ones,
           aka users that were in groups and that were deleted, a special user
           'Not found' is left in the group."""
        self.changeUser('pmCreator1')
        view = self.portal.restrictedTraverse('@@display-group-users')
        group = api.group.get(self.developers_creators)
        group_id = group.getId()
        view(group_ids=[group_id])
        self.assertEqual(len(view.groups), 1)
        self.assertEqual(
            view._get_groups_and_members(group),
            [(0, api.user.get('pmCreator1')),
             (0, api.user.get('pmCreator1b')),
             (0, api.user.get('pmManager'))])
        # add a 'not found' user, will not be displayed
        self._make_not_found_user()
        self.assertEqual(
            view._get_groups_and_members(group),
            [(0, api.user.get('pmCreator1')),
             (0, api.user.get('pmCreator1b')),
             (0, api.user.get('pmManager'))])

    def _display_user_groups_sub_groups_false(self):
        return [(1, api.user.get('pmCreator1')),
                (1, api.user.get('pmCreator1b')),
                (1, api.user.get('pmManager')),
                (0, api.user.get('pmObserver1')),
                (0, api.user.get('pmReviewer1'))]

    def _display_user_groups_sub_groups_true(self):
        return [(1, api.group.get(self.developers_creators)),
                (2, api.user.get('pmCreator1')),
                (2, api.user.get('pmCreator1b')),
                (2, api.user.get('pmManager')),
                (0, api.user.get('pmManager')),
                (0, api.user.get('pmObserver1')),
                (0, api.user.get('pmReviewer1'))]

    def test_pm_DisplayGroupUsersViewGroupsInGroups(self):
        """Subgroups are displayed with contained members.
           Normal users see only members and Manager will also see the contained group.
           This is only relevant when using the recursive_groups PAS plugin."""
        # add group developers_creators to developers_observers
        self._addPrincipalToGroup(self.developers_creators, self.developers_observers)
        self.changeUser('pmCreator1')
        view = self.portal.restrictedTraverse('@@display-group-users')
        group = api.group.get(self.developers_observers)
        group_id = group.getId()
        view(group_ids=[group_id])
        self.assertEqual(len(view.groups), 1)
        # pmManager is in creators and observers but
        # with keep_subgroups=False, only one is kept
        self.assertListEqual(view._get_groups_and_members(group),
                             self._display_user_groups_sub_groups_false())
        # when displaying, sub groups may be displayed, this is the case for Managers
        # pmManager is in creators and observers and is dispayed 2 times
        self.assertEqual(view._get_groups_and_members(group, keep_subgroups=True),
                         self._display_user_groups_sub_groups_true())

    def test_pm_DisplayGroupUsersViewAllPloneGroups(self):
        """It is possible to get every Plone groups."""
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates(('itemcreated', ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', copyGroups=(self.vendors_reviewers, ))
        view = item.restrictedTraverse('@@display-group-users')
        # append a "*" to a org uid to get every Plone groups
        group_id = self.developers.UID() + '*'
        view(group_ids=group_id)
        self.assertTrue(len(view.groups) > 1)
        # only available to proposingGroup members
        self.changeUser('pmReviewer2')
        self.assertTrue(self.hasPermission(View, item))
        # calling view with '*' raises Unauthorized
        self.assertRaises(Unauthorized, view, group_ids=group_id)
        # but ok to get only one Plone group members
        self.assertTrue(view(group_ids=self.developers_creators))

    def test_pm_MeetingStoreItemsPodTemplateAsAnnexBatchActionForm_may_store(self):
        """By default only available if something defined in
           MeetingConfig.meetingItemTemplatesToStoreAsAnnex and user able to edit Meeting."""
        cfg = self.meetingConfig
        self.assertFalse(cfg.getMeetingItemTemplatesToStoreAsAnnex())
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        form = meeting.restrictedTraverse('@@store-items-template-as-annex-batch-action')
        self.assertTrue(self.hasPermission(ModifyPortalContent, meeting))
        self.assertFalse(form.available())
        self.assertRaises(Unauthorized, form)

        # configure MeetingConfig.meetingItemTemplatesToStoreAsAnnex
        # values are taking POD templates having a store_as_annex
        self.assertEqual(
            cfg.getField('meetingItemTemplatesToStoreAsAnnex').Vocabulary(cfg).keys(),
            [])
        annex_type_uid = cfg.annexes_types.item_decision_annexes.get('decision-annex').UID()
        cfg.podtemplates.itemTemplate.store_as_annex = annex_type_uid
        self.assertEqual(
            cfg.getField('meetingItemTemplatesToStoreAsAnnex').Vocabulary(cfg).keys(),
            ['itemTemplate__output_format__odt'])
        cfg.setMeetingItemTemplatesToStoreAsAnnex('itemTemplate__output_format__odt')
        form.update()
        self.assertTrue(form.available())

        # may_store is False if user not able to edit meeting
        self.changeUser('pmCreator1')
        self.assertFalse(self.hasPermission(ModifyPortalContent, meeting))
        self.assertFalse(form.available())

    def test_pm_MeetingStoreItemsPodTemplateAsAnnexBatchActionForm_handleApply(self):
        """This will store a POD template selected in
           MeetingConfig.meetingItemTemplatesToStoreAsAnnex as an annex
           for every selected items."""
        cfg = self.meetingConfig
        # define correct config
        annex_type_uid = cfg.annexes_types.item_decision_annexes.get('decision-annex').UID()
        cfg.podtemplates.itemTemplate.store_as_annex = annex_type_uid
        cfg.setMeetingItemTemplatesToStoreAsAnnex('itemTemplate__output_format__odt')

        # create meeting with items
        self.changeUser('pmManager')
        meeting = self._createMeetingWithItems()
        form = meeting.restrictedTraverse('@@store-items-template-as-annex-batch-action')

        # store annex for 3 first items
        first_3_item_uids = [item.UID for item in meeting.get_items(ordered=True, the_objects=False)[0:3]]
        self.request.form['form.widgets.uids'] = u','.join(first_3_item_uids)
        self.request.form['form.widgets.pod_template'] = 'itemTemplate__output_format__odt'
        form.update()
        form.handleApply(form, None)
        itemTemplateId = cfg.podtemplates.itemTemplate.getId()
        items = meeting.get_items(ordered=True)
        # 3 first item have the stored annex
        for i in range(0, 3):
            annexes = get_annexes(items[i])
            self.assertEqual(len(annexes), 1)
            self.assertTrue(annexes[0].used_pod_template_id, itemTemplateId)
        # but not the others
        for i in range(3, 6):
            annexes = get_annexes(items[i])
            self.assertFalse(annexes)

        # call again with next 3 uids
        form = meeting.restrictedTraverse('@@store-items-template-as-annex-batch-action')
        next_3_item_uids = [item.UID for item in meeting.get_items(ordered=True, the_objects=False)[3:6]]
        self.request.form['form.widgets.uids'] = u','.join(next_3_item_uids)
        form.brains = None
        form.update()
        form.handleApply(form, None)
        for i in range(0, 5):
            annexes = get_annexes(items[i])
            self.assertEqual(len(annexes), 1)
            self.assertTrue(annexes[0].used_pod_template_id, itemTemplateId)
        # last element does not have annex
        annexes = get_annexes(items[6])
        self.assertFalse(annexes)

        # call again, last is stored and it does not fail when no items left
        form = meeting.restrictedTraverse('@@store-items-template-as-annex-batch-action')
        last_item_uid = meeting.get_items(ordered=True, the_objects=False)[-1].UID
        self.request.form['form.widgets.uids'] = last_item_uid
        form.brains = None
        form.update()
        form.handleApply(form, None)
        for i in range(0, 6):
            annexes = get_annexes(items[i])
            self.assertEqual(len(annexes), 1)
            self.assertTrue(annexes[0].used_pod_template_id, itemTemplateId)

        # call a last time, when nothing to do, nothing is done
        form = meeting.restrictedTraverse('@@store-items-template-as-annex-batch-action')
        item_uids = [item.UID for item in meeting.get_items(ordered=True, the_objects=False)]
        self.request.form['form.widgets.uids'] = item_uids
        form.update()
        form.handleApply(form, None)
        for i in range(0, 6):
            annexes = get_annexes(items[i])
            self.assertEqual(len(annexes), 1)
            self.assertTrue(annexes[0].used_pod_template_id, itemTemplateId)

    def test_pm_PMTransitionBatchActionFormOnlyForOperationalRoles(self):
        """The PMTransitionBatchActionForm is only available to operational roles,
           so users like (restricted) power observers will not be able to use it."""
        # with operational roles
        self.changeUser('pmCreator1')
        pmFolder = self.getMeetingFolder()
        form = getMultiAdapter((pmFolder.searches_items, self.request), name=u'transition-batch-action')
        self.assertTrue(form.available())

        # without operational roles
        self.changeUser('powerobserver1')
        pmFolder = self.getMeetingFolder()
        form = getMultiAdapter((pmFolder.searches_items, self.request), name=u'transition-batch-action')
        self.assertFalse(form.available())

    def test_pm_PMTransitionBatchActionFormOnlyForMeetingManagersOnMeeting(self):
        """The PMTransitionBatchActionForm is only available to MeetingManagers on
           dashoboards of the meeting_view."""
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.freezeMeeting(meeting)
        # freeze the meeting so it is viewable in most workflows to various groups
        form = getMultiAdapter((meeting, self.request), name=u'transition-batch-action')
        self.assertTrue(form.available())
        # not available to others
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=(self._stateMappingFor('frozen', meta_type='Meeting'),))
        meeting.update_local_roles()
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(form.available())
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(form.available())
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(form.available())

    def test_pm_PMLabelsBatchActionForm(self):
        """Check labels change batch action."""
        cfg = self.meetingConfig
        cfg.setEnableLabels(True)
        cfg.setItemCopyGroupsStates(('itemcreated', ))
        self._enableField('copyGroups')

        # create some items
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        self.request.form['form.widgets.uids'] = ','.join([item1.UID(), item2.UID()])
        searches_items = self.getMeetingFolder().searches_items
        form = searches_items.restrictedTraverse('@@labels-batch-action')
        form.update()
        self.assertEqual(len(form.brains), 2)
        self.assertTrue(form.available())
        self.assertTrue(form._can_change_labels())
        # when an item is no more editable, labels are no more batch editable
        self.proposeItem(item1)
        self.assertTrue(form.available())
        self.assertFalse(form._can_change_labels())
        # except when MeetingConfig.itemLabelsEditableByProposingGroupForever is True
        cfg.setItemLabelsEditableByProposingGroupForever(True)
        self.assertTrue(form.available())
        self.assertTrue(form._can_change_labels())
        # but not with an item of another group
        self.changeUser('pmCreator2')
        item3 = self.create('MeetingItem', copyGroups=[self.developers_creators])
        self.changeUser('pmCreator1')
        self.request.form['form.widgets.uids'] = ','.join([item1.UID(), item2.UID(), item3.UID()])
        form = searches_items.restrictedTraverse('@@labels-batch-action')
        form.update()
        self.assertEqual(len(form.brains), 3)
        self.assertTrue(form.available())
        self.assertFalse(form._can_change_labels())

    def test_pm_UpdateLocalRolesBatchActionForm(self):
        """This will call update_local_roles on selected elements."""
        cfg = self.meetingConfig
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self._setPowerObserverStates(states=())
        powerobservers = '{0}_powerobservers'.format(cfg.getId())

        # create some items
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item3 = self.create('MeetingItem')
        self.request.form['form.widgets.uids'] = ','.join([item1.UID(), item3.UID()])
        searches_items = self.getMeetingFolder().searches_items
        # not available as not Manager
        self.assertRaises(Unauthorized,
                          searches_items.restrictedTraverse,
                          '@@update-local-roles-batch-action')
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-local-roles-batch-action').available())

        # as Manager
        self.changeUser('siteadmin')
        self.assertFalse(powerobservers in item1.__ac_local_roles__)
        self.assertFalse(powerobservers in item2.__ac_local_roles__)
        self.assertFalse(powerobservers in item3.__ac_local_roles__)
        self._setPowerObserverStates(states=(self._stateMappingFor('itemcreated'),))
        searches_items = self.getMeetingFolder().searches_items
        form = searches_items.restrictedTraverse('@@update-local-roles-batch-action')
        self.assertTrue(form.available())
        form.update()
        form.handleApply(form, None)
        self.assertTrue(powerobservers in item1.__ac_local_roles__)
        self.assertFalse(powerobservers in item2.__ac_local_roles__)
        self.assertTrue(powerobservers in item3.__ac_local_roles__)

        # also available for meetings
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # not available as not Manager
        searches_decisions = self.getMeetingFolder().searches_decisions
        self.assertRaises(Unauthorized,
                          searches_decisions.restrictedTraverse,
                          '@@update-local-roles-batch-action')
        self.assertFalse(searches_decisions.unrestrictedTraverse(
            '@@update-local-roles-batch-action').available())
        # as Manager
        self.changeUser('siteadmin')
        self.assertFalse(powerobservers in meeting.__ac_local_roles__)
        self._setPowerObserverStates(field_name='meeting_states', states=('created',))
        searches_decisions = self.getMeetingFolder().searches_decisions
        self.request.form['form.widgets.uids'] = unicode(meeting.UID())
        form = searches_decisions.restrictedTraverse('@@update-local-roles-batch-action')
        self.assertTrue(form.available())
        form.update()
        form.handleApply(form, None)
        self.assertTrue(powerobservers in meeting.__ac_local_roles__)

    def test_pm_UpdateGroupsInChargeBatchActionForm(self):
        """This will update groupsInCharge for selected items."""
        cfg = self.meetingConfig
        cfg.setItemGroupsInChargeStates(('itemcreated', ))
        # not available when not using groupsInCharge
        self.changeUser('pmCreator1')
        searches_items = self.getMeetingFolder().searches_items
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-groups-in-charge-batch-action').available())
        # enable groupsInCharge
        self._enableField('groupsInCharge')
        self.assertTrue(searches_items.unrestrictedTraverse(
            '@@update-groups-in-charge-batch-action').available())

        # not available to non operational users
        self.changeUser('powerobserver1')
        searches_items = self.getMeetingFolder().searches_items
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-groups-in-charge-batch-action').available())

        # create some items
        self.changeUser('pmCreator1')
        searches_items = self.getMeetingFolder().searches_items
        item1 = self.create('MeetingItem', groupsInCharge=[self.developers_uid])
        item1_uid = item1.UID()
        item2 = self.create('MeetingItem', groupsInCharge=[self.vendors_uid])
        item2_uid = item2.UID()
        item3 = self.create('MeetingItem', groupsInCharge=[self.developers_uid, self.vendors_uid])
        item3_uid = item3.UID()
        self.request.form['form.widgets.uids'] = ','.join([item1_uid, item2_uid, item3_uid])
        form = searches_items.restrictedTraverse('@@update-groups-in-charge-batch-action')
        form.update()
        # values are ordered
        self.assertEqual(
            [term.value for term in form.widgets['added_values'].terms.terms._terms],
            [self.developers_uid, self.vendors_uid])

        # add vendors
        # for now item1 not found in catalog
        self.assertFalse(self.catalog(getGroupsInCharge=self.vendors_uid, UID=item1_uid))
        self.request['form.widgets.action_choice'] = 'add'
        self.request['form.widgets.added_values'] = [self.vendors_uid]
        # local_roles not set
        self.assertFalse(self.vendors_observers in item1.__ac_local_roles__)
        form.handleApply(form, None)
        # was added
        self.assertEqual(item1.getGroupsInCharge(), [self.developers_uid, self.vendors_uid])
        # local_roles are set
        self.assertTrue(self.vendors_observers in item1.__ac_local_roles__)
        # already selected, not changed
        self.assertEqual(item2.getGroupsInCharge(), [self.vendors_uid])
        self.assertEqual(item3.getGroupsInCharge(), [self.developers_uid, self.vendors_uid])
        # adapted elements were reindexed
        self.assertTrue(self.catalog(getGroupsInCharge=self.vendors_uid, UID=item1_uid))

        # add developers
        self.request['form.widgets.action_choice'] = 'add'
        self.request['form.widgets.added_values'] = [self.developers_uid]
        form = searches_items.restrictedTraverse('@@update-groups-in-charge-batch-action')
        form.update()
        form.handleApply(form, None)
        # was added as first value, order is respected
        self.assertEqual(item2.getGroupsInCharge(), [self.developers_uid, self.vendors_uid])
        # already selected, not changed
        self.assertEqual(item1.getGroupsInCharge(), [self.developers_uid, self.vendors_uid])
        self.assertEqual(item3.getGroupsInCharge(), [self.developers_uid, self.vendors_uid])

        # remove vendors
        self.request['form.widgets.action_choice'] = 'remove'
        self.request['form.widgets.removed_values'] = [self.vendors_uid]
        form = searches_items.restrictedTraverse('@@update-groups-in-charge-batch-action')
        form.update()
        form.handleApply(form, None)
        # was removed for the 3 items
        self.assertEqual(item1.getGroupsInCharge(), [self.developers_uid])
        self.assertEqual(item2.getGroupsInCharge(), [self.developers_uid])
        self.assertEqual(item3.getGroupsInCharge(), [self.developers_uid])
        # local_roles removed
        self.assertFalse(self.vendors_observers in item1.__ac_local_roles__)

        # when using auto groups in charge from proposing group or category
        # action is displayed to MeetingManagers
        cfg2 = self.meetingConfig2
        searches_items = self.getMeetingFolder(cfg2).searches_items
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-groups-in-charge-batch-action').available())
        self.changeUser('pmManager')
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-groups-in-charge-batch-action').available())
        cfg2.setIncludeGroupsInChargeDefinedOnCategory(True)
        self.assertTrue(searches_items.unrestrictedTraverse(
            '@@update-groups-in-charge-batch-action').available())

    def test_pm_UpdateCopyGroupsBatchActionForm(self):
        """This will update copyGroups for selected items."""
        cfg = self.meetingConfig
        cfg.setItemCopyGroupsStates(('itemcreated', ))
        # not available when not using copyGroups
        self.changeUser('pmCreator1')
        searches_items = self.getMeetingFolder().searches_items
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-copy-groups-batch-action').available())
        # enable copyGroups
        self._enableField('copyGroups')
        self.assertTrue(searches_items.unrestrictedTraverse(
            '@@update-copy-groups-batch-action').available())

        # not available to non operational users
        self.changeUser('powerobserver1')
        searches_items = self.getMeetingFolder().searches_items
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-copy-groups-batch-action').available())

        # create 2 items
        self.changeUser('pmCreator1')
        searches_items = self.getMeetingFolder().searches_items
        item1 = self.create('MeetingItem', copyGroups=[self.developers_reviewers])
        item1_uid = item1.UID()
        item2 = self.create('MeetingItem', copyGroups=[self.vendors_reviewers])
        item2_uid = item2.UID()
        self.request.form['form.widgets.uids'] = ','.join([item1_uid, item2_uid])
        form = searches_items.restrictedTraverse('@@update-copy-groups-batch-action')
        form.update()
        # values are ordered
        self.assertEqual(
            [term.value for term in form.widgets['added_values'].terms.terms._terms],
            [self.developers_reviewers, self.vendors_reviewers])

        # add vendors
        # for now item1 not found in catalog
        self.assertFalse(self.catalog(getCopyGroups=self.vendors_uid, UID=item1_uid))
        self.request['form.widgets.action_choice'] = 'add'
        self.request['form.widgets.added_values'] = [self.vendors_reviewers]
        # local_roles not set
        self.assertFalse(self.vendors_reviewers in item1.__ac_local_roles__)
        form.handleApply(form, None)
        # was added
        self.assertEqual(item1.getCopyGroups(), (self.developers_reviewers, self.vendors_reviewers))
        # local_roles are set
        self.assertTrue(self.vendors_reviewers in item1.__ac_local_roles__)
        # already selected, not changed
        self.assertEqual(item2.getCopyGroups(), (self.vendors_reviewers, ))
        # adapted elements were reindexed
        self.assertTrue(self.catalog(getCopyGroups=self.vendors_reviewers, UID=item1_uid))

    def test_pm_UpdateCommitteesBatchActionForm(self):
        """This will update copyGroups for selected items."""
        cfg = self.meetingConfig
        cfg_id = cfg.getId()
        self._enableField("committees", related_to="Meeting")
        cfg_committees = cfg.getCommittees()
        com1_id = cfg_committees[0]['row_id']
        com2_id = cfg_committees[1]['row_id']
        com3_id = cfg_committees[2]['row_id']
        # enable_editors
        cfg_committees[0]['enable_editors'] = "1"
        cfg_committees[1]['enable_editors'] = "1"
        cfg_committees[2]['enable_editors'] = "1"
        cfg.setItemCommitteesStates(['itemcreated'])
        com1_editors_group_id = "%s_%s" % (cfg_id, com1_id)
        com2_editors_group_id = "%s_%s" % (cfg_id, com2_id)
        com3_editors_group_id = "%s_%s" % (cfg_id, com3_id)
        # only available to MeetingManagers
        self.changeUser('pmCreator1')
        searches_items = self.getMeetingFolder().searches_items
        self.assertFalse(searches_items.unrestrictedTraverse(
            '@@update-committees-batch-action').available())
        self.changeUser('pmManager')
        searches_items = self.getMeetingFolder().searches_items
        self.assertTrue(searches_items.unrestrictedTraverse(
            '@@update-committees-batch-action').available())
        # create 3 items
        item1 = self.create('MeetingItem', committees=[com1_id])
        self.assertTrue(com1_editors_group_id in item1.__ac_local_roles__)
        item1_uid = item1.UID()
        item2 = self.create('MeetingItem', committees=[com2_id])
        self.assertTrue(com2_editors_group_id in item2.__ac_local_roles__)
        item2_uid = item2.UID()
        item3 = self.create('MeetingItem', committees=[NO_COMMITTEE])
        item3_uid = item3.UID()
        self.request.form['form.widgets.uids'] = ','.join([item1_uid, item2_uid, item3_uid])
        form = searches_items.restrictedTraverse('@@update-committees-batch-action')
        form.update()
        # try to add NO_COMMITTEE, nothing changed as can not be selected in addition with another
        self.request['form.widgets.action_choice'] = 'add'
        self.request['form.widgets.added_values'] = [NO_COMMITTEE]
        form.handleApply(form, None)
        self.assertEqual(item1.getCommittees(), (com1_id, ))
        self.assertEqual(item2.getCommittees(), (com2_id, ))
        self.assertEqual(item3.getCommittees(), (NO_COMMITTEE, ))
        # add com3_id, will be added in addition to com1_id and com2_id
        # but not NO_COMMITTEE that must be alone
        self.assertFalse(com3_editors_group_id in item1.__ac_local_roles__)
        self.assertFalse(com3_editors_group_id in item2.__ac_local_roles__)
        self.assertFalse(com3_editors_group_id in item3.__ac_local_roles__)
        self.request['form.widgets.added_values'] = [com3_id]
        form.handleApply(form, None)
        self.assertEqual(item1.getCommittees(), (com1_id, com3_id))
        self.assertEqual(item2.getCommittees(), (com2_id, com3_id))
        self.assertEqual(item3.getCommittees(), (NO_COMMITTEE, ))
        self.assertTrue(com3_editors_group_id in item1.__ac_local_roles__)
        self.assertTrue(com3_editors_group_id in item2.__ac_local_roles__)
        self.assertFalse(com3_editors_group_id in item3.__ac_local_roles__)
        # required so last value can not be removed
        self.request['form.widgets.action_choice'] = 'remove'
        self.request['form.widgets.added_values'] = [NO_COMMITTEE]
        form.handleApply(form, None)
        self.assertEqual(item3.getCommittees(), (NO_COMMITTEE, ))
        # remove com1_id
        self.request['form.widgets.removed_values'] = [com1_id]
        form.handleApply(form, None)
        self.assertEqual(item1.getCommittees(), (com3_id, ))
        self.assertFalse(com1_editors_group_id in item1.__ac_local_roles__)
        self.assertFalse(com2_editors_group_id in item1.__ac_local_roles__)
        self.assertTrue(com3_editors_group_id in item1.__ac_local_roles__)

    def test_pm_DownloadAnnexesActionForm(self):
        """This batch action will download annexes as a zip file."""
        cfg = self.meetingConfig
        cfg.setEnabledAnnexesBatchActions([])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)
        self.request['form.widgets.uids'] = u','.join([annex1.UID(), annex2.UID()])
        self.request.form['form.widgets.uids'] = self.request['form.widgets.uids']
        self.request.form['ajax_load'] = 'dummy'

        # available when activated
        form = item.restrictedTraverse('@@download-annexes-batch-action')
        self.assertRaises(Unauthorized, form)
        self.assertFalse(form.available())
        cfg.setEnabledAnnexesBatchActions(['download-annexes'])
        form.update()
        self.assertTrue(form.available())
        data = form.handleApply(form, None)
        # headers are set
        self.assertEqual(self.request.response.getHeader('content-type'), 'application/zip')
        self.assertEqual(self.request.response.getHeader('content-disposition'),
                         'attachment;filename=o1.zip')
        # we received a Zip file
        m = magic.Magic()
        self.assertTrue(m.from_buffer(data).startswith('Zip archive data, at least v2.0 to extract'))
        # annexes without a filename are ignored
        annex1.file.filename = None
        annex2.file.filename = None
        data = form.handleApply(form, None)
        self.assertEqual(m.from_buffer(data), 'Zip archive data (empty)')

    def test_pm_DeleteAnnexesActionForm(self):
        """This batch action will delete annexes."""
        cfg = self.meetingConfig
        cfg.setEnabledAnnexesBatchActions([])
        self._deactivate_wfas(['only_creator_may_delete'])
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)
        # annex without a file name does not break
        annex2.file.filename = None
        self.request['form.widgets.uids'] = u','.join([annex1.UID(), annex2.UID()])
        self.request.form['form.widgets.uids'] = self.request['form.widgets.uids']
        self.request.form['ajax_load'] = 'dummy'

        # available when activated
        form = item.restrictedTraverse('@@delete-batch-action')
        self.assertRaises(Unauthorized, form)
        self.assertFalse(form.available())
        cfg.setEnabledAnnexesBatchActions(['delete'])
        form.update()
        self.assertTrue(form.available())
        # action not avilable when not able to edit item
        self.changeUser('pmObserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(form.available())
        # proceed, this will delete annexes
        self.changeUser('pmCreator1')
        form.update()
        self.assertEqual(get_annexes(item), [annex1, annex2])
        form.handleApply(form, None)
        self.assertEqual(get_annexes(item), [])

        # pmManager trying to delete an annex on a presented item
        self.changeUser('pmCreator2')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        self.validateItem(item)
        self.changeUser('pmManager')
        self.create('Meeting')
        form = item.restrictedTraverse('@@delete-batch-action')
        self.request['form.widgets.uids'] = u'{0}'.format(annex.UID())
        self.request.form['form.widgets.uids'] = self.request['form.widgets.uids']
        form.update()
        self.assertEqual(get_annexes(item), [annex])
        form.handleApply(form, None)
        self.assertEqual(get_annexes(item), [])

    def test_pm_DownloadAnnexesBatchActionForm(self):
        """Batch action to download annexes of a given annex_type for selected elements."""
        self.changeUser('pmCreator1')
        item1 = self.create('MeetingItem')
        # only PDF annexes will be considered, we have 2 PDF of 1 page each
        annex = self.addAnnex(item1, annexFile=self.annexFilePDF)
        self.addAnnex(item1)
        self.addAnnex(item1, annexType='overhead-analysis')
        item2 = self.create('MeetingItem')
        self.addAnnex(item2, annexFile=self.annexFilePDF)
        self.addAnnex(item2, annexType='overhead-analysis')
        self.request.form['form.widgets.uids'] = ','.join([item1.UID(), item2.UID()])
        searches_items = self.getMeetingFolder().searches_items
        # not available as not MeetingManager
        form = searches_items.unrestrictedTraverse('@@concatenate-annexes-batch-action')
        self.assertRaises(Unauthorized, form)
        # as MeetingManager
        self.changeUser('pmManager')
        searches_items = self.getMeetingFolder().searches_items
        form = searches_items.unrestrictedTraverse('@@concatenate-annexes-batch-action')
        self.request['form.widgets.annex_types'] = [
            item1.categorized_elements[annex.UID()]['category_uid']]
        self.assertFalse(self.request.get('pdf_file_content'))
        self.assertTrue(form())
        form.handleApply(form, None)
        self.assertTrue('Pages\n/Count 2' in self.request.get('pdf_file_content').getvalue())
        # when using two_sided, a blank page is inserted
        self.request['form.widgets.two_sided'] = 'true'
        form.handleApply(form, None)
        self.assertTrue('Pages\n/Count 3' in self.request.get('pdf_file_content').getvalue())

    def test_pm_ftw_labels_viewlet_available(self):
        """Only available on items if enabled in MeetingConfig."""
        cfg = self.meetingConfig
        self.assertFalse(cfg.getEnableLabels())
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        viewlet = self._get_viewlet(
            context=item, manager_name='plone.belowcontenttitle', viewlet_name='ftw.labels.labeling')
        self.assertFalse(viewlet.available)

        # get the labeljar, that is actually the MeetingConfig
        labeljar = getAdapter(item, ILabelJar)
        self.assertEqual(labeljar.context, cfg)
        # remove default labels
        labeljar.storage.clear()
        self.assertEqual(labeljar.list(), [])
        # enableLabels
        cfg.setEnableLabels(True)
        # still not available as no labels defined
        self.assertFalse(viewlet.available)
        labeljar.add('Label', 'green', False)
        self.assertTrue(viewlet.available)

    def _enable_ftw_labels(self):
        cfg = self.meetingConfig
        cfg.setEnableLabels(True)
        self.changeUser('pmCreator1')
        labeljar = getAdapter(cfg, ILabelJar)
        labeljar.add('Label1', 'green', False)
        labeljar.add('Label2', 'red', False)
        return labeljar

    def test_pm_ftw_labels_viewlet_can_edit(self):
        """can_edit when user has Modify portal content permission."""
        # enable viewlet
        self._enable_ftw_labels()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', decision=self.decisionText)
        viewlet = self._get_viewlet(
            context=item,
            manager_name='plone.belowcontenttitle',
            viewlet_name='ftw.labels.labeling')
        self.assertTrue(viewlet.available)

        # can_edit
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(viewlet.can_edit)
        # propose so no more editable
        self.validateItem(item)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(viewlet.can_edit)
        # enable MeetingConfig.itemLabelsEditableByProposingGroupForever
        self.meetingConfig.setItemLabelsEditableByProposingGroupForever(True)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(viewlet.can_edit)

        # MeetingManagers may edit labels even when item decided
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.closeMeeting(meeting)
        self.assertEqual(item.query_state(), 'accepted')
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(viewlet.can_edit)
        # proposing group editors may still edit labels
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(viewlet.can_edit)
        # but not proposing group other roles
        self.changeUser('pmObserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertFalse(viewlet.can_edit)

    def test_pm_ftw_labels_labeling_update_protected(self):
        """Make sure the @@labeling/update method is correctly protected.
           Indeed, a scenario where an item is labelled then ModifyPortalContent is lost
           because state changed, make sure if a browser screen was not updated, labeling
           update raises Unauthorized."""
        self._enable_ftw_labels()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('@@labeling')
        labeling = ILabeling(item)
        self.assertEqual(labeling.storage, {})
        self.request.form['activate_labels'] = ['label1']
        view.update()
        self.assertTrue('label1' in labeling.storage)

        # propose item, view is not more available
        self.proposeItem(item)
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@labeling').update)

    def test_pm_TopLevelTabs(self):
        """The CatalogNavigationTabs.topLevelTabs is overrided to manage groupConfigs."""
        # configure configGroups, 2 configGroups, one will contain meetingConfig
        # the other is empty, and meetingConfig2 is not in a configGroup
        self.tool.setConfigGroups(
            ({'label': 'ConfigGroup1', 'row_id': 'unique_id_1'},)
        )
        cfg = self.meetingConfig
        cfg2Id = self.meetingConfig2.getId()
        cfg.setConfigGroup('unique_id_1')
        # does not break as anonymous
        logout()
        view = getMultiAdapter((self.portal, self.request), name='portal_tabs_view')
        self.assertEqual(len(view.topLevelTabs()), 1)
        self.assertEqual(view.topLevelTabs()[0]['id'], 'index_html')

        # user having access to every configs
        self.changeUser('pmCreator1')
        # index_html + active MeetingConfigs
        active_configs = self.tool.getActiveConfigs()
        self.assertEqual(len(view.topLevelTabs()), 1 + len(active_configs))
        self.assertEqual(view.topLevelTabs()[0]['id'], 'index_html')
        self.assertEqual(view.topLevelTabs()[1]['id'], 'mc_config_group_unique_id_1')
        self.assertEqual(view.topLevelTabs()[2]['id'], 'mc_{0}'.format(cfg2Id))

        # user having access only to cfg, it gets the configGroup
        self.changeUser('powerobserver1')
        self.assertEqual(len(view.topLevelTabs()), 2)
        self.assertEqual(view.topLevelTabs()[0]['id'], 'index_html')
        self.assertEqual(view.topLevelTabs()[1]['id'], 'mc_config_group_unique_id_1')

        # user having access only to cfg2 will not get configGroup
        self.changeUser('restrictedpowerobserver2')
        self.assertEqual(len(view.topLevelTabs()), 2)
        self.assertEqual(view.topLevelTabs()[0]['id'], 'index_html')
        self.assertEqual(view.topLevelTabs()[1]['id'], 'mc_{0}'.format(cfg2Id))

    def test_pm_TopLevelTabsMCInsertedBeforeCustomTabs(self):
        """MC related tabs are inserted between 'index_html' tab and eventual extra custom tabs."""
        extra_tab = Action('extra_tab', title='Extra tab', visible=True)
        self.portal.portal_actions.portal_tabs._setObject('extra_tab', extra_tab)
        self.changeUser('pmCreator1')
        view = getMultiAdapter((self.portal, self.request), name='portal_tabs_view')
        active_config_ids = ['mc_{0}'.format(cfg.getId()) for cfg in self.tool.getActiveConfigs()]
        self.assertEqual(
            [tab['id'] for tab in view.topLevelTabs()],
            ['index_html'] + active_config_ids + ['extra_tab'])

    def test_pm_SelectedTabs(self):
        """The GlobalSectionsViewlet.selectedTabs is overrided to manage groupConfigs."""
        # configure configGroups, 2 configGroups, one will contain meetingConfig
        # the other is empty, and meetingConfig2 is not in a configGroup
        self.tool.setConfigGroups(
            ({'label': 'ConfigGroup1', 'row_id': 'unique_id_1'},)
        )
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = self.meetingConfig2.getId()
        cfg.setConfigGroup('unique_id_1')

        # does not break as anonymous
        logout()
        viewlet = self._get_viewlet(
            context=self.portal,
            manager_name='plone.portalheader',
            viewlet_name='plone.global_sections')
        viewlet.update()
        self.assertEqual(viewlet.selected_portal_tab, 'index_html')

        # as user able to access every cfg, default is the groupedConfig
        # use default MC url as current 'URL'
        self.changeUser('pmCreator1')
        viewlet_context = self.getMeetingFolder()
        viewlet = self._get_viewlet(
            context=viewlet_context,
            manager_name='plone.portalheader',
            viewlet_name='plone.global_sections')
        redirect_to_app = getMultiAdapter(
            (self.portal, self.request),
            name='plonemeeting_redirect_to_app_view')
        self.request['URL'] = redirect_to_app()
        viewlet.update()
        self.assertEqual(viewlet.selected_portal_tab, 'mc_config_group_unique_id_1')

        # now with cfg2 out of configGroups
        self.setMeetingConfig(cfg2Id)
        viewlet_context = self.getMeetingFolder()
        viewlet = self._get_viewlet(
            context=viewlet_context,
            manager_name='plone.portalheader',
            viewlet_name='plone.global_sections')
        cfg2.setIsDefault(True)
        cfg2.updateIsDefaultFields()
        self.request['URL'] = redirect_to_app()
        viewlet.update()
        self.assertEqual(viewlet.selected_portal_tab, 'mc_{0}'.format(cfg2Id))

        # now in the configuration
        # of cfg1 in a configGroup
        self.changeUser('pmManager')
        # when accessing http.../meeting-config-id, request URL contains
        # http.../meeting-config-id/base_view
        self.request['URL'] = cfg.absolute_url() + '/' + cfg.getLayout()
        viewlet = self._get_viewlet(
            context=cfg,
            manager_name='plone.portalheader',
            viewlet_name='plone.global_sections')
        viewlet.update()
        self.assertEqual(viewlet.selected_portal_tab, 'mc_config_group_unique_id_1')
        # cfg2 out of configGroups
        self.request['URL'] = cfg2.absolute_url()
        viewlet = self._get_viewlet(
            context=cfg2,
            manager_name='plone.portalheader',
            viewlet_name='plone.global_sections')
        viewlet.update()
        self.assertEqual(viewlet.selected_portal_tab, 'mc_{0}'.format(cfg2Id))

    def _setUpDashBoard(self):
        """ """
        # create a folder2 that will be displayed in the dashboard
        self.changeUser('pmManager')
        self.meeting = self._createMeetingWithItems()
        view = self.getMeetingFolder().restrictedTraverse('@@document-generation')
        self.helper = view.get_generation_context_helper()

    def test_pm_get_all_items_dghv(self):
        self._setUpDashBoard()
        brains = self.catalog(meta_type="MeetingItem")
        result = self.helper.get_all_items_dghv(brains)
        itemList = [brain.getObject() for brain in brains]
        self.assertListEqual(itemList, [view.real_context for view in result])

    def test_pm_get_all_items_dghv_with_advice(self):
        cfg = self.meetingConfig

        def compute_data(item, advisorUids=None):
            brains = self.catalog(meta_type="MeetingItem")
            result = self.helper.get_all_items_dghv_with_advice(brains, advisorUids)
            itemList = [brain.getObject() for brain in brains]
            index = itemList.index(item)
            return result, itemList, index

        def assert_results(item, advisorUids=None, advisorIdsToBeReturned=[], occurenceOfItem=1):
            result, itemList, index = compute_data(item, advisorUids)
            if occurenceOfItem == 1:
                self.assertListEqual(itemList, [itemRes['itemView'].real_context for itemRes in result])
            else:
                itemList = [itemRes['itemView'].real_context for itemRes in result]
                self.assertEqual(occurenceOfItem, itemList.count(item))
            if advisorIdsToBeReturned:
                for advisor in advisorIdsToBeReturned:
                    self.assertEqual(result.pop(index)['advice'], item.getAdviceDataFor(item, advisor))
                    index = itemList.index(item)
            else:
                self.assertIsNone(result[index]['advice'])

        self._setUpDashBoard()
        brains = self.catalog(meta_type="MeetingItem")
        result = self.helper.get_all_items_dghv_with_advice(brains)
        itemList = [brain.getObject() for brain in brains]
        self.assertListEqual(itemList, [itemRes['itemView'].real_context for itemRes in result])

        cfg.setCustomAdvisers(
            [{'row_id': 'unique_id_123',
              'org': self.developers_uid,
              'gives_auto_advice_on': '',
              'for_item_created_from': '2016/08/08',
              'delay': '5',
              'delay_label': ''}, ])
        cfg.setPowerAdvisersGroups((self.vendors_uid,))
        self._setPowerObserverStates(states=('itemcreated',))
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'),))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'),))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'),))
        notify(ObjectEditedEvent(cfg))

        item = self.create('MeetingItem')
        item._update_after_edit()

        assert_results(item)
        assert_results(item, [self.vendors_uid])
        assert_results(item, [self.developers_uid])

        item.setOptionalAdvisers(('{0}__rowid__unique_id_123'.format(self.developers_uid),))
        item._update_after_edit()

        # test with 1 not given advice
        assert_results(item, advisorIdsToBeReturned=[self.developers_uid])
        assert_results(item, [self.vendors_uid])
        assert_results(item, [self.developers_uid], [self.developers_uid])

        # test with 1 given advice
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': richtextval(u'My comment')})
        self.changeUser('pmManager')
        assert_results(item, advisorIdsToBeReturned=[self.developers_uid])
        assert_results(item, [self.vendors_uid])
        assert_results(item, [self.developers_uid], [self.developers_uid])

        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'negative',
                                    'advice_comment': richtextval(u'My comment')})

        self.changeUser('pmManager')
        assert_results(item,
                       advisorIdsToBeReturned=[self.developers_uid, self.vendors_uid],
                       occurenceOfItem=2)
        assert_results(item,
                       [self.vendors_uid], [self.vendors_uid])
        assert_results(item,
                       [self.developers_uid], [self.developers_uid])

    def test_pm_goto_object(self):
        """Test the item navigation widget."""
        cfg = self.meetingConfig
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        cfg.setRestrictAccessToSecretItems(True)
        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=('presented',))
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                           'reverse': '0'},))
        # create 2 'public' items and 1 'secret' item
        self.changeUser('pmManager')
        publicItem1 = self.create('MeetingItem')
        publicItem2 = self.create('MeetingItem')
        secretItem1 = self.create('MeetingItem')
        secretItem1.setPrivacy('secret')
        secretItem1.reindexObject()
        secretItem2 = self.create('MeetingItem')
        secretItem2.setPrivacy('secret')
        secretItem2.reindexObject()
        secretItem3 = self.create('MeetingItem')
        secretItem3.setPrivacy('secret')
        secretItem3.reindexObject()
        # create meeting and present items
        meeting = self.create('Meeting')
        self.presentItem(secretItem1)
        self.presentItem(publicItem1)
        self.presentItem(secretItem2)
        self.presentItem(publicItem2)
        self.presentItem(secretItem3)
        self.assertEqual(
            meeting.get_items(ordered=True),
            [secretItem1, publicItem1, secretItem2, publicItem2, secretItem3])

        self.changeUser('restrictedpowerobserver1')
        # go on first item and navigate to following items
        # getSiblingItem is not taking care of isPrivacyViewable, but the object_goto view does
        self.assertEqual(publicItem1.getSiblingItem('first'), secretItem1.getItemNumber())
        self.assertEqual(publicItem1.getSiblingItem('next'), secretItem2.getItemNumber())

        # the object_goto view is taking care of not sending a user where he does not have access
        # user does not have access to secretItem so even if getSiblingItem returns it
        # the view will send user to the next viewable item
        self.assertFalse(secretItem1.isPrivacyViewable())
        self.assertFalse(secretItem2.isPrivacyViewable())
        self.assertFalse(secretItem3.isPrivacyViewable())
        self.assertEqual(publicItem1.getSiblingItem('last'), secretItem3.getItemNumber())
        view = publicItem1.restrictedTraverse('@@object_goto')
        # first, next and last items are not accessible (not privacy viewable)
        self.assertEqual(view('next'), publicItem2.absolute_url())
        self.assertEqual(view('previous'), view.context.absolute_url())
        self.assertEqual(view('first'), view.context.absolute_url())
        self.assertEqual(view('last'), publicItem2.absolute_url())

        # do secret items accessible
        secretItem1.setPrivacy('public')
        secretItem1.reindexObject()
        secretItem2.setPrivacy('public')
        secretItem2.reindexObject()
        secretItem3.setPrivacy('public')
        secretItem3.reindexObject()
        # MeetingItem.isPrivacyViewable is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.assertEqual(view('next'), secretItem2.absolute_url())
        self.assertEqual(view('previous'), secretItem1.absolute_url())
        self.assertEqual(view('first'), secretItem1.absolute_url())
        self.assertEqual(view('last'), secretItem3.absolute_url())

    def test_pm_goto_object_meeting(self):
        """Test the item navigation widget when way='meeting'."""
        cfg = self.meetingConfig
        cfg.setMaxShownMeetingItems(2)
        self._removeConfigObjectsFor(cfg)
        cfg.setInsertingMethodsOnAddItem(({'insertingMethod': 'at_the_end',
                                           'reverse': '0'},))
        # create a meeting with 6 items and display
        # items presented on meeting by batch of 2
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item3 = self.create('MeetingItem')
        item4 = self.create('MeetingItem')
        item5 = self.create('MeetingItem')
        item6 = self.create('MeetingItem')
        meeting = self.create('Meeting')
        meeting_url = meeting.absolute_url()
        self.presentItem(item1)
        self.presentItem(item2)
        self.presentItem(item3)
        self.presentItem(item4)
        self.presentItem(item5)
        self.presentItem(item6)
        # from item1, page 1 of meeting
        self.assertEqual(item1.getItemNumber(), 100)
        view = item1.restrictedTraverse('@@object_goto')
        view(itemNumber=None, way='meeting')
        self.assertEqual(self.request.response.getHeader('location'),
                         "{0}?custom_b_start=0".format(meeting_url))
        # from item2, page 1 of meeting
        self.assertEqual(item2.getItemNumber(), 200)
        view = item2.restrictedTraverse('@@object_goto')
        view(itemNumber=None, way='meeting')
        self.assertEqual(self.request.response.getHeader('location'),
                         "{0}?custom_b_start=0".format(meeting_url))
        # from item3, page 2 of meeting
        self.assertEqual(item3.getItemNumber(), 300)
        view = item3.restrictedTraverse('@@object_goto')
        view(itemNumber=None, way='meeting')
        self.assertEqual(self.request.response.getHeader('location'),
                         "{0}?custom_b_start=2".format(meeting_url))

        # check faceted orphans mecanism
        # items presented on meeting by batch of 5
        # accessing item6 should send us to first page
        cfg.setMaxShownMeetingItems(5)
        self.assertEqual(item6.getItemNumber(), 600)
        view = item6.restrictedTraverse('@@object_goto')
        view(itemNumber=None, way='meeting')
        self.assertEqual(self.request.response.getHeader('location'),
                         "{0}?custom_b_start=0".format(meeting_url))
        # with bach of 4, accessing item5 will send us to page 2
        cfg.setMaxShownMeetingItems(4)
        self.assertEqual(item5.getItemNumber(), 500)
        view = item5.restrictedTraverse('@@object_goto')
        view(itemNumber=None, way='meeting')
        self.assertEqual(self.request.response.getHeader('location'),
                         "{0}?custom_b_start=4".format(meeting_url))

    def test_pm_ETags(self):
        """Test that correct ETags are used for :
           - dashboard (Folder);
           - items (MeetingItem);
           - meetings (Meeting)."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        presented_item = self.create('MeetingItem')
        self.presentItem(presented_item)
        transaction.commit()
        browser = Browser(self.app)
        browser.addHeader('Authorization', 'Basic %s:%s' % ('pmManager', DEFAULT_USER_PASSWORD,))
        browser.open(self.portal.absolute_url())

        # dashboards
        config_modified = ConfigModified(cfg, self.request)()
        tool_modified = ToolModified(self.tool, self.request)()
        pmFolder = self.getMeetingFolder()
        self.request['PUBLISHED'] = pmFolder
        browser.open(pmFolder.absolute_url() + '/searches_items')
        self.assertTrue(config_modified in browser.headers['etag'])
        self.assertTrue(tool_modified in browser.headers['etag'])
        linked_meeting_modified = LinkedMeetingModified(pmFolder, self.request)()
        self.assertNotEqual(linked_meeting_modified, 'lm_0')
        # item
        self.request['PUBLISHED'] = item
        context_modified = ContextModified(item, self.request)()
        browser.open(item.absolute_url())
        self.assertTrue(config_modified in browser.headers['etag'])
        self.assertTrue(tool_modified in browser.headers['etag'])
        self.assertTrue(context_modified in browser.headers['etag'])
        self.assertEqual(LinkedMeetingModified(item, self.request)(), 'lm_0')
        self.assertTrue('msgviewlet_' in browser.headers['etag'])
        # item in meeting
        self.request['PUBLISHED'] = presented_item
        context_modified = ContextModified(presented_item, self.request)()
        linked_meeting_modified = LinkedMeetingModified(presented_item, self.request)()
        self.assertNotEqual(linked_meeting_modified, 'lm_0')
        browser.open(presented_item.absolute_url())
        self.assertTrue(config_modified in browser.headers['etag'])
        self.assertTrue(tool_modified in browser.headers['etag'])
        self.assertTrue(context_modified in browser.headers['etag'])
        self.assertTrue(linked_meeting_modified in browser.headers['etag'])
        # meeting
        self.request['PUBLISHED'] = meeting
        context_modified = ContextModified(meeting, self.request)()
        browser.open(meeting.absolute_url())
        self.assertTrue(config_modified in browser.headers['etag'])
        self.assertTrue(tool_modified in browser.headers['etag'])
        self.assertTrue(context_modified in browser.headers['etag'])

    def test_pm_FTWLabels(self):
        """By default, labels are editable if item editable, except for MeetingManagers
           that may edit labels forever.
           Personal labels are editable by anybody able to see the item."""
        cfg = self.meetingConfig
        # as label jar is updated by the import process
        # make sure we have a persistentmapping containing persistentmappings
        labeljar = getAdapter(cfg, ILabelJar)
        for value in labeljar.storage.values():
            self.assertTrue(isinstance(value, PersistentMapping))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision(self.decisionText)
        # labels
        # able to edit item, able to edit labels
        labelingview = item.restrictedTraverse('@@labeling')
        self.request.form['activate_labels'] = ['label']
        labelingview.update()
        item_labeling = ILabeling(item)
        self.assertEqual(item_labeling.storage, {'label': []})
        self.proposeItem(item)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertRaises(Unauthorized, labelingview.update)
        # MeetingManager
        self.changeUser('pmManager')
        self.request.form['activate_labels'] = []
        labelingview.update()
        self.assertEqual(item_labeling.storage, {})
        # decide item so it is no more editable by MeetingManager
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.closeMeeting(meeting)
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        # labels still editable
        self.request.form['activate_labels'] = ['label']
        labelingview.update()
        self.assertEqual(item_labeling.storage, {'label': []})

        # personal labels
        # anybody able to see the item may change personal label
        self.changeUser('pmCreator1')
        self.assertFalse(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(self.hasPermission(View, item))
        self.assertRaises(Unauthorized, labelingview.update)
        self.request.form['label_id'] = 'personal-label'
        self.request.form['active'] = 'False'
        labelingview.pers_update()
        self.assertEqual(item_labeling.storage, {'label': [], 'personal-label': ['pmCreator1']})
        # powerobserver
        self.changeUser('siteadmin')
        self._setPowerObserverStates(states=(item.query_state(),))
        item._update_after_edit()
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertRaises(Unauthorized, labelingview.update)
        labelingview.pers_update()
        self.assertEqual(item_labeling.storage, {'label': [], 'personal-label': ['pmCreator1', 'powerobserver1']})

    def test_pm_Get_contact_infos(self):
        """Method that returns contact infos for a given Plone userid,
           this rely on fact that a person may be linked to a Plone user using the person.userid field."""
        self.changeUser('siteadmin')
        self.portal.contacts.position_types = [
            {'token': 'default', 'name': u'DefaultA|DefaultB|DefaultC|DefaultD'},
            {'token': 'default2', 'name': u'Default2A|Default2B|Default2C|Default2D'}, ]
        person = self.portal.contacts.get('person1')
        person.userid = 'pmManager'
        person.reindexObject(idxs=['userid'])
        org = get_own_organization()
        newhp = api.content.create(
            container=person, type='held_position', label=u'New held position',
            title='New held position', position=self._relation(org),
            usages=['assemblyMember'], position_type='default2')
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        # called with empty position_types, first is returned
        # use held_position.label if provided
        self.assertEqual(person.held_pos1.label, u'Assembly member 1')
        self.assertEqual(
            helper.get_contact_infos([], 'pmManager'),
            {'held_position': person.held_pos1,
             'held_position_label': u'Assembly member 1',
             'held_position_prefixed_label': u'L\'Assembly member 1',
             'held_position_prefixed_label_by': u'de l\'Assembly member 1',
             'held_position_prefixed_label_to': u'à l\'Assembly member 1',
             'label_prefix': '',
             'label_prefix_by': '',
             'label_prefix_to': '',
             'person': person,
             'person_fullname': u'Person1FirstName Person1LastName',
             'person_title': u'Monsieur Person1FirstName Person1LastName'})

        self.assertEqual(
            helper.get_contact_infos(['default'], 'pmManager'),
            {'held_position': person.held_pos1,
             'held_position_label': u'Assembly member 1',
             'held_position_prefixed_label': u'L\'Assembly member 1',
             'held_position_prefixed_label_by': u'de l\'Assembly member 1',
             'held_position_prefixed_label_to': u'à l\'Assembly member 1',
             'label_prefix': '',
             'label_prefix_by': '',
             'label_prefix_to': '',
             'person': person,
             'person_fullname': u'Person1FirstName Person1LastName',
             'person_title': u'Monsieur Person1FirstName Person1LastName'})
        self.assertEqual(
            helper.get_contact_infos(['default2'], 'pmManager'),
            {'held_position': newhp,
             'held_position_label': u'New held position',
             'held_position_prefixed_label': u'Le New held position',
             'held_position_prefixed_label_by': u'du New held position',
             'held_position_prefixed_label_to': u'au New held position',
             'label_prefix': '',
             'label_prefix_by': '',
             'label_prefix_to': '',
             'person': person,
             'person_fullname': u'Person1FirstName Person1LastName',
             'person_title': u'Monsieur Person1FirstName Person1LastName'})
        # held_position_prefixed_label works only if using position_type and not label
        newhp.label = u''
        self.assertEqual(
            helper.get_contact_infos(['default2'], 'pmManager'),
            {'held_position': newhp,
             'held_position_label': u'Default2A',
             'held_position_prefixed_label': u'Le Default2A',
             'held_position_prefixed_label_by': u'du Default2A',
             'held_position_prefixed_label_to': u'au Default2A',
             'label_prefix': u'Le ',
             'label_prefix_by': u'du ',
             'label_prefix_to': u'au ',
             'person': person,
             'person_fullname': u'Person1FirstName Person1LastName',
             'person_title': u'Monsieur Person1FirstName Person1LastName'})
        # for female
        person.gender = u'F'
        self.assertEqual(
            helper.get_contact_infos(['default2'], 'pmManager'),
            {'held_position': newhp,
             'held_position_label': u'Default2C',
             'held_position_prefixed_label': u'La Default2C',
             'held_position_prefixed_label_by': u'de la Default2C',
             'held_position_prefixed_label_to': u'\xe0 la Default2C',
             'label_prefix': u'La ',
             'label_prefix_by': u'de la ',
             'label_prefix_to': u'\xe0 la ',
             'person': person,
             'person_fullname': u'Person1FirstName Person1LastName',
             'person_title': u'Monsieur Person1FirstName Person1LastName'})

    def test_pm_dashboard_document_generation_link_viewlet(self):
        """Dashboard POD templates are available on a per MeetingConfig basis."""
        self.changeUser('pmCreator1')
        # some DashboardPODTemplates are defined in cfg1
        pmFolder = self.getMeetingFolder()
        adapter1 = getAdapter(pmFolder, IDashboardGenerablePODTemplates)
        self.assertTrue(adapter1.get_all_pod_templates())
        # NO DashboardPODTemplates are defined in cfg2
        pmFolder2 = self.getMeetingFolder(self.meetingConfig2)
        adapter2 = getAdapter(pmFolder2, IDashboardGenerablePODTemplates)
        self.assertFalse(adapter2.get_all_pod_templates())

    def test_pm_content_document_generation_link_viewlet(self):
        """POD templates are available on a per MeetingConfig basis and
           ConfigurablePODTemplates are available for meeting content, IMeeting as well."""
        cfg = self.meetingConfig
        cfg.setItemAdviceStates(('itemcreated',))
        cfg.setItemAdviceEditStates(('itemcreated',))

        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid,))
        item._update_after_edit()
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        # adapters
        # item
        item_adapter = getAdapter(item, IGenerablePODTemplates)
        item_generable_ids = [template.getId() for template in item_adapter.get_generable_templates()]
        self.assertEqual(item_generable_ids, ['itemTemplate'])
        # render viewlet on item
        viewlet = self._get_viewlet(context=item,
                                    manager_name='plone.abovecontentbody',
                                    viewlet_name='document-generation-link')
        viewlet.update()
        rendered = viewlet.render()
        self.assertTrue(cfg.podtemplates.itemTemplate.UID() in rendered)
        self.assertTrue('store_as_annex' in rendered)
        # meeting, does not use DashboardPODTemplates
        meeting = self.create('Meeting')
        meeting_adapter = getAdapter(meeting, IGenerablePODTemplates)
        meeting_generable_ids = [template.getId() for template in meeting_adapter.get_generable_templates()]
        self.assertEqual(meeting_generable_ids, ['agendaTemplate', 'allItemTemplate'])
        # render viewlet on meeting
        viewlet = self._get_viewlet(context=meeting,
                                    manager_name='plone.abovecontentbody',
                                    viewlet_name='document-generation-link')
        viewlet.update()
        rendered = viewlet.render()
        self.assertTrue(cfg.podtemplates.agendaTemplate.UID() in rendered)
        self.assertTrue('store_as_annex' in rendered)
        # advice
        # by defaut, no POD template for advice, enable itemTemplate
        cfg.podtemplates.itemTemplate.pod_portal_types = [u'meetingadvice']
        advice_adapter = getAdapter(advice, IGenerablePODTemplates)
        advice_generable_ids = [template.getId() for template in advice_adapter.get_generable_templates()]
        self.assertEqual(advice_generable_ids, ['itemTemplate'])
        # render viewlet on advice
        viewlet = self._get_viewlet(context=advice,
                                    manager_name='plone.abovecontentbody',
                                    viewlet_name='document-generation-link')
        viewlet.update()
        rendered = viewlet.render()
        self.assertTrue(cfg.podtemplates.itemTemplate.UID() in rendered)
        self.assertTrue('store_as_annex' in rendered)

    def test_pm_dashboard_document_generation_link_viewlet_on_contacts(self):
        """Dashboard POD templates are available on contacts dashboards."""
        self.changeUser('pmManager')
        # a DashboardPODTemplate is defined for the organizations dashboard
        adapter1 = getAdapter(self.portal.contacts.get('orgs-searches'), IDashboardGenerablePODTemplates)
        self.request.form['c1[]'] = adapter1.context.get('all_orgs').UID()
        # one generable template
        generable_templates = adapter1.get_generable_templates()
        self.assertTrue(generable_templates)
        self.assertTrue(generable_templates[0].use_objects)
        # NO DashboardPODTemplates are defined for persons dashboard
        adapter2 = getAdapter(self.portal.contacts.get('persons-searches'), IDashboardGenerablePODTemplates)
        self.request.form['c1[]'] = adapter2.context.get('all_persons').UID()
        self.assertFalse(adapter2.get_generable_templates())

    def test_pm_RichTextWidget(self):
        """Test the PMRichTextWidget used on meeting for example."""
        cfg = self.meetingConfig
        self._enableField('observations', related_to='Meeting')
        self.changeUser('pmManager')
        self._removeConfigObjectsFor(cfg)
        meeting = self.create('Meeting')
        # editable by MeetingManager
        # display mode
        widget = get_dx_widget(meeting, field_name="observations")
        self.assertEqual(widget.mode, DISPLAY_MODE)
        editable_action = "@@richtext-edit?field_name=observations"
        self.assertTrue(editable_action in widget.render())
        # input mode
        widget = get_dx_widget(meeting, field_name="observations", mode=INPUT_MODE)
        self.assertTrue('class="ckeditor_plone"' in widget.render())

        # only viewable for others
        self.changeUser('pmCreator1')
        # display mode, not able to switch to input mode
        widget = get_dx_widget(meeting, field_name="observations")
        self.assertFalse(editable_action in widget.render())
        self.assertFalse(widget.may_edit())
        # input mode
        widget = get_dx_widget(meeting, field_name="observations", mode=INPUT_MODE)
        self.assertTrue('class="ckeditor_plone"' in widget.render())

        # not editable when content is locked
        self.changeUser('siteadmin')
        self.assertTrue(widget.may_edit())
        lockable = ILockable(meeting)
        lockable.lock()
        self.assertTrue(widget.may_edit())
        self.changeUser('pmManager')
        # not editable as locked
        self.assertFalse(widget.may_edit())
        # unlock then editable
        lockable.unlock()
        self.assertTrue(widget.may_edit())
        # ajaxsave is correctly setup
        self.assertIn(
            "ajaxsave_enabled",
            widget.context.restrictedTraverse('@@richtext-edit')('observations'))

    def test_pm_Print_scan_id_barcode(self):
        """Test the print_scan_id_barcode that takes care of raising
           an Exception in case QR code for same context is generated several times."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        # may only be called one time
        self.assertEqual(helper.printed_scan_id_barcode, [])
        # kwargs are passed from print_scan_id_barcode to sub methods
        barcode = helper.print_scan_id_barcode(barcode_options={'filetype': 'GIF'})
        data = barcode.read()
        self.assertTrue(data.startswith("GIF"), data)
        self.assertEqual(helper.printed_scan_id_barcode, [item.UID()])
        with self.assertRaises(Exception) as cm:
            helper.print_scan_id_barcode(barcode_options={'filetype': 'GIF'})
        self.assertEqual(cm.exception.message, SEVERAL_SAME_BARCODE_ERROR)
        # new helper instantiation has empty printed_scan_id_barcode
        helper = view.get_generation_context_helper()
        self.assertEqual(helper.printed_scan_id_barcode, [])

    def test_pm_DocumentGenerationContext(self):
        """We added some specific values to the generation
           context when generating POD templates."""
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        # MeetingItem
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        data = view.get_base_generation_context(helper, None)
        # we do not have the complete utils.py but just the safe_utils.py
        from Products.PloneMeeting import utils
        from Products.PloneMeeting import safe_utils
        self.assertNotEqual(data['pm_utils'], utils)
        self.assertEqual(data['pm_utils'], safe_utils)
        self.assertEqual(data['self'], item)
        self.assertEqual(data['tool'], self.tool)
        self.assertEqual(data['cfg'], cfg)
        self.assertEqual(data['meetingConfig'], cfg)
        self.assertEqual(data['meeting'], None)
        self.presentItem(item)
        data = view.get_base_generation_context(helper, None)
        self.assertEqual(data['meeting'], meeting)
        # Meeting
        view = meeting.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()
        data = view.get_base_generation_context(helper, None)
        self.assertEqual(data['self'], meeting)
        self.assertEqual(data['tool'], self.tool)
        self.assertEqual(data['cfg'], cfg)
        self.assertEqual(data['meetingConfig'], cfg)
        self.assertEqual(data['meeting'], None)

    def test_pm_print_signatures_by_position(self):
        """
        See testContacts.test_pm_print_signatories_by_position for
        the contacts version
        """
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        meeting.signatures = richtextval('my name\nmy signature')
        view = meeting.restrictedTraverse("document-generation")
        helper = view.get_generation_context_helper()

        signatures = helper.print_signatures_by_position()
        self.assertEqual(
            signatures[0],
            meeting.get_signatures().split("\n")[0]
        )
        self.assertEqual(
            signatures[1],
            meeting.get_signatures().split("\n")[1]
        )

    def test_pm_item_meeting_show_history(self):
        """Test the contenthistory.show_history() for item and meeting that
           will depend on MeetingConfig.hideHistoryTo parameter."""
        cfg = self.meetingConfig
        self._setPowerObserverStates(states=(self._stateMappingFor('itemcreated'),))
        self.changeUser('pmCreator1')
        item = self.create("MeetingItem")
        contenthistory = getMultiAdapter((item, self.request), name='contenthistory')
        self.assertTrue(contenthistory.show_history())
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, item))
        self.assertTrue(contenthistory.show_history())

        # now configure so powerobservers may not access history
        cfg.setHideHistoryTo(
            ('Meeting.powerobservers', 'MeetingItem.powerobservers', ))
        self.assertFalse(contenthistory.show_history())

        # when power observer is also member of the item proposingGroup
        # then he has access to the item history
        self._addPrincipalToGroup(self.member.getId(), self.developers_creators)
        self.assertTrue(contenthistory.show_history())

        # will also hide the link on Meeting if relevant
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        contenthistory = getMultiAdapter((meeting, self.request), name='contenthistory')
        self.assertTrue(contenthistory.show_history())
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(contenthistory.show_history())
        cfg.setHideHistoryTo(())
        self.assertTrue(contenthistory.show_history())

    def test_pm_Get_meeting_assembly_stats(self):
        """Method that generates assembly stats when using contacts."""
        cfg = self.meetingConfig
        # enable attendees and signatories fields for Meeting
        self._setUpOrderedContacts()

        self.changeUser('pmManager')
        meeting1 = self.create('Meeting')
        meeting2 = self.create('Meeting', date=datetime(2021, 10, 8))
        meeting3 = self.create('Meeting', date=datetime(2021, 10, 10))
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse("document-generation")
        helper = view.get_generation_context_helper()
        brains = self.catalog(portal_type=cfg.getMeetingTypeName())
        helper.get_meeting_assembly_stats(brains)
        # for now every body present
        self.assertEqual([v['present'] for v in
                          helper.get_meeting_assembly_stats(brains)],
                         [3, 3, 3, 3])
        # set some absents and excused
        attendees = meeting1.get_attendees()
        attendee1 = attendees[0]
        attendee2 = attendees[1]
        meeting1.ordered_contacts[attendee1]['attendee'] = False
        meeting1.ordered_contacts[attendee1]['absent'] = True
        meeting1.ordered_contacts[attendee2]['attendee'] = False
        meeting1.ordered_contacts[attendee2]['excused'] = True
        meeting2.ordered_contacts[attendee1]['attendee'] = False
        meeting2.ordered_contacts[attendee1]['absent'] = True
        meeting2.ordered_contacts[attendee2]['attendee'] = False
        meeting2.ordered_contacts[attendee2]['excused'] = True
        meeting3.ordered_contacts[attendee1]['attendee'] = False
        meeting3.ordered_contacts[attendee1]['absent'] = True
        meeting3.ordered_contacts[attendee2]['attendee'] = False
        meeting3.ordered_contacts[attendee2]['absent'] = True

        # get_meeting_assembly_stats
        stats = helper.get_meeting_assembly_stats(brains)
        self.assertEqual([v['present'] for v in stats], [0, 0, 3, 3])
        self.assertEqual([v['absent'] for v in stats], [3, 1, 0, 0])
        self.assertEqual([v['excused'] for v in stats], [0, 2, 0, 0])

        def _compute_attendance(attendances):
            presents = []
            for info in attendances:
                presents.append(sorted([at['present'] for at in info['attendances']]))
            absents = []
            for info in attendances:
                absents.append(sorted([at['absent'] for at in info['attendances']]))
            excused = []
            for info in attendances:
                excused.append(sorted([at['excused'] for at in info['attendances']]))
            proportions = []
            for info in attendances:
                proportions.append(sorted([at['proportion'] for at in info['attendances']]))
            return presents, absents, excused, proportions

        # get_meeting_assembly_stats_by_meeting
        attendances = helper.get_meeting_assembly_stats_by_meeting(brains)
        presents, absents, excused, proportions = _compute_attendance(attendances)
        self.assertEqual(sorted(presents), [[0, 0, 2, 2], [0, 0, 2, 2], [0, 0, 2, 2]])
        self.assertEqual(sorted(absents), [[0, 0, 0, 2], [0, 0, 0, 2], [0, 0, 2, 2]])
        self.assertEqual(sorted(excused), [[0, 0, 0, 0], [0, 0, 0, 2], [0, 0, 0, 2]])
        self.assertEqual(sorted(proportions), [
            [0.0, 0.0, 100.0, 100.0],
            [0.0, 0.0, 100.0, 100.0],
            [0.0, 0.0, 100.0, 100.0]])

        # define some attendees absent and excused on some items
        attendees = meeting1.get_attendees()
        attendee3 = attendees[0]
        attendee4 = attendees[1]
        items = meeting1.get_items(ordered=True)
        item1_uid = items[0].UID()
        item2_uid = items[1].UID()
        meeting1.item_excused[item1_uid] = [attendee3]
        meeting1.item_excused[item2_uid] = [attendee3]
        meeting1.item_absents[item1_uid] = [attendee4]
        attendances = helper.get_meeting_assembly_stats_by_meeting(brains)
        presents, absents, excused, proportions = _compute_attendance(attendances)
        self.assertEqual(sorted(presents), [[0, 0, 0, 1], [0, 0, 2, 2], [0, 0, 2, 2]])
        self.assertEqual(sorted(absents), [[0, 0, 0, 2], [0, 0, 1, 2], [0, 0, 2, 2]])
        self.assertEqual(sorted(excused), [[0, 0, 0, 0], [0, 0, 0, 2], [0, 0, 2, 2]])
        self.assertEqual(sorted(proportions), [
            [0.0, 0.0, 0.0, 50.0],
            [0.0, 0.0, 100.0, 100.0],
            [0.0, 0.0, 100.0, 100.0]])

    def test_pm_Folder_contents(self):
        """Test the @@folder_contents, especially for DashboardCollection
           as it is overrided in imio.helpers."""
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting')
        # working in Folder folder_contents
        folder = self.getMeetingFolder()
        self.assertTrue(
            '/'.join(item.getPhysicalPath()) in folder.restrictedTraverse('@@folder_contents')())
        self.assertTrue(
            '/'.join(meeting.getPhysicalPath()) in folder.restrictedTraverse('@@folder_contents')())
        # working with item or meeting related DashboardCollections
        item_collection = self.meetingConfig.searches.searches_items.searchallitems
        self.assertTrue(
            '/'.join(item.getPhysicalPath()) in item_collection.restrictedTraverse('@@folder_contents')())
        meeting_collection = self.meetingConfig.searches.searches_meetings.searchnotdecidedmeetings
        self.assertTrue(
            '/'.join(meeting.getPhysicalPath()) in meeting_collection.restrictedTraverse('@@folder_contents')())

    def test_pm_title_viewlet(self):
        """Test that MeetingConfig title is displayed on pmFolders (faceted folders)
           for users and in the configuration."""
        cfg = self.meetingConfig
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        cfg_title = safe_unicode(cfg.Title())
        self.changeUser('pmCreator1')
        pm_folder = self.getMeetingFolder()
        self.assertTrue(u"<title>%s - Items" % cfg_title in
                        pm_folder.searches_items.restrictedTraverse('base_view')())
        self.assertTrue(u"<title>%s - Decisions" % cfg_title in
                        pm_folder.searches_decisions.restrictedTraverse('base_view')())
        # but not on item
        item = self.create("MeetingItem")
        self.assertTrue(u"<title>o1 &mdash; Plone site</title>" in
                        item.restrictedTraverse('base_view')())
        # and not on meeting
        self.changeUser('pmManager')
        meeting = self.create("Meeting", date=datetime(2025, 3, 20))
        self.assertTrue(u"<title>20 march 2025 &mdash; Plone site</title>" in
                        meeting.restrictedTraverse('@@meeting_view')())
        # but also in config
        self.assertTrue(u"<title>%s - Items" % cfg_title in
                        cfg.searches.searches_items.restrictedTraverse('base_view')())

    def test_pm_deliberation_for_restapi(self):
        """Used by plonemeeting.restapi to render formatted data."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', motivation=self.motivationText, decision=self.decisionText)
        view = item.restrictedTraverse('@@document-generation')
        helper = view.get_generation_context_helper()
        data = helper.deliberation_for_restapi()
        self.assertEqual(data["deliberation"], self.motivationText + self.decisionText)
        self.assertEqual(data["deliberation_motivation"], self.motivationText)
        self.assertEqual(data["deliberation_decision"], self.decisionText)
        self.assertEqual(data["public_deliberation"], self.motivationText + self.decisionText)
        self.assertEqual(data["public_deliberation_decided"], self.motivationText + self.decisionText)
        return item, view, helper, data


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testViews, prefix='test_pm_'))
    return suite
