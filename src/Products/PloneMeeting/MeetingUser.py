# -*- coding: utf-8 -*-
#
# File: MeetingUser.py
#
# Copyright (c) 2013 by PloneGov
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from zope.interface import implements
import interfaces

from Products.CMFDynamicViewFTI.browserdefault import BrowserDefaultMixin

from Products.PloneMeeting.config import *

##code-section module-header #fill in your manual code here
from App.class_init import InitializeClass
from zope.i18n import translate
from Products.PloneMeeting.utils import getCustomAdapter, HubSessionsMarshaller, FakeMeetingUser, getFieldContent


# Marshaller -------------------------------------------------------------------
class MeetingUserMarshaller(HubSessionsMarshaller):
    '''Allows to marshall a meeting user into a XML file.'''
    security = ClassSecurityInfo()
    security.declareObjectPrivate()
    security.setDefaultAccess('deny')
    fieldsToMarshall = 'all'
    rootElementName = 'meetingUser'
InitializeClass(MeetingUserMarshaller)
##/code-section module-header

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
    ),
    StringField(
        name='configId',
        widget=StringField._properties['widget'](
            visible=False,
            label='Configid',
            label_msgid='PloneMeeting_label_configId',
            i18n_domain='PloneMeeting',
        ),
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
    ),
    StringField(
        name='meetingAppDefaultView',
        widget=SelectionWidget(
            description="MeetingAppDefaultView",
            description_msgid="meeting_app_default_view_descr",
            label='Meetingappdefaultview',
            label_msgid='PloneMeeting_label_meetingAppDefaultView',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listMeetingAppAvailableViews',
        default_method='getMeetingAppDefaultValue',
    ),
    StringField(
        name='mailFormat',
        widget=SelectionWidget(
            description="MailFormat",
            description_msgid="mail_format_descr",
            label='Mailformat',
            label_msgid='PloneMeeting_label_mailFormat',
            i18n_domain='PloneMeeting',
        ),
        enforceVocabulary=True,
        vocabulary='listMailFormats',
        default_method='getDefaultMailFormat',
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
        enforceVocabulary=True,
        multiValued=1,
        vocabulary='listItemsListVisibleColumns',
        default_method="getDefaultVisibleColumns",
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
        enforceVocabulary=True,
        multiValued=1,
        vocabulary="listItemColumns",
        default_method="getDefaultItemColumns",
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
        enforceVocabulary=True,
        multiValued=1,
        vocabulary="listMeetingColumns",
        default_method="getDefaultMeetingColumns",
    ),
    BooleanField(
        name='openAnnexesInSeparateWindows',
        widget=BooleanField._properties['widget'](
            description="OpenAnnexesInSeparateWindows",
            description_msgid="open_annexes_in_separate_windows_descr",
            label='Openannexesinseparatewindows',
            label_msgid='PloneMeeting_label_openAnnexesInSeparateWindows',
            i18n_domain='PloneMeeting',
        ),
        default_method="getOpenAnnexesDefaultValue",
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
        enforceVocabulary=True,
        multiValued=1,
        vocabulary="listItemEvents",
        default_method="getDefaultItemEvents",
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
        enforceVocabulary=True,
        multiValued=1,
        vocabulary="listMeetingEvents",
        default_method="getDefaultMeetingEvents",
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

MeetingUser_schema = BaseSchema.copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
# Register the marshaller for DAV/XML export.
MeetingUser_schema.registerLayer('marshall', MeetingUserMarshaller())


##/code-section after-schema

class MeetingUser(BaseContent, BrowserDefaultMixin):
    """
    """
    security = ClassSecurityInfo()
    implements(interfaces.IMeetingUser)

    meta_type = 'MeetingUser'
    _at_rename_after_creation = True

    schema = MeetingUser_schema

    ##code-section class-header #fill in your manual code here
    ##/code-section class-header

    # Methods

    # Manually created methods

    security.declarePublic('getSelf')
    def getSelf(self):
        if self.__class__.__name__ != 'MeetingUser':
            return self.context
        return self

    security.declarePublic('getBilingual')
    def getBilingual(self, name, force=None, sep='-'):
        '''Returns the possibly translated content of field named p_name.'''
        return getFieldContent(self, name, force, sep)

    security.declarePublic('adapted')
    def adapted(self):
        return getCustomAdapter(self)

    security.declareProtected('Modify portal content', 'onEdit')
    def onEdit(self, isCreated):
        '''See doc in interfaces.py.'''

    security.declarePublic('config')
    def config(self):
        return self.getParentNode().getParentNode()

    security.declarePrivate('updateMeetingUser')
    def updateMeetingUser(self):
        '''Updates this meeting user (local roles, title).'''
        # Updates the title
        userInfo = self.portal_membership.getMemberById(self.id)
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
        _ = self.translate
        res = DisplayList((
            ("assemblyMember", _('meeting_user_usage_assemblyMember', domain=d, context=self.REQUEST)),
            ("signer", _('meeting_user_usage_signer', domain=d, context=self.REQUEST)),
            ("voter", _("meeting_user_usage_voter", domain=d, context=self.REQUEST)),
            ("asker", _("meeting_user_usage_asker", domain=d, context=self.REQUEST)),
        ))
        return res

    security.declarePublic('mayConsultVote')
    def mayConsultVote(self, loggedUser, item):
        '''See doc in interfaces.py.'''
        mUser = self.getSelf()
        if (loggedUser.id == mUser.getId()) or \
           loggedUser.has_role('MeetingManager') or \
           loggedUser.has_role('Manager') or \
           item.getMeeting().adapted().isDecided():
            return True
        return False

    security.declarePublic('mayEditVote')
    def mayEditVote(self, loggedUser, item):
        '''See doc in interfaces.py.'''
        mUser = self.getSelf()
        if loggedUser.has_role('Manager'):
            return True
        meeting = item.getMeeting()
        if item.getMeeting().queryState() in meeting.meetingClosedStates:
            return False
        else:
            meetingConfig = item.portal_plonemeeting.getMeetingConfig(item)
            votesEncoder = meetingConfig.getVotesEncoder()
            if (loggedUser.id == mUser.getId()) and \
               ('theVoterHimself' in votesEncoder):
                return True
            if loggedUser.has_role('MeetingManager') and \
               ('aMeetingManager' in votesEncoder):
                return True
        return False

    security.declareProtected('Modify portal content', 'onTransferred')
    def onTransferred(self, extApp):
        '''See doc in interfaces.py.'''

    security.declarePublic('isManager')
    def isManager(self):
        '''Has logged user role Manager?'''
        user = self.portal_membership.getAuthenticatedMember()
        return user.has_role('Manager')

    def listMeetingAppAvailableViews(self):
        return self.config().listMeetingAppAvailableViews()

    def getMeetingAppDefaultValue(self):
        return self.config().getMeetingAppDefaultView()

    def listMailFormats(self):
        return self.config().listMailFormats()

    def getDefaultMailFormat(self):
        return self.config().getMailFormat()

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

    def getOpenAnnexesDefaultValue(self):
        return self.config().getOpenAnnexesInSeparateWindows()

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
        user = tool.portal_membership.getAuthenticatedMember()
        isMeetingManager = user.has_role('MeetingManager')
        isCreator = tool.userIsAmong('creators')
        isAdviser = tool.userIsAmong('advisers')
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
        cfg = meeting.portal_plonemeeting.getMeetingConfig(meeting)
        # Is this user replaced by another user ?
        if self.getId() in meeting.userReplacements:
            # Yes it is. Find the replacement.
            repl = getattr(cfg.meetingusers,
                           meeting.userReplacements[self.getId()])
            # Return the replacement user instead of this user, with adapted
            # characteristics, in the form of a FakeMeetingUser instance.
            return FakeMeetingUser(repl.getId(), repl, self)
        # Is this user a replacement for another user ?
        for baseUser, replUser in meeting.userReplacements.iteritems():
            if self.getId() != replUser:
                continue
            # Yes it is. Find the replaced person.
            repl = getattr(cfg.meetingusers, baseUser)
            # Return this user (self), but with adapted characteristics
            # (because he replaces someone else), in the form of a
            # FakeMeetingUser instance.
            return FakeMeetingUser(self.getId(), self, repl)
        return self

    security.declarePublic('isPresent')
    def isPresent(self, item, meeting):
        '''Is this user present at p_meeting when p_item is discussed?'''
        aId = self.getId()
        if aId in item.getItemAbsents():
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
# end of class MeetingUser

##code-section module-footer #fill in your manual code here
##/code-section module-footer
