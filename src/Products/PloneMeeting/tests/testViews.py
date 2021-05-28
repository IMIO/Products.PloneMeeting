# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_own_organization
from collective.documentgenerator.interfaces import IGenerablePODTemplates
from collective.eeafaceted.dashboard.interfaces import IDashboardGenerablePODTemplates
from DateTime import DateTime
from datetime import datetime
from ftw.labels.interfaces import ILabeling
from ftw.labels.interfaces import ILabelJar
from imio.helpers.cache import cleanRamCacheFor
from imio.history.utils import getLastWFAction
from os import path
from persistent.mapping import PersistentMapping
from plone import api
from plone.app.testing import logout
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from plone.testing.z2 import Browser
from Products import PloneMeeting as products_plonemeeting
from Products.CMFCore.ActionInformation import Action
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.Five import zcml
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import ITEM_DEFAULT_TEMPLATE_ID
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.etags import ConfigModified
from Products.PloneMeeting.etags import ContextModified
from Products.PloneMeeting.etags import LinkedMeetingModified
from Products.PloneMeeting.etags import ToolModified
from Products.PloneMeeting.MeetingItem import MeetingItem
from Products.PloneMeeting.tests.PloneMeetingTestCase import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.tests.PloneMeetingTestCase import IMG_BASE64_DATA
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.utils import get_annexes
from Products.statusmessages.interfaces import IStatusMessage
from z3c.relationfield.relation import RelationValue
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.intid.interfaces import IIntIds

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
        self.assertEqual(len(view.templatesTree['children']), 2)
        # no sub children
        self.assertFalse(view.templatesTree['children'][0]['children'])
        self.assertFalse(view.displayShowHideAllLinks())
        # as pmCreator2, 3 templates available
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        self.assertEqual(len(cfg.getItemTemplates(filtered=True)), 3)
        self.assertEqual(len(view.templatesTree['children']), 3)
        # no sub children
        self.assertFalse(view.templatesTree['children'][0]['children'])
        self.assertFalse(view.templatesTree['children'][1]['children'])
        self.assertFalse(view.templatesTree['children'][2]['children'])
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
        itemTemplate = view.templatesTree['children'][0]['item']
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
        itemTemplate = view.templatesTree['children'][1]['item']
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
        userGroups = self.tool.get_orgs_for_user(suffixes=['creators'])
        self.assertEqual(newItem2.getProposingGroup(), userGroups[0].UID())
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
        self.assertEqual(len(view.templatesTree['children']), 2)
        self.assertEqual(view.templatesTree['children'][0]['item'].meta_type, 'MeetingItem')
        self.assertEqual(view.templatesTree['children'][1]['item'].meta_type, 'MeetingItem')
        self.assertFalse(view.displayShowHideAllLinks())

        # add an itemTemplate in a subFolder
        self.changeUser('siteadmin')
        cfg.itemtemplates.invokeFactory('Folder', id='subfolder', title="Sub folder")
        subFolder = cfg.itemtemplates.subfolder
        self.create('MeetingItemTemplate', folder=subFolder)

        # we have the subfolder and item under it
        self.changeUser('pmCreator1')
        view()
        self.assertEqual(len(view.templatesTree['children']), 3)
        self.assertEqual(view.templatesTree['children'][0]['item'].meta_type, 'MeetingItem')
        self.assertEqual(view.templatesTree['children'][1]['item'].meta_type, 'MeetingItem')
        self.assertEqual(view.templatesTree['children'][2]['item'].meta_type, 'ATFolder')
        self.assertEqual(view.templatesTree['children'][2]['children'][0]['item'].meta_type, 'MeetingItem')
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
        self.assertEqual(len(view.templatesTree['children']), 3)
        # but available to 'pmCreator2'
        self.changeUser('pmCreator2')
        pmFolder = self.getMeetingFolder()
        view = pmFolder.restrictedTraverse('@@createitemfromtemplate')
        view()
        self.assertEqual(len(view.templatesTree['children']), 5)
        self.assertEqual(view.templatesTree['children'][4]['item'].id, 'subfolder1')

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
        self.assertEqual(len(view.templatesTree['children']), 3)
        self.assertEqual(view.templatesTree['children'][0]['item'].id, ITEM_DEFAULT_TEMPLATE_ID)
        self.assertEqual(view.templatesTree['children'][1]['item'].id, 'template1')
        self.assertEqual(view.templatesTree['children'][2]['item'].id, 'subfolder')
        self.assertEqual(view.templatesTree['children'][2]['children'][0]['item'].id, 'subsubfolder')
        self.assertEqual(view.templatesTree['children'][2]['children'][0]['children'][0]['item'].id, 'o1')
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
                                    'advice_comment': RichTextValue(u'My comment')})
        self.assertTrue(not itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_addable'])
        self.assertTrue(itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['advice_editable'])
        # an editable item will found by the query
        self.assertTrue(len(self.catalog(**query)) == 1)
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even once updated, it will still be found
        itemWithDelayAwareAdvice.updateLocalRoles()
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
        itemWithDelayAwareAdvice.updateLocalRoles()
        self.assertTrue(not self.catalog(**query))

        # try with an not_given timed_out advice as indexAdvisers behaves differently
        # remove meetingadvice, back to not timed_out, updateLocalRoles then proceed
        self.deleteAsManager(itemWithDelayAwareAdvice.meetingadvice.UID())
        itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime.now()
        itemWithDelayAwareAdvice.updateLocalRoles()
        # found for now
        itemWithDelayAwareAdvice.adviceIndex[self.vendors_uid]['delay_started_on'] = datetime(2016, 1, 1)
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # even if a reindexObject occurs in between, still found
        itemWithDelayAwareAdvice.reindexObject()
        self.assertTrue(self.catalog(**query)[0].UID == itemWithDelayAwareAdvice.UID())
        # but once updated, it is not found anymore
        itemWithDelayAwareAdvice.updateLocalRoles()
        self.assertTrue(not self.catalog(**query))

    def test_pm_UpdateDelayAwareAdvicesComputeQuery(self):
        '''
          The computed query only consider organizations for which a delay aware advice is configured.
        '''
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
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
                               for advice_state in ('advice_not_given', ) + ADVICE_STATES_ALIVE]})
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
                    for advice_state in ('advice_not_given', ) + ADVICE_STATES_ALIVE]}))
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
        self.assertEqual(len(query['indexAdvisers']), 2 * (1 + len(ADVICE_STATES_ALIVE)))
        self.assertEqual(
            sorted(query),
            sorted({'indexAdvisers':
                    ['delay__{0}_{1}'.format(self.vendors_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + ADVICE_STATES_ALIVE] +
                    ['delay__{0}_{1}'.format(self.developers_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + ADVICE_STATES_ALIVE]}))
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
        self.assertEqual(len(query['indexAdvisers']), 2 * (1 + len(ADVICE_STATES_ALIVE)))
        self.assertEqual(
            sorted(query),
            sorted({'indexAdvisers':
                    ['delay__{0}_{1}'.format(self.vendors_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + ADVICE_STATES_ALIVE] +
                    ['delay__{0}_{1}'.format(self.developers_uid, advice_state)
                     for advice_state in ('advice_not_given', ) + ADVICE_STATES_ALIVE]}))

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

    def test_pm_SendPodTemplateToMailingList(self):
        """Send a Pod template to a mailing list."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        template = self.meetingConfig.podtemplates.itemTemplate
        # no mailing lists for now
        self.assertEqual(template.mailing_lists, u'')
        self.failIf(self.tool.getAvailableMailingLists(item, template))

        # define mailing_lists
        # False condition
        template.mailing_lists = "list1;python:False;user1@test.be\nlist2;python:False;user1@test.be"
        self.assertEqual(self.tool.getAvailableMailingLists(item, template), [])
        # wrong TAL condition, the list is there with error
        template.mailing_lists = "list1;python:wrong_expression;user1@test.be\nlist2;python:False;user1@test.be"
        error_msg = translate('Mailing lists are not correctly defined, original error is \"${error}\"',
                              mapping={'error': u'name \'wrong_expression\' is not defined', },
                              context=self.request)
        self.assertEqual(self.tool.getAvailableMailingLists(item, template), [error_msg])
        # correct and True condition
        template.mailing_lists = "list1;python:True;user1@test.be\nlist2;python:False;user1@test.be"
        self.assertEqual(self.tool.getAvailableMailingLists(item, template), ['list1'])

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
        template.mailing_lists = "list1;python:True;user1@test.be\nlist2;python:False;user1@test.be"
        messages = IStatusMessage(self.request).show()
        msg = translate('pt_mailing_sent', domain='PloneMeeting', context=self.request)
        self.assertNotEquals(messages[-1].message, msg)
        view()
        messages = IStatusMessage(self.request).show()
        self.assertEqual(messages[-1].message, msg)

    def test_pm_SendPodTemplateToMailingListRecipient(self):
        """Recipients may be defined using several ways :
           - python script;
           - userid;
           - email;
           - Plone group."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        template = self.meetingConfig.podtemplates.itemTemplate
        self.request.set('template_uid', template.UID())
        self.request.set('output_format', 'odt')
        view = item.restrictedTraverse('@@document-generation')

        # script
        self.assertEqual(view._extractRecipients("python:['pmCreator1']"),
                         [u'M. PMCreator One <pmcreator1@plonemeeting.org>'])
        # userid
        self.assertEqual(view._extractRecipients("pmCreator1"),
                         [u'M. PMCreator One <pmcreator1@plonemeeting.org>'])
        # email
        self.assertEqual(view._extractRecipients("pmcreator1@plonemeeting.org"),
                         ['pmcreator1@plonemeeting.org'])
        # group
        group_dev_creators = "group:{0}".format(self.developers_creators)
        self.assertEqual(sorted(view._extractRecipients(group_dev_creators)),
                         [u'M. PMCreator One <pmcreator1@plonemeeting.org>',
                          u'M. PMCreator One bee <pmcreator1b@plonemeeting.org>',
                          u'M. PMManager <pmmanager@plonemeeting.org>'])

        # mixed
        self.assertEqual(sorted(view._extractRecipients(
            "python:['pmCreator1'],pmCreator1,pmCreator2,{0},new@example.com".format(group_dev_creators))),
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
        self.request.set(ITEM_SCAN_ID_NAME, 'IMIO013999900000001')
        self.deleteAsManager(annex.UID())
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.scan_id, 'IMIO013999900000001')

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
            u'python: "{0} (generated by {1})".format(pod_template.Title(), member.getId())'
        self.deleteAsManager(annex.UID())
        view()
        annex = get_annexes(item)[0]
        self.assertEqual(annex.Title(), 'Meeting item (generated by pmManager)')

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
        self.assertEqual(annex.scan_id, '013999900000001')

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
        self.assertEqual(view.getItemsListVisibleFields().keys(),
                         ['description', 'motivation', 'decision'])

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
        self.assertEqual(helper.printXhtml(item,
                                           [motivation, 'separator', decision, 'separator', text],
                                           image_src_to_paths=True,
                                           keepWithNext=True,
                                           keepWithNextNumberOfChars=60),
                         '<p>The motivation using UTF-8 characters : &#232;&#224;.</p>'
                         '<p>&#160;</p>'
                         '<p class="ParaKWN">The d&#233;cision using UTF-8 characters.</p>'
                         '<p class="ParaKWN">&#160;</p>'
                         '<p class="ParaKWN">Text with image <img src="{0}" /> and more text.</p>'
                         .format(img_blob_path))

    def test_pm_PrintXhtmlImageSrcToData(self):
        ''' '''
        item, motivation, decision, helper = self._setupPrintXhtml()

        # use image_src_to_data
        file_path = path.join(path.dirname(__file__), 'dot.gif')
        data = open(file_path, 'r')
        img_id = item.invokeFactory('Image', id='img', title='Image', file=data.read())
        img = getattr(item, img_id)
        pattern = '<p>Text with image <img src="{0}" /> and more text.</p>'
        text = pattern.format(img.absolute_url())
        # in tests the monkeypatch for safe_html.hasScript does not seem to be applied...
        # so disable remove_javascript from safe_html
        self.portal.portal_transforms.safe_html._v_transform.config['remove_javascript'] = 0
        self.assertEqual(helper.printXhtml(item,
                                           text,
                                           image_src_to_paths=False,
                                           image_src_to_data=True,
                                           use_safe_html=True),
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
        '''safe_html will do result XHTML compliant.'''
        item, motivation, decision, helper = self._setupPrintXhtml()
        # use_safe_html is True by default
        self.assertEqual(
            helper.printXhtml(item, [motivation, '<br>']),
            motivation + '<br />')
        self.assertEqual(
            helper.printXhtml(item, [motivation, '<br>'], use_safe_html=False),
            motivation + '<br>')

    def test_pm_PrintXhtmlClean(self):
        '''clean=True will use separate_images from imio.helpers.xhtlm.'''
        item, motivation, decision, helper = self._setupPrintXhtml()
        text = '<p>Text1</p><p><img src="http://plone/nohost/img1.png" />' \
            '<img src="http://plone/nohost/img2.png" /></p>' \
            '<p>Text2</p><p><img src="http://plone/nohost/img3.png" /></p>'
        # True by default
        self.assertEqual(helper.printXhtml(item, text, clean=False), text)
        # when used, images are moved in their own <p> when necessary
        self.assertEqual(helper.printXhtml(item, text),
                         '<p>Text1</p>'
                         '<p><img src="http://plone/nohost/img1.png" /></p>'
                         '<p><img src="http://plone/nohost/img2.png" /></p>'
                         '<p>Text2</p>'
                         '<p><img src="http://plone/nohost/img3.png" /></p>')

    def test_pm_PrintAdvicesInfos(self):
        """Test the printAdvicesInfos method."""
        cfg = self.meetingConfig
        cfg.setSelectableAdvisers((self.developers_uid, self.vendors_uid))
        cfg.setItemAdviceStates((self._stateMappingFor('itemcreated'),))
        cfg.setItemAdviceEditStates((self._stateMappingFor('itemcreated'),))
        cfg.setItemAdviceViewStates((self._stateMappingFor('itemcreated'),))
        cfg.at_post_edit_script()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.developers_uid, self.vendors_uid), )
        item._update_after_edit()
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()

        # advices not given
        self.assertEqual(
            helper.printAdvicesInfos(item),
            "<p class='pmAdvices'><u><b>Advices :</b></u></p>"
            "<p class='pmAdvices'><u>Developers:</u><br /><u>Advice type :</u> "
            "<i>Not given yet</i></p><p class='pmAdvices'><u>Vendors:</u><br />"
            "<u>Advice type :</u> <i>Not given yet</i></p>")
        self.changeUser('pmAdviser1')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.developers_uid,
                                    'advice_type': u'positive',
                                    'advice_comment': RichTextValue(u'My comment')})
        # mixes advice given and not given
        self.assertEqual(
            helper.printAdvicesInfos(item),
            "<p class='pmAdvices'><u><b>Advices :</b></u></p>"
            "<p class='pmAdvices'><u>Vendors:</u><br /><u>Advice type :</u> "
            "<i>Not given yet</i></p><p class='pmAdvices'><u>Developers:</u><br />"
            "<u>Advice type :</u> <i>Positive</i><br /><u>Advice given by :</u> "
            "<i>M. PMAdviser One</i><br /><u>Advice comment :</u> My comment<p></p></p>")

        # every advices given
        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'negative'})
        self.changeUser('pmCreator1')
        self.assertEqual(
            helper.printAdvicesInfos(item),
            "<p class='pmAdvices'><u><b>Advices :</b></u></p><p class='pmAdvices'>"
            "<u>Vendors:</u><br /><u>Advice type :</u> <i>Negative</i><br />"
            "<u>Advice given by :</u> <i>M. PMReviewer Two</i><br />"
            "<u>Advice comment :</u> -<p></p></p><p class='pmAdvices'><u>Developers:</u><br />"
            "<u>Advice type :</u> <i>Positive</i><br /><u>Advice given by :</u> "
            "<i>M. PMAdviser One</i><br /><u>Advice comment :</u> My comment<p></p></p>")

    def test_pm_PrintMeetingDate(self):
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
        self.create('Meeting', date=DateTime('2019/01/01'))
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
            ['01 january 2019', DateTime('2019/01/01')]
        )
        # powerobserver1 can't see the meeting so noMeetingMarker is expected when unrestricted=False
        self.assertListEqual(
            [helper.print_meeting_date(unrestricted=False, noMeetingMarker=''),
             helper.print_meeting_date(returnDateTime=True, unrestricted=False, noMeetingMarker=None)],
            ['', None]
        )

    def test_pm_PrintPreferredMeetingDate(self):
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
        meeting = self.create('Meeting', date=DateTime('2019/01/01'))
        view = item.restrictedTraverse('document-generation')
        helper = view.get_generation_context_helper()

        self.assertListEqual(  # item has not preferred meeting so noMeetingMarker is expected
            [helper.print_preferred_meeting_date(), helper.print_preferred_meeting_date(noMeetingMarker='xxx')],
            ['-', 'xxx']
        )

        item.setPreferredMeeting(meeting.UID())
        self.assertListEqual(  # standard case, a preferred meeting date is expected
            [helper.print_preferred_meeting_date(), helper.print_preferred_meeting_date(returnDateTime=True)],
            ['01 january 2019', DateTime('2019/01/01')]
        )

        self.changeUser('powerobserver1')
        self.assertListEqual(
            # powerobserver1 can't see the meeting so noMeetingMarker is expected when unrestricted=False
            [helper.print_preferred_meeting_date(unrestricted=False, noMeetingMarker=''),
             helper.print_preferred_meeting_date(returnDateTime=True, unrestricted=False, noMeetingMarker=None)],
            ['', None],
        )

    def test_pm_MeetingUpdateItemReferences(self):
        """Test call to @@update-item-references from the meeting that will update
           every references of items of a meeting."""
        cfg = self.meetingConfig
        # remove recurring items in self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=DateTime('2017/03/03'))
        self.presentItem(item)
        self.freezeMeeting(meeting)
        self.assertEqual(item.getItemReference(), 'Ref. 20170303/1')
        # change itemReferenceFormat
        # change itemReferenceFormat to include an item data (Title)
        cfg.setItemReferenceFormat(
            "python: here.getMeeting().getDate().strftime('%Y%m%d') + '/' + "
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
        cfg.setUseGroupsAsCategories(False)
        cfg.setInsertingMethodsOnAddItem((
            {'insertingMethod': 'on_list_type',
             'reverse': '0'},
            {'insertingMethod': 'on_categories',
             'reverse': '0'},
            {'insertingMethod': 'on_proposing_groups',
             'reverse': '0'},)
        )
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2019/01/18'))
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
        self.assertEqual(meeting.getItems(ordered=True), right_ordered_items)
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
        mixed_items = meeting.getItems(ordered=True)
        self.assertEqual(mixed_items,
                         [item7, item8, item3, item4, item5, item2, item10, item6, item1, item9])
        # references are correct
        self.assertEqual([item.getItemReference() for item in mixed_items], right_item_references)
        # reorder items
        view = meeting.restrictedTraverse('@@reorder-items')
        view()
        # order and references are correct
        self.assertEqual(meeting.getItems(ordered=True), right_ordered_items)
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
        self.assertEqual(
            view.group_users(group),
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One bee</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMManager</div>")
        # add a 'not found' user, will not be displayed
        self._make_not_found_user()
        self.assertEqual(
            view.group_users(group),
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One bee</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMManager</div>")

    def test_pm_DisplayGroupUsersViewAllPloneGroups(self):
        """It is possible to get every Plone groups."""
        cfg = self.meetingConfig
        cfg.setUseCopies(True)
        cfg.setItemCopyGroupsStates(('itemcreated', ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', copyGroups=(self.vendors_reviewers, ))
        view = item.restrictedTraverse('@@display-group-users')
        # append a "*" to a org uid to get every Plone groups
        group_id = self.developers.UID() + '*'
        view(group_ids=group_id)
        plone_group = api.group.get(self.developers_creators)
        self.assertEqual(
            view.group_users(plone_group),
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One bee</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMManager</div>")
        # add a 'not found' user, will not be displayed
        self._make_not_found_user()
        self.assertEqual(
            view.group_users(plone_group),
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMCreator One bee</div>"
            "<img src='http://nohost/plone/user.png'> <div class='user-or-group'>M. PMManager</div>")
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
        meeting = self.create('Meeting', date=DateTime('2017/08/08'))
        form = meeting.restrictedTraverse('@@store-items-template-as-annex-batch-action')
        form.update()
        self.assertTrue(self.hasPermission(ModifyPortalContent, meeting))
        self.assertFalse(form.available())
        self.assertRaises(Unauthorized, form.handleApply, form, None)

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
        first_3_item_uids = [item.UID for item in meeting.getItems(ordered=True, theObjects=False)[0:3]]
        self.request.form['form.widgets.uids'] = ','.join(first_3_item_uids)
        self.request.form['form.widgets.pod_template'] = 'itemTemplate__output_format__odt'
        form.update()
        form.handleApply(form, None)
        itemTemplateId = cfg.podtemplates.itemTemplate.getId()
        items = meeting.getItems(ordered=True)
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
        next_3_item_uids = [item.UID for item in meeting.getItems(ordered=True, theObjects=False)[3:6]]
        self.request.form['form.widgets.uids'] = ','.join(next_3_item_uids)
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
        last_item_uid = meeting.getItems(ordered=True, theObjects=False)[-1].UID
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
        item_uids = [item.UID for item in meeting.getItems(ordered=True, theObjects=False)]
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
        meeting = self.create('Meeting', date=DateTime('2018/03/14'))
        self.freezeMeeting(meeting)
        # freeze the meeting so it is viewable in most workflows to various groups
        form = getMultiAdapter((meeting, self.request), name=u'transition-batch-action')
        self.assertTrue(form.available())
        # not available to others
        self._setPowerObserverStates(field_name='meeting_states',
                                     states=(self._stateMappingFor('frozen', meta_type='Meeting'),))
        meeting.updateLocalRoles()
        self.changeUser('powerobserver1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(form.available())
        self.changeUser('pmCreator1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(form.available())
        self.changeUser('pmReviewer1')
        self.assertTrue(self.hasPermission(View, meeting))
        self.assertFalse(form.available())

    def test_pm_UpdateLocalRolesBatchActionForm(self):
        """This will call updateLocalRoles on selected elements."""
        cfg = self.meetingConfig
        self._setPowerObserverStates(states=())
        powerobservers = '{0}_powerobservers'.format(cfg.getId())

        # create some items
        self.changeUser('pmManager')
        item1 = self.create('MeetingItem')
        item2 = self.create('MeetingItem')
        item3 = self.create('MeetingItem')
        self.request.form['form.widgets.uids'] = ','.join([item1.UID(), item3.UID()])
        dashboardFolder = self.getMeetingFolder().searches_items
        # not available as not Manager
        self.assertRaises(Unauthorized, dashboardFolder.restrictedTraverse, '@@update-local-roles-batch-action')
        self.assertFalse(dashboardFolder.unrestrictedTraverse(
            '@@update-local-roles-batch-action').available())

        # as Manager
        self.changeUser('siteadmin')
        self.assertFalse(powerobservers in item1.__ac_local_roles__)
        self.assertFalse(powerobservers in item2.__ac_local_roles__)
        self.assertFalse(powerobservers in item3.__ac_local_roles__)
        self._setPowerObserverStates(states=(self._stateMappingFor('itemcreated'),))
        dashboardFolder = self.getMeetingFolder().searches_items
        form = dashboardFolder.restrictedTraverse('@@update-local-roles-batch-action')
        self.assertTrue(form.available())
        form.update()
        form.handleApply(form, None)
        self.assertTrue(powerobservers in item1.__ac_local_roles__)
        self.assertFalse(powerobservers in item2.__ac_local_roles__)
        self.assertTrue(powerobservers in item3.__ac_local_roles__)

        # not available on meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting', date=DateTime('2019/03/08'))
        self.changeUser('siteadmin')
        form = meeting.restrictedTraverse('@@update-local-roles-batch-action')
        self.assertFalse(form.available())

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
        item = self.create('MeetingItem')
        viewlet = self._get_viewlet(
            context=item, manager_name='plone.belowcontenttitle', viewlet_name='ftw.labels.labeling')
        self.assertTrue(viewlet.available)

        # can_edit
        self.assertTrue(self.hasPermission(ModifyPortalContent, item))
        self.assertTrue(viewlet.can_edit)
        # propose so no more editable
        self.proposeItem(item)
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
        cfg.at_post_edit_script()

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
                                    'advice_comment': RichTextValue(u'My comment')})
        self.changeUser('pmManager')
        assert_results(item, advisorIdsToBeReturned=[self.developers_uid])
        assert_results(item, [self.vendors_uid])
        assert_results(item, [self.developers_uid], [self.developers_uid])

        self.changeUser('pmReviewer2')
        createContentInContainer(item,
                                 'meetingadvice',
                                 **{'advice_group': self.vendors_uid,
                                    'advice_type': u'negative',
                                    'advice_comment': RichTextValue(u'My comment')})

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
        meeting = self.create('Meeting', date=DateTime('2018/07/31'))
        self.presentItem(secretItem1)
        self.presentItem(publicItem1)
        self.presentItem(secretItem2)
        self.presentItem(publicItem2)
        self.presentItem(secretItem3)
        self.assertEqual(
            meeting.getItems(ordered=True),
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
        self.assertEqual(view('3', 'next'), publicItem2.absolute_url())
        self.assertEqual(view('1', 'previous'), view.context.absolute_url())
        self.assertEqual(view('1', 'first'), view.context.absolute_url())
        self.assertEqual(view('5', 'last'), publicItem2.absolute_url())

        # do secret items accessible
        secretItem1.setPrivacy('public')
        secretItem1.reindexObject()
        secretItem2.setPrivacy('public')
        secretItem2.reindexObject()
        secretItem3.setPrivacy('public')
        secretItem3.reindexObject()
        # MeetingItem.isPrivacyViewable is RAMCached
        cleanRamCacheFor('Products.PloneMeeting.MeetingItem.isPrivacyViewable')
        self.assertEqual(view('3', 'next'), secretItem2.absolute_url())
        self.assertEqual(view('1', 'previous'), secretItem1.absolute_url())
        self.assertEqual(view('1', 'first'), secretItem1.absolute_url())
        self.assertEqual(view('5', 'last'), secretItem3.absolute_url())

    def test_pm_ETags(self):
        """Test that correct ETags are used for :
           - dashboard (Folder);
           - items (MeetingItem);
           - meetings (Meeting)."""
        cfg = self.meetingConfig
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        meeting = self.create('Meeting', date=DateTime('2019/02/28'))
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
        meeting = self.create('Meeting', date=DateTime('2019/03/14'))
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
        self._setPowerObserverStates(states=(item.queryState(),))
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
        intids = getUtility(IIntIds)
        org = get_own_organization()
        newhp = api.content.create(
            container=person, type='held_position', label=u'New held position',
            title='New held position', position=RelationValue(intids.getId(org)),
            usages=['assemblyMember'], position_type='default2')
        person.userid = 'pmManager'
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
             'held_position_prefixed_label': u'Assembly member 1',
             'held_position_prefixed_label_by': u'Assembly member 1',
             'held_position_prefixed_label_to': u'Assembly member 1',
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
             'held_position_prefixed_label': u'Assembly member 1',
             'held_position_prefixed_label_by': u'Assembly member 1',
             'held_position_prefixed_label_to': u'Assembly member 1',
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
             'held_position_prefixed_label': u'New held position',
             'held_position_prefixed_label_by': u'New held position',
             'held_position_prefixed_label_to': u'New held position',
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
               'advice_comment': RichTextValue(u'My comment')})
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
        meeting = self.create('Meeting', date=DateTime('2019/11/26'))
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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testViews, prefix='test_pm_'))
    return suite
