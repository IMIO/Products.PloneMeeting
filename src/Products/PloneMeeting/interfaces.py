# -*- coding: utf-8 -*-
#
# File: interfaces.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from zope.interface import Interface

##code-section HEAD
from zope.component.interfaces import IObjectEvent
from zope.publisher.interfaces.browser import IBrowserRequest


class IFacetedSearchesMarker(Interface):
    """
      Marker interface applied to the 'searches'
      folder added to each MeetingConfig.
    """


class IFacetedSearchesMeetingItemsMarker(Interface):
    """
      Marker interface applied to the 'searches/meetingitems'
      folder added to each MeetingConfig.
    """


class IFacetedSearchesMeetingsMarker(Interface):
    """
      Marker interface applied to the 'searches/meetings'
      folder added to each MeetingConfig.
    """


class IFacetedSearchesDecisionsMarker(Interface):
    """
      Marker interface applied to the 'searches/decisions'
      folder added to each MeetingConfig.
    """


class IAdvicesUpdatedEvent(IObjectEvent):
    """
    """


class IItemDuplicatedEvent(IObjectEvent):
    """
    """


class IItemDuplicatedFromConfigEvent(IObjectEvent):
    """
    """


class IItemAfterTransitionEvent(IObjectEvent):
    """
    """


class IRedirect(Interface):
    """
    """
    def redirect():
        """
          Redirect to the right place in case we use plone.app.jquerytools overlays
        """


class IPloneMeetingLayer(IBrowserRequest):
    """
      Define a layer so some elements are only added for it
    """
    pass


class IAnnexable(Interface):
    """
      Adapter interface that manage elements than contains annexes.
    """

    def addAnnex(context):
        """
          Create an annex (MeetingFile) with given parameters and adds it to this item.
        """

    def isValidAnnexId(context, idCandidate):
        """
          May p_idCandidate be used for a new annex that will be linked to this item?
        """

    def getAnnexesToPrint(context, relatedTo='item'):
        """
          Creates a list of annexes to print for document generation
          The result is a list containing dicts where first key is the annex title
          and second key is a tuple of path where to find relevant images to print :
          [
           {'title': 'My annex title',
            'UID': 'annex_UID',
            'number_of_images': 2,
            'images': [{'image_number': 1,
                        'image_path': '/path/to/image1.png',},
                       {'image_number': 2,
                        'image_path': '/path/to/image2.png',},
                      ]},
           {'title': 'My annex2 title',
            'UID': 'annex2_UID',
            'number_of_images': 1,
            'images': [{'image_number': 1,
                        'image_path': '/path/to/image21.png',},
                      ]},
          ]
          Returned annexes depend on the p_relatedTo value.
        """

    def updateAnnexIndex(context, annex=None, removeAnnex=False):
        """
          This method updates self.annexIndex (see doc in
          MeetingItem.__init__). If p_annex is None, this method recomputes the
          whole annexIndex. If p_annex is not None:
          - if p_remove is False, info about the newly created p_annex is added
            to self.annexIndex;
          - if p_remove is True, info about the deleted p_annex is removed from
            self.annexIndex.
        """

    def getAnnexes(context, relatedTo=None):
        """
          Returns contained annexes respecting order (container is ordered).
          It returns annexes depending on p_relatedTo.  If p_relatedTo is None,
          every annexes are returned, no matter the relatedTo.
        """

    def getLastInsertedAnnex(context):
        """
          Gets the last inserted annex on this item, regardless relatedTo.
        """

    def getAnnexesByType(context, relatedTo, makeSubLists=True,
                         typesIds=[], realAnnexes=False):
        """
          Returns an annexInfo dict (or real annex objects if p_realAnnexes is
          True) for every annex linked to me:
          - p_relatedTo will filter annexes depending on MeetingFileType.relatedTo value.
          - if p_makeSubLists is True, the result (a list) contains a
            subList containing all annexes of a given type; if False,
            the result is a single list containing all requested annexes,
            sorted by annex type.
          If p_typesIds in not empty, only annexes of types having ids
          listed in this param will be returned.
          In all cases, within each annex type annexes are sorted by
          creation date (more recent last).
        """
##/code-section HEAD


class IMeetingItem(Interface):
    """Marker interface for .MeetingItem.MeetingItem
    """


class IMeeting(Interface):
    """Marker interface for .Meeting.Meeting
    """


class IToolPloneMeeting(Interface):
    """Marker interface for .ToolPloneMeeting.ToolPloneMeeting
    """


class IMeetingCategory(Interface):
    """Marker interface for .MeetingCategory.MeetingCategory
    """


class IMeetingConfig(Interface):
    """Marker interface for .MeetingConfig.MeetingConfig
    """


class IMeetingFileType(Interface):
    """Marker interface for .MeetingFileType.MeetingFileType
    """


class IMeetingFile(Interface):
    """Marker interface for .MeetingFile.MeetingFile
    """


class IMeetingGroup(Interface):
    """Marker interface for .MeetingGroup.MeetingGroup
    """


class IPodTemplate(Interface):
    """Marker interface for .PodTemplate.PodTemplate
    """


class IMeetingUser(Interface):
    """Marker interface for .MeetingUser.MeetingUser
    """

##code-section FOOT
# Interfaces used for customizing the behaviour of meeting items ---------------


class IMeetingItemDocumentation:
    '''Normally, the methods described here should be part of IMeetingItem.
       Because it is impossible to do so with an overengineered yet overrigid
       ArchGenXML 2, we document the provided methods in this absurd class.'''
    def getItemReference():
        '''Returns the reference associated to this item. If the format of your
           item references is simple, you should define it by a TAL expression,
           directly in the MeetingConfig (through the web or via a profile).
           Indeed, this is the default behaviour of getItemReference: to produce
           a reference based on a format specified as a TAL expression in the
           MeetingConfig. If your references are too complex, then override
           this method in a specific adapter.'''
    def mustShowItemReference():
        '''When must I show the item reference ? In the default implementation,
           item references are shown as soon as a meeting is published.'''
    def getPredecessors():
        '''Return a list of dict containing informations we want to show about
           the predecessors.  The dict will contains the 'title' to display,
           the 'url' to link to, the 'tagtitle' that will be used as title for the
           link HTML tag and a 'class' defining a css class name'''
    def getSpecificDocumentContext():
        '''When a document is generated from an item, the POD template that is
           used (see http://appyframework.org/pod.html) receives some variables
           in its context (the item, the currently logged user, etc). If you
           want to give more elements in the context, you can override this
           method, that must return a dict whose keys will correspond to
           variables that you can use in the POD template, and whose values
           will be the values of those variables.'''
    def getSpecificMailContext(event, translationMapping):
        '''When a given p_event occurs on this meeting item, PloneMeeting will
           send mail. For defining the mail subject and body, PloneMeeting will
           use i18n labels <event>_mail_subject and <event>_mail_body in i18n
           domain 'PloneMeeting'. When writing translations for those labels in
           your i18n .po files, PloneMeeting will give you the following
           variables that you may insert with the syntax ${variableName}
             - portalUrl          The full URL of your Plone site
             - portalTitle        The title your Plone site
             - itemTitle          The title of the meeting item
             - lastAnnexTitle     The title of the last annex added to this item
                                  (be it desision-related or not)
             - lastAnnexTypeTitle The title of the annex type of the last annex
                                  added to this item
             - meetingTitle       The title of the meeting to which this item
                                  belongs (only when relevant)
             - objectDavUrl       The WebDAV URL of the object
           If you want to have other variables than those provided by default,
           you can override this method: you will receive the default
           p_translationMapping and you can add variables in it (the
           p_translationMapping is a dict whose keys are variable names and
           values are variable values). If you want to define yourself custom
           mail subjects and bodies, simply return (mailSubject, mailBody). If
           this method returns nothing, the mail body and subject will be
           defined as described above.'''
    def includeMailRecipient(event, userId):
        '''This method is called when p_event occurs on this meeting item, and
           when PloneMeeting should normally send a notification to user
           p_userId (which has the necessary role or permission); user will
           actually be added to the list of recipients only if this method
           returns True. The default PloneMeeting behaviour for this method is
           to return True in all cases. (Adapt it if you want to filter the
           recipients of a notification belong other criteria than their role
           or permission.)'''
    def addRecurringItemToMeeting(meeting):
        '''This meeting item was just created (by copy/pasting a recurring item)
           in the folder that also contains the p_meeting into which it must
           be inserted. So in this method, we must trigger automatically some
           transitions on the workflow defined for meeting items, in order
           to insert this item into the p_meeting and set it at the correct
           state.  If this method returns True, it means that an error occured
           while adding the recurring item to the meeting.'''
    def mayWriteCompleteness():
        '''This manage the condition that check if MeetingItem.complentess
           may be edited by the current user.'''
    def mayTakeOver():
        '''This manage the condition that check if MeetingItem.takenOverBy
           may be edited by the current user.'''
    def transformRichTextField(fieldName, richContent):
        '''This method is called every time an item is created or updated. It
           allows you to modify the content of any "richtext" attribute
           (description, decision...) defined on the item (the field name is
           given in p_fieldName). The method must return the adapted version of
           p_richContent, which contains the XHTML content of the "richtext"
           field (a string). The default PloneMeeting behaviour for this method
           is to return p_richContent untouched.'''
    def onEdit(isCreated):
        '''This method is called every time an item is created or updated.
           p_isCreated is True if the object was just created. It is called
           within Archetypes methods at_post_create_script and
           at_post_edit_script. You do not need to reindex the item. The
           default PloneMeeting implementation for this method does nothing.'''
    def getInsertOrder(insertMethod, meeting, late):
        '''When inserting an item into a meeting, several "methods" are
           available, built in PloneMeeting (follow category order, proposing
           group order, all groups order, at the end, etc). If you want to
           implement your own "method", you may want to propose an alternative
           behaviour here, by returning an "order", or "weight" (as an integer
           value) that you assign to the current item. According to this
           "order", the item will be inserted at the right place. This method
           receives:
           - the p_insertMethod as specified in the meeting config, which
             may not be useful if you choose to implement your own one;
           - p_meeting is the meeting into which we are inserting the item;
           - the boolean p_late value, which indicates if the item is being
             inserted among "normal" (p_late=False) or "late" (p_late=True)
             items on the meeting.
        '''
    def getIcons(inMeeting, meeting):
        '''Gets info about the icons to show for this item while displaying it in
           a list of items. If p_inMeeting is False, the concerned list of items
           is the list of available items for p_meeting. Else, it is one of the
           list of items within the meeting (normal or late items). This method
           must return a list of 2-tuples
           [(s_iconName1, s_label1),(s_iconName2, s_label2),]:
           - "iconName" must be the name of the icon file which must lie in a
             skin, ie "late.png";
           - "label" must be a i18n label in the "PloneMeeting" domain that will
             be used for the "title" attribute for the image.  If a mapping is
             needed, the label can be a list where first element is the msgid
             and second element the mapping dict.
        '''
    def mayCloneToOtherMeetingConfig(destMeetingConfigId):
        '''Check that we can clone the item to p_destMeetingConfigId.
           Checks are ordered from light to heavy as this could be called
           several times...'''
    def onDiscussChanged(toDiscuss):
        '''This method is called when value of field "toDiscuss" (p_toDiscuss)
           has changed on an item.'''
    def isPrivacyViewable():
        '''Privacy acts as a simple filter in front of workflow-based security.
           It means that, if someone has the "View" permission on an item, he
           may only access some information about the item. Field-specific
           permissions exists for managing this problem, but on a too detailed
           level (the field). Managing lots of field-specific permissions is
           laborious, unmaintanable and produces huge workflow descriptions.
           The idea here is to get an intermediate security filter. Very simple:
           people that have View permission on an item where
           item.isPrivacyViewable is False, will be able to consult information
           shown in lists of items (titles, descriptions, decisions), excepted
           advices and annexes, and will not be able to go to meetingitem_view.

           The default implementation: isPrivacyViewable is True for any user
           belonging to any of the Plone groups related to the MeetingGroup
           which is the proposing group for the item.
           Copy groups and advisers will also be able to access the item.
           Note that isPrivacyViewable is automatically True if the item has
           field privacy=False.'''
    def getExtraFieldsToCopyWhenCloning():
        '''While cloning an item (to another MeetingConfig or not), some fields are selected
           to be copied to the new cloned items.  If we want to add some arbitrary
           fields like fields coming from a SchemaExtender, we can specify this
           with this method that will returns a list of extra field ids to copy to
           the cloned item.  The parameter p_cloned_to_same_mc is True if current item
           will be cloned to the same meeting config, and is False if item is
           actually sent to another meeting config.'''
    def itemPositiveDecidedStates():
        '''Return a tuple containing item states considered as 'positive'
           like 'accepted' for example.'''
    def getCertifiedSignatures(forceUseCertifiedSignaturesOnMeetingConfig=False):
        '''Gets the certified signatures for this item.
           Either use signatures defined on the proposing MeetingGroup if exists,
           or use the meetingConfig certified signatures.
           If p_forceUseCertifiedSignaturesOnMeetingConfig, signatures defined on
           the MeetingConfig will be used, no matter signatures are defined on the proposing group.'''
    def mayEditAdviceConfidentiality():
        '''Condition for being able to edit the confidentiality of asked advices.
           By default, only MeetingManagers able to edit the item may change advice confidentiality.'''
    def _itemToAdviceIsViewable(groupId):
        '''Is the item viewable by given p_groupId for which advice has been asked?'''
    def _adviceIsAddable(groupId):
        """Is advice asked to p_groupId addable on item?"""
    def _adviceIsEditable(groupId):
        """Is advice asked to p_groupId editable on item?"""
    def _sendAdviceToGiveToGroup(groupId):
        """Send the 'your advice is asked on this item' mail notification to given p_groupId?"""


class IMeetingItemWorkflowConditions(Interface):
    '''Conditions that may be defined in the workflow associated with a meeting
       item are defined as methods in this interface.'''
    def mayPropose():
        '''May this item be proposed by a member to some reviewer ?'''
    def mayPrevalidate():
        '''May this item be pre-validated by a pre-reviewer ?
           [only relevant when workflow adaptation "pre-validation" is
           enabled].'''
    def mayValidate():
        '''May this item be validated by a reviewer and proposed to a meeting
           manager ?'''
    def mayPresent():
        '''May this item be presented in a meeting ?'''
    def mayDecide():
        '''May a decision take place on this item (accept, reject...)?'''
    def mayDelay():
        '''May this item be delayed to another meeting ?'''
    def mayConfirm():
        '''May the decision be definitely confirmed?'''
    def mayCorrect():
        '''May the user cancel the previous action performed on me?'''
    def mayPublish():
        '''May one publish me?'''
    def meetingIsPublished():
        '''Is the meeting where I am included published ?'''
    def mayFreeze():
        '''May one freeze me ?'''
    def mayArchive():
        '''May one archive me ?'''
    def isLateFor(meeting):
        '''Normally, when meeting agendas are published (and seen by everyone),
           we shouldn't continue to add items to it. But sometimes those things
           need to happen :-). This method allows to determine under which
           circumstances an item may still be "late-presented" to a p_meeting.

           Here is the default behaviour of this method as implemented into
           PloneMeeting: an item whose preferred meeting is p_meeting, and
           that was validated after the p_meeting has been published, may still
           be presented to the p_meeting if the meeting is still in "published"
           state (so in this case, m_isLateFor returns True).

           Note that when such items are presented into a meeting, they are
           added in a special section, below the items that were presented under
           "normal" circumstances. This way, people that consult meeting agendas
           know that there is a fixed part of items that were in the meeting
           when it was first published, and that there are additional "late"
           items that were added in a hurry.'''


class IMeetingItemWorkflowActions(Interface):
    '''Actions that may be triggered while the workflow linked to an item
       executes.'''
    def doPropose(stateChange):
        '''Executes when an item is proposed to a reviewer.'''
    def doPrevalidate(stateChange):
        '''Executes when an item is pre-reviewed.'''
    def doValidate(stateChange):
        '''Executes when an action is validated by a reviewer and proposed to
           the meeting owner.'''
    def doPresent(stateChange):
        '''Executes when an item is presented in a meeting.'''
    def doItemPublish(stateChange):
        '''Executes when the meeting containing this item is published.'''
    def doItemFreeze(stateChange):
        '''Executes when the meeting containing this item is frozen (ie
           published, but without most people having the possibility to modify
           it).'''
    def doAccept(stateChange):
        '''Executes when an item is accepted.'''
    def doRefuse(stateChange):
        '''Executes when an item is refused.'''
    def doDelay(stateChange):
        '''Executes when an item is delayed.'''
    def doCorrect(stateChange):
        '''Executes when the user performs a wrong action and needs to undo
           it.'''
    def doConfirm(stateChange):
        '''Executes when an item is definitely confirmed.'''
    def doItemArchive(stateChange):
        '''Executes when the meeting containing this item is archived.'''


class IMeetingItemCustom(IMeetingItem):
    '''If you want to propose your own implementations of IMeetingItem methods,
       you must define an adapter that adapts IMeetingItem to
       IMeetingItemCustom.'''


# Interfaces used for customizing the behaviour of meetings --------------------
class IMeetingDocumentation:
    '''Normally, the methods described here should be part of IMeeting.
       Because it is impossible to do so with an overengineered yet overrigid
       ArchGenXML 2, we document the provided methods in this absurd class.'''
    def getAvailableItems():
        '''Returns the list of items that may be presented to me.'''
    def isDecided():
        '''Am I in a state such that decisions have all been taken?'''
    def getSpecificDocumentContext():
        '''Similar to the method of the same name in IMeetingItem.'''
    def getSpecificMailContext(event, translationMapping):
        '''Similar to the method of the same name in IMeetingItem. There is one
           diffence: for a meeting, the set of variables that one may use when
           writing translations is the following:
             - portalUrl          The full URL of your Plone site
             - portalTitle        The title your Plone site
             - meetingTitle       The title of this meeting
             - objectDavUrl       The WebDAV URL of this meeting.'''
    def includeMailRecipient(event, userId):
        '''This method is called when p_event occurs on this meeting, and
           when PloneMeeting should normally send a notification to user
           p_userId (which has the necessary role or permission); user will
           actually be added to the list of recipients only if this method
           returns True. The default PloneMeeting behaviour for this method is
           to return True in all cases. (Adapt it if you want to filter the
           recipients of a notification belong other criteria than their role
           or permission.)'''
    def showVotes():
        '''Under what circumstances must I show the tab "Votes" for every item
           of this meeting? The default implementation for this method
           returns True when the meeting has started (based on meeting.date or
           meeting.startDate if used).'''
    def onEdit(isCreated):
        '''This method is called every time a meeting is created or updated.'''
    def showRemoveSelectedItemsAction():
        '''Return True/False if the 'Remove selected items' action must be displayed
           on the meeting view displaying presented items.'''


class IMeetingWorkflowConditions(Interface):
    '''Conditions that may be defined in the workflow associated with a meeting
       are defined as methods in this interface.'''
    def mayPublish():
        '''May the user put me in a state where I am complete and I can be
           published and consulted by authorized persons before I begin?'''
    def mayFroze():
        '''May the user 'froze' the meeting? In this state, the meeting is
           published, is not decided yet but nobody may modify the meeting
           agenda anymore (at least in theory).'''
    def mayDecide():
        '''May the user put me in a state where all the decisions related to
           all my items are taken ?'''
    def mayClose():
        '''May the user put me in a state where all the decisions are completely
           finalized ?'''
    def mayArchive():
        '''May the user archive me ?'''
    def mayCorrect():
        '''May the user cancel the previous action performed on me?'''
    def mayRepublish():
        '''May the user publish me again ? Returns False by default.'''

    # The following conditions are not workflow conditions in the strict sense,
    # but are conditions that depend on the meeting state.
    def mayAcceptItems():
        '''May I accept new items to be integrated to me ? (am I in a relevant
           state, is my date still in the future, ...)'''
    def mayChangeItemsOrder():
        '''May one change order of my list of items ?'''


class IMeetingWorkflowActions(Interface):
    '''Actions that may be triggered while the workflow linked to a meeting
       executes.'''
    def doPublish(stateChange):
        '''Executes when the meeting is "published" (=becomes visible by every
           authorized user). In the default PloneMeeting implementation,
           Meeting.doPublish calls Item.doPublish for every "presented" item
           contained in the meeting. It does so on the sorted list of items, so
           Item.doPublish methods are called in the item order. The default
           implementation also attributes a meeting number to the
           meeting (a sequence number within the meeting configuration).'''
    def doDecide(stateChange):
        '''Executes when all items contained in me are "decided". In the default
           PloneMeeting implementation, Meeting.doDecide calls Item.doAccept
           for every "frozen" item contained in the meeting. It does so on the
           sorted list of items because we use getItemsInOrder.'''
    def doClose(stateChange):
        '''Executes when all decisions are finalized. In the default
           PloneMeeting implementation, Meeting.doClose calls Item.doConfirm
           for every "accepted" item contained in the meeting. It does so on the
           sorted list of items because we use getItemsInOrder.'''
    def doArchive(stateChange):
        '''Executes when the meeting is archived.'''
    def doRepublish(stateChange):
        '''Executes when I am published again.'''
    def doBackToDecided(stateChange):
        '''Executes when I undo a "close" transition.'''
    def doBackToCreated(stateChange):
        '''Executes when I undo a "publish" transition.'''
    def doBackToPublished(stateChange):
        '''Executes when I undo a "decide" transition.'''
    def doBackToClosed(stateChange):
        '''Executes when I undo a "archive" transition.'''


class IMeetingCustom(IMeeting):
    '''If you want to propose your own implementations of IMeeting methods,
       you must define an adapter that adapts IMeeting to IMeetingCustom.'''


# Interfaces used for customizing the behaviour of meeting categories ----------
class IMeetingCategoryDocumentation:
    '''Normally, the methods described here should be part of IMeetingCategory.
       Because it is impossible to do so with an overengineered yet overrigid
       ArchGenXML 2, we document the provided methods in this absurd class.'''
    def onEdit(isCreated):
        '''This method is called every time a category is created or updated.
           p_isCreated is True if the object was just created. It is called
           within Archetypes methods at_post_create_script and
           at_post_edit_script. You do not need to reindex the category. The
           default PloneMeeting implementation for this method does nothing.'''
    def isSelectable(item):
        '''When creating or updating a meeting item, the user may choose a
           category (or a classifier if you use field "classifier" in the
           corresponding meeting configuration). Selectable categories are
           categories for which method isSelectable returns True. The
           default implementation of isSelectable returns True if the workflow
           state is "active" for the category and if the current user is creator
           for at least one of the 'usingGroups' selected on the category.
           If a p_userId is given, it will check if the category is selectable
           for given userId.'''


class IMeetingCategoryCustom(IMeetingCategory):
    '''If you want to propose your own implementations of IMeetingCategory methods,
       you must define an adapter that adapts IMeetingCategory to IMeetingCategoryCustom.'''


# Interfaces used for customizing the behaviour of meeting configs -------------
# See docstring of previous classes for understanding this section.
class IMeetingConfigDocumentation:
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''
    def getMeetingsAcceptingItems():
        '''Gets the meetings that can accept items.'''


class IMeetingConfigCustom(IMeetingConfig):
    pass


# Interfaces used for customizing the behaviour of meeting files ---------------
# See docstring of previous classes for understanding this section.
class IMeetingFileDocumentation:
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''


class IMeetingFileCustom(IMeetingFile):
    pass


# Interfaces used for customizing the behaviour of meeting file types ----------
# See docstring of previous classes for understanding this section.
class IMeetingFileTypeDocumentation:
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''
    def isSelectable(row_id=None):
        '''When adding an annex to an item, the user may choose a file type for
           this annex, among all file types defined in the corresponding meeting
           config for which this method isSelectable returns True. The
           default implementation of isSelectable returns True if the workflow
           state is "active" for the meeting file type.  If a p_row_id is given,
           it will check if the corresponding subType having p_row_id 'isActive'.'''


class IMeetingFileTypeCustom(IMeetingFileType):
    pass


# Interfaces used for customizing the behaviour of meeting groups --------------
# See docstring of previous classes for understanding this section.
class IMeetingGroupDocumentation:
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''


class IMeetingGroupCustom(IMeetingGroup):
    '''If you want to propose your own implementations of IMeetingGroup methods,
       you must define an adapter that adapts IMeetingGroup to
       IMeetingGroupCustom.'''


# Interfaces used for customizing the behaviour of pod templates ---------------
# See docstring of previous classes for understanding this section.
class IPodTemplateDocumentation:
    def onEdit(isCreated):
        '''Called when an object p_isCreated or edited.'''


class IPodTemplateCustom(IPodTemplate):
    pass


# Interfaces used for customizing the behaviour of the PloneMeeting tool -------
# See docstring of previous classes for understanding this section.
class IToolPloneMeetingDocumentation:
    def onEdit(isCreated):
        '''Called when the tool p_isCreated or edited.'''
    def getSpecificMailContext(event, translationMapping):
        '''See doc in methods with similar names above.'''


class IToolPloneMeetingCustom(IToolPloneMeeting):
    '''If you want to propose your own implementations of tool methods,
       you must define an adapter that adapts IToolPloneMeeting to
       IToolPloneMeetingCustom.'''


# Interfaces used for customizing the behaviour of meeting users ---------------
# See docstring of previous classes for understanding this section.
class IMeetingUserDocumentation:
    def mayConsultVote(loggedUser, item):
        '''May the currently logged user (p_loggedUser) see the vote from this
           meeting user on p_item?

           The default implementation returns True if the logged user is the
           voter, a Manager or a MeetingManager or if the meeting was decided
           (result of meeting.isDecided()).'''
    def mayEditVote(loggedUser, item):
        '''May the currently logged user (p_loggedUser) edit the vote from this
           meeting user on p_item?

           The default implementation returns True if the meeting has not been
           decided yet (result of meeting.isDecided()), and if the logged user
           is the voter himself (provided voters encode votes according to the
           meeting configuration) or if the logged user is a meeting manager
           (provided meeting managers encode votes according to the meeting
           configuration) or if the logged user is a Manager.'''


class IMeetingUserCustom(IMeetingUser):
    pass
##/code-section FOOT
