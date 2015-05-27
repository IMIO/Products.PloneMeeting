# -*- coding: utf-8 -*-
#
# File: adapters.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

import logging
logger = logging.getLogger('PloneMeeting')
from AccessControl import Unauthorized

from zope.annotation import IAnnotations
from zope.i18n import translate

from plone.memoize import ram

from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.utils import checkPermission

from eea.facetednavigation.criteria.handler import Criteria as eeaCriteria
from imio.actionspanel.adapters import ContentDeletableAdapter as APContentDeletableAdapter
from imio.dashboard.adapters import CustomViewFieldsVocabularyAdapter
from imio.history.adapters import ImioWfHistoryAdapter
from imio.prettylink.adapters import PrettyLinkAdapter
from collective.documentviewer.settings import GlobalSettings


class AnnexableAdapter(object):
    """
      Manage every related annexes management functionnalities.
    """

    def __init__(self, context):
        self.context = context
        self.request = self.context.REQUEST

    def addAnnex(self, idCandidate, annex_title, annex_file,
                 relatedTo, meetingFileTypeUID, **kwargs):
        '''See docstring in interfaces.py'''
        # first of all, check if we can actually add the annex
        if relatedTo == 'item_decision':
            if not checkPermission("PloneMeeting: Write decision annex", self.context):
                raise Unauthorized
        else:
            # we use the "PloneMeeting: Add annex" permission for item normal annexes and advice annexes
            if not checkPermission("PloneMeeting: Add annex", self.context):
                raise Unauthorized

        # if we can, proceed
        if not idCandidate:
            idCandidate = annex_file.filename
        # Split leading underscore(s); else, Plone argues that you do not have the
        # rights to create the annex
        idCandidate = idCandidate.lstrip('_')
        # Normalize idCandidate
        idCandidate = self.context.plone_utils.normalizeString(idCandidate)
        i = 0
        idMayBeUsed = False
        while not idMayBeUsed:
            i += 1
            if not self.isValidAnnexId(idCandidate):
                # We need to find another name (prepend a number)
                elems = idCandidate.rsplit('.', 1)
                baseName = elems[0]
                if len(elems) == 1:
                    ext = ''
                else:
                    ext = '.%s' % elems[1]
                idCandidate = '%s%d%s' % (baseName, i, ext)
            else:
                # Ok idCandidate is good!
                idMayBeUsed = True

        newAnnexId = self.context.invokeFactory('MeetingFile', id=idCandidate)
        newAnnex = getattr(self.context, newAnnexId)
        newAnnex.setFile(annex_file, **kwargs)
        newAnnex.setTitle(annex_title)
        newAnnex.setMeetingFileType(meetingFileTypeUID)

        # do some specific stuffs if we are adding an annex on an item, not on an advice
        if self.context.meta_type == 'MeetingItem':
            # Add the annex creation to item history
            self.context.updateHistory('add',
                                       newAnnex,
                                       decisionRelated=(relatedTo == 'item_decision'))
            # Invalidate advices if needed and adding a normal annex
            if relatedTo == 'item' and self.context.willInvalidateAdvices():
                self.context.updateAdvices(invalidate=True)

            # Potentially I must notify MeetingManagers through email.
            if self.context.wfConditions().meetingIsPublished():
                self.context.sendMailIfRelevant('annexAdded', 'MeetingManager', isRole=True)

        # After processForm that itself calls at_post_create_script,
        # current user may loose permission to edit
        # the object because we copy item permissions.
        newAnnex.processForm()
        # display a warning portal message if annex size is large
        if newAnnex.warnSize():
            self.context.plone_utils.addPortalMessage(_("The annex that you just added has a large size and could be "
                                                        "difficult to download by users wanting to view it!"),
                                                      type='warning')
        userId = self.context.portal_membership.getAuthenticatedMember().getId()
        logger.info('Annex at %s uploaded by "%s".' % (newAnnex.absolute_url_path(), userId))

    def isValidAnnexId(self, idCandidate):
        '''See docstring in interfaces.py'''
        res = True
        if hasattr(self.context.aq_base, idCandidate) or \
           (idCandidate in self.context.alreadyUsedAnnexNames):
            res = False
        return res

    def getAnnexesToPrint_cachekey(method, self, relatedTo='item'):
        '''cachekey method for self.getAnnexesToPrint.
           We cache it because it is called several times while used in POD templates.'''
        # invalidate if annexes changed or if toPrint changed
        return ([(annex.UID(), annex.getToPrint()) for annex in self.getAnnexes(relatedTo)])

    @ram.cache(getAnnexesToPrint_cachekey)
    def getAnnexesToPrint(self, relatedTo='item'):
        '''See docstring in interfaces.py'''
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        global_settings = GlobalSettings(portal)
        annexes = self.getAnnexes(relatedTo)
        res = []
        i = 1
        for annex in annexes:
            # first check if annex needs to be printed
            if not annex.getToPrint():
                continue
            # if the annex needs to be printed, check if everything is ok to print it
            annex_annotations = IAnnotations(annex)
            # must have been converted successfully
            if not 'collective.documentviewer' in annex_annotations.keys() or not \
               'successfully_converted' in annex_annotations['collective.documentviewer'] or not \
               annex_annotations['collective.documentviewer']['successfully_converted'] is True:
                continue

            # everything seems right, manage this annex
            # build path to images
            data = {}
            data['title'] = annex.Title()
            annexUID = annex.UID()
            data['UID'] = annex.UID()
            data['number'] = i
            data['images'] = []
            data['number_of_images'] = annex_annotations['collective.documentviewer']['num_pages']
            # we need to traverse to something like : @@dvpdffiles/c/7/c7e2e8b5597c4dc28cf2dee9447dcf9a/large/dump_1.png
            dvpdffiles = portal.unrestrictedTraverse('@@dvpdffiles')
            filetraverser = dvpdffiles.publishTraverse(self.request, annexUID[0])
            filetraverser = dvpdffiles.publishTraverse(self.request, annexUID[1])
            filetraverser = dvpdffiles.publishTraverse(self.request, annexUID)
            large = filetraverser.publishTraverse(self.request, 'large')
            for image_number in range(data['number_of_images']):
                realImageNumber = image_number + 1
                large_image_dump = large.publishTraverse(self.request, 'dump_%d.png' % realImageNumber)
                # depending on the fact that we are using 'Blob' or 'File' as storage_type,
                # the 'large' object is different.  Either a Blob ('Blob') or a DirectoryResource ('File')
                if global_settings.storage_type == 'Blob':
                    blob = large_image_dump.settings.blob_files[large_image_dump.filepath]
                    # if we do not check 'readers', the blob._p_blob_committed is sometimes None...
                    blob.readers
                    path = blob._p_blob_committed
                else:
                    path = large_image_dump.context.path
                data['images'].append({'number': realImageNumber,
                                       'path': path,
                                       })
            res.append(data)
            i = i + 1
        return res

    def updateAnnexIndex(self, annex=None, removeAnnex=False):
        '''See docstring in interfaces.py'''
        if annex:
            if removeAnnex:
                # Remove p_annex-related info
                removeUid = annex.UID()
                for annexInfo in self.context.annexIndex:
                    if removeUid == annexInfo['UID']:
                        self.context.annexIndex.remove(annexInfo)
                        break
            else:
                # Add p_annex-related info
                self.context.annexIndex.append(annex.getAnnexInfo())
        else:
            del self.context.annexIndex[:]
            sortableList = []
            for annex in self.getAnnexes():
                sortableList.append(annex.getAnnexInfo())
            sortableList.sort(key=lambda x: x['modification_date'])
            for a in sortableList:
                self.context.annexIndex.append(a)

    def getAnnexes(self, relatedTo=None):
        '''See docstring in interfaces.py'''
        annexes = self.context.objectValues('MeetingFile')
        return [annex for annex in annexes if (not relatedTo or annex.findRelatedTo() == relatedTo)]

    def getLastInsertedAnnex(self):
        '''See docstring in interfaces.py'''
        res = None
        if self.context.annexIndex:
            annexUid = self.context.annexIndex[-1]['UID']
            res = self.context.uid_catalog(UID=annexUid)[0].getObject()
        return res

    def _isViewableForCurrentUser(self, cfg, isPowerObserver, isRestrictedPowerObserver, annexInfo):
        '''
          Returns True if current user may view the annex
        '''
        # if confidentiality is used and annex is marked as confidential,
        # annexes could be hidden to power observers and/or restricted power observers
        if cfg.getEnableAnnexConfidentiality() and annexInfo['isConfidential'] and \
           ((isPowerObserver and 'power_observers' in cfg.getAnnexConfidentialFor()) or
           (isRestrictedPowerObserver and 'restricted_power_observers' in cfg.getAnnexConfidentialFor())):
            return False
        return True

    def getAnnexesByType_cachekey(method, self, relatedTo, makeSubLists=True,
                                  typesIds=[], realAnnexes=False):
        '''cachekey method for self.getAnnexesByType.'''
        # if MeetingConfig changed (MeetingConfig.annexConfidentialFor for example)
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return (self.context, relatedTo, makeSubLists, typesIds,
                realAnnexes, self.context.annexIndex, self.request['AUTHENTICATED_USER'],
                cfg.modified())

    @ram.cache(getAnnexesByType_cachekey)
    def getAnnexesByType(self, relatedTo, makeSubLists=True,
                         typesIds=[], realAnnexes=False):
        '''See docstring in interfaces.py'''
        res = []
        if not hasattr(self.context, 'annexIndex'):
            self.updateAnnexIndex()
        # bypass if no annex for current context
        if not self.context.annexIndex:
            return res

        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        meetingFileTypes = cfg.getFileTypes(relatedTo,
                                            typesIds=typesIds,
                                            onlySelectable=False,
                                            includeSubTypes=False)
        useConfidentiality = cfg.getEnableAnnexConfidentiality()
        isPowerObserver = False
        if useConfidentiality:
            isPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=False)
        isRestrictedPowerObserver = False
        if useConfidentiality:
            isRestrictedPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=True)
        for fileType in meetingFileTypes:
            annexes = []
            for annexInfo in self.context.annexIndex:
                if (annexInfo['relatedTo'] == relatedTo) and \
                   (annexInfo['meetingFileTypeObjectUID'] == fileType['meetingFileTypeObjectUID']):
                    # manage annex confidentiality, do not consider annex not to show
                    if not self._isViewableForCurrentUser(cfg, isPowerObserver, isRestrictedPowerObserver, annexInfo):
                        continue
                    if not realAnnexes:
                        annexes.append(annexInfo)
                    else:
                        # Retrieve the real annex
                        annex = self.context.portal_catalog(UID=annexInfo['UID'])[0].getObject()
                        annexes.append(annex)
            if annexes:
                if makeSubLists:
                    res.append(annexes)
                else:
                    res += annexes
        return res


class MeetingItemContentDeletableAdapter(APContentDeletableAdapter):
    """
      Manage the mayDelete for MeetingItem.
      Must have 'Delete objects' on the item.
    """
    def __init__(self, context):
        self.context = context

    def mayDelete(self):
        '''See docstring in interfaces.py.'''
        # check 'Delete objects' permission
        return super(MeetingItemContentDeletableAdapter, self).mayDelete()


class MeetingContentDeletableAdapter(APContentDeletableAdapter):
    """
      Manage the mayDelete for Meeting.
      - must have 'Delete objects' on the meeting;
      - must be 'Manager' to remove 'wholeMeeting';
      - meeting must be empty to be removed.
    """
    def __init__(self, context):
        self.context = context

    def mayDelete(self):
        '''See docstring in interfaces.py.'''
        if not super(MeetingContentDeletableAdapter, self).mayDelete():
            return False

        if 'wholeMeeting' in self.context.REQUEST:
            member = getToolByName(self.context, 'portal_membership').getAuthenticatedMember()
            # if we try to remove a 'Meeting' using the 'wholeMeeting' option
            # we need to check that current user is a 'Manager'
            if member.has_role('Manager'):
                return True
        else:
            if not self.context.getRawItems():
                return True


class MeetingFileContentDeletableAdapter(APContentDeletableAdapter):
    """
      Manage the mayDelete for MeetingFile.
      A MeetingFile can be deleted by users able to edit parent (item or advice).
    """
    def __init__(self, context):
        self.context = context

    def mayDelete(self):
        '''See docstring in interfaces.py.'''
        parent = self.context.getParent()
        if checkPermission(ModifyPortalContent, parent):
            return True
        return False


class PMPrettyLinkAdapter(PrettyLinkAdapter):
    """
      Override to take into account PloneMeeting use cases...
    """

    def _leadingIcons(self):
        """
          Manage icons to display before the icons managed by PrettyLink._icons.
        """
        res = []
        if not self.context.meta_type == 'MeetingItem':
            return res

        inMeeting = self.kwargs.get('inMeeting', True)
        meeting = self.kwargs.get('meeting', None)
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedItemAttributes = cfg.getUsedItemAttributes()
        if not inMeeting:
            # Item is in the list of available items for p_meeting. Check if we
            # must show a deadline- or late-related icon.
            if self.context.wfConditions().isLateFor(meeting):
                # A late item, or worse: a late item not respecting the freeze
                # deadline.
                if meeting.attributeIsUsed('deadlineFreeze') and \
                   not self.context.lastValidatedBefore(meeting.getDeadlineFreeze()):
                    res.append(('deadlineKo.png', translate('icon_help_publish_freeze_ko',
                                                            domain="PloneMeeting",
                                                            context=self.request)))
                else:
                    res.append(('late.png', translate('icon_help_late',
                                                      domain="PloneMeeting",
                                                      context=self.request)))
            elif (meeting.queryState() == 'created') and \
                    meeting.attributeIsUsed('deadlinePublish') and \
                    not self.context.lastValidatedBefore(meeting.getDeadlinePublish()):
                res.append(('deadlineKo.png', translate('icon_help_publish_deadline_ko',
                                                        domain="PloneMeeting",
                                                        context=self.request)))
        else:
            # The item is in the list of normal or late items for p_meeting.
            # Check if we must show a decision-related status for the item
            # (delayed, refused...).
            itemState = self.context.queryState()
            if itemState == 'delayed':
                res.append(('delayed.png', translate('icon_help_delayed',
                                                     domain="PloneMeeting",
                                                     context=self.request)))
            elif itemState == 'refused':
                res.append(('refused.png', translate('icon_help_refused',
                                                     domain="PloneMeeting",
                                                     context=self.request)))
            elif itemState == 'returned_to_proposing_group':
                res.append(('return_to_proposing_group.png', translate('icon_help_returned_to_proposing_group',
                                                                       domain="PloneMeeting",
                                                                       context=self.request)))
            elif itemState == 'prevalidated':
                res.append(('prevalidate.png', translate('icon_help_prevalidated',
                                                         domain="PloneMeeting",
                                                         context=self.request)))
            # Display icons about sent/cloned to other meetingConfigs
            clonedToOtherMCIds = self.context._getOtherMeetingConfigsImAmClonedIn()
            for clonedToOtherMCId in clonedToOtherMCIds:
                # Append a tuple with name of the icon and a list containing
                # the msgid and the mapping as a dict
                res.append(("%s.png" %
                            cfg._getCloneToOtherMCActionId(clonedToOtherMCId, cfg.getId()),
                            translate('sentto_othermeetingconfig',
                                      mapping={
                                      'meetingConfigTitle': getattr(tool,
                                                                    clonedToOtherMCId).Title()},
                                      domain="PloneMeeting",
                                      context=self.request)))
            # if not already cloned to another mc, maybe it will be?
            if not clonedToOtherMCIds:
                otherMeetingConfigsClonableTo = self.context.getOtherMeetingConfigsClonableTo()
                for otherMeetingConfigClonableTo in otherMeetingConfigsClonableTo:
                    # Append a tuple with name of the icon and a list containing
                    # the msgid and the mapping as a dict
                    res.append(("will_be_%s.png" %
                                cfg._getCloneToOtherMCActionId(otherMeetingConfigClonableTo, cfg.getId()),
                                translate('will_be_sentto_othermeetingconfig',
                                          mapping={
                                          'meetingConfigTitle': getattr(tool,
                                                                        otherMeetingConfigClonableTo).Title()},
                                          domain="PloneMeeting",
                                          context=self.request)))
            # display icons if element is down the workflow or up for at least second time...
            # display it only for items before state 'validated'
            if not self.context.hasMeeting() and not itemState == 'validated':
                # down the workflow, the last transition was a backTo... transition
                lastEvent = self.context.getLastEvent()
                if lastEvent['action']:
                    if lastEvent['action'].startswith('back'):
                        res.append(('wf_down.png', translate('icon_help_wf_down',
                                                             domain="PloneMeeting",
                                                             context=self.request)))
                    else:
                        # up the workflow for at least second times and not linked to a meeting
                        # check if last event was already made in item workflow_history
                        history = self.context.workflow_history[cfg.getItemWorkflow()]
                        i = 0
                        for event in history:
                            if event['action'] == lastEvent['action']:
                                i = i + 1
                                if i > 1:
                                    res.append(('wf_up.png', translate('icon_help_wf_up',
                                                                       domain="PloneMeeting",
                                                                       context=self.request)))
                                    break
        # In some cases, it does not matter if an item is inMeeting or not.
        if 'oralQuestion' in usedItemAttributes:
            if self.context.getOralQuestion():
                res.append(('oralQuestion.png', translate('this_item_is_an_oral_question',
                                                          domain="PloneMeeting",
                                                          context=self.request)))
        if 'emergency' in usedItemAttributes:
            # display an icon if emergency asked/accepted/refused
            itemEmergency = self.context.getEmergency()
            if itemEmergency == 'emergency_asked':
                res.append(('emergency_asked.png', translate('emergency_asked',
                                                             domain="PloneMeeting",
                                                             context=self.request)))
            elif itemEmergency == 'emergency_accepted':
                res.append(('emergency_accepted.png', translate('emergency_accepted',
                                                                domain="PloneMeeting",
                                                                context=self.request)))
            elif itemEmergency == 'emergency_refused':
                res.append(('emergency_refused.png', translate('emergency_refused',
                                                               domain="PloneMeeting",
                                                               context=self.request)))
        if 'takenOverBy' in usedItemAttributes:
            takenOverBy = self.context.getTakenOverBy()
            if takenOverBy:
                # if taken over, display a different icon if taken over by current user or not
                takenOverByCurrentUser = self.request['AUTHENTICATED_USER'].getId() == takenOverBy and True or False
                iconName = takenOverByCurrentUser and 'takenOverByCurrentUser.png' or 'takenOverByOtherUser.png'
                res.append((iconName, translate('Taken over by ${fullname}',
                                                domain="PloneMeeting",
                                                mapping={'fullname': tool.getUserName(takenOverBy)},
                                                context=self.request)))
        return res


class PMCustomViewFieldsVocabularyAdapter(CustomViewFieldsVocabularyAdapter):
    """Add some additional fields."""

    def additionalViewFields(self):
        """See docstring in interfaces.py."""
        additionalFields = super(PMCustomViewFieldsVocabularyAdapter, self).additionalViewFields()
        additionalFields.add('proposing_group_acronym', 'Proposing group acronym')
        additionalFields.add('advices', 'Advices')
        return additionalFields


class PMHistoryAdapter(ImioWfHistoryAdapter):
    """
      Override the imio.history ImioHistoryAdapter.
    """
    def ignorableHistoryComments(self):
        """Add some more ignorable history comments."""
        ignorable_history_comment = super(PMHistoryAdapter, self).ignorableHistoryComments()
        ignorable_history_comment += ('create_meeting_item_from_template_comments',
                                      'create_from_predecessor_comments',
                                      'Duplicate and keep link_comments',
                                      'Duplicate_comments')
        return ignorable_history_comment

    def mayViewComment(self, event):
        """
          By default, every p_event comment is viewable except for MeetingItem, if
          'hideItemHistoryCommentsToUsersOutsideProposingGroup' is enabled in the MeetingConfig,
          only members of the proposing group will be able to access history comment.
        """
        userMayAccessComment = True
        if self.context.meta_type == 'MeetingItem':
            tool = getToolByName(self.context, 'portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            if cfg.getHideItemHistoryCommentsToUsersOutsideProposingGroup() and not tool.isManager(self.context):
                userMeetingGroupIds = [mGroup.getId() for mGroup in tool.getGroupsForUser()]
                if not self.context.getProposingGroup() in userMeetingGroupIds:
                    userMayAccessComment = False
        return userMayAccessComment

    def getHistory(self, checkMayView=True):
        """Override getHistory because it manages data changes."""
        return self.context.getHistory(checkMayView=checkMayView)


class Criteria(eeaCriteria):
    """ Handle criteria
    """

    def __init__(self, context):
        """ Handle criteria
        """
        super(Criteria, self).__init__(context)
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if cfg:
            self.context = cfg.searches
            criteria = list(self._criteria())
            if context.meta_type == 'Meeting':
                # remove the 'collection' widget
                for criterion in criteria:
                    if criterion.widget == 'collection-link':
                        criteria.remove(criterion)
            self.criteria = criteria


class CompoundCriterionBaseAdapter(object):

    def __init__(self, context):
        self.context = context
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def query(self):
        ''' '''
        return {}


class ItemsOfMyGroupsAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items of groups of the current user, no matter wich suffix
           of the group the user is in.'''
        userGroupIds = [mGroup.getId() for mGroup in self.tool.getGroupsForUser()]
        return {'portal_type': self.cfg.getItemTypeName(),
                'getProposingGroup': userGroupIds}


class MyItemsTakenOverAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items that current user take over.'''
        membershipTool = getToolByName(self.context, 'portal_membership')
        member = membershipTool.getAuthenticatedMember()
        return {'portal_type': self.cfg.getItemTypeName(),
                'getTakenOverBy': member.getId()}


class ItemsInCopyAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items for which the current user is in copyGroups.'''
        membershipTool = getToolByName(self.context, 'portal_membership')
        groupsTool = getToolByName(self.context, 'portal_groups')
        member = membershipTool.getAuthenticatedMember()
        userGroups = groupsTool.getGroupsForPrincipal(member)
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'getCopyGroups' use 'OR' by default
                'getCopyGroups': userGroups}


class ItemsToValidateOfHighestHierarchicLevelAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Return a list of items that the user can validate regarding his highest hierarchic level.
           So if a user is 'prereviewer' and 'reviewier', the search will only return items
           in state corresponding to his 'reviewer' role.'''
        membershipTool = getToolByName(self.context, 'portal_membership')
        member = membershipTool.getAuthenticatedMember()
        groupsTool = getToolByName(self.context, 'portal_groups')
        groupIds = groupsTool.getGroupsForPrincipal(member)
        res = []
        highestReviewerLevel = self.cfg._highestReviewerLevel(groupIds)
        if not highestReviewerLevel:
            # in this case, we do not want to display a result
            # we return an unknown review_state
            return {'review_state': ['unknown_review_state', ]}
        for groupId in groupIds:
            if groupId.endswith('_%s' % highestReviewerLevel):
                # append group name without suffix
                res.append(groupId[:-len('_%s' % highestReviewerLevel)])
        review_state = MEETINGREVIEWERS[highestReviewerLevel]
        # specific management for workflows using the 'pre_validation' wfAdaptation
        if highestReviewerLevel == 'reviewers' and \
           ('pre_validation' in self.cfg.getWorkflowAdaptations() or
           'pre_validation_keep_reviewer_permissions' in self.cfg.getWorkflowAdaptations()):
            review_state = 'prevalidated'

        return {'portal_type': self.cfg.getItemTypeName(),
                'getProposingGroup': res,
                'review_state': review_state}


class ItemsToValidateOfMyReviewerGroupsAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Return a list of items that the user could validate.  So it returns every items the current
           user is able to validate at any state of the validation process.  So if a user is 'prereviewer'
           and 'reviewer' for a group, the search will return items in both states.'''
        membershipTool = getToolByName(self.context, 'portal_membership')
        groupsTool = getToolByName(self.context, 'portal_groups')
        member = membershipTool.getAuthenticatedMember()
        groupIds = groupsTool.getGroupsForPrincipal(member)
        reviewProcessInfos = []
        for groupId in groupIds:
            for reviewer_suffix, review_state in MEETINGREVIEWERS.items():
                # current user may be able to validate at at least
                # one level of the entire validation process, we take it into account
                if groupId.endswith('_%s' % reviewer_suffix):
                    # specific management for workflows using the 'pre_validation' wfAdaptation
                    if reviewer_suffix == 'reviewers' and \
                       ('pre_validation' in self.cfg.getWorkflowAdaptations() or
                       'pre_validation_keep_reviewer_permissions' in self.cfg.getWorkflowAdaptations()):
                        review_state = 'prevalidated'
                    reviewProcessInfos.append('%s__reviewprocess__%s' % (groupId[:-len(reviewer_suffix) - 1],
                                                                         review_state))
        if not reviewProcessInfos:
            # in this case, we do not want to display a result
            # we return an unknown review_state
            return {'review_state': ['unknown_review_state', ]}

        return {'portal_type': self.cfg.getItemTypeName(),
                'reviewProcessInfo': reviewProcessInfos}


class ItemsToAdviceAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items for which the current user must give an advice.'''
        groups = self.tool.getGroupsForUser(suffix='advisers')
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will return 'not delay-aware' and 'delay-aware' advices
        groupIds = [g.getId() + '_advice_not_given' for g in groups] + \
                   ['delay__' + g.getId() + '_advice_not_given' for g in groups]
        # Create query parameters
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': groupIds}


class ItemsToAdviceWithoutDelayAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items for which the current user must give an advice without delay.'''
        groups = self.tool.getGroupsForUser(suffix='advisers')
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will only return 'not delay-aware' advices
        groupIds = [g.getId() + '_advice_not_given' for g in groups]
        # Create query parameters
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': groupIds}


class ItemsToAdviceWithDelayAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items for which the current user must give an advice with delay.'''

        groups = self.tool.getGroupsForUser(suffix='advisers')
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will only return 'delay-aware' advices
        groupIds = ['delay__' + g.getId() + '_advice_not_given' for g in groups]
        # Create query parameters
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': groupIds}


class ItemsToAdviceWithExceededDelayAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries all items for which the current user must give an advice with exceeded delay.'''
        groups = self.tool.getGroupsForUser(suffix='advisers')
        # Add a '_delay_exceeded' at the end of every group id: we want "not given" advices.
        # this search will only return 'delay-aware' advices for wich delay is exceeded
        groupIds = ['delay__' + g.getId() + '_advice_delay_exceeded' for g in groups]
        # Create query parameters
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': groupIds}


class AdvisedItemsAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries items for which an advice has been given.'''
        groups = self.tool.getGroupsForUser(suffix='advisers')
        # advised items are items that has an advice in a particular review_state
        # just append every available meetingadvice state: we want "given" advices.
        # this search will return every advices
        wfTool = getToolByName(self.context, 'portal_workflow')
        adviceWF = wfTool.getWorkflowsFor('meetingadvice')[0]
        adviceStates = adviceWF.states.keys()
        groupIds = []
        for adviceState in adviceStates:
            groupIds += [g.getId() + '_%s' % adviceState for g in groups]
            groupIds += ['delay__' + g.getId() + '_%s' % adviceState for g in groups]
        # Create query parameters
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': groupIds}


class AdvisedItemsWithDelayAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries items for which an advice has been given with delay.'''
        groups = self.tool.getGroupsForUser(suffix='advisers')
        # advised items are items that has an advice in a particular review_state
        # just append every available meetingadvice state: we want "given" advices.
        # this search will only return 'delay-aware' advices
        wfTool = getToolByName(self.context, 'portal_workflow')
        adviceWF = wfTool.getWorkflowsFor('meetingadvice')[0]
        adviceStates = adviceWF.states.keys()
        groupIds = []
        for adviceState in adviceStates:
            groupIds += ['delay__' + g.getId() + '_%s' % adviceState for g in groups]
        # Create query parameters
        return {'portal_type': self.cfg.getItemTypeName(),
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': groupIds}


class DecidedItemsAdapter(CompoundCriterionBaseAdapter):

    @property
    def query(self):
        '''Queries decided items.'''
        return {'portal_type': self.cfg.getItemTypeName(),
                'review_state': self.cfg.getItemDecidedStates()}
