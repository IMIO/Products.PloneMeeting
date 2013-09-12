# -*- coding: utf-8 -*-
# Copyright (c) 2008 by PloneGov
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
                 meetingTransitionInsertingMe='_init_',
                 usages=['as_recurring_item'], templateUsingGroups=[]):
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
        self.usages = usages
        self.meetingTransitionInsertingMe = meetingTransitionInsertingMe
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
    def __init__(self, id, title, theIcon, predefinedTitle,
                 decisionRelated=False, active=True):
        self.id = id
        self.setBilingual('title', title)
        self.theIcon = theIcon
        self.setBilingual('predefinedTitle', predefinedTitle)
        self.decisionRelated = decisionRelated
        self.active = active


class PodTemplateDescriptor(Descriptor):
    def __init__(self, id, title, description='', active=True):
        self.id = id
        self.setBilingual('title', title)
        self.setBilingual('description', description)
        # Filename of the POD template to use. This file must be present in the
        # "templates" folder of a profile.
        self.podTemplate = None
        self.podFormat = 'odt'
        self.podCondition = 'python:True'
        self.podPermission = 'View'
        self.freezeEvent = ''
        self.mailingLists = ''
        self.active = active


class PloneGroupDescriptor(Descriptor):
    def __init__(self, id, title, roles):
        self.id = id
        self.title = title
        self.roles = roles


class UserDescriptor(Descriptor):
    '''Useful for creating test users, so PloneMeeting may directly be tested
       after a profile has been imported.'''
    def __init__(self, id, globalRoles, email='user AT plonemeeting.org',
                 password='meeting', fullname=None):
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
    multiSelectFields = ('itemAdviceStates', 'itemAdviceEditStates', 'itemAdviceViewStates')
    # The 'instance' static attribute stores an instance used for assigning
    # default values to a meeting config being created through-the-web.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = GroupDescriptor(None, None, None)
        return klass.instance
    get = classmethod(get)

    def __init__(self, id, title, acronym, description='', active=True,
                 givesMandatoryAdviceOn='python:False',
                 asCopyGroupOn='python:False', ):
        self.id = id
        self.setBilingual('title', title)
        self.acronym = acronym
        self.setBilingual('description', description)
        self.givesMandatoryAdviceOn = givesMandatoryAdviceOn
        self.itemAdviceStates = []
        self.itemAdviceEditStates = []
        self.itemAdviceViewStates = []
        self.asCopyGroupOn = asCopyGroupOn
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


class ExternalApplicationDescriptor(Descriptor):
    multiSelectFields = ('usages', 'notifyEvents')
    # Get a prototypical instances used for getting default values.
    instance = None

    def get(klass):
        if not klass.instance:
            klass.instance = ExternalApplicationDescriptor(None, None)
        return klass.instance
    get = classmethod(get)

    def __init__(self, id, title, usages=['import'], notifyUrl='',
                 notifyEmail=''):
        self.id = id
        self.setBilingual('title', title)
        self.usages = usages
        self.notifyUrl = notifyUrl
        self.notifyEmail = notifyEmail
        self.notifyProxy = ''
        self.notifyLogin = ''
        self.notifyPassword = ''
        self.notifyProtocol = 'httpGet'
        self.notifyEvents = []
        self.notifyCondition = ''
        self.secondUrl = ''
        self.deferredMeetingImport = False


class MeetingConfigDescriptor(Descriptor):
    multiSelectFields = ('usedItemAttributes', 'historizedItemAttributes',
                         'recordItemHistoryStates', 'usedMeetingAttributes',
                         'historizedMeetingAttributes', 'recordMeetingHistoryStates',
                         'itemsListVisibleColumns', 'itemColumns', 'meetingColumns',
                         'workflowAdaptations', 'transitionsToConfirm', 'mailItemEvents',
                         'mailMeetingEvents', 'usedAdviceTypes', 'itemAdviceStates', 'itemDecidedStates',
                         'itemAdviceEditStates', 'itemAdviceViewStates', 'itemPowerObserversStates',
                         'meetingPowerObserversStates', 'meetingConfigsToCloneTo', 'itemAdviceInvalidateStates',
                         'selectableCopyGroups', 'votesEncoder', 'meetingTopicStates',
                         'decisionTopicStates', 'xhtmlTransformFields', 'xhtmlTransformTypes', 'usedVoteValues'
                         )

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

        # General parameters ---------------------------------------------------
        self.assembly = 'Person 1, Person 2'
        self.signatures = 'Person 1, Person 2, Person 3'
        self.certifiedSignatures = 'Role 1,\nPerson 1\nRole 2,\nPerson 2'
        # "Places" describe some predefined places where meetings occur. It is a
        # text widget that should contain one place per line.
        self.places = ''
        self.budgetDefault = ''
        self.defaultMeetingItemMotivation = ''
        self.folderTitle = folderTitle
        self.shortName = ''  # Will be used for deducing content types specific
        # to this MeetingConfig (item, meeting)
        self.isDefault = isDefault
        # What is the number of the last item for this meeting config ?
        self.lastItemNumber = 0
        # What is the number of the last meeting for this meeting config ?
        self.lastMeetingNumber = 0
        # Reinitialise the meeting number every year ?
        self.yearlyInitMeetingNumber = False
        # If this meeting config corresponds to an organization that identifies
        # its successive forms (ie 5th Parliament, City council 2000-2006, etc),
        # the identifier of the current form may be specified here
        # (ie 'P5', 'CC00_06'...)
        self.configVersion = ''
        self.enableAnnexToPrint = False

        # Data-related parameters ----------------------------------------------
        # Some attributes on an item are optional. In the field
        # "usedItemAttributes", you specify which of those optional attributes
        # you will use in your meeting configuration.
        self.usedItemAttributes = []
        # In the next field, you specify item fields for which you want to keep
        # track of changes.
        self.historizedItemAttributes = []
        # Some attributes on a meeting are optional, too.
        # Item states into which item events will be stored in item's history.
        self.recordItemHistoryStates = ('itempublished', 'itemfrozen',
                                        'accepted', 'refused', 'confirmed',
                                        'delayed', 'itemarchived')
        self.usedMeetingAttributes = ['assembly', 'signatures']
        # In the next field, you specify meeting fields for which you want to
        # keep track of changes.
        self.historizedMeetingAttributes = []
        # Meeting states into which item events will be stored in item's history
        self.recordMeetingHistoryStates = ('published', 'decided', 'closed',
                                           'archived')
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
            "here.getMeeting().getDate().strftime('%Y%m%d') or '') " \
            "+ '/' + str(here.getItemNumber(relativeTo='meeting'))"
        # When adding items to a meeting, must I add the items at the end of
        # the items list or at the end of the items belonging to the same
        # category or proposing group ?
        self.sortingMethodOnAddItem = "at_the_end"
        # List if item tags defined for this meeting config
        self.allItemTags = ''  # Must be terms separated by carriage returns in
        # a string.
        # Must we sort the tags in alphabetic order ?
        self.sortAllItemTags = False
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
        # default HubSessions workflows.
        self.workflowAdaptations = []
        # "Transitions to confirm" are Meeting or Item-related transitions for
        # which, in the user interface, a click on the corresponding icon or
        # button will show a confirmation popup. In this popup, the user will
        # also be able to enter the workflow comment.
        self.transitionsToConfirm = [
            # All Meeting transitions, "forward" as well as "backward".
            'Meeting.publish', 'Meeting.freeze', 'Meeting.decide',
            'Meeting.close', 'Meeting.archive',
            'Meeting.backToClosed', 'Meeting.backToDecided',
            'Meeting.backToFrozen', 'Meeting.backToPublished',
            'Meeting.republish', 'Meeting.backToCreated',
            # Some important MeetingItem transitions
            'MeetingItem.backToProposed', 'MeetingItem.backToItemCreated',
            'MeetingItem.accept', 'MeetingItem.refuse', 'MeetingItem.delay',
        ]
        self.useCopies = False
        self.selectableCopyGroups = []
        self.itemCopyGroupsStates = ['accepted', 'refused', 'delayed', ]

        # GUI-related parameters -----------------------------------------------
        # When the system displays the list of all meetings (the "all meetings"
        # topic), only meetings having one of the stated listed in
        # meetingTopicStates will be shown.
        self.meetingTopicStates = ('created', 'published', 'frozen')
        # In the "decisions" portlet, the "all decisions" portlet will only show
        # meetings having one of the states listed in decisionTopicStates.
        self.decisionTopicStates = ('decided', 'closed', 'archived')
        # Maximum number of meetings or decisions shown in the meeting and
        # decision portlets. If overflow, a combo box is shown instead of a
        # list of links.
        self.maxShownMeetings = 10
        # If a decision if maxDaysDecisions old (or older), it is not shown
        # anymore in the "decisions" portlet. This decision may still be
        # consulted by clicking on "all decisions" in the same portlet.
        self.maxDaysDecisions = 14
        # Which view do you want to select when entering a PloneMeeting folder ?
        self.meetingAppDefaultView = 'topic_searchallmeetings'
        # In the meetingitems_list.pt, you can choose which columns are shown
        self.itemsListVisibleColumns = ['state', 'categoryOrProposingGroup',
                                        'annexes', 'annexesDecision', 'actions']

        # In item-related topic results, what columns are shown?
        self.itemColumns = ['creationDate', 'creator', 'state', 'annexes',
                            'advices', 'actions']
        # In meeting-related topic results, what columns are shown?
        self.meetingColumns = ['creationDate', 'creator', 'state', 'actions']
        # Lists of available, meeting and late-items are paginated. What are
        # the maximum number of items to show at once?
        self.maxShownAvailableItems = 50
        self.maxShownMeetingItems = 50
        self.maxShownLateItems = 50
        # When showing paginated lists of items, two functions may be visible:
        # go to the page where a given item lies, and go to the meetingitem_view
        # of a given item.
        self.enableGotoPage = False
        self.enableGotoItem = True
        # When opening annexes, some users want to get them in separate windows.
        self.openAnnexesInSeparateWindows = False

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
        self.meetingFileTypes = []

        # Tasks-related parameters ---------------------------------------------
        # Macro that will be called within meetingitem_view.pt for displaying
        # tasks linked to the shown item.
        self.tasksMacro = ''
        # What role is provided by the external task module for creating tasks?
        self.taskCreatorRole = ''

        # Advices parameters ---------------------------------------------------
        # Enable / disable advices
        self.useAdvices = False
        # List of item states when it is possible to define an advice
        self.itemAdviceStates = ['proposed', 'validated', 'presented',
                                 'itempublished']
        self.itemAdviceEditStates = ['proposed', 'validated']
        self.itemAdviceViewStates = ['proposed', 'validated', 'presented', 'itempublished']
        # List of item and meeting states the users in the MeetingConfig
        # corresponding powerObservers group will see the item/meeting
        self.itemPowerObserversStates = ['itemfrozen', 'accepted', 'refused', 'delayed']
        self.meetingPowerObserversStates = ['frozen', 'decided', 'closed']
        self.usedAdviceTypes = ['positive', 'negative']
        self.defaultAdviceType = 'positive'
        # When advice mandatoriness is enabled, it is not possible to put an
        # item in a meeting while madatory advices are not all positive.
        self.enforceAdviceMandatoriness = True
        # When advice invalidation is enabled, every time an item is updated
        # after at least one advice has been given, the advice comes back to
        # 'not_given'. By "an advice is updated", we mean: button "OK" is
        # pressed on meetingitem_edit or an annex is added or deleted on it.
        self.enableAdviceInvalidation = True
        # Items where advice invalidation should be enabled.
        self.itemAdviceInvalidateStates = ['proposed', 'validated', 'presented']
        self.adviceStyle = 'standard'

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

    multiSelectFields = ('availableOcrLanguages', 'modelAdaptations',
                         'searchItemStates')

    def __init__(self, meetingFolderTitle, meetingConfigs, groups):
        self.meetingFolderTitle = meetingFolderTitle
        self.ploneDiskAware = False
        self.unoEnabledPython = ''
        self.openOfficePort = 2002
        self.functionalAdminEmail = ''
        self.functionalAdminName = ''
        self.usedColorSystem = 'no_color'
        self.colorSystemDisabledFor = ''
        self.restrictUsers = False
        self.unrestrictedUsers = ''
        self.dateFormat = '%d %mt %Y'
        self.extractTextFromFiles = False
        self.availableOcrLanguages = ('eng',)
        self.defaultOcrLanguage = 'eng'
        self.modelAdaptations = []
        self.publicUrl = ''
        self.deferredNotificationsHandling = False
        self.enableUserPreferences = True
        self.enableAnnexPreview = False
        self.siteStartDate = None
        self.maxSearchResults = 50
        self.maxShownFoundItems = 10
        self.maxShownFoundMeetings = 10
        self.maxShownFoundAnnexes = 10
        # If True, the following param will, on the search screen, display
        # radio buttons allowing to choose if item keywords encompass index
        # Title, Description, getDecision or SearchableText.
        self.showItemKeywordsTargets = True
        self.searchItemStates = []
        self.meetingConfigs = meetingConfigs  # ~[MeetingConfigDescriptor]~
        self.groups = groups  # ~[GroupDescriptor]~
        self.usersOutsideGroups = []  # ~[UserDescriptor]~
        self.externalApplications = []  # ~[ExternalApplicationDescriptor]~
# ------------------------------------------------------------------------------
