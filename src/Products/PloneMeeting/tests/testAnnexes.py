# -*- coding: utf-8 -*-
#
# File: testAnnexes.py
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_plone_group
from collective.iconifiedcategory.browser.tabview import CategorizedContent
from collective.iconifiedcategory.event import IconifiedAttrChangedEvent
from collective.iconifiedcategory.interfaces import IIconifiedPreview
from collective.iconifiedcategory.utils import _categorized_elements
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.utils import get_categorized_elements
from collective.iconifiedcategory.utils import get_category_object
from collective.iconifiedcategory.utils import get_config_root
from collective.iconifiedcategory.utils import get_group
from collective.iconifiedcategory.utils import update_all_categorized_elements
from imio.actionspanel.interfaces import IContentDeletable
from imio.annex.columns import ActionsColumn
from imio.annex.columns import PrettyLinkColumn
from imio.annex.utils import get_annexes_to_print
from imio.helpers.content import get_vocab
from imio.helpers.content import get_vocab_values
from imio.helpers.content import richtextval
from plone import api
from plone.app.testing import logout
from plone.dexterity.utils import createContentInContainer
from plone.indexer.wrapper import IndexableObjectWrapper
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.PloneMeeting.config import AddAnnex
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import BUDGETIMPACTEDITORS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.content.content_category import other_mc_correspondences_constraint
from Products.PloneMeeting.MeetingConfig import PROPOSINGGROUPPREFIX
from Products.PloneMeeting.MeetingConfig import SUFFIXPROFILEPREFIX
from Products.PloneMeeting.tests.PloneMeetingTestCase import PloneMeetingTestCase
from Products.PloneMeeting.tests.PloneMeetingTestCase import pm_logger
from Products.PloneMeeting.utils import get_annexes
from tempfile import mkdtemp
from time import sleep
from zope.annotation import IAnnotations
from zope.event import notify
from zope.interface import Invalid
from zope.lifecycleevent import ObjectModifiedEvent

import magic


class testAnnexes(PloneMeetingTestCase):
    '''Tests various aspects of annexes management.'''

    def test_pm_MayChangeAnnexConfidentiality(self):
        '''May change if :
           - confidentiality enabled;
           - has the Modify portal content permission;
           - is a MeetingManager.
           '''
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        self.assertFalse(annex.confidential)
        self.assertTrue(self.hasPermission(ModifyPortalContent, annex))
        annex_config = get_config_root(annex)
        annex_group = get_group(annex_config, annex)

        self.assertFalse(annex_group.confidentiality_activated)
        view = annex.restrictedTraverse('@@iconified-confidential')
        self.assertRaises(Unauthorized,
                          view.set_values, {'confidential': 'true'})
        # enable confidentiality
        annex_group.confidentiality_activated = True
        # now it fails because not a MeetingManager
        cfg = self.tool.getMeetingConfig(annex)
        self.assertFalse(self.tool.isManager(cfg))
        self.assertRaises(Unauthorized,
                          view.set_values, {'confidential': 'true'})

        # right, now as a MeetingManager, it works
        self.changeUser('pmManager')
        view.set_values({'confidential': 'true'})
        self.assertTrue(annex.confidential)

    def _setupConfidentialityOnItemAnnexes(self, powerObserverStates=[], copyGroups=[]):
        """ """
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        # make sure by default no access to items for powerobservers
        self._setPowerObserverStates(states=powerObserverStates)

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', copyGroups=copyGroups)
        # enable confidentiality
        self._enable_annex_config(item)
        annexes_table = item.restrictedTraverse('@@iconifiedcategory')
        categorized_child = item.restrictedTraverse('@@categorized-childs-infos')
        annex_category = cfg.annexes_types.item_annexes.get('financial-analysis')
        categorized_child.category_uid = annex_category.UID()
        categorized_child.filters = {}

        annexNotConfidential = self.addAnnex(item, annexTitle='Annex not confidential')
        annexConfidential = self.addAnnex(item, annexTitle='Annex confidential')
        annexConfidential.confidential = True
        notify(ObjectModifiedEvent(annexConfidential))
        return item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForBudgetImpactEditors(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        # give budget impact editors view on item
        cfg.setItemBudgetInfosStates([item_initial_state])
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_budgetimpacteditors', ))
        item.update_local_roles()
        # give budget impact editors view on item
        # by default, budget impact editors local role will only give ability to edit budget infos, not to view item
        item.__ac_local_roles__['{0}_{1}'.format(cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)] = ['Reader']
        item.reindexObjectSecurity()

        self.changeUser('budgetimpacteditor')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        self._setPowerObserverStates(states=(item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        item.update_local_roles()

        self.changeUser('powerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForRestrictedPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=(item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        item.update_local_roles()

        self.changeUser('restrictedpowerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForAdvisers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        cfg.setItemAdviceStates((item_initial_state, ))
        cfg.setItemAdviceEditStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('reader_advices', ))
        item.setOptionalAdvisers((self.developers_uid, ))
        item.update_local_roles()

        self.changeUser('pmAdviser1')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForCopyGroups(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor(('reader_copy_groups', ))
        item.setCopyGroups((self.vendors_reviewers, ))
        item.update_local_roles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForGroupsInCharge(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        proposingGroup = item.getProposingGroup(theObject=True)
        cfg.setItemGroupsInChargeStates([item_initial_state])

        # does not fail in no group in charge
        self.assertFalse(proposingGroup.groups_in_charge)
        cfg.setItemAnnexConfidentialVisibleFor(('reader_groupsincharge', ))
        update_all_categorized_elements(item)
        self._setUpGroupsInCharge(item)

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def _get_meeting_managers_for(self, cfg):
        meeting_managers_group_id = '{0}_{1}'.format(cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
        meeting_managers_group = api.group.get(meeting_managers_group_id)
        meeting_manager_ids = meeting_managers_group.getMemberIds()
        return meeting_manager_ids

    def test_pm_ItemGetCategorizedElementsWithConfidentialityForProposingGroupSuffixes(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()

        # validate the item so it is visible by every roles of the proposing group
        self.validateItem(item)
        self.assertEqual(item.query_state(), 'validated')

        proposingGroupSuffixes = [k for k in cfg.listItemAttributeVisibleFor()
                                  if k.startswith(PROPOSINGGROUPPREFIX)]
        for proposingGroupSuffix in proposingGroupSuffixes:
            cfg.setItemAnnexConfidentialVisibleFor((proposingGroupSuffix, ))
            update_all_categorized_elements(item)
            # get a user from the right 'developers' subgroup but make sure it is not a MeetingManager
            group_suffix = proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, '')
            developers_suffixed_group = get_plone_group(self.developers_uid, group_suffix)
            userIds = [userId for userId in developers_suffixed_group.getMemberIds()
                       if userId not in self._get_meeting_managers_for(cfg)]
            if not userIds:
                pm_logger.info("Could not test if developers.'%s' can access confidential "
                               "annexes because there are no user in the group !" % group_suffix)
                continue
            self.changeUser(userIds[0])
            if not self.hasPermission(View, item):
                pm_logger.info("Could not test if '%s' can access confidential "
                               "annexes because he may not see the item !" % self.member.getId())
                continue
            self._checkElementConfidentialAnnexAccess(cfg, item, annexNotConfidential, annexConfidential,
                                                      annexes_table, categorized_child)

    def _checkElementConfidentialAnnexAccess(self,
                                             cfg,
                                             obj,
                                             annexNotConfidential,
                                             annexConfidential,
                                             annexes_table,
                                             categorized_child):
        """ """
        # avoid wrong value in cfg.xxxAnnexConfidentialVisibleFor fields
        for field_name in ('itemAnnexConfidentialVisibleFor',
                           'adviceAnnexConfidentialVisibleFor',
                           'meetingAnnexConfidentialVisibleFor'):
            field = cfg.getField(field_name)
            self.assertIsNone(field.validate(field.get(cfg), cfg))
        self.assertTrue(self.hasPermission(View, obj))
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        # is viewable for Manager and MeetingManager
        current_user_id = self.member.getId()
        self.changeUser('siteadmin')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        self.changeUser('pmManager')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        self.changeUser(current_user_id)

        # disable access to condifential elements to every profiles
        cfg.setItemAnnexConfidentialVisibleFor(())
        cfg.setAdviceAnnexConfidentialVisibleFor(())
        cfg.setMeetingAnnexConfidentialVisibleFor(())
        update_all_categorized_elements(obj)
        self._checkMayNotAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                   annexes_table, categorized_child)
        # is viewable for Manager and MeetingManager
        self.changeUser('siteadmin')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)
        self.changeUser('pmManager')
        self._checkMayAccessConfidentialAnnexes(obj, annexNotConfidential, annexConfidential,
                                                annexes_table, categorized_child)

    def _checkNumberOfAnnexesOnView(self, obj, number):
        """Check number next to annex type icon."""
        # avoid cache on views
        self.tool.invalidateAllCache()
        if obj.__class__.__name__ == 'MeetingAdvice':
            rendered_view = obj.restrictedTraverse('@@view')()
            term_check = 'title="Adviceannex(es)"><span>{0}</span>'
        elif obj.__class__.__name__ == 'Meeting':
            rendered_view = obj.restrictedTraverse('@@meeting_view')()
            term_check = 'title="Meetingannex(es)"><span>{0}</span>'
        else:
            # MeetingItem
            rendered_view = obj.restrictedTraverse('meetingitem_view')()
            term_check = 'title="Financialanalysis"><span>{0}</span>'
        rendered_view = rendered_view.replace(' ', '').replace('\n', '')
        self.assertTrue(term_check.format(number) in rendered_view)

    def _checkMayAccessConfidentialAnnexes(self,
                                           obj,
                                           annexNotConfidential,
                                           annexConfidential,
                                           annexes_table,
                                           categorized_child):
        """ """
        # current user may see every annexes
        self.assertEqual(set([elt['UID'] for elt in get_categorized_elements(obj)]),
                         set((annexNotConfidential.UID(), annexConfidential.UID())))
        self.assertTrue('Annex not confidential' in annexes_table())
        self.assertTrue('Annex confidential' in annexes_table())
        categorized_child.update()
        result = categorized_child.index()
        self.assertTrue('<span title="">Annex not confidential</span>' in result)
        self.assertTrue('<span title="">Annex confidential</span>' in result)
        # check that we have 2 annexes displayed on view
        self._checkNumberOfAnnexesOnView(obj, 2)

    def _checkMayNotAccessConfidentialAnnexes(self,
                                              obj,
                                              annexNotConfidential,
                                              annexConfidential,
                                              annexes_table,
                                              categorized_child):
        """ """
        # confidential annexes not viewable
        self.assertEqual([elt['UID'] for elt in get_categorized_elements(obj)],
                         [annexNotConfidential.UID()])
        self.assertTrue('Annex not confidential' in annexes_table())
        self.assertFalse('Annex confidential' in annexes_table())
        categorized_child.update()
        result = categorized_child.index()
        self.assertTrue('<span title="">Annex not confidential</span>' in result)
        self.assertFalse('<span title="">Annex confidential</span>' in result)
        # check that we have 1 annex displayed on view
        self._checkNumberOfAnnexesOnView(obj, 1)

    def _setupConfidentialityOnAdviceAnnexes(self):
        """ """
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        # make sure by default no access to items for powerobservers
        self._setPowerObserverStates(states=[])

        cfg.setItemAdviceStates((item_initial_state, ))
        cfg.setItemAdviceEditStates((item_initial_state, ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item.update_local_roles()
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        # enable confidentiality
        self._enable_annex_config(advice)
        annexes_table = advice.restrictedTraverse('@@iconifiedcategory')
        annex_category = cfg.annexes_types.advice_annexes.get('advice-annex')
        categorized_child = advice.restrictedTraverse('@@categorized-childs-infos')
        categorized_child.category_uid = annex_category.UID()
        categorized_child.filters = {}

        annexNotConfidential = self.addAnnex(advice, annexTitle='Annex not confidential')
        annexConfidential = self.addAnnex(advice, annexTitle='Annex confidential')
        annexConfidential.confidential = True
        notify(ObjectModifiedEvent(annexConfidential))
        return item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForAdviserGroup(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setAdviceAnnexConfidentialVisibleFor(('adviser_group', ))
        update_all_categorized_elements(advice)

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForBudgetImpactEditors(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setItemBudgetInfosStates([item_initial_state])
        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_budgetimpacteditors', ))
        item.update_local_roles()
        # give budget impact editors view on item
        # by default, budget impact editors local role will only give ability to edit budget infos, not to view item
        item.__ac_local_roles__['{0}_{1}'.format(cfg.getId(), BUDGETIMPACTEDITORS_GROUP_SUFFIX)] = ['Reader']
        item._propagateReaderAndMeetingManagerLocalRolesToSubObjects(cfg)
        item.reindexObjectSecurity()

        self.changeUser('budgetimpacteditor')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForAdvisers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_advices', ))
        update_all_categorized_elements(advice)

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForCopyGroups(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        self._enableField('copyGroups')
        cfg.setItemCopyGroupsStates((item_initial_state, ))
        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_copy_groups', ))
        item.setCopyGroups((self.vendors_reviewers, ))
        item.update_local_roles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForGroupsInCharge(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        proposingGroup = item.getProposingGroup(theObject=True)
        cfg.setItemGroupsInChargeStates([item_initial_state])

        # does not fail in no group in charge
        self.assertFalse(proposingGroup.groups_in_charge)
        cfg.setAdviceAnnexConfidentialVisibleFor(('reader_groupsincharge', ))
        update_all_categorized_elements(item)
        self._setUpGroupsInCharge(item)
        item.update_local_roles()

        self.changeUser('pmReviewer2')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        self._setPowerObserverStates(states=(item_initial_state, ))
        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        item.update_local_roles()

        self.changeUser('powerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForRestrictedPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     states=(item_initial_state, ))
        cfg.setAdviceAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        item.update_local_roles()

        self.changeUser('restrictedpowerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_AdviceGetCategorizedElementsWithConfidentialityForProposingGroupSuffixes(self):
        ''' '''
        cfg = self.meetingConfig
        item_initial_state, item, advice, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnAdviceAnnexes()

        # validate the item so it is visible by every roles of the proposing group
        self.validateItem(item)
        self.assertEqual(item.query_state(), 'validated')

        proposingGroupSuffixes = [k for k in cfg.listItemAttributeVisibleFor()
                                  if k.startswith(PROPOSINGGROUPPREFIX)]
        for proposingGroupSuffix in proposingGroupSuffixes:
            cfg.setAdviceAnnexConfidentialVisibleFor((proposingGroupSuffix, ))
            update_all_categorized_elements(advice)
            # get a user from the right 'developers' subgroup but make sure it is not a MeetingManager
            group_suffix = proposingGroupSuffix.replace(PROPOSINGGROUPPREFIX, '')
            developers_suffixed_group = get_plone_group(self.developers_uid, group_suffix)
            userIds = [userId for userId in developers_suffixed_group.getMemberIds()
                       if userId not in self._get_meeting_managers_for(cfg)]
            if not userIds:
                pm_logger.info("Could not test if developers.'%s' can access confidential "
                               "annexes because there are no user in the group !" % group_suffix)
                continue
            self.changeUser(userIds[0])
            if not self.hasPermission(View, advice):
                pm_logger.info("Could not test if '%s' can access confidential "
                               "annexes because he may not see the item !" % self.member.getId())
                continue
            self._checkElementConfidentialAnnexAccess(cfg, advice, annexNotConfidential, annexConfidential,
                                                      annexes_table, categorized_child)

    def _setupConfidentialityOnMeetingAnnexes(self):
        """ """
        cfg = self.meetingConfig
        cfgMeetingWF = self.wfTool.getWorkflowsFor(cfg.getMeetingTypeName())[0]
        meeting_initial_state = self.wfTool[cfgMeetingWF.getId()].initial_state
        # make sure by default no access to items for powerobservers
        self._setPowerObserverStates(states=[])

        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # enable confidentiality
        self._enable_annex_config(meeting)

        annexes_table = meeting.restrictedTraverse('@@iconifiedcategory')
        categorized_child = meeting.restrictedTraverse('@@categorized-childs-infos')
        annex_category = cfg.annexes_types.meeting_annexes.get('meeting-annex')
        categorized_child.category_uid = annex_category.UID()
        categorized_child.filters = {}

        annexNotConfidential = self.addAnnex(meeting, annexTitle='Annex not confidential')
        annexConfidential = self.addAnnex(meeting, annexTitle='Annex confidential')
        annexConfidential.confidential = True
        notify(ObjectModifiedEvent(annexConfidential))
        return meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential

    def test_pm_MeetingGetCategorizedElementsWithConfidentialityForPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnMeetingAnnexes()

        self._setPowerObserverStates(field_name='meeting_states',
                                     states=(meeting_initial_state, ))
        cfg.setMeetingAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        meeting.update_local_roles()

        self.changeUser('powerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_MeetingGetCategorizedElementsWithConfidentialityForRestrictedPowerObservers(self):
        ''' '''
        cfg = self.meetingConfig
        meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnMeetingAnnexes()

        self._setPowerObserverStates(observer_type='restrictedpowerobservers',
                                     field_name='meeting_states',
                                     states=(meeting_initial_state, ))
        cfg.setMeetingAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        meeting.update_local_roles()

        self.changeUser('restrictedpowerobserver1')
        self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                  annexes_table, categorized_child)

    def test_pm_MeetingGetCategorizedElementsWithConfidentialityForProposingGroupProfiles(self):
        ''' '''
        cfg = self.meetingConfig
        meeting_initial_state, meeting, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnMeetingAnnexes()

        # freeze the meeting so it is visible by every profiles
        self.freezeMeeting(meeting)
        self.assertEqual(meeting.query_state(), 'frozen')

        profileSuffixes = [k for k in cfg.listMeetingAnnexConfidentialVisibleFor()
                           if k.startswith(SUFFIXPROFILEPREFIX)]
        for profileSuffix in profileSuffixes:
            # every users of a Plone subgroup profileSuffix will have access
            for org in (self.developers, self.vendors):
                cfg.setMeetingAnnexConfidentialVisibleFor((profileSuffix, ))
                notify(ObjectEditedEvent(cfg))
                update_all_categorized_elements(meeting)
                group_suffix = profileSuffix.replace(SUFFIXPROFILEPREFIX, '')
                # get a user from the right 'developers/vendors' subgroup
                suffixed_group = get_plone_group(org.UID(), group_suffix)
                userIds = [userId for userId in suffixed_group.getMemberIds()
                           if userId not in self._get_meeting_managers_for(cfg)]
                if not userIds:
                    pm_logger.info("Could not test if profile '%s' can access confidential "
                                   "annexes for group '%s' because no users is defined in this profile !"
                                   % (group_suffix, org.getId()))
                    continue
                self.changeUser(userIds[0])
                if not self.hasPermission(View, meeting):
                    pm_logger.info("Could not test if '%s' can access confidential "
                                   "annexes because he may not see the item !" % self.member.getId())
                    continue
                self._checkElementConfidentialAnnexAccess(cfg, meeting, annexNotConfidential, annexConfidential,
                                                          annexes_table, categorized_child)

    def test_pm_SwitchingConfidentialityUsingActionView(self):
        """Test that enabling/disabling/enabling
           confidentiality on an annex works correctly."""
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        # confidential annexes are visible by proposing group creators
        cfg.setItemAnnexConfidentialVisibleFor(('suffix_proposing_group_creators', ))

        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes(
                powerObserverStates=(item_initial_state, ))

        view = annexConfidential.restrictedTraverse('@@iconified-confidential')
        view.attribute_mapping = {'confidential': 'confidential'}

        # confidential for now
        self.changeUser('powerobserver1')
        self.assertFalse(annexConfidential.UID() in get_categorized_elements(item))
        self.assertEqual(annexConfidential.__ac_local_roles__,
                         {'pmCreator1': ['Owner'],
                          self.developers_creators: ['AnnexReader']})
        # remove confidentiality, only MeetingManagers may change confidentiality
        self.changeUser('pmManager')
        self.request.set('confidential', False)
        view()
        self.changeUser('powerobserver1')
        self.assertTrue(annexConfidential.UID() in
                        [elt['UID'] for elt in get_categorized_elements(item)])
        self.assertEqual(annexConfidential.__ac_local_roles__,
                         {'pmCreator1': ['Owner']})
        # confidential again
        self.changeUser('pmManager')
        self.request.set('confidential', True)
        view()
        self.changeUser('powerobserver1')
        self.assertFalse(annexConfidential.UID() in
                         [elt['UID'] for elt in get_categorized_elements(item)])
        self.assertEqual(annexConfidential.__ac_local_roles__,
                         {'pmCreator1': ['Owner'],
                          self.developers_creators: ['AnnexReader']})

    def test_pm_AnnexRestrictShownAndEditableAttributes(self):
        """Test MeetingConfig.annexRestrictShownAndEditableAttributes
           that defines what annex attributes are displayed/editable only to MeetingManagers."""
        # enable every attributes
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setAnnexRestrictShownAndEditableAttributes(())
        config = cfg.annexes_types.item_annexes
        annex_attr_names = (
            'confidentiality_activated',
            'signed_activated',
            'publishable_activated',
            'to_be_printed_activated')
        # enable every attr for annex, none for annexDecision
        for attr_name in annex_attr_names:
            setattr(config, attr_name, True)

        # helper check method
        annex_attr_change_view_names = (
            '@@iconified-confidential',
            '@@iconified-signed',
            '@@iconified-publishable',
            '@@iconified-print')

        def _check(annexes_table,
                   annex,
                   annex_decision,
                   displayed=annex_attr_change_view_names,
                   editable=annex_attr_change_view_names):
            ''' '''
            # nothing displayed for annexDecision
            for view_name in displayed:
                self.assertTrue(view_name in annexes_table.table_render(portal_type='annex'))
                self.assertFalse(view_name in annexes_table.table_render(portal_type='annexDecision'))
            for view_name in editable:
                self.assertTrue(annex.restrictedTraverse(view_name)._may_set_values({}))
                self.assertFalse(annex_decision.restrictedTraverse(view_name)._may_set_values({}))

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_decision = self.addAnnex(item, relatedTo='item_decision')
        annexes_table = item.restrictedTraverse('@@iconifiedcategory')
        annexes_table._update()
        # everything displayed/editable by user
        self.assertEqual(cfg.getAnnexRestrictShownAndEditableAttributes(), ())
        _check(annexes_table, annex, annex_decision)
        # confidential no more editable but viewable
        cfg.setAnnexRestrictShownAndEditableAttributes(('confidentiality_edit'))
        list_editable_annex_attr_change_view_names = list(annex_attr_change_view_names)
        list_editable_annex_attr_change_view_names.remove('@@iconified-confidential')
        _check(annexes_table, annex, annex_decision, editable=list_editable_annex_attr_change_view_names)
        # confidential and signed no more editable but viewable
        cfg.setAnnexRestrictShownAndEditableAttributes(('confidentiality_edit', 'signed_edit'))
        list_editable_annex_attr_change_view_names.remove('@@iconified-signed')
        _check(annexes_table, annex, annex_decision, editable=list_editable_annex_attr_change_view_names)
        # when someting not displayed, not editable automatically
        cfg.setAnnexRestrictShownAndEditableAttributes(('confidentiality_edit',
                                                        'signed_edit',
                                                        'publishable_display'))
        list_editable_annex_attr_change_view_names.remove('@@iconified-publishable')
        list_displayed_annex_attr_change_view_names = list(annex_attr_change_view_names)
        list_displayed_annex_attr_change_view_names.remove('@@iconified-publishable')
        _check(annexes_table, annex, annex_decision,
               editable=list_editable_annex_attr_change_view_names,
               displayed=list_displayed_annex_attr_change_view_names)

    def _manage_custom_searchable_fields(self, item):
        """"""
        pass

    def test_pm_AnnexesTitleFoundInItemSearchableText(self):
        '''Annexes title is indexed in the item SearchableText.'''
        self.tool.setDeferParentReindex(())
        ANNEX_TITLE = "SpecialAnnexTitle"
        ITEM_TITLE = "SpecialItemTitle"
        ITEM_DESCRIPTION = "Item description text"
        ITEM_DECISION = "Item decision text"
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title=ITEM_TITLE)
        item.setDescription(ITEM_DESCRIPTION)
        item.setDecision(ITEM_DECISION)
        item.setMotivation('')
        self._manage_custom_searchable_fields(item)
        item.reindexObject(idxs=['SearchableText', ])
        index = self.catalog.Indexes['SearchableText']
        self.assertTrue(len(self.catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(self.catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(self.catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertFalse(self.catalog(SearchableText=ANNEX_TITLE))
        indexable_wrapper = IndexableObjectWrapper(item, self.catalog)
        self.assertEquals(
            indexable_wrapper.SearchableText,
            '{0}  <p>{1}</p>  <p>{2}</p> '.format(
                ITEM_TITLE, ITEM_DESCRIPTION, ITEM_DECISION)
        )
        itemRID = self.catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          [ITEM_TITLE.lower(), 'p', 'item', 'description', 'text', 'p',
                           'p', 'item', 'decision', 'text', 'p'])

        # add an annex and test that the annex title is found in the item's SearchableText
        annex = self.addAnnex(item, annexTitle=ANNEX_TITLE)
        # now querying for ANNEX_TITLE will return the relevant item
        self.assertTrue(len(self.catalog(SearchableText=ITEM_TITLE)) == 1)
        self.assertTrue(len(self.catalog(SearchableText=ITEM_DESCRIPTION)) == 1)
        self.assertTrue(len(self.catalog(SearchableText=ITEM_DECISION)) == 1)
        self.assertTrue(len(self.catalog(SearchableText=ANNEX_TITLE)) == 1)
        indexable_wrapper = IndexableObjectWrapper(item, self.catalog)
        self.assertEquals(
            indexable_wrapper.SearchableText,
            '{0}  <p>{1}</p>  <p>{2}</p>  {3}'.format(
                ITEM_TITLE, ITEM_DESCRIPTION, ITEM_DECISION, ANNEX_TITLE))
        itemRID = self.catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          [ITEM_TITLE.lower(), 'p', 'item', 'description', 'text', 'p',
                           'p', 'item', 'decision', 'text', 'p', ANNEX_TITLE.lower()])
        # works also when clear and rebuild catalog
        self.catalog.clearFindAndRebuild()
        itemRID = self.catalog(UID=item.UID())[0].getRID()
        self.assertEquals(index.getEntryForObject(itemRID),
                          [ITEM_TITLE.lower(), 'p', 'item', 'description', 'text', 'p',
                           'p', 'item', 'decision', 'text', 'p', ANNEX_TITLE.lower()])
        # when 'annex' is selected in ToolPloneMeeting.deferParentReindex, then
        # the SearchableText is not updated when annex added
        # add an annex and test that the annex title is found in the item's SearchableText
        self.tool.setDeferParentReindex(['annex'])
        self.addAnnex(item, annexTitle="SuperSpecialAnnexTitle")
        self.assertEqual(len(self.catalog(SearchableText="SuperSpecialAnnexTitle")), 0)
        # updated by the @@pm-night-tasks or a reindexObject
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, "@@pm-night-tasks")
        self.changeUser('siteadmin')
        self.portal.restrictedTraverse("@@pm-night-tasks")()
        self.changeUser('pmCreator1')
        self.assertEqual(len(self.catalog(SearchableText="SuperSpecialAnnexTitle")), 1)
        # if we remove the annex, the item is not found anymore when querying
        # on removed annex's title
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertTrue(self.catalog(SearchableText=ITEM_TITLE))
        self.assertFalse(self.catalog(SearchableText=ANNEX_TITLE))
        self.assertEqual(len(self.catalog(SearchableText="SuperSpecialAnnexTitle")), 1)

    def test_pm_AnnexesTitleFoundInMeetingSearchableText(self):
        '''Annexes title is indexed in the meeting SearchableText.'''
        self.tool.setDeferParentReindex(())
        ANNEX_TITLE = "SpecialAnnexTitle"
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.assertFalse(self.catalog(SearchableText=ANNEX_TITLE))
        # add an annex
        annex = self.addAnnex(meeting, annexTitle=ANNEX_TITLE)
        self.assertTrue(len(self.catalog(SearchableText=ANNEX_TITLE)) == 1)
        # remove the annex
        self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
        self.assertFalse(self.catalog(SearchableText=ANNEX_TITLE))

    def test_pm_ItemAnnexesContentNotInAnnexSearchableText(self):
        '''Annexes content is not indexed in any SearchableText.'''
        self.tool.setDeferParentReindex(())
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', title='My beautifull item')
        # add an annex
        annex = self.addAnnex(item, annexTitle="Big bad text.txt", annexFile=u'annex_not_to_index.txt')
        self.presentItem(item)
        self.changeUser('pmManager')
        self.assertEqual(len(self.catalog(UID=annex.UID())), 1)
        brains = self.catalog(Title='Big bad text')
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, annex.UID())
        # ensure its SearchableText entry is empty
        index = self.catalog.Indexes['SearchableText']
        annexRID = self.catalog(UID=annex.UID())[0].getRID()
        entry = index.getEntryForObject(annexRID)
        self.assertIsNone(entry)
        # ensure it can't be found while searching its content in case it is indexed on another context
        self.assertEqual(len(self.catalog(SearchableText='If you')), 0)
        self.assertEqual(len(self.catalog(SearchableText='you see')), 0)
        self.assertEqual(len(self.catalog(SearchableText='see me')), 0)
        self.assertEqual(len(self.catalog(SearchableText='me ...')), 0)
        self.assertEqual(len(self.catalog(SearchableText='Well you')), 0)
        self.assertEqual(len(self.catalog(SearchableText='you know')), 0)
        self.assertEqual(len(self.catalog(SearchableText='know how')), 0)
        self.assertEqual(len(self.catalog(SearchableText='how it')), 0)
        self.assertEqual(len(self.catalog(SearchableText='it ends')), 0)

    def test_pm_MeetingAnnexesContentNotInAnnexSearchableText(self):
        '''Annexes content is not indexed in any SearchableText.'''
        self.tool.setDeferParentReindex(())
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        # add an annex
        annex = self.addAnnex(meeting, annexTitle="Big bad text.txt", annexFile=u'annex_not_to_index.txt')
        # ensure this annex is indexed
        annex.reindexObject()
        self.assertEqual(len(self.catalog(UID=annex.UID())), 1)
        brains = self.catalog(Title='Big bad text')
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].UID, annex.UID())
        # ensure its SearchableText entry is empty
        index = self.catalog.Indexes['SearchableText']
        annexRID = self.catalog(UID=annex.UID())[0].getRID()
        entry = index.getEntryForObject(annexRID)
        self.assertIsNone(entry)
        # ensure it can't be found while searching its content in case it is indexed on another context
        self.assertEqual(len(self.catalog(SearchableText='If you')), 0)
        self.assertEqual(len(self.catalog(SearchableText='you see')), 0)
        self.assertEqual(len(self.catalog(SearchableText='see me')), 0)
        self.assertEqual(len(self.catalog(SearchableText='me ...')), 0)
        self.assertEqual(len(self.catalog(SearchableText='Well you')), 0)
        self.assertEqual(len(self.catalog(SearchableText='you know')), 0)
        self.assertEqual(len(self.catalog(SearchableText='know how')), 0)
        self.assertEqual(len(self.catalog(SearchableText='how it')), 0)
        self.assertEqual(len(self.catalog(SearchableText='it ends')), 0)

    def test_pm_AnnexesConvertedIfAutoConvertIsEnabled(self):
        """If collective.documentviewer 'auto_convert' is enabled,
           the annexes and decision annexes are converted."""
        gsettings = self._enableAutoConvert()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        annex = self.addAnnex(item)
        # annex has been converted no matter 'to_print' value
        self.assertFalse(annex.to_print)
        self.assertTrue(IIconifiedPreview(annex).converted)

        # annex is not converted if auto_convert is disabled
        gsettings.auto_convert = False
        not_converted_annex = self.addAnnex(item)
        self.assertFalse(not_converted_annex.to_print)
        self.assertFalse(IIconifiedPreview(not_converted_annex).converted)

    def test_pm_AnnexesConvertedIsPreviewable(self):
        """The preview work as expected."""
        gsettings = self._enableAutoConvert()
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        annex = self.addAnnex(item)
        annex_uid = annex.UID()
        path = '@@dvpdffiles/%s/%s/%s/small/dump_1.%s' % (
            annex_uid[0], annex_uid[1], annex_uid, gsettings.pdf_image_format)
        image_dump = self.portal.unrestrictedTraverse(path)
        # we get a 'jpeg' image
        self.assertEqual(image_dump.context.content_type, 'image/jpeg')

    def test_pm_AnnexesConvertedDependingOnAnnexToPrintMode(self):
        """If collective.documentviewer 'auto_convert' is disabled,
           annexes set 'to_print' is only converted if
           MeetingConfig.annexToPrintMode is 'enabled_for_printing'."""
        self._enableAutoConvert(enable=False)
        cfg = self.meetingConfig
        cfg.setAnnexToPrintMode('enabled_for_info')

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        not_converted_annex = self.addAnnex(item)
        # annex 'to_print' was set to False because 'to_be_printed_activated'
        # is not enabled on the category group
        category = get_category_object(not_converted_annex, not_converted_annex.content_category)
        category_group = category.get_category_group()
        self.assertFalse(category_group.to_be_printed_activated)
        self.assertFalse(not_converted_annex.to_print)
        self.assertFalse(IIconifiedPreview(not_converted_annex).converted)

        # no matter 'to_be_printed_activated' is enabled
        # if MeetingConfig.annexToPrintMode is not 'enabled_for_printing'
        # the annex is not converted
        category_group.to_be_printed_activated = True
        not_converted_annex2 = self.addAnnex(item)
        self.assertFalse(not_converted_annex2.to_print)
        self.assertFalse(IIconifiedPreview(not_converted_annex2).converted)

        # annex is converted if 'to_be_printed_activated' enabled and
        # MeetingConfig.annexToPrintMode is 'enabled_for_printing'
        cfg.setAnnexToPrintMode('enabled_for_printing')
        converted_annex = self.addAnnex(item)
        self.assertFalse(converted_annex.to_print)
        self.assertFalse(IIconifiedPreview(converted_annex).converted)
        converted_annex.to_print = True
        notify(IconifiedAttrChangedEvent(converted_annex,
                                         attr_name='to_print',
                                         old_values={'to_print': False},
                                         new_values={'to_print': True}))
        self.assertTrue(converted_annex.to_print)
        self.assertTrue(IIconifiedPreview(converted_annex).converted)

        # if an annex is not 'to_print', it is not converted
        converted_annex2 = self.addAnnex(item)
        converted_annex2.to_print = False
        notify(IconifiedAttrChangedEvent(converted_annex2,
                                         attr_name='to_print',
                                         old_values={'to_print': True},
                                         new_values={'to_print': False}))
        self.assertFalse(converted_annex2.to_print)
        self.assertFalse(IIconifiedPreview(converted_annex2).converted)

    def test_pm_AnnexOnlyConvertedAgainWhenNecessary(self):
        """When conversion is enabled, either by 'auto_convert' or
           when MeetingConfig.annexToPrintMode is 'enabled_for_printing',
           if an annex is updated, it will be converted again onModified."""
        gsettings = self._enableAutoConvert()
        # enable to_be_printed
        self._enable_annex_config(self.meetingConfig, param="to_be_printed")

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.annexFile = u'file_correct.pdf'
        annex = self.addAnnex(item)
        # has been converted
        self.assertTrue(IIconifiedPreview(annex).converted)
        ann = IAnnotations(annex)['collective.documentviewer']
        initial_conversion_date = ann['last_updated']

        # now play with 'to_print', it will not be converted again
        sleep(2)
        annex.to_print = False
        notify(ObjectModifiedEvent(annex))
        self.assertEqual(initial_conversion_date,
                         IAnnotations(annex)['collective.documentviewer']['last_updated'])
        annex.to_print = True
        notify(ObjectModifiedEvent(annex))
        self.assertEqual(initial_conversion_date,
                         IAnnotations(annex)['collective.documentviewer']['last_updated'])

        # if contents really changed, not only the ModificationDate then it is converted again
        modified = annex.modified()
        annex.notifyModified()
        self.assertNotEqual(modified, annex.modified())
        notify(ObjectModifiedEvent(annex))
        # still not converted again as file content did not changed
        self.assertEqual(initial_conversion_date,
                         IAnnotations(annex)['collective.documentviewer']['last_updated'])
        # if file content changed, then annex is converted again
        self.annexFile = u'file_correct2.pdf'
        annex.file = self._annex_file_content()
        notify(ObjectModifiedEvent(annex))
        self.assertNotEqual(initial_conversion_date,
                            IAnnotations(annex)['collective.documentviewer']['last_updated'])

        # works also if auto_convert not enabled but
        # MeetingConfig.annexToPrintMode is 'enabled_for_printing'
        gsettings.auto_convert = False
        self.meetingConfig.setAnnexToPrintMode('enabled_for_printing')
        sleep(2)
        self.annexFile = u'file_correct.pdf'
        annex.file = self._annex_file_content()
        notify(ObjectModifiedEvent(annex))
        self.assertNotEqual(initial_conversion_date,
                            IAnnotations(annex)['collective.documentviewer']['last_updated'])

    def test_pm_Get_annexes_to_print(self):
        """Test this from imio.annex.utils.
           Will return printable annexes with path to blob."""
        gsettings = self._enableAutoConvert()

        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self._enable_annex_config(item, param="to_be_printed")
        annex1 = self.addAnnex(item, annexTitle="Annex 1")
        annex2 = self.addAnnex(item, annexTitle="Annex 2", annexType='overhead-analysis')
        annex3 = self.addAnnex(item, annexTitle="Annex 3")
        annex1.to_print = True
        annex2.to_print = True
        self.assertFalse(annex3.to_print)
        update_all_categorized_elements(item)
        annexes_to_print = get_annexes_to_print(item, caching=False)
        self.assertEqual(len(annexes_to_print), 2)
        self.assertEqual(annexes_to_print[0]['UID'], annex1.UID())
        self.assertEqual(annexes_to_print[1]['UID'], annex2.UID())
        # change global config image format will still work
        gsettings.pdf_image_format = 'png'
        # same result
        annexes_to_print2 = get_annexes_to_print(item, caching=False)
        self.assertEqual(annexes_to_print, annexes_to_print2)
        # filters
        annexes_to_print = get_annexes_to_print(item, filters={'category_id': 'overhead-analysis'})
        self.assertEqual(len(annexes_to_print), 1)
        self.assertEqual(annexes_to_print[0]['UID'], annex2.UID())

    def test_pm_ChangeAnnexPosition(self):
        """Annexes are orderable by the user able to add annexes."""
        cfg = self.meetingConfig
        self._removeConfigObjectsFor(cfg)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', decision=self.decisionText)
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)
        annex3 = self.addAnnex(item)
        self.assertEqual(item.objectValues(), [annex1, annex2, annex3])
        item.folder_position_typeaware(position='down', id=annex1.getId())
        self.assertEqual(item.objectValues(), [annex2, annex1, annex3])
        # member of the same group are able to change annexes position
        self.assertTrue(self.developers_creators in self.member.getGroups())
        self.changeUser('pmCreator1b')
        self.assertTrue(self.developers_creators in self.member.getGroups())
        item.folder_position_typeaware(position='down', id=annex1.getId())
        self.assertEqual(item.objectValues(), [annex2, annex3, annex1])
        # only members able to add annexes are able to change position
        self.validateItem(item)
        self.assertEqual(item.query_state(), 'validated')
        self.assertFalse(self.hasPermission(AddAnnex, item))
        # adding decision annex may be adapted
        if item.may_add_annex_decision(cfg, item.query_state()):
            self.assertTrue(self.hasPermission(AddAnnexDecision, item))
        else:
            self.assertFalse(self.hasPermission(AddAnnexDecision, item))
            self.assertRaises(Unauthorized,
                              item.folder_position_typeaware,
                              position='up',
                              id=annex1.getId())
        # creators may manage decision annexes on decided item
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.closeMeeting(meeting)
        self.assertEqual(item.query_state(), 'accepted')
        self.assertFalse(self.hasPermission(AddAnnex, item))
        self.assertTrue(self.hasPermission(AddAnnexDecision, item))
        item.folder_position_typeaware(position='up', id=annex1.getId())
        # an observer could not change annex position
        self.changeUser('pmObserver1')
        self.cleanMemoize()
        self.assertTrue(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(AddAnnex, item))
        self.assertFalse(self.hasPermission(AddAnnexDecision, item))
        self.assertRaises(Unauthorized,
                          item.folder_position_typeaware,
                          position='bottom',
                          id=annex1.getId())

    def test_pm_AnnexesCreationDateKeptWhenItemDuplicated(self):
        """When an item is duplicated, if annexes are kept,
           the annexes creation date is also kept."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(item)
        clonedItem = item.clone()
        self.assertEqual(annex1.created(), clonedItem.objectValues()[0].created())
        self.assertEqual(annex2.created(), clonedItem.objectValues()[1].created())

    def test_pm_ConfidentialAnnexesWhenItemDuplicated(self):
        """When an item is duplicated, if there were confidential annexes, accesses are correct."""
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfg.setSelectableCopyGroups((self.vendors_creators, ))
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        cfg.setItemCopyGroupsStates((item_initial_state, ))
        cfg.setItemAnnexConfidentialVisibleFor((u'suffix_proposing_group_creators',
                                                u'suffix_proposing_group_reviewers'))
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes(
                copyGroups=(self.vendors_creators, ))
        self.assertEqual(len(get_categorized_elements(item)), 2)
        clonedItem = item.clone()
        # every annexes are correctly viewable
        self.assertEqual(len(get_categorized_elements(clonedItem)), 2)
        # now a member not from proposingGroup duplicate the item because he may see it
        self.changeUser('pmCreator2')
        self.assertTrue(self.hasPermission(View, item))
        # may only view one annex
        self.assertEqual(len(get_categorized_elements(item)), 1)
        clonedItem = item.clone()
        self.assertEqual(len(get_categorized_elements(clonedItem)), 1)
        # if may view confidential annex, it is kept
        cfg.setItemAnnexConfidentialVisibleFor((u'suffix_proposing_group_creators',
                                                u'suffix_proposing_group_reviewers',
                                                u'reader_copy_groups'))
        update_all_categorized_elements(item)
        self.assertEqual(len(get_categorized_elements(item)), 2)
        clonedItem = item.clone()
        self.assertEqual(len(get_categorized_elements(clonedItem)), 2)
        # check that local_roles regarding proposingGroup are correctly set on new annexes
        item.setCopyGroups(())
        clonedItem = item.clone()
        self.assertEqual(len(get_categorized_elements(clonedItem)), 2)

    def test_pm_AnnexesDeletableByItemEditor(self):
        """annex/annexDecision may be deleted if user may edit the item."""
        cfg = self.meetingConfig
        # use the 'only_creator_may_delete' WF adaptation if available
        # in this case, it will ensure that when validated, the item may not be
        # deleted but annexes may be deleted by item editor
        wfAdaptations = cfg.getWorkflowAdaptations()
        if 'only_creator_may_delete' in get_vocab_values(cfg, 'WorkflowAdaptations') and \
           'only_creator_may_delete' not in wfAdaptations:
            wfAdaptations = wfAdaptations + ('only_creator_may_delete', )
            cfg.setWorkflowAdaptations(wfAdaptations)
            notify(ObjectEditedEvent(cfg))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        annex1 = self.addAnnex(item)
        annexDecision1 = self.addAnnex(item, relatedTo='item_decision')
        annex2 = self.addAnnex(item)
        annexDecision2 = self.addAnnex(item, relatedTo='item_decision')
        annex3 = self.addAnnex(item)
        annexDecision3 = self.addAnnex(item, relatedTo='item_decision')
        # delete annex as item creator
        self.assertTrue(IContentDeletable(annex1).mayDelete())
        self.assertTrue(IContentDeletable(annexDecision1).mayDelete())
        self.assertTrue(IContentDeletable(annex2).mayDelete())
        self.assertTrue(IContentDeletable(annexDecision2).mayDelete())
        self.assertTrue(IContentDeletable(annex3).mayDelete())
        self.assertTrue(IContentDeletable(annexDecision3).mayDelete())
        item.restrictedTraverse('@@delete_givenuid')(annex1.UID())
        item.restrictedTraverse('@@delete_givenuid')(annexDecision1.UID())

        self.proposeItem(item)
        # creator no more able to delete annex
        self.assertFalse(IContentDeletable(annex2).mayDelete())
        self.assertFalse(IContentDeletable(annexDecision2).mayDelete())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annex2.UID())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annexDecision2.UID())
        self.changeUser('pmReviewer1')
        if 'only_creator_may_delete' in get_vocab_values(cfg, 'WorkflowAdaptations'):
            self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertTrue(IContentDeletable(annex2).mayDelete())
        item.restrictedTraverse('@@delete_givenuid')(annex2.UID())
        item.restrictedTraverse('@@delete_givenuid')(annexDecision2.UID())

        self.validateItem(item)
        # reviewer no more able to delete annex
        self.assertFalse(IContentDeletable(annex3).mayDelete())
        self.assertFalse(IContentDeletable(annexDecision3).mayDelete())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annex3.UID())
        self.assertRaises(Unauthorized,
                          item.restrictedTraverse('@@delete_givenuid'),
                          annexDecision3.UID())
        self.changeUser('pmManager')
        if 'only_creator_may_delete' in get_vocab_values(cfg, 'WorkflowAdaptations'):
            self.assertFalse(self.hasPermission(DeleteObjects, item))
        self.assertTrue(IContentDeletable(annex3).mayDelete())
        item.restrictedTraverse('@@delete_givenuid')(annex3.UID())
        item.restrictedTraverse('@@delete_givenuid')(annexDecision3.UID())

    def test_pm_DecisionAnnexesDeletableByOwner(self):
        """annexDecision may be deleted by the Owner, aka the user that added the annex."""
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setDecision('<p>Decision</p>')
        self.validateItem(item)
        # when an item is 'accepted', the MeetingMember may add annexDecision
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.presentItem(item)
        self.decideMeeting(meeting)
        self.do(item, 'accept')
        self.assertEqual(item.query_state(), 'accepted')
        self.changeUser('pmCreator1')
        decisionAnnex1 = self.addAnnex(item, relatedTo='item_decision')
        self.assertTrue(decisionAnnex1 in item.objectValues())
        # doable if cfg.ownerMayDeleteAnnexDecision is True
        self.assertFalse(cfg.getOwnerMayDeleteAnnexDecision())
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@delete_givenuid'), decisionAnnex1.UID())
        cfg.setOwnerMayDeleteAnnexDecision(True)
        item.restrictedTraverse('@@delete_givenuid')(decisionAnnex1.UID())
        self.assertFalse(decisionAnnex1 in item.objectValues())
        # add an annex and another user having same groups for item can not remove it
        decisionAnnex2 = self.addAnnex(item, relatedTo='item_decision')
        self.changeUser('pmCreator1b')
        self.assertRaises(Unauthorized, item.restrictedTraverse('@@delete_givenuid'), decisionAnnex2.UID())

    def test_pm_ItemAnnexFormVocabularies(self):
        """The vocabularies used for MeetingItem is different if used for annex or annexDecision."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        self.changeUser('pmManager')
        item = self.create('MeetingItem')
        # set item in a state where both annex and annexDecision are addable
        self.validateItem(item)

        # check with form, context is the MeetingItem
        form_annex = item.restrictedTraverse('++add++annex')
        self.request['PUBLISHED'] = form_annex
        form_annex_instance = form_annex.form_instance
        form_annex_instance.update()
        form_annex_widget = form_annex_instance.widgets['IIconifiedCategorization.content_category']
        form_annex_widget_terms = [term.token for term in form_annex_widget.terms]
        self.assertEqual(
            form_annex_widget_terms,
            ['{0}-annexes_types_-_item_annexes_-_financial-analysis'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_financial-analysis_-_financial-analysis-sub-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_budget-analysis'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_overhead-analysis'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_overhead-analysis_-_overhead-analysis-sub-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_item-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_preview-annex'.format(cfgId),
             '{0}-annexes_types_-_item_annexes_-_preview-hide-download-annex'.format(cfgId)])

        # now for decisionAnnex
        # check with form, context is the MeetingItem
        form_annexDecision = item.restrictedTraverse('++add++annexDecision')
        self.request['PUBLISHED'] = form_annexDecision
        form_annexDecision_instance = form_annexDecision.form_instance
        form_annexDecision_instance.update()
        form_annexDecision_widget = form_annexDecision_instance.widgets['IIconifiedCategorization.content_category']
        form_annexDecision_widget_terms = [term.token for term in form_annexDecision_widget.terms]
        self.assertEqual(
            form_annexDecision_widget_terms,
            ['{0}-annexes_types_-_item_decision_annexes_-_decision-annex'.format(cfgId)])

    def test_pm_MeetingAnnexFormVocabularies(self):
        """This is essentially done to make sure ++add++annex works
           correctly when adding an annex on a meeting."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        self.changeUser('pmManager')
        meeting = self.create('Meeting')

        # check with form, context is the MeetingItem
        form_annex = meeting.restrictedTraverse('++add++annex')
        form_annex_instance = form_annex.form_instance
        form_annex_instance.update()
        form_annex_widget = form_annex_instance.widgets['IIconifiedCategorization.content_category']
        form_annex_widget_terms = [term.token for term in form_annex_widget.terms]
        self.assertEqual(
            form_annex_widget_terms,
            ['{0}-annexes_types_-_meeting_annexes_-_meeting-annex'.format(cfgId)])

    def test_pm_AdviceAnnexFormVocabularies(self):
        """This is essentially done to make sure ++add++annex works
           correctly when adding an annex on an advice."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        item, advice = self._setupItemWithAdvice()

        # check with form, context is the advice
        form_annex = advice.restrictedTraverse('++add++annex')
        form_annex_instance = form_annex.form_instance
        form_annex_instance.update()
        form_annex_widget = form_annex_instance.widgets['IIconifiedCategorization.content_category']
        form_annex_widget_terms = [term.token for term in form_annex_widget.terms]
        self.assertEqual(
            form_annex_widget_terms,
            ['{0}-annexes_types_-_advice_annexes_-_advice-annex'.format(cfgId),
             '{0}-annexes_types_-_advice_annexes_-_advice-legal-analysis'.format(cfgId)])

    def test_pm_UpdateCategorizedElements(self):
        """The actions "update_categorized_elements" from collective.iconifiedcategory
           will update annex confidentiality accesses."""
        cfg = self.meetingConfig
        cfgId = cfg.getId()
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_restrictedpowerobservers', ))
        self._setPowerObserverStates(states=('itemcreated', ))

        # only available to 'Managers'
        self.changeUser('pmCreator1')
        self.assertRaises(Unauthorized,
                          cfg.annexes_types.item_annexes.restrictedTraverse,
                          '@@update-categorized-elements')

        # create item with annex
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        # enable confidentiality
        self._enable_annex_config(item)
        annex.confidential = True
        notify(ObjectModifiedEvent(annex))
        category = get_category_object(annex, annex.content_category)
        currentIndexedCategoryTitle = category.Title()
        self.assertEqual(item.categorized_elements[annex.UID()]['category_title'],
                         currentIndexedCategoryTitle)
        # restrictedpowerobservers have access to annex, not powerobservers
        rpoId = '{0}_restrictedpowerobservers'.format(cfgId)
        poId = '{0}_powerobservers'.format(cfgId)
        self.assertEqual(
            annex.__ac_local_roles__[rpoId], ['AnnexReader'])
        self.assertFalse(poId in annex.__ac_local_roles__)

        # change configuration : category title and MeetingConfig.itemAnnexConfidentialVisibleFor
        cfg.setItemAnnexConfidentialVisibleFor(('configgroup_powerobservers', ))
        NEW_CATEGORY_TITLE = 'New category title'
        category.title = NEW_CATEGORY_TITLE
        self.assertNotEqual(currentIndexedCategoryTitle, NEW_CATEGORY_TITLE)
        # categorized_elements was not updated
        self.assertNotEqual(item.categorized_elements[annex.UID()]['category_title'],
                            NEW_CATEGORY_TITLE)

        # call @@update-categorized-elements then check again
        self.changeUser('siteadmin')
        view = cfg.annexes_types.item_annexes.restrictedTraverse('@@update-categorized-elements')
        view()
        self.assertEqual(item.categorized_elements[annex.UID()]['category_title'],
                         NEW_CATEGORY_TITLE)
        # accesses were also updated : powerobservers have access to annex, not restrictedpowerobservers
        self.assertEqual(
            annex.__ac_local_roles__[poId], ['AnnexReader'])
        self.assertFalse(rpoId in annex.__ac_local_roles__)

    def test_pm_CategorizedAnnexesShowMethods(self):
        """Test the @@categorized-annexes view."""
        cfg = self.meetingConfig
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        view = item.restrictedTraverse('@@categorized-annexes')
        view._update()
        # both annex and annexDecision are displayed and addable
        self.assertTrue(view.showAddAnnex())
        self.assertTrue(view.showAddAnnexDecision())
        self.assertTrue(view.showDecisionAnnexesSection())
        # add an annex and an annexDecision
        self.addAnnex(item)
        annexDecision = self.addAnnex(item, relatedTo='item_decision')
        terms, show = view.showAddAnnex()
        self.assertTrue(show)
        terms, show = view.showAddAnnexDecision()
        self.assertTrue(show)
        self.assertTrue(view.showAnnexesSection())
        self.assertTrue(view.showDecisionAnnexesSection())
        # propose item, annex sections are still shown but only decision annex is addable
        self.proposeItem(item)
        terms, show = view.showAddAnnex()
        self.assertFalse(show)
        terms, show = view.showAddAnnexDecision()
        self.assertTrue(show)
        self.assertTrue(view.showAnnexesSection())
        self.assertTrue(view.showDecisionAnnexesSection())
        # ok for reviewer
        self.changeUser('pmReviewer1')
        terms, show = view.showAddAnnex()
        self.assertTrue(show)
        terms, show = view.showAddAnnexDecision()
        self.assertTrue(show)
        self.assertTrue(view.showAnnexesSection())
        self.assertTrue(view.showDecisionAnnexesSection())

        # annexDecision section is shown if annexDecision are stored or if
        # annexDecision annex types are available (active), disable the annexDecision annex types
        for annex_type in cfg.annexes_types.item_decision_annexes.objectValues():
            self._disableObj(annex_type, notify_event=True)
        view = item.restrictedTraverse('@@categorized-annexes')
        view._update()
        # showDecisionAnnexesSection still True because annexDecision exists
        self.assertTrue(view.showDecisionAnnexesSection())
        terms, show = view.showAddAnnex()
        self.assertTrue(show)
        terms, show = view.showAddAnnexDecision()
        self.assertFalse(show)
        self.deleteAsManager(annexDecision.UID())
        view = item.restrictedTraverse('@@categorized-annexes')
        view._update()
        self.assertFalse(view.showDecisionAnnexesSection())

    def test_pm_Other_mc_correspondences_constraint(self):
        """Test for field other_mc_correspondences constraint."""
        self.changeUser('pmManager')
        cfg = self.meetingConfig
        annex_type = cfg.annexes_types.item_annexes.get(self.annexFileType)
        # get vocabulary name
        type_info = self.portal.portal_types.get(annex_type.portal_type)
        vocab_name = type_info.lookupSchema()['other_mc_correspondences'].value_type.vocabularyName
        terms = get_vocab(annex_type, vocab_name)._terms
        self.assertRaises(Invalid, other_mc_correspondences_constraint, [terms[0].value, terms[1].value])
        self.assertTrue(other_mc_correspondences_constraint([terms[0].value]))
        self.assertTrue(other_mc_correspondences_constraint([terms[1].value]))
        self.assertTrue(other_mc_correspondences_constraint([terms[-1].value]))

    def test_pm_Other_mc_correspondences_vocabulary(self):
        """Test for field other_mc_correspondences vocabulary."""
        # disable eventual cfg3
        if hasattr(self, "meetingConfig3"):
            self.changeUser("siteadmin")
            # disabled MC are listed to be able to prepare config so delete it
            self.tool.manage_delObjects([self.meetingConfig3.getId(), ])
        cfg = self.meetingConfig
        annex_type = cfg.annexes_types.item_annexes.get(self.annexFileType)
        # get vocabulary name
        type_info = self.portal.portal_types.get(annex_type.portal_type)
        vocab_name = type_info.lookupSchema()['other_mc_correspondences'].value_type.vocabularyName
        # build expected result depending on existing MC
        expected = []
        for mc in self.tool.objectValues('MeetingConfig'):
            if cfg == mc:
                continue
            mc_title = mc.Title()
            values = [
                u'{0} ➔ Item annexes ➔ *** Do not keep annex ***'.format(mc_title),
                u'{0} ➔ Item annexes ➔ Budget analysis'.format(mc_title),
                u'{0} ➔ Item annexes ➔ Budget analysis '
                u'➔ Budget analysis sub annex'.format(mc_title),
                u'{0} ➔ Item annexes ➔ Financial analysis'.format(mc_title),
                u'{0} ➔ Item annexes ➔ Financial analysis '
                u'➔ Financial analysis sub annex'.format(mc_title),
                u'{0} ➔ Item annexes ➔ Legal analysis'.format(mc_title),
                u'{0} ➔ Item annexes ➔ Other annex(es)'.format(mc_title),
                u'{0} ➔ Item decision annexes ➔ Decision annex(es)'.format(mc_title)]
            expected.extend(values)
        self.assertEqual(
            [term.title for term in get_vocab(annex_type, vocab_name)._terms],
            expected)

    def test_pm_Annex_type_only_for_meeting_managers(self):
        """An ItemAnnexContentCategory may be defined only selectable by MeetingManagers."""
        cfg = self.meetingConfig
        vocab = get_vocab(None, 'collective.iconifiedcategory.categories', only_factory=True)
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        view = item.restrictedTraverse('@@categorized-annexes')
        view._update()

        # we will make 'only_for_meeting_managers' the 'overhead-analysis' category
        # and the 'budget-analysis_-_budget-analysis-sub-annex' subcategory
        overhead_analysis = cfg.annexes_types.item_annexes.get('overhead-analysis')
        overhead_analysis_category_id = calculate_category_id(overhead_analysis)
        budget_analysis_subannex = cfg.annexes_types.item_annexes.get(
            'budget-analysis').get('budget-analysis-sub-annex')
        budget_analysis_subannex_category_id = calculate_category_id(budget_analysis_subannex)

        term_tokens = [term.token for term in vocab(annex)._terms]
        self.assertTrue(overhead_analysis_category_id in term_tokens)
        self.assertTrue(budget_analysis_subannex_category_id in term_tokens)

        # hide the 2 categories
        overhead_analysis.only_for_meeting_managers = True
        # manage cache
        notify(ObjectModifiedEvent(overhead_analysis))
        budget_analysis_subannex.only_for_meeting_managers = True
        notify(ObjectModifiedEvent(budget_analysis_subannex))

        # no more in vocabulary for 'pmCreator1'
        term_tokens = [term.token for term in vocab(annex)._terms]
        self.assertFalse(overhead_analysis_category_id in term_tokens)
        self.assertFalse(budget_analysis_subannex_category_id in term_tokens)
        self.assertTrue(view.showAddAnnex())
        self.assertTrue(view.showAddAnnexDecision())

        # in vocabulary for a MeetingManager
        self.changeUser('pmManager')
        term_tokens = [term.token for term in vocab(annex)._terms]
        self.assertTrue(overhead_analysis_category_id in term_tokens)
        self.assertTrue(budget_analysis_subannex_category_id in term_tokens)
        self.assertTrue(view.showAddAnnex())
        self.assertTrue(view.showAddAnnexDecision())

        # if it is selected on an annex, then it is not in the vocabulary
        # but it is displayed correctly in the z3c.form that uses a MissingTerms adapter
        annex2 = self.addAnnex(item, annexType='overhead-analysis')
        self.changeUser('pmCreator1')
        term_tokens = [term.token for term in vocab(annex2)._terms]
        self.assertFalse(overhead_analysis_category_id in term_tokens)
        # but correctly displayed in the widget
        annex2_view = annex2.restrictedTraverse('view')
        annex2_view.update()
        widget = annex2_view.widgets['IIconifiedCategorization.content_category']
        self.assertTrue("Administrative overhead analysis" in widget.render())
        self.assertFalse(budget_analysis_subannex_category_id in term_tokens)
        self.changeUser('pmManager')
        term_tokens = [term.token for term in vocab(annex2)._terms]
        self.assertTrue(overhead_analysis_category_id in term_tokens)
        self.assertTrue(budget_analysis_subannex_category_id in term_tokens)

        # restrict every annexTypes and decisionAnnexTypes
        self.changeUser('pmCreator1')
        for annex_type in cfg.annexes_types.item_annexes.objectValues():
            annex_type.only_for_meeting_managers = True
            # manage cache
            notify(ObjectModifiedEvent(annex_type))
        for annex_type in cfg.annexes_types.item_decision_annexes.objectValues():
            # manage cache
            notify(ObjectModifiedEvent(annex_type))
            annex_type.only_for_meeting_managers = True
        terms, show = view.showAddAnnex()
        self.assertFalse(show)
        terms, show = view.showAddAnnexDecision()
        self.assertFalse(show)
        self.assertFalse(vocab(item))
        self.changeUser('pmManager')
        terms, show = view.showAddAnnex()
        self.assertTrue(show)
        terms, show = view.showAddAnnexDecision()
        self.assertTrue(show)
        self.assertTrue(vocab(item))

    def test_pm_Actions_panel_history_only_for_managers(self):
        """The 'history' icon in the actions panel is only shown to real Managers."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex = self.addAnnex(item)
        annex_infos = get_categorized_elements(item, uids=[annex.UID()])
        annex_content = CategorizedContent(item, annex_infos[0])
        column = ActionsColumn(self.portal, self.request, self)
        self.assertFalse('@@historyview' in column.renderCell(annex_content))
        self.changeUser('pmManager')
        self.assertFalse('@@historyview' in column.renderCell(annex_content))
        self.changeUser('admin')
        self.assertTrue('@@historyview' in column.renderCell(annex_content))

    def test_pm_annex_pretty_link_column_escaped(self):
        """The various elements displayed in PrettyLinkColumn are escaped to
           avoid JS injection or else."""
        nasty_js = "<script>alert(0)</script>"
        escaped_nasty_js = "&lt;script&gt;alert(0)&lt;/script&gt;"
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        annex1 = self.addAnnex(item)
        annex2 = self.addAnnex(
            item,
            annexTitle="<script>alert(0)</script>",
            annexDescription="<script>alert(0)</script>")
        annex1_infos = get_categorized_elements(item, uids=[annex1.UID()])
        annex2_infos = get_categorized_elements(item, uids=[annex2.UID()])
        annex1_content = CategorizedContent(item, annex1_infos[0])
        annex2_content = CategorizedContent(item, annex2_infos[0])
        column = PrettyLinkColumn(self.portal, self.request, self)
        self.assertEqual(column.renderCell(annex1_content).count(nasty_js), 0)
        self.assertEqual(column.renderCell(annex1_content).count(escaped_nasty_js), 0)
        self.assertEqual(column.renderCell(annex2_content).count(nasty_js), 0)
        self.assertEqual(column.renderCell(annex2_content).count(escaped_nasty_js), 3)

    def test_pm_ParentModificationDateUpdatedWhenAnnexChanged(self):
        """When an annex is added/modified/removed, the parent modification date is updated."""

        def _check_parent_modified(parent, parent_modified, annex):
            """ """
            parent_uid = parent.UID()
            # modification date was updated
            self.assertNotEqual(parent_modified, item.modified())
            parent_modified = parent.modified()
            self.assertEqual(self.catalog(UID=parent_uid)[0].modified, parent_modified)

            # edit the annex
            notify(ObjectModifiedEvent(annex))
            # modification date was updated
            self.assertNotEqual(parent_modified, item.modified())
            parent_modified = parent.modified()
            self.assertEqual(self.catalog(UID=parent_uid)[0].modified, parent_modified)

            # remove an annex
            self.portal.restrictedTraverse('@@delete_givenuid')(annex.UID())
            # modification date was updated
            self.assertNotEqual(parent_modified, item.modified())
            parent_modified = parent.modified()
            self.assertEqual(self.catalog(UID=parent_uid)[0].modified, parent_modified)

        # on MeetingItem
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        parent_modified = item.modified()
        self.assertEqual(self.catalog(UID=item.UID())[0].modified, parent_modified)
        # add an annex
        annex = self.addAnnex(item)
        _check_parent_modified(item, parent_modified, annex)
        # add a decision annex
        decision_annex = self.addAnnex(item, relatedTo='item_decision')
        _check_parent_modified(item, parent_modified, decision_annex)

        # on Meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        parent_modified = meeting.modified()
        self.assertEqual(self.catalog(UID=meeting.UID())[0].modified, parent_modified)
        # add an annex
        annex = self.addAnnex(meeting)
        _check_parent_modified(meeting, parent_modified, annex)

    def test_pm_AnnexesCategorizedChildsCaching(self):
        """The icon displayed in various place with number of annexes is cached.
           Check classic behavior for creator to add, remove, edit annex."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        # cache is invalidated upon any change on annex create/delete/edit/change attr
        # add an annex and remove it to check that the view caching was invalidated
        view = item.restrictedTraverse('@@categorized-childs')
        no_annex_rendered = view()
        annex1 = self.addAnnex(item)
        one_annex_rendered = view()
        self.assertNotEqual(no_annex_rendered, one_annex_rendered)
        annex2 = self.addAnnex(item)
        two_annex_rendered = view()
        self.assertNotEqual(one_annex_rendered, two_annex_rendered)
        self.deleteAsManager(annex1.UID())
        one_annex_left_rendered = view()
        self.assertEqual(one_annex_left_rendered, one_annex_rendered)
        self.deleteAsManager(annex2.UID())
        no_annex_left_rendered = view()
        self.assertEqual(no_annex_left_rendered, no_annex_rendered)

    def test_pm_ConfidentialAnnexesCategorizedChildsCaching(self):
        """The icon displayed in various place with number of annexes is cached.
           It works with confidentiality."""
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        # make pmCreator1 able to change annex confidentiality
        cfg.setAnnexRestrictShownAndEditableAttributes(())
        # confidential annexes are visible by pg creators
        cfg.setItemAnnexConfidentialVisibleFor(('suffix_proposing_group_creators', ))
        # setup item and annexes
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes(
                powerObserverStates=(item_initial_state, ))
        # the view to change confidentiality
        confidential_action = annexConfidential.restrictedTraverse('@@iconified-confidential')
        confidential_action.attribute_mapping = {'confidential': 'confidential'}

        # creators may see confidential annexes
        view = item.restrictedTraverse('@@categorized-childs')
        one_annex = "<span>1</span>"
        two_annexes = "<span>2</span>"
        self.assertTrue(two_annexes in view())

        # as gp reviewer, one annex
        self.changeUser("pmReviewer1")
        self.assertTrue(one_annex in view())

        # as restrictedpowerobserver, one annex
        self.changeUser("restrictedpowerobserver1")
        self.assertTrue(one_annex in view())

        # make confidential annex no more confidential
        self.changeUser("pmCreator1")
        confidential_action()
        self.assertTrue(two_annexes in view())

        # now everyone see every annexes
        self.changeUser("pmReviewer1")
        self.assertTrue(two_annexes in view())
        self.changeUser("restrictedpowerobserver1")
        self.assertTrue(two_annexes in view())

    def test_pm_AddingAnnexesDoesNotCreateWrongCatalogPaths(self):
        """A bug due to reindeing parent when annex added was adding
           wrong path to the catalog._catalog.uids, check that it is no more the case."""
        cfg = self.meetingConfig
        self.changeUser('siteadmin')
        cfg.setItemAdviceStates(['itemcreated'])
        cfg.setItemAdviceEditStates(['itemcreated'])
        cfg.setItemAdviceViewStates(['itemcreated'])

        def _check_catalog(step=1):
            # avoid problems regarding permissions, for example
            # pmManager does not have access to disabled messages from collective.messagesviewlet
            self.changeUser('siteadmin')
            # number of path is correct, just "step" added
            self.number_of_paths += step
            self.assertEqual(len(self.catalog._catalog.uids), self.number_of_paths)
            self.assertEqual(len(self.catalog()), self.number_of_paths)
            # no paths ending with '/'
            self.assertFalse([path for path in self.catalog._catalog.uids.keys()
                              if path.endswith('/')])
            self.changeUser('pmManager')

        self.changeUser('pmManager')
        # make sure pmManager folders are created
        self.getMeetingFolder()
        self.number_of_paths = len(self.catalog._catalog.uids)
        # Item
        item = self.create('MeetingItem')
        _check_catalog()
        item_annex = self.addAnnex(item)
        _check_catalog()
        self.addAnnex(item, relatedTo='item_decision')
        _check_catalog()
        # Meeting
        meeting = self.create('Meeting')
        # meeting + 2 recurring items
        self.assertEqual(len(meeting.get_items()), 2)
        _check_catalog(step=3)
        meeting_annex = self.addAnnex(meeting)
        _check_catalog()
        # advice
        item.setOptionalAdvisers([self.developers_uid])
        item._update_after_edit()
        _check_catalog(step=0)
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.developers_uid,
               'advice_type': u'positive',
               'advice_comment': richtextval(u'My comment')})
        _check_catalog()
        advice_annex = self.addAnnex(advice)
        _check_catalog()
        # removal of everything
        self.portal.restrictedTraverse('@@delete_givenuid')(item_annex.UID())
        _check_catalog(step=-1)
        self.portal.restrictedTraverse('@@delete_givenuid')(advice_annex.UID())
        _check_catalog(step=-1)
        self.portal.restrictedTraverse('@@delete_givenuid')(advice.UID())
        _check_catalog(step=-1)
        # remove item will also remove decision annex
        self.portal.restrictedTraverse('@@delete_givenuid')(item.UID())
        _check_catalog(step=-2)
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting_annex.UID())
        _check_catalog(step=-1)
        # may only remove an empty meeting, remove 2 recurring items
        for meeting_item in meeting.get_items():
            # set it back to 'itemcreated' in case item only deletable in 'itemcreated'
            self.backToState(meeting_item, 'itemcreated')
            self.portal.restrictedTraverse('@@delete_givenuid')(meeting_item.UID())
            _check_catalog(step=-1)
        self.changeUser('pmManager')
        self.portal.restrictedTraverse('@@delete_givenuid')(meeting.UID())
        _check_catalog(step=-1)

    def test_pm_QuickUploadForm(self):
        """Test that the @@quickupload-form loads correctly."""
        self._removeConfigObjectsFor(self.meetingConfig)
        # MeetingItem
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.request.set('typeupload', 'annex')
        rendered = item.restrictedTraverse('@@quickupload-form')()
        self.assertTrue('form.widgets.content_category' in rendered)
        self.assertTrue('annexes_types-item_annexes-financial-analysis' in rendered)
        self.request.set('typeupload', 'annexDecision')
        rendered = item.restrictedTraverse('@@quickupload-form')()
        self.assertTrue('form.widgets.content_category' in rendered)
        self.assertTrue('annexes_types-item_decision_annexes-decision-annex' in rendered)
        # Meeting
        self.changeUser('pmManager')
        meeting = self.create('Meeting')
        self.request.set('typeupload', 'annex')
        rendered = meeting.restrictedTraverse('@@quickupload-form')()
        self.assertTrue('form.widgets.content_category' in rendered)
        self.assertTrue('annexes_types-meeting_annexes-meeting-annex' in rendered)
        # Folder
        # when using portlet quickupload to manage a "Documents" folder
        self.changeUser('siteadmin')
        self.request.set('typeupload', '')
        rendered = self.portal.restrictedTraverse('@@quickupload-form')()
        self.assertFalse('form.widgets.content_category' in rendered)
        self.assertTrue('form.widgets.title' in rendered)
        self.assertTrue('form.widgets.description' in rendered)

    def test_pm_AnnexShowPreview(self):
        """Test when show_preview is defined on annex type."""
        cfg = self.meetingConfig
        self._enableField('copyGroups')
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state
        cfg.setItemCopyGroupsStates((item_initial_state, ))
        cfg.setSelectableCopyGroups((self.vendors_creators, ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem', copyGroups=(self.vendors_creators, ))
        annex0 = self.addAnnex(item)
        # must be PDF
        self.assertRaises(Invalid, self.addAnnex, item, annexType='preview-annex')
        annex1 = self.addAnnex(item, annexType='preview-annex', annexFile=self.annexFilePDF)
        annex2 = self.addAnnex(item, annexType='preview-hide-download-annex')
        infos = _categorized_elements(item)
        # every annexes were converted
        self.assertEqual(infos[annex0.UID()]['preview_status'], 'not_converted')
        self.assertEqual(infos[annex1.UID()]['preview_status'], 'converted')
        self.assertEqual(infos[annex2.UID()]['preview_status'], 'converted')
        # check who may access the download button
        for observer_user_id in ('powerobserver1', 'pmCreator2'):
            self.changeUser(observer_user_id)
            self.assertTrue(self.hasPermission(View, item))
            self.assertTrue(self.hasPermission(View, annex0))
            self.assertTrue(self.hasPermission(View, annex1))
            self.assertTrue(self.hasPermission(View, annex2))
            self.assertTrue(annex0.show_download())
            self.assertTrue(annex1.show_download())
            self.assertFalse(annex2.show_download())
            # trying to download will raise Unauthorized
            self.assertTrue(annex0.restrictedTraverse('@@download')())
            self.assertTrue(annex1.restrictedTraverse('@@download')())
            self.assertRaises(Unauthorized, annex2.restrictedTraverse('@@download'))
        # but the creator may download
        self.changeUser('pmCreator1')
        self.assertTrue(annex0.show_download())
        self.assertTrue(annex1.show_download())
        self.assertTrue(annex2.show_download())
        self.assertTrue(annex0.restrictedTraverse('@@download')())
        self.assertTrue(annex1.restrictedTraverse('@@download')())
        self.assertTrue(annex2.restrictedTraverse('@@download')())
        # not kept when item duplicated
        self.changeUser('pmCreator2')
        self.assertTrue(annex2.getId() in item.objectIds())
        self.assertEqual(len(get_annexes(item)), 3)
        new_item = item.clone(copyAnnexes=True, copyDecisionAnnexes=True)
        self.assertEqual(len(get_annexes(new_item)), 2)
        self.assertFalse(annex2.getId() in new_item.objectIds())
        # handled by download annexes (as zip) batch action form
        self.request['form.widgets.uids'] = u','.join([annex0.UID(), annex1.UID(), annex2.UID()])
        self.request.form['form.widgets.uids'] = self.request['form.widgets.uids']
        self.request.form['ajax_load'] = 'dummy'
        form = item.restrictedTraverse('@@download-annexes-batch-action')
        self.assertTrue(form.available())
        form.update()
        self.assertEqual(form.annex_not_downloadable, annex2)
        self.assertRaises(Unauthorized, form.handleApply, form, None)
        # OK for pmCreator1
        self.changeUser('pmCreator1')
        form = item.restrictedTraverse('@@download-annexes-batch-action')
        self.assertTrue(form.available())
        form.update()
        self.assertIsNone(form.annex_not_downloadable)
        data = form.handleApply(form, None)
        m = magic.Magic()
        self.assertTrue(m.from_buffer(data).startswith('Zip archive data, at least v2.0 to extract'))

    def test_pm_AnonymousCanNotDownloadAnnex(self):
        """As we overrided can_view to let user download not viewable annexes
           make sure it is not accesible to anonymous."""
        cfg = self.meetingConfig
        cfg.setItemAnnexConfidentialVisibleFor(('suffix_proposing_group_creators', ))
        item_initial_state, item, annexes_table, categorized_child, \
            annexNotConfidential, annexConfidential = self._setupConfidentialityOnItemAnnexes()
        # the creator may download as confidential annexes are available to creators
        self.changeUser('pmCreator1')
        self.assertTrue(annexNotConfidential.restrictedTraverse('@@download')())
        self.assertTrue(annexConfidential.restrictedTraverse('@@download')())
        # but anonymous trying to download will raise Unauthorized
        logout()
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(View, annexNotConfidential))
        self.assertFalse(self.hasPermission(View, annexConfidential))
        self.assertRaises(Unauthorized, annexNotConfidential.restrictedTraverse('@@download'))
        self.assertRaises(Unauthorized, annexConfidential.restrictedTraverse('@@download'))
        # user that can not access will also raise Unauthorized
        self.changeUser('pmCreator2')
        self.assertFalse(self.hasPermission(View, item))
        self.assertFalse(self.hasPermission(View, annexNotConfidential))
        self.assertFalse(self.hasPermission(View, annexConfidential))
        self.assertRaises(Unauthorized, annexNotConfidential.restrictedTraverse('@@download'))
        self.assertRaises(Unauthorized, annexConfidential.restrictedTraverse('@@download'))

    def test_pm_AnnexWithScanIdRemovedWhenItemDuplicated(self):
        """Annex with scan_id will be removed when an item is duplicated."""
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        self.addAnnex(item)
        self.addAnnex(item, scan_id='001')
        self.addAnnex(item, relatedTo='item_decision')
        self.addAnnex(item, relatedTo='item_decision', scan_id='002')
        self.assertEqual(len(get_annexes(item)), 4)
        # clone
        newItem = item.clone(copyAnnexes=True, copyDecisionAnnexes=True)
        self.assertEqual(len(get_annexes(newItem)), 2)
        self.assertEqual(
            [anAnnex for anAnnex in get_annexes(newItem)
             if getattr(anAnnex, 'scan_id', None)],
            [])

    def test_pm_AnnexWithScanIdWithAnnexTypeCorrespondenceKeptWhenItemSendToOtherMC(self):
        """Annex with scan_id will be kept when item sent to another MC
           if an annex_type correspondence is defined."""
        cfg = self.meetingConfig
        cfg2 = self.meetingConfig2
        cfg2Id = cfg2.getId()
        cfg.setItemManualSentToOtherMCStates((self._stateMappingFor('itemcreated'),))
        # adapt other_mc_correspondences to set to nothing
        annexCat1 = cfg.annexes_types.item_annexes.get(self.annexFileType)
        annexCat2 = cfg2.annexes_types.item_annexes.get(self.annexFileType)
        annexCat1.other_mc_correspondences = set()

        self.changeUser('pmManager')
        item = self.create('MeetingItem', otherMeetingConfigsClonableTo=(cfg2Id,))
        annex = self.addAnnex(item, scan_id='001')
        decision_annex = self.addAnnex(item, relatedTo='item_decision', scan_id='002')
        self.assertEqual(len(get_annexes(item)), 2)
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertFalse(get_annexes(clonedItem))
        self.deleteAsManager(clonedItem.UID())

        # define a correspondence, then annex is kept but scan_id is removed
        annexCat1.other_mc_correspondences = set([annexCat2.UID()])
        clonedItem = item.cloneToOtherMeetingConfig(cfg2Id)
        self.assertEqual(len(get_annexes(clonedItem)), 1)
        self.assertIsNone(get_annexes(clonedItem)[0].scan_id)
        # not found in catalog, correctly reindexed
        self.assertTrue('scan_id' in self.catalog.Indexes)
        self.assertEqual(len(self.catalog(scan_id='001')), 1)
        self.assertEqual(self.catalog(scan_id='001')[0].UID, annex.UID())
        self.assertEqual(len(self.catalog(scan_id='002')), 1)
        self.assertEqual(self.catalog(scan_id='002')[0].UID, decision_annex.UID())


def test_suite():
    from unittest import makeSuite
    from unittest import TestSuite
    suite = TestSuite()
    suite.addTest(makeSuite(testAnnexes, prefix='test_pm_'))
    return suite
