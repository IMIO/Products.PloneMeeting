# -*- coding: utf-8 -*-
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

from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.config import DEFAULT_USER_PASSWORD
from Products.PloneMeeting.config import DEFAULT_LIST_TYPES


class Descriptor:
    '''This abstract class represents Python data that will be used for
       initializing an Archetypes object.'''
    multiSelectFields = []
    excludedFields = ['active']

    def getData(self, **kw):
        '''Gets data in the format needed for initializing the corresponding
           Archetypes object. Any element ik p_kw will replace the value
           from p_self.'''
        res = {}
        for k, v in self.__dict__.iteritems():
            if k in self.excludedFields:
                continue
            if k in kw:
                v = kw[k]
            if type(v) not in (list, tuple):
                res[k] = v
            else:
                if k in self.multiSelectFields:
                    res[k] = v
        # Add elements from kw that do not correspond to a field on self
        for k, v in kw.iteritems():
            if k not in self.__dict__:
                res[k] = v
        return res

    def setBilingual(self, name, value):
        '''Field named p_name is potentially a bilingual field. If it is the
           case, p_value is a tuple of strings, and not a single string value.
           In this case, we set 2 attributes instead of one on p_self, the
           second one being named like the first one suffixed with char "2".'''
        if not value or isinstance(value, basestring):
            setattr(self, name, value)
        else:
            setattr(self, name, value[0])
            setattr(self, name + '2', value[1])


class RecurringItemDescriptor(Descriptor):
    excludedFields = ['title']

    def __init__(self, id, title, proposingGroup, description='', category='',
                 associatedGroups=(), decision='', itemKeywords='', itemTags=(),
                 meetingTransitionInsertingMe='_init_'):
        self.id = id
        self.setBilingual('title', title)
        # when usage is 'as_template_item', the proposingGroup can be empty ('')
        self.proposingGroup = proposingGroup
        self.setBilingual('description', description)
        self.category = category
        self.associatedGroups = associatedGroups
        self.setBilingual('decision', decision)
        self.itemKeywords = itemKeywords
        self.itemTags = itemTags
        self.meetingTransitionInsertingMe = meetingTransitionInsertingMe


class ItemTemplateDescriptor(Descriptor):
    excludedFields = ['title']

    def __init__(self, id, title, proposingGroup, description='', category='',
                 associatedGroups=(), decision='', itemKeywords='', itemTags=(),
                 templateUsingGroups=[]):
        self.id = id
        self.setBilingual('title', title)
        # when usage is 'as_template_item', the proposingGroup can be empty ('')
        self.proposingGroup = proposingGroup
        self.setBilingual('description', description)
        self.category = category
        self.associatedGroups = associatedGroups
        self.setBilingual('decision', decision)
        self.itemKeywords = itemKeywords
        self.itemTags = itemTags
        self.templateUsingGroups = templateUsingGroups


class CategoryDescriptor(Descriptor):
    multiSelectFields = ['usingGroups', ]

    def __init__(self, id, title, description='', categoryId='',
                 usingGroups=[], active=True):
        self.id = id
        self.setBilingual('title', title)
        self.setBilingual('description', description)
        self.categoryId = categoryId
        self.usingGroups = usingGroups
        self.active = active


class MeetingFileTypeDescriptor(Descriptor):
    multiSelectFields = ('otherMCCorrespondences', 'subTypes', )

    def __init__(self, id, title, theIcon, predefinedTitle,
                 relatedTo='item', otherMCCorrespondences=(),
                 active=True, subTypes=(), isConfidentialDefault=False):
        self.id = id
        self.setBilingual('title', title)
        self.theIcon = theIcon
        self.setBilingual('predefinedTitle', predefinedTitle)
        self.relatedTo = relatedTo
        self.subTypes = subTypes
        self.isConfidentialDefault = isConfidentialDefault
        self.active = active
        self.otherMCCorrespondences = otherMCCorrespondences


class PodTemplateDescriptor(Descriptor):
    multiSelectFields = ('pod_formats', 'pod_portal_types', 'dashboard_collections_ids')

    def __init__(self, id, title, description='', enabled=True, dashboard=False):
        self.id = id
        self.title = title
        self.description = description
        # Filename of the POD template to use. This file must be present in the
        # "templates" folder of a profile.
        self.odt_file = None
        self.pod_formats = ['odt', ]
        self.pod_portal_types = []
        # ids of DashboardCollections to restrict the DashboardPODTemplate to
        self.dashboard_collections_ids = []
        self.tal_condition = ''
        #self.freezeEvent = ''
        #self.mailingLists = ''
        self.enabled = enabled
        self.dashboard = dashboard


class PloneGroupDescriptor(Descriptor):
    def __init__(self, id, title, roles):
        self.id = id
        self.title = title
        self.roles = roles


class UserDescriptor(Descriptor):
    '''Useful for creating test users, so PloneMeeting may directly be tested
       after a profile has been imported.'''
    def __init__(self, id, globalRoles, email='user AT plonemeeting.org',
                 password=DEFAULT_USER_PASSWORD, fullname=None):
        self.id = id
        self.globalRoles = globalRoles
        self.email = email.replace(' AT ', '@')  # Anti-spam
        self.password = password
        self.fullname = fullname
        self.ploneGroups = []  # ~[PloneGroupDescriptor]~


class MeetingUserDescriptor(Descriptor):
    multiSelectFields = ['usages']
    excludedFields = ['active', 'signatureImage']

    def __init__(self, id, gender='m', duty=None, replacementDuty=None,
                 usages=['voter'], signatureImage=None,
                 signatureIsDefault=False, active=True):
        self.id = id
        self.gender = gender
        self.setBilingual('duty', duty)
        self.setBilingual('replacementDuty', replacementDuty)
        self.usages = usages
        self.signatureImage = signatureImage
        self.signatureIsDefault = signatureIsDefault
        self.active = active


class GroupDescriptor(Descriptor):
    multiSelectFields = ('certifiedSignatures', 'itemAdviceStates', 'itemAdviceEditStates', 'itemAdviceViewStates')
    # The 'instance' static attribute stores an instance used for assigning
    # default values to a meeting config being created through-the-web.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = GroupDescriptor(None, None, None)
        return klass.instance
    get = classmethod(get)

    def __init__(self, id, title, acronym, description='',
                 active=True, asCopyGroupOn='', ):
        self.id = id
        self.setBilingual('title', title)
        self.acronym = acronym
        self.setBilingual('description', description)
        self.itemAdviceStates = []
        self.itemAdviceEditStates = []
        self.itemAdviceViewStates = []
        self.asCopyGroupOn = asCopyGroupOn
        self.certifiedSignatures = []
        # Add lists of users (observers, reviewers, etc) ~[UserDescriptor]~
        for role in MEETING_GROUP_SUFFIXES:
            setattr(self, role, [])
        self.active = active

    def getUsers(self):
        res = []
        for role in MEETING_GROUP_SUFFIXES:
            for user in getattr(self, role):
                if user not in res:
                    res.append(user)
        return res

    def getIdSuffixed(self, suffix='advisers'):
        return '%s_%s' % (self.id, suffix)


class MeetingConfigDescriptor(Descriptor):
    multiSelectFields = ('certifiedSignatures', 'usedItemAttributes', 'historizedItemAttributes',
                         'recordItemHistoryStates', 'usedMeetingAttributes',
                         'historizedMeetingAttributes', 'recordMeetingHistoryStates',
                         'itemsListVisibleColumns', 'itemsListVisibleFields', 'itemColumns', 'meetingColumns',
                         'workflowAdaptations', 'transitionsToConfirm', 'transitionsForPresentingAnItem',
                         'onTransitionFieldTransforms', 'onMeetingTransitionItemTransitionToTrigger',
                         'meetingPresentItemWhenNoCurrentMeetingStates',
                         'itemAutoSentToOtherMCStates', 'itemManualSentToOtherMCStates',
                         'mailItemEvents', 'mailMeetingEvents', 'usedAdviceTypes', 'itemAdviceStates',
                         'itemDecidedStates', 'itemAdviceEditStates', 'itemAdviceViewStates', 'itemBudgetInfosStates',
                         'powerAdvisersGroups', 'itemPowerObserversStates', 'meetingPowerObserversStates',
                         'itemRestrictedPowerObserversStates', 'meetingRestrictedPowerObserversStates',
                         'meetingConfigsToCloneTo', 'itemAdviceInvalidateStates', 'customAdvisers',
                         'selectableCopyGroups', 'votesEncoder', 'meetingTopicStates', 'decisionTopicStates',
                         'listTypes', 'xhtmlTransformFields', 'xhtmlTransformTypes',
                         'usedVoteValues', 'insertingMethodsOnAddItem')
    excludedFields = ['maxDaysDecisions', 'meetingAppDefaultView']

    # The 'instance' static attribute stores an instance used for assigning
    # default values to a meeting config being created through-the-web.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = MeetingConfigDescriptor(None, None, None)
        return klass.instance
    get = classmethod(get)

    def __init__(self, id, title, folderTitle, isDefault=False, active=True):
        self.id = id  # Identifier of the meeting config.
        self.setBilingual('title', title)
        self.active = active
        # ids of users that will be MeetingManagers for this MeetingConfig
        self.meetingManagers = []

        # General parameters ---------------------------------------------------
        self.assembly = 'Person 1, Person 2'
        self.signatures = 'Person 1, Person 2, Person 3'
        self.certifiedSignatures = []
        # "Places" describe some predefined places where meetings occur. It is a
        # text widget that should contain one place per line.
        self.places = ''
        self.budgetDefault = ''
        self.defaultMeetingItemMotivation = ''
        self.folderTitle = folderTitle
        self.shortName = ''  # Will be used for deducing content types specific
        # to this MeetingConfig (item, meeting)
        self.isDefault = isDefault
        self.itemIconColor = "default"
        # What is the number of the last meeting for this meeting config ?
        self.lastMeetingNumber = 0
        # Reinitialise the meeting number every year ?
        self.yearlyInitMeetingNumber = False
        # If this meeting config corresponds to an organization that identifies
        # its successive forms (ie 5th Parliament, City council 2000-2006, etc),
        # the identifier of the current form may be specified here
        # (ie 'P5', 'CC00_06'...)
        self.configVersion = ''
        self.itemCreatedOnlyUsingTemplate = False
        self.enableAnnexToPrint = 'disabled'

        # Data-related parameters ----------------------------------------------
        self.annexToPrintDefault = False
        self.annexDecisionToPrintDefault = False
        self.annexAdviceToPrintDefault = False
        # Some attributes on an item are optional. In the field
        # "usedItemAttributes", you specify which of those optional attributes
        # you will use in your meeting configuration.
        self.usedItemAttributes = []
        # In the next field, you specify item fields for which you want to keep
        # track of changes.
        self.historizedItemAttributes = []
        # Some attributes on a meeting are optional, too.
        # Item states into which item events will be stored in item's history.
        self.recordItemHistoryStates = ()
        self.usedMeetingAttributes = ['assembly', 'signatures']
        # In the next field, you specify meeting fields for which you want to
        # keep track of changes.
        self.historizedMeetingAttributes = []
        # Meeting states into which item events will be stored in item's history
        self.recordMeetingHistoryStates = ()
        # Do you want to use MeetingGroups as categories ? In this case, you
        # do not need to define categories anymore.
        self.useGroupsAsCategories = True
        # Must the "toDiscuss" value be set when inserting an item into a
        # meeting ? If no, the user having permission to write the item will be
        # able to set this value, as soon as on item creation.
        self.toDiscussSetOnItemInsert = True
        # What must be the default value for the "toDiscuss" field for normal
        # items ?
        self.toDiscussDefault = True
        # What must be the default value for the "toDiscuss" field for late
        # items ?
        self.toDiscussLateDefault = True
        # Must we show column 'toDiscuss' on lists of late items ?
        self.toDiscussShownForLateItems = True
        # What is the format of the item references ?
        # Default is Ref. MeetingDate/ItemNumberInMeeting
        self.itemReferenceFormat = "python: 'Ref. ' + (here.hasMeeting() and " \
            "here.restrictedTraverse('pm_unrestricted_methods').getLinkedMeetingDate().strftime('%Y%m%d') or '') " \
            "+ '/' + str(here.getItemNumber(relativeTo='meeting'))"
        # When adding items to a meeting, what sortingMethod must be applied successively?
        self.insertingMethodsOnAddItem = ({'insertingMethod': 'at_the_end', }, )
        # List if item tags defined for this meeting config
        self.allItemTags = ''  # Must be terms separated by carriage returns in
        # a string.
        # Must we sort the tags in alphabetic order ?
        self.sortAllItemTags = False
        # used for MeetingItem.listType vocabulary
        self.listTypes = DEFAULT_LIST_TYPES
        # What rich text fields must undergo a transform ?
        self.xhtmlTransformFields = []
        # What kind(s) of transform(s) must be applied to these fields ?
        self.xhtmlTransformTypes = []
        # The "publish" deadline, for a meeting, is the deadline for validating
        # items that must be presented to this meeting. "5.9:30" means:
        # "5 days before meeting date, at 9:30."
        self.publishDeadlineDefault = '5.9:30'
        # The "freeze" deadline, for a meeting, is the deadline for validating
        # items that must be late-presented to this meeting.
        self.freezeDeadlineDefault = '1.14:30'
        # The date for the pre-meeting is computed from the meeting date to
        # which a "delta" is applied as defined hereafter (same format as
        # above fields).
        self.preMeetingDateDefault = '4.08:30'
        # Will we manage replacements of users ?
        self.useUserReplacements = False
        # annex confidentiality
        self.enableAnnexConfidentiality = False
        self.annexConfidentialFor = ()
        # advice confidentiality
        self.enableAdviceConfidentiality = False
        self.adviceConfidentialityDefault = False
        self.adviceConfidentialFor = ()
        # List of other meetingConfigs, item of this meetingConfig
        # will be clonable to
        self.meetingConfigsToCloneTo = []

        # POD templates --------------------------------------------------------
        self.podTemplates = []
        # MeetingUsers --------------------------------------------------------
        self.meetingUsers = []  # ~[MeetingUserDescriptor]~

        # Workflow- and security-related parameters ----------------------------
        self.itemWorkflow = 'meetingitem_workflow'
        self.itemConditionsInterface = 'Products.PloneMeeting.interfaces.' \
                                       'IMeetingItemWorkflowConditions'
        self.itemActionsInterface = 'Products.PloneMeeting.interfaces.' \
                                    'IMeetingItemWorkflowActions'
        self.meetingWorkflow = 'meeting_workflow'
        self.meetingConditionsInterface = 'Products.PloneMeeting.interfaces.' \
                                          'IMeetingWorkflowConditions'
        self.meetingActionsInterface = 'Products.PloneMeeting.interfaces.' \
                                       'IMeetingWorkflowActions'
        self.itemDecidedStates = []
        # Workflow adaptations are sets of changes that can be applied to
        # default PloneMeeting workflows.
        self.workflowAdaptations = []
        # "Transitions to confirm" are Meeting or Item-related transitions for
        # which, in the user interface, a click on the corresponding icon or
        # button will show a confirmation popup. In this popup, the user will
        # also be able to enter the workflow comment.
        self.transitionsToConfirm = []
        self.transitionsForPresentingAnItem = []
        self.onTransitionFieldTransforms = []
        self.onMeetingTransitionItemTransitionToTrigger = []
        self.meetingPresentItemWhenNoCurrentMeetingStates = []
        self.itemAutoSentToOtherMCStates = ['accepted', ]
        self.itemManualSentToOtherMCStates = []
        self.useCopies = False
        self.selectableCopyGroups = []
        self.itemCopyGroupsStates = ['accepted', 'refused', 'delayed', ]
        self.hideItemHistoryCommentsToUsersOutsideProposingGroup = False
        self.restrictAccessToSecretItems = False

        # GUI-related parameters -----------------------------------------------
        # When the system displays the list of all meetings (the "all meetings"
        # topic), only meetings having one of the stated listed in
        # meetingTopicStates will be shown.
        # this will be applied on the 'searchallmeetings' Collection
        self.meetingTopicStates = ('created', 'published', 'frozen')
        # In the "decisions" portlet, the "all decisions" portlet will only show
        # meetings having one of the states listed in decisionTopicStates.
        # this will be applied on the 'searchalldecisions' Collection
        self.decisionTopicStates = ('decided', 'closed', 'archived')
        # Maximum number of meetings or decisions shown in the meeting and
        # decision portlets. If overflow, a combo box is shown instead of a
        # list of links.
        self.maxShownMeetings = 5
        # If a decision if maxDaysDecisions old (or older), it is not shown
        # anymore in the "decisions" portlet. This decision may still be
        # consulted by clicking on "all decisions" in the same portlet.
        # this will be applied on the 'searchalldecisions' Collection
        self.maxDaysDecisions = 60
        # Which view do you want to select when entering a PloneMeeting folder ?
        self.meetingAppDefaultView = 'searchallitems'
        # Columns shown on the meeting view.  Order is important!
        self.itemsListVisibleColumns = ['Creator', 'CreationDate', 'review_state',
                                        'getProposingGroup', 'actions']
        # what fields of the item will be displayed in the items listings
        # while clicking on the show more infos action (glasses icon)
        self.itemsListVisibleFields = ['MeetingItem.description', 'MeetingItem.decision']
        # columns shown on items listings.  Order is important!
        self.itemColumns = ['Creator', 'CreationDate', 'review_state',
                            'getProposingGroup', 'linkedMeetingDate', 'actions']
        # columns shown on meetings listings.  Order is important!
        self.meetingColumns = ['Creator', 'CreationDate', 'review_state', 'actions']
        # advanced filters shown
        self.dashboardItemsListingsFilters = ('c4', 'c6', 'c7', 'c8', 'c9', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15')
        self.dashboardMeetingAvailableItemsFilters = ('c4', 'c10', 'c15')
        self.dashboardMeetingLinkedItemsFilters = ('c4', 'c6', 'c7', 'c12', 'c13', 'c14', 'c15')
        # default batching value, this must be a multiple of "20"
        self.maxShownListings = "20"
        self.maxShownAvailableItems = "20"
        self.maxShownMeetingItems = "40"

        # Mail-related parameters -----------------------------------------------
        # Mail mode can be: activated, deactivated, test.
        self.mailMode = 'activated'
        self.mailFormat = 'text'  # Or html.
        # What are the item-related events that trigger mail sending ?
        self.mailItemEvents = []
        # What are the meeting-related events that trigger mail sending?
        self.mailMeetingEvents = []

        # MeetingConfig sub-objects --------------------------------------------
        self.categories = []  # ~[CategoryDescriptor]~
        self.classifiers = []  # ~[CategoryDescriptor]~
        self.recurringItems = []  # ~[RecurringItemDescriptor]~
        self.itemTemplates = []  # ~[ItemTemplateDescriptor]~
        self.meetingFileTypes = []

        # Advices parameters ---------------------------------------------------
        # Enable / disable advices
        self.useAdvices = False
        # List of item states when it is possible to define an advice
        self.itemAdviceStates = []
        self.itemAdviceEditStates = []
        self.itemAdviceViewStates = []
        # List of item states when it is possible for 'Budget impact reviewers' to edit the budgetInfos
        self.itemBudgetInfosStates = []
        # List of MeetingGroup ids to consider as Power advisers
        self.powerAdvisersGroups = []
        # List of item and meeting states the users in the MeetingConfig
        # corresponding powerObservers group will see the item/meeting
        self.itemPowerObserversStates = ['itemfrozen', 'accepted', 'refused', 'delayed']
        self.meetingPowerObserversStates = ['frozen', 'decided', 'closed']
        self.itemRestrictedPowerObserversStates = []
        self.meetingRestrictedPowerObserversStates = []
        self.usedAdviceTypes = ('positive', 'positive_with_remarks', 'negative', 'nil')
        self.defaultAdviceType = 'positive'
        # When advice mandatoriness is enabled, it is not possible to put an
        # item in a meeting while madatory advices are not all positive.
        self.enforceAdviceMandatoriness = False
        # When advice invalidation is enabled, every time an item is updated
        # after at least one advice has been given, the advice comes back to
        # 'not_given'. By "an advice is updated", we mean: button "OK" is
        # pressed on meetingitem_edit or an annex is added or deleted on it.
        self.enableAdviceInvalidation = False
        # Items where advice invalidation should be enabled.
        self.itemAdviceInvalidateStates = []
        self.adviceStyle = 'standard'
        self.defaultAdviceHiddenDuringRedaction = False
        self.transitionReinitializingDelays = ''
        self.historizeItemDataWhenAdviceIsGiven = True
        self.customAdvisers = []

        # Votes parameters -----------------------------------------------------
        self.useVotes = False
        self.votesEncoder = ('theVoterHimself',)
        self.usedVoteValues = ('not_yet', 'yes', 'no', 'abstain')
        self.defaultVoteValue = 'not_yet'
        self.voteCondition = 'True'


class PloneMeetingConfiguration(Descriptor):
    # The 'instance' static attribute stores an instance used for assigning
    # default values to the portal_plonemeeting tool when it is not initialized
    # through a profile.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = PloneMeetingConfiguration('My meetings', [], [])
        return klass.instance
    get = classmethod(get)

    multiSelectFields = ('availableOcrLanguages', 'modelAdaptations', 'workingDays', )

    def __init__(self, meetingFolderTitle, meetingConfigs, groups):
        self.meetingFolderTitle = meetingFolderTitle
        self.functionalAdminEmail = ''
        self.functionalAdminName = ''
        self.restrictUsers = False
        self.unrestrictedUsers = ''
        self.dateFormat = '%d %mt %Y'
        self.extractTextFromFiles = False
        self.availableOcrLanguages = ('eng',)
        self.defaultOcrLanguage = 'eng'
        self.modelAdaptations = []
        self.enableUserPreferences = False
        self.enableAnnexPreview = False
        self.workingDays = ('mon', 'tue', 'wed', 'thu', 'fri')
        self.holidays = [{'date': '2015/01/01', },
                         {'date': '2015/04/06', },
                         {'date': '2015/05/01', },
                         {'date': '2015/05/14', },
                         {'date': '2015/05/25', },
                         {'date': '2015/07/21', },
                         {'date': '2015/08/15', },
                         {'date': '2015/09/27', },
                         {'date': '2015/11/01', },
                         {'date': '2015/11/11', },
                         {'date': '2015/12/25', }]
        self.delayUnavailableEndDays = ()
        self.meetingConfigs = meetingConfigs  # ~[MeetingConfigDescriptor]~
        self.groups = groups  # ~[GroupDescriptor]~
        self.usersOutsideGroups = []  # ~[UserDescriptor]~
# ------------------------------------------------------------------------------
