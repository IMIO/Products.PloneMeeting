# -*- coding: utf-8 -*-
#
# File: MeetingUser.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

from AccessControl import ClassSecurityInfo
from plone import api
from Products.Archetypes.atapi import AttributeStorage
from Products.Archetypes.atapi import BaseContent
from Products.Archetypes.atapi import BaseSchema
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import ImageField
from Products.Archetypes.atapi import LinesField
from Products.Archetypes.atapi import MultiSelectionWidget
from Products.Archetypes.atapi import registerType
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import SelectionWidget
from Products.Archetypes.atapi import StringField
from Products.CMFCore.utils import getToolByName
from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin
from Products.PloneMeeting.config import PROJECTNAME
from Products.PloneMeeting.config import WriteRiskyConfig
from Products.PloneMeeting.utils import getCustomAdapter
from zope.i18n import translate
from zope.interface import implements

import interfaces


schema = Schema((

    StringField(
        name='title',
        widget=StringField._properties['widget'](
            visible=False,
            label='Title',
            label_msgid='PloneMeeting_label_title',
            i18n_domain='PloneMeeting',
        ),
        accessor="Title",
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='configId',
        widget=StringField._properties['widget'](
            visible=False,
            label='Configid',
            label_msgid='PloneMeeting_label_configId',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='gender',
        widget=SelectionWidget(
            description="MeetingUserGender",
            description_msgid="meeting_user_gender_descr",
            condition="python: here.isManager()",
            label='Gender',
            label_msgid='PloneMeeting_label_gender',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listGenders',
    ),
    StringField(
        name='duty',
        widget=StringField._properties['widget'](
            description="MeetingUserDuty",
            description_msgid="meeting_user_duty_descr",
            condition="python: here.isManager()",
            label='Duty',
            label_msgid='PloneMeeting_label_duty',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='replacementDuty',
        widget=StringField._properties['widget'](
            description="MeetingUserReplacementDuty",
            description_msgid="meeting_user_replacement_duty_descr",
            condition="python: here.isManager()",
            label='Replacementduty',
            label_msgid='PloneMeeting_label_replacementDuty',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='usages',
        widget=MultiSelectionWidget(
            description="MeetingUserUsages",
            description_msgid="meeting_user_usages_descr",
            format="checkbox",
            condition="python: here.isManager()",
            label='Usages',
            label_msgid='PloneMeeting_label_usages',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listUsages',
        write_permission="PloneMeeting: Write risky config",
    ),
    ImageField(
        name='signatureImage',
        widget=ImageField._properties['widget'](
            description="MeetingUserSignatureImage",
            description_msgid="meeting_user_signature_image_descr",
            condition="python: here.isManager()",
            label='Signatureimage',
            label_msgid='PloneMeeting_label_signatureImage',
            i18n_domain='PloneMeeting',
        ),
        storage=AttributeStorage(),
        write_permission="PloneMeeting: Write risky config",
    ),
    BooleanField(
        name='signatureIsDefault',
        default=False,
        widget=BooleanField._properties['widget'](
            description="MeetingUserSignatureIsDefault",
            description_msgid="meeting_user_signature_is_default",
            condition="python: here.isManager()",
            label='Signatureisdefault',
            label_msgid='PloneMeeting_label_signatureIsDefault',
            i18n_domain='PloneMeeting',
        ),
        write_permission="PloneMeeting: Write risky config",
    ),
    StringField(
        name='adviceStyle',
        widget=SelectionWidget(
            description="AdviceStyle",
            description_msgid="advice_style_descr",
            label='Advicestyle',
            label_msgid='PloneMeeting_label_adviceStyle',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
        vocabulary='listAdviceStyles',
        default_method="getDefaultAdviceStyle",
    ),
    LinesField(
        name='itemsListVisibleColumns',
        widget=MultiSelectionWidget(
            description="ItemsListVisibleColumns",
            description_msgid="items_list_visible_columns_descr",
            format="checkbox",
            label='Itemslistvisiblecolumns',
            label_msgid='PloneMeeting_label_itemsListVisibleColumns',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary='listItemsListVisibleColumns',
        default_method="getDefaultVisibleColumns",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='itemColumns',
        widget=MultiSelectionWidget(
            description="ItemColumns",
            description_msgid="item_columns_descr",
            format="checkbox",
            label='Itemcolumns',
            label_msgid='PloneMeeting_label_itemColumns',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary="listItemColumns",
        default_method="getDefaultItemColumns",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='meetingColumns',
        widget=MultiSelectionWidget(
            description="MeetingColumns",
            description_msgid="meeting_columns_descr",
            format="checkbox",
            label='Meetingcolumns',
            label_msgid='PloneMeeting_label_meetingColumns',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary="listMeetingColumns",
        default_method="getDefaultMeetingColumns",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='mailItemEvents',
        widget=MultiSelectionWidget(
            description="MailItemEvents",
            description_msgid="mail_item_events_descr",
            condition="python: here.listItemEvents()",
            format="checkbox",
            label='Mailitemevents',
            label_msgid='PloneMeeting_label_mailItemEvents',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary="listItemEvents",
        default_method="getDefaultItemEvents",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),
    LinesField(
        name='mailMeetingEvents',
        widget=MultiSelectionWidget(
            description="MailMeetingEvents",
            description_msgid="mail_meeting_events",
            condition="python: here.listMeetingEvents()",
            format="checkbox",
            label='Mailmeetingevents',
            label_msgid='PloneMeeting_label_mailMeetingEvents',
            i18n_domain='PloneMeeting',
        ),
        multiValued=1,
        vocabulary="listMeetingEvents",
        default_method="getDefaultMeetingEvents",
        enforceVocabulary=True,
        write_permission="PloneMeeting: Write risky config",
    ),

),
)

MeetingUser_schema = BaseSchema.copy() + \
    schema.copy()

MeetingUser_schema['id'].write_permission = "PloneMeeting: Write risky config"
MeetingUser_schema['title'].write_permission = "PloneMeeting: Write risky config"
# hide metadata fields and even protect it vy the WriteRiskyConfig permission
for field in MeetingUser_schema.getSchemataFields('metadata'):
    field.widget.visible = {'edit': 'invisible', 'view': 'invisible'}
    field.write_permission = WriteRiskyConfig


class MeetingUser(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingUser)

    meta_type = 'MeetingUser'
    _at_rename_after_creation = True

    schema = MeetingUser_schema

    security.declarePublic('getSelf')

    def getSelf(self):
        if self.getTagName() != 'MeetingUser':
            return self.context
        return self

    security.declarePublic('adapted')

    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')

    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''
        pass

    def query_state(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    security.declarePublic('config')

    def config(self):
        return self.getParentNode().getParentNode()

    security.declarePrivate('updateMeetingUser')

    def updateMeetingUser(self):
        '''Updates this meeting user (local roles, title).'''
        # Updates the title
        membershipTool = api.portal.get_tool('portal_membership')
        userInfo = membershipTool.getMemberById(self.id)
        if userInfo and userInfo.getProperty('fullname'):
            title = userInfo.getProperty('fullname')
        else:
            title = self.id
        self.setTitle(title)
        self.setConfigId(self.config().id)
        # Update local roles. Corresponding Plone user owns me.
        if 'Owner' not in self.get_local_roles_for_userid(self.id):
            self.manage_addLocalRoles(self.id, ('Owner',))

    security.declarePrivate('at_post_create_script')

    def at_post_create_script(self):
        self.updateMeetingUser()
        self.adapted().onEdit(isCreated=True)

    security.declarePrivate('at_post_edit_script')

    def at_post_edit_script(self):
        self.updateMeetingUser()
        self.adapted().onEdit(isCreated=False)

    def listGenders(self):
        '''Lists the genders (M, F).'''
        res = DisplayList((
            ("m", translate('gender_m', domain='PloneMeeting', context=self.REQUEST)),
            ("f", translate('gender_f', domain='PloneMeeting', context=self.REQUEST)),
        ))
        return res

    def listUsages(self):
        '''Returns list of possible usages (for what will this user be useful
           in voting process: "assembly member", "signer" or "voter").'''
        d = 'PloneMeeting'
        res = DisplayList((
            ("assemblyMember", translate('meeting_user_usage_assemblyMember', domain=d, context=self.REQUEST)),
            ("signer", translate('meeting_user_usage_signer', domain=d, context=self.REQUEST)),
            ("voter", translate("meeting_user_usage_voter", domain=d, context=self.REQUEST)),
            ("asker", translate("meeting_user_usage_asker", domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('mayConsultVote')

    def mayConsultVote(self, loggedUser, item):
        '''See doc in interfaces.py.'''
        mUser = self.getSelf()
        tool = getToolByName(mUser, 'portal_plonemeeting')
        if (loggedUser.id == mUser.getId()) or \
           tool.isManager(item) or \
           item.getMeeting().adapted().isDecided():
            return True
        return False

    security.declarePublic('mayEditVote')

    def mayEditVote(self, loggedUser, item):
        '''See doc in interfaces.py.'''
        mUser = self.getSelf()
        tool = getToolByName(item, 'portal_plonemeeting')
        if loggedUser.has_role('Manager'):
            return True
        meeting = item.getMeeting()
        if item.getMeeting().query_state() in meeting.meetingClosedStates:
            return False
        else:
            cfg = tool.getMeetingConfig(item)
            votesEncoder = cfg.getVotesEncoder()
            if (loggedUser.id == mUser.getId()) and \
               ('theVoterHimself' in votesEncoder):
                return True
            if tool.isManager(item) and \
               ('aMeetingManager' in votesEncoder):
                return True
        return False

    security.declarePublic('isManager')

    def isManager(self):
        '''Has logged user role Manager?'''
        membershipTool = api.portal.get_tool('portal_membership')
        user = membershipTool.getAuthenticatedMember()
        return user.has_role('Manager')

    def listAdviceStyles(self):
        return self.config().listAdviceStyles()

    def getDefaultAdviceStyle(self):
        return self.config().getAdviceStyle()

    def listItemsListVisibleColumns(self):
        return self.config().listItemsListVisibleColumns()

    def getDefaultVisibleColumns(self):
        return self.config().getItemsListVisibleColumns()

    def listItemColumns(self):
        return self.config().listItemColumns()

    def getDefaultItemColumns(self):
        return self.config().getItemColumns()

    def listMeetingColumns(self):
        return self.config().listMeetingColumns()

    def getDefaultMeetingColumns(self):
        return self.config().getMeetingColumns()

    def listItemEvents(self):
        config = self.config()
        allEvents = config.listItemEvents()
        selectedEvents = config.getMailItemEvents()
        # From the list of all events that are selectable in the config
        # (=configItemEvents), the user may only (de)activate events
        # that are selected in the config (=selectedEvents). Among
        # selectedEvents, the user may only (de)activate events that make sense
        # (ie, if the user is not an adviser, it has no sense to propose him to
        # (de)activate events sent to an adviser).
        res = []
        # We must know if the user is a MeetingManager, an item creator or
        # adviser
        tool = config.getParentNode()
        isMeetingManager = tool.isManager(config)
        isCreator = tool.userIsAmong(['creators'])
        isAdviser = tool.userIsAmong(['advisers'])
        for event in selectedEvents:
            keepIt = False
            if (event in ('lateItem', 'annexAdded', 'askDiscussItem')) and \
               isMeetingManager:
                keepIt = True
            elif event in ('itemPresented', 'itemUnpresented', 'itemDelayed', 'itemClonedToThisMC') and isCreator:
                keepIt = True
            elif event in ('adviceToGive', 'adviceInvalidated') and isAdviser:
                keepIt = True
            elif event == 'adviceEdited':
                keepIt = True  # This event requires permission "View".
            if keepIt:
                res.append((event, allEvents.getValue(event)))
        return DisplayList(tuple(res))

    def getDefaultItemEvents(self):
        return self.listItemEvents().keys()

    def listMeetingEvents(self):
        config = self.config()
        allEvents = config.listMeetingEvents()
        # On an archive site, there may be no transition defined on a meeting.
        if not allEvents.keys():
            return DisplayList()
        selectedEvents = config.getMailMeetingEvents()
        res = []
        # Here, I could only keep transitions for which the user has the
        # permission to View the meeting at its end state. But in most cases,
        # meeting-related events can be seen by everyone.
        for event in selectedEvents:
            eventValue = allEvents.getValue(event)
            if not eventValue:
                continue
            res.append((event, eventValue))
        return DisplayList(tuple(res))

    def getDefaultMeetingEvents(self):
        return self.listMeetingEvents().keys()

    def getForUseIn(self, meeting):
        '''Gets the user as playing a role in p_meeting, taking into account
           possible user replacements.'''
        if not hasattr(meeting.aq_base, 'userReplacements'):
            return self
        # cfg = meeting.portal_plonemeeting.getMeetingConfig(meeting)
        # Is this user replaced by another user ?
        if self.getId() in meeting.userReplacements:
            # Yes it is. Find the replacement.
            # repl = getattr(cfg.meetingusers,
            #                meeting.userReplacements[self.getId()])
            # Return the replacement user instead of this user, with adapted
            # characteristics, in the form of a FakeMeetingUser instance.
            return None
        # Is this user a replacement for another user ?
        for baseUser, replUser in meeting.userReplacements.iteritems():
            if self.getId() != replUser:
                continue
            # Yes it is. Find the replaced person.
            # repl = getattr(cfg.meetingusers, baseUser)
            # Return this user (self), but with adapted characteristics
            # (because he replaces someone else), in the form of a
            # FakeMeetingUser instance.
            return None
        return self

    security.declarePublic('isPresent')

    def isPresent(self, item, meeting):
        '''Is this user present at p_meeting when p_item is discussed?'''
        aId = self.getId()
        if aId in item.get_item_absents():
            return False
        if aId in meeting.getLateAttendees():
            entranceNumber = meeting.getEntranceItem(aId)
            if not entranceNumber or \
               (entranceNumber > item.getItemNumber(relativeTo='meeting')):
                return False
        if aId in meeting.getDepartures(item, when='before', alsoEarlier=True):
            return False
        return True

    security.declarePublic('indexUsages')

    def indexUsages(self):
        '''Returns the index content for usages.'''
        return self.getUsages()


registerType(MeetingUser, PROJECTNAME)
