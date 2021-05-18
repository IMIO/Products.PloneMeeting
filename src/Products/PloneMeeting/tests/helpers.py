# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import select_organization
from DateTime import DateTime
from imio.helpers.cache import cleanRamCacheFor
from plone import api
from plone.app.testing import logout
from plone.app.textfield.value import RichTextValue
from plone.dexterity.utils import createContentInContainer
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View


class PloneMeetingTestingHelpers:
    '''Stub class that provides some helper methods about testing.'''

    TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_1 = TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_2 = ('propose', )
    TRANSITIONS_FOR_PROPOSING_ITEM_1 = TRANSITIONS_FOR_PROPOSING_ITEM_2 = ('propose', 'prevalidate', )

    TRANSITIONS_FOR_VALIDATING_ITEM_1 = TRANSITIONS_FOR_VALIDATING_ITEM_2 = ('propose', 'validate', )
    TRANSITIONS_FOR_PREVALIDATING_ITEM_1 = TRANSITIONS_FOR_PREVALIDATING_ITEM_2 = ('propose', 'prevalidate', )
    TRANSITIONS_FOR_PRESENTING_ITEM_1 = TRANSITIONS_FOR_PRESENTING_ITEM_2 = (
        'propose', 'prevalidate', 'validate', 'present', )

    TRANSITIONS_FOR_PUBLISHING_MEETING_1 = TRANSITIONS_FOR_PUBLISHING_MEETING_2 = ('publish', )
    TRANSITIONS_FOR_FREEZING_MEETING_1 = TRANSITIONS_FOR_FREEZING_MEETING_2 = ('publish', 'freeze', )
    TRANSITIONS_FOR_DECIDING_MEETING_1 = TRANSITIONS_FOR_DECIDING_MEETING_2 = ('publish', 'freeze', 'decide', )
    TRANSITIONS_FOR_CLOSING_MEETING_1 = TRANSITIONS_FOR_CLOSING_MEETING_2 = ('publish',
                                                                             'freeze',
                                                                             'decide',
                                                                             'close', )
    TRANSITIONS_FOR_ACCEPTING_ITEMS_MEETING_1 = TRANSITIONS_FOR_ACCEPTING_ITEMS_MEETING_2 = ('publish', 'freeze', )
    BACK_TO_WF_PATH_1 = BACK_TO_WF_PATH_2 = {
        # Meeting
        'created': ('backToDecided',
                    'backToFrozen',
                    'backToPublished',
                    'backToCreated',),
        # MeetingItem
        'itemcreated': ('backToItemPublished',
                        'backToItemFrozen',
                        'backToPresented',
                        'backToValidated',
                        'backToProposed',
                        'backToItemCreated', ),
        'proposed': ('backToItemPublished',
                     'backToItemFrozen',
                     'backToPresented',
                     'backToValidated',
                     'backToProposed', ),
        'validated': ('backToItemPublished',
                      'backToItemFrozen',
                      'backToPresented',
                      'backToValidated', ),
        'presented': ('backToItemPublished',
                      'backToItemFrozen',
                      'backToItemPublished',
                      'backToPresented', )}

    WF_ITEM_STATE_NAME_MAPPINGS_1 = {'itemcreated': 'itemcreated',
                                     'proposed_first_level': 'proposed',
                                     'proposed': 'proposed',
                                     'validated': 'validated',
                                     'presented': 'presented',
                                     'itemfrozen': 'itemfrozen'}
    WF_ITEM_STATE_NAME_MAPPINGS_2 = {'itemcreated': 'itemcreated',
                                     'proposed_first_level': 'proposed',
                                     'proposed': 'proposed',
                                     'validated': 'validated',
                                     'presented': 'presented',
                                     'itemfrozen': 'itemfrozen'}
    WF_MEETING_STATE_NAME_MAPPINGS_1 = {'frozen': 'frozen'}
    WF_MEETING_STATE_NAME_MAPPINGS_2 = {'frozen': 'frozen'}

    WF_ITEM_TRANSITION_NAME_MAPPINGS_1 = {
        'backToItemCreated': 'backToItemCreated',
        'backToProposed': 'backToProposed', }
    WF_ITEM_TRANSITION_NAME_MAPPINGS_2 = {
        'backToItemCreated': 'backToItemCreated',
        'backToProposed': 'backToProposed', }
    WF_MEETING_TRANSITION_NAME_MAPPINGS_1 = {}
    WF_MEETING_TRANSITION_NAME_MAPPINGS_2 = {}

    # in which state an item must be after a particular meeting transition?
    ITEM_WF_STATE_AFTER_MEETING_TRANSITION = {'publish_decisions': 'confirmed',
                                              'close': 'confirmed', }

    def _stateMappingFor(self, state_name, meta_type='MeetingItem'):
        """ """
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        pattern = ''
        if meta_type == 'MeetingItem':
            pattern = 'WF_ITEM_STATE_NAME_MAPPINGS_%d'
        else:
            pattern = 'WF_MEETING_STATE_NAME_MAPPINGS_%d'
        return getattr(self, (pattern % meetingConfigNumber)).get(state_name, state_name)

    def _transitionMappingFor(self, transition_name, meta_type='MeetingItem'):
        """ """
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        pattern = ''
        if meta_type == 'MeetingItem':
            pattern = 'WF_ITEM_TRANSITION_NAME_MAPPINGS_%d'
        else:
            pattern = 'WF_MEETING_TRANSITION_NAME_MAPPINGS_%d'
        return getattr(self, (pattern % meetingConfigNumber)).get(transition_name, transition_name)

    def _createMeetingWithItems(self, meetingDate=DateTime()):
        '''Create a meeting with a bunch of items.'''
        def _set_proposing_group(item, org):
            """Take into account fact that configuration uses groupsInCharge."""
            groups_in_charge = org.groups_in_charge
            if groups_in_charge:
                item.setProposingGroupWithGroupInCharge(
                    '{0}__groupincharge__{1}'.format(
                        org.UID(), groups_in_charge[0]))
            else:
                item.setProposingGroup(org.UID())
        meeting = self.create('Meeting', date=meetingDate)
        # a meeting could be created with items if it has
        # recurring items...  But we can also add some more...
        # id=item-1
        item1 = self.create('MeetingItem', title='Item 1')
        _set_proposing_group(item1, self.vendors)
        item1.setAssociatedGroups((self.developers_uid,))
        item1.setPrivacy('public')
        item1.setPollType('secret_separated')
        item1.setCategory('research')
        item1.setClassifier('classifier3')
        # id=item-2
        item2 = self.create('MeetingItem', title='Item 2')
        _set_proposing_group(item2, self.developers)
        item2.setPrivacy('public')
        item2.setPollType('no_vote')
        item2.setCategory('development')
        item2.setClassifier('classifier2')
        # id=item-3
        item3 = self.create('MeetingItem', title='Item 3')
        _set_proposing_group(item3, self.vendors)
        item3.setPrivacy('secret')
        item3.setPollType('freehand')
        item3.setCategory('development')
        item3.setClassifier('classifier2')
        # id=item-4
        item4 = self.create('MeetingItem', title='Item 4')
        _set_proposing_group(item4, self.developers)
        item4.setPrivacy('secret')
        item4.setPollType('freehand')
        item4.setCategory('events')
        item4.setClassifier('classifier1')
        # id=item-5
        item5 = self.create('MeetingItem', title='Item 5')
        _set_proposing_group(item5, self.vendors)
        item5.setPrivacy('public')
        item5.setPollType('secret')
        item5.setCategory('events')
        item5.setClassifier('classifier1')
        for item in (item1, item2, item3, item4, item5):
            item.setDecision('<p>A decision</p>')
            self.presentItem(item)
        return meeting

    def _getTransitionsToCloseAMeeting(self):
        """ """
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        return getattr(self, ('TRANSITIONS_FOR_CLOSING_MEETING_%d' % meetingConfigNumber))

    def _getNecessaryMeetingTransitionsToAcceptItem(self):
        '''Returns the necessary transitions to trigger on the Meeting before being
           able to accept an item.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        return getattr(self, ('TRANSITIONS_FOR_ACCEPTING_ITEMS_MEETING_%d' % meetingConfigNumber))

    def get_transitions_for_proposing_item(self, first_level=False):
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        if first_level:
            return getattr(
                self, ('TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_%d' % meetingConfigNumber))
        else:
            return getattr(
                self, ('TRANSITIONS_FOR_PROPOSING_ITEM_%d' % meetingConfigNumber))

    def proposeItem(self, item, first_level=False, as_manager=True):
        '''Propose passed p_item using TRANSITIONS_FOR_PROPOSING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PROPOSING_ITEM_x is 1 or 2.
           If p_first_level is True, we will use TRANSITIONS_FOR_PROPOSING_ITEM_FIRST_LEVEL_x,
           this makes it possible to reach an intermediate propose level.'''
        self._doTransitionsFor(item,
                               self.get_transitions_for_proposing_item(first_level),
                               as_manager=as_manager)

    def prevalidateItem(self, item, as_manager=True):
        '''Prevalidate passed p_item using TRANSITIONS_FOR_PREVALIDATING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PREVALIDATING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            item,
            getattr(self, ('TRANSITIONS_FOR_PREVALIDATING_ITEM_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def validateItem(self, item, as_manager=True):
        '''Validate passed p_item using TRANSITIONS_FOR_VALIDATING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_VALIDATING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            item,
            getattr(self, ('TRANSITIONS_FOR_VALIDATING_ITEM_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def presentItem(self, item, as_manager=True):
        '''Present passed p_item using TRANSITIONS_FOR_PRESENTING_ITEM_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PRESENTING_ITEM_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            item,
            getattr(self, ('TRANSITIONS_FOR_PRESENTING_ITEM_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def publishMeeting(self, meeting, as_manager=False):
        '''Publish passed p_meeting using TRANSITIONS_FOR_PUBLISHING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_PUBLISHING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            meeting,
            getattr(self, ('TRANSITIONS_FOR_PUBLISHING_MEETING_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def freezeMeeting(self, meeting, as_manager=False):
        '''Freeze passed p_meeting using TRANSITIONS_FOR_FREEZING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_FREEZING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            meeting,
            getattr(self, ('TRANSITIONS_FOR_FREEZING_MEETING_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def decideMeeting(self, meeting, as_manager=False):
        '''Decide passed p_meeting using TRANSITIONS_FOR_DECIDING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_DECIDING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            meeting,
            getattr(self, ('TRANSITIONS_FOR_DECIDING_MEETING_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def closeMeeting(self, meeting, as_manager=False):
        '''Close passed p_meeting using TRANSITIONS_FOR_CLOSING_MEETING_x.
           The p_meetingConfigNumber specify if we use meetingConfig or meetingConfig2, so
           the _x here above in TRANSITIONS_FOR_CLOSING_MEETING_x is 1 or 2.'''
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        self._doTransitionsFor(
            meeting,
            getattr(self, ('TRANSITIONS_FOR_CLOSING_MEETING_%d' % meetingConfigNumber)),
            as_manager=as_manager)

    def backToState(self, itemOrMeeting, state, as_manager=True):
        """Set the p_item back to p_state.
           Given p_state MUST BE original state name, aka state existing in PloneMeeting workflow."""
        # if a wf path is defined in BACK_TO_WF_PATH_x to go to relevant state, use it
        # if not, trigger every 'backToXXX' existing transition
        meetingConfigNumber = self._determinateUsedMeetingConfigNumber()
        BACK_TO_WF_PATH = getattr(self, 'BACK_TO_WF_PATH_%d' % meetingConfigNumber)
        useDefinedWfPath = False
        # check if a mapping exist for state name, returns original state if no mapping exists
        state = self._stateMappingFor(state)
        if state in BACK_TO_WF_PATH:
            transitions = BACK_TO_WF_PATH[state]
            useDefinedWfPath = True
        # do things as admin to avoid permission issues
        if as_manager:
            currentUser = self.member.getId()
            self.changeUser('admin')
        max_attempts = 20
        nb_attempts = 0
        while not itemOrMeeting.queryState() == state and nb_attempts <= max_attempts:
            nb_attempts += 1
            if not useDefinedWfPath:
                transitions = self.transitions(itemOrMeeting)
            for tr in transitions:
                if (tr.startswith('back') or useDefinedWfPath) and tr in self.transitions(itemOrMeeting):
                    self.do(itemOrMeeting, tr)
                    break
        if nb_attempts >= max_attempts or state != itemOrMeeting.queryState():
            raise ValueError('impossible to go back to {}'.format(state))
        if as_manager:
            self.changeUser(currentUser)

    def _doTransitionsFor(self, itemOrMeeting, transitions, as_manager=False):
        """Helper that just trigger given p_transitions on given p_itemOrMeeting."""
        # do things as admin to avoid permission issues
        if as_manager:
            currentUser = self.member.getId()
            self.changeUser('admin')
        for tr in transitions:
            if tr in self.transitions(itemOrMeeting):
                self.do(itemOrMeeting, tr)
        if as_manager:
            self.changeUser(currentUser)

    def _determinateUsedMeetingConfigNumber(self):
        """Helper method that check if we use meetingConfig or meetingConfig2."""
        if self.meetingConfig.getId() == self.meetingConfig2.getId():
            # we are using meetingConfig2
            return 2
        return 1

    def _removeAllMembers(self, group, members):
        """Allow to remove all members from a group.
           Overrided to do it as 'Manager' to be able not
           to change permissions ever lines"""
        from plone.app.testing.helpers import setRoles
        currentMember = api.user.get_current()
        currentMemberRoles = currentMember.getRoles()
        setRoles(self.portal, currentMember.getId(), currentMemberRoles + ['Manager', ])
        for member in members:
            group.removeMember(member)
        setRoles(self.portal, currentMember.getId(), currentMemberRoles)

    def _addAllMembers(self, group, members):
        """Allow to add again all the members from a group.
           Overrided to do it as 'Manager' to be able not
           to change permissions ever lines"""
        from plone.app.testing.helpers import setRoles
        currentMember = api.user.get_current()
        currentMemberRoles = currentMember.getRoles()
        setRoles(self.portal, currentMember.getId(), currentMemberRoles + ['Manager', ])
        for member in members:
            group.addMember(member)
        setRoles(self.portal, currentMember.getId(), currentMemberRoles)

    def _removeUsersFromEveryGroups(self, user_ids):
        """Remove extra users from their groups to not break test,
           useful for profiles having extra users or roles."""
        for extra_user_id in user_ids:
            user = api.user.get(extra_user_id)
            # remove from every groups, bypass Plone groups (including virtual)
            for group_id in [user_group_id for user_group_id in user.getGroups()
                             if '_' in user_group_id]:
                api.group.remove_user(groupname=group_id, username=extra_user_id)
        cleanRamCacheFor('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')

    def _initial_state(self, obj):
        """Return the workflow initial_state of given p_obj."""
        wf_name = self.wfTool.getWorkflowsFor(obj)[0].getId()
        return self.wfTool[wf_name].initial_state

    def _make_not_found_user(self, user_id='new_test_user'):
        """Add a p_user_id member to the p_group_id group then delete it."""
        currentUser = self.member.getId()
        self.changeUser('admin')
        membershipTool = api.portal.get_tool('portal_membership')
        membershipTool.addMember(id=user_id,
                                 password='12345',
                                 roles=('Member', ),
                                 domains=())
        self._addPrincipalToGroup(user_id, self.developers_creators)
        membershipTool.deleteMembers((user_id, ))
        # now we have a 'not found' user in developers_creators
        self.assertTrue((user_id, '<{0}: not found>'.format(user_id)) in
                        self.portal.acl_users.source_groups.listAssignedPrincipals(self.developers_creators))
        # groupData.getGroupMembers/groupData.getGroupMemberIds ignore not found
        self.assertFalse(user_id in api.group.get(self.developers_creators).getGroupMemberIds())
        self.changeUser(currentUser)

    def _check_access(self, obj, userIds=[], read=True, write=True):
        """ """
        original_user_id = self.member.getId()
        # no userIds means use current user id
        if not userIds:
            userIds = [original_user_id]
        for userId in userIds:
            self.changeUser(userId)
            if read:
                self.assertTrue(self.hasPermission(View, obj))
            else:
                self.assertFalse(self.hasPermission(View, obj))
            if write:
                self.assertTrue(self.hasPermission(ModifyPortalContent, obj))
            else:
                self.assertFalse(self.hasPermission(ModifyPortalContent, obj))
        self.changeUser(original_user_id)

    def _setupStorePodAsAnnex(self):
        """ """
        cfg = self.meetingConfig
        pod_template = cfg.podtemplates.itemTemplate
        annex_type = cfg.annexes_types.item_annexes.get('item-annex')
        pod_template.store_as_annex = annex_type.UID()
        self.request.set('template_uid', pod_template.UID())
        self.request.set('output_format', 'odt')
        self.request.set('store_as_annex', '1')
        # create an item
        original_member_id = self.member.getId()
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        if original_member_id:
            self.changeUser(original_member_id)
        return pod_template, annex_type, item

    def _setupItemWithAdvice(self):
        """Create an item and adds an advice to it."""
        cfg = self.meetingConfig
        cfgItemWF = self.wfTool.getWorkflowsFor(cfg.getItemTypeName())[0]
        item_initial_state = self.wfTool[cfgItemWF.getId()].initial_state

        cfg.setItemAdviceStates((item_initial_state, ))
        cfg.setItemAdviceEditStates((item_initial_state, ))
        self.changeUser('pmCreator1')
        item = self.create('MeetingItem')
        item.setOptionalAdvisers((self.vendors_uid, ))
        item.updateLocalRoles()
        self.changeUser('pmReviewer2')
        advice = createContentInContainer(
            item,
            'meetingadvice',
            **{'advice_group': self.vendors_uid,
               'advice_type': u'positive',
               'advice_comment': RichTextValue(u'My comment')})
        return item, advice

    def _setUpGroupsInCharge(self, item, groups=[]):
        """As group in charge is an adaptable method, it may be setup differently."""
        if not groups:
            groups = [self.vendors_uid]
        item.setGroupsInCharge(groups)
        item.updateLocalRoles()

    def _tearDownGroupsInCharge(self, item):
        """If group in charge is overrided, it may be setup differently."""
        item.setGroupsInCharge([])

    def _select_organization(self, org_uid, remove=False):
        """Select organization in ORGANIZATIONS_REGISTRY."""
        select_organization(org_uid, remove=remove)
        self.cleanMemoize()

    def _setUpOrderedContacts(self):
        """ """
        # login to be able to query held_positions for orderedContacts vocabulary
        self.changeUser('siteadmin')
        cfg = self.meetingConfig
        cfg.setUsedMeetingAttributes(('attendees', 'excused', 'absents', 'signatories', ))
        cfg.setUsedItemAttributes(('attendees', 'excused', 'absents', 'signatories', 'itemInitiator'))
        ordered_contacts = cfg.getField('orderedContacts').Vocabulary(cfg).keys()
        cfg.setOrderedContacts(ordered_contacts)
        logout()
