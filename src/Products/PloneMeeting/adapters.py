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

from persistent.list import PersistentList
from zope.annotation import IAnnotations
from zope.i18n import translate

from plone.memoize import ram

from Products.CMFCore.permissions import ModifyPortalContent
from Products.MimetypesRegistry.common import MimeTypeException
from Products.CMFPlone.utils import safe_unicode
from plone import api
from plone.api.exc import InvalidParameterError

from collective.documentviewer.settings import GlobalSettings
from eea.facetednavigation.criteria.handler import Criteria as eeaCriteria
from eea.facetednavigation.interfaces import IFacetedNavigable
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget
from imio.actionspanel.adapters import ContentDeletableAdapter as APContentDeletableAdapter
from imio.history.adapters import ImioWfHistoryAdapter
from imio.prettylink.adapters import PrettyLinkAdapter
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.config import MEETINGROLES
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.utils import checkPermission
from Products.PloneMeeting.utils import getCurrentMeetingObject

CONTENT_TYPE_NOT_FOUND = 'The content_type for MeetingFile at %s was not found in mimetypes_registry!'
FILE_EXTENSION_NOT_FOUND = 'The extension used by MeetingFile at %s does not correspond to ' \
    'an extension available in the mimetype %s found in mimetypes_registry!'

# this catalog query will find nothing, used in CompoundCriterion adapters when necessary
FIND_NOTHING_QUERY = {'review_state': {'query': ['unknown_review_state', ]}, }


class AnnexableAdapter(object):
    """
      Manage every related annexes management functionnalities.
    """

    def __init__(self, context):
        self.context = context
        # check for REQUEST when using async
        self.request = None
        if hasattr(self.context, 'REQUEST'):
            self.request = self.context.REQUEST

    def addAnnex(self, idCandidate, annex_title, annex_file,
                 relatedTo, meetingFileTypeUID, **kwargs):
        '''See docstring in interfaces.py'''
        # first of all, check if we can actually add the annex
        if relatedTo == 'item_decision' and \
           not checkPermission("PloneMeeting: Write decision annex", self.context):
            raise Unauthorized
        elif (not relatedTo == 'item_decision' and
              not checkPermission("PloneMeeting: Add annex", self.context)):
            # we use the "PloneMeeting: Add annex" permission for item normal annexes and advice annexes
            raise Unauthorized

        # if we can, proceed
        if not idCandidate:
            idCandidate = annex_file.filename
        # Split leading underscore(s); else, Plone argues that you do not have the
        # rights to create the annex
        idCandidate = idCandidate.lstrip('_')
        # Normalize idCandidate
        plone_utils = api.portal.get_tool('plone_utils')
        idCandidate = plone_utils.normalizeString(idCandidate)
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

        # as we heritate 'Modify portal content' from item
        # make sure current user creating the annex has this permission
        # here or it is not possible to set title and meetingFileType
        # it cas be the case when adding an annex on an item the user can not edit
        data = {'title': annex_title,
                'meetingFileType': meetingFileTypeUID}
        saved_modify_perm = self.context._Modify_portal_content_Permission
        self.context._Modify_portal_content_Permission = ['Member', ]
        newAnnexId = self.context.invokeFactory('MeetingFile',
                                                id=idCandidate,
                                                **data)
        self.context._Modify_portal_content_Permission = saved_modify_perm
        newAnnex = getattr(self.context, newAnnexId)
        newAnnex.setFile(annex_file, **kwargs)

        # do some specific stuffs if we are adding an annex on an item, not on an advice
        if self.context.meta_type == 'MeetingItem':
            # Add the annex creation to item history
            self.context.updateHistory('add',
                                       newAnnex,
                                       decisionRelated=(relatedTo == 'item_decision'))
            # Invalidate advices if needed and adding a normal annex
            if relatedTo == 'item' and self.context.willInvalidateAdvices():
                self.context.updateLocalRoles(invalidate=True)

            # Potentially I must notify MeetingManagers through email.
            if self.context.wfConditions().meetingIsPublished():
                self.context.sendMailIfRelevant('annexAdded', 'MeetingManager', isRole=True)

        # After processForm that itself calls at_post_create_script,
        # current user may loose permission to edit
        # the object because we copy item permissions.
        newAnnex.processForm()
        # display a warning portal message if annex size is large
        if newAnnex.warnSize():
            plone_utils.addPortalMessage(_("The annex that you just added has a large size and could be "
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
        portal = api.portal.get()
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
            annexes = self.getAnnexes()
            # sort annexes by modification date
            annexes.sort(key=lambda x: x.modified())
            for annex in annexes:
                self.context.annexIndex.append(annex.getAnnexInfo())

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
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return (self.context, relatedTo, makeSubLists, typesIds,
                realAnnexes, self.context.annexIndex, self.request['AUTHENTICATED_USER'],
                cfg.modified())

    @ram.cache(getAnnexesByType_cachekey)
    def getAnnexesByType(self, relatedTo, makeSubLists=True,
                         typesIds=[], realAnnexes=False):
        '''See docstring in interfaces.py'''
        res = []
        # bypass if no annex for current context
        if not self.context.annexIndex:
            return res

        tool = api.portal.get_tool('portal_plonemeeting')
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
                        annex = getattr(self.context, annexInfo['id'])
                        annexes.append(annex)
            if annexes:
                if makeSubLists:
                    res.append(annexes)
                else:
                    res += annexes
        return res

    def isConvertable(self, annex):
        """
          Check if the annex is convertable (hopefully).  If the annex mimetype is one taken into
          account by collective.documentviewer CONVERTABLE_TYPES, then it should be convertable...
        """
        mr = api.portal.get_tool('mimetypes_registry')
        try:
            content_type = mr.lookup(annex.content_type)
        except MimeTypeException:
            content_type = None
        if not content_type:
            logger.warning(CONTENT_TYPE_NOT_FOUND % annex.absolute_url_path())
            return False
        # get printable extensions from collective.documentviewer
        printableExtensions = self._documentViewerPrintableExtensions()

        # mr.lookup returns a list
        extensions = content_type[0].extensions
        # now that we have the extensions, find the one we are using
        currentExtension = ''
        # in case we have myimage.JPG, make sure extension is lowercase as
        # extentions on mimetypes_registry are lowercase...
        try:
            filename = annex.getFilename()
        except AttributeError:
            filename = annex.getFile().filename
        file_extension = filename.split('.')[-1].lower()
        for extension in extensions:
            if file_extension == extension:
                currentExtension = extension
                break

        # if we found the exact extension we are using, we can see if it is in the list
        # of printable extensions provided by collective.documentviewer
        # most of times, this is True...
        if currentExtension in printableExtensions:
            return True
        if not currentExtension:
            logger.warning(FILE_EXTENSION_NOT_FOUND % (annex.absolute_url_path(),
                                                       content_type[0]))

        # if we did not find the currentExtension in the mimetype's extensions,
        # for example an uploaded element without extension, check nevertheless
        # if the mimetype seems to be managed by collective.documentviewer
        if set(extensions).intersection(set(printableExtensions)):
            return True

        return False

    def conversionFailed(self, annex):
        """
          Check if conversion failed
        """
        annotations = IAnnotations(annex)
        if 'collective.documentviewer' in annotations and \
           'successfully_converted' in annotations['collective.documentviewer'] and \
           annotations['collective.documentviewer']['successfully_converted'] is False:
            return True
        return False

    def _documentViewerPrintableExtensions(self):
        """
          Compute file extensions that will be considered as printable.
        """
        from collective.documentviewer.config import CONVERTABLE_TYPES
        printableExtensions = []
        for convertable_type in CONVERTABLE_TYPES.iteritems():
            printableExtensions.extend(convertable_type[1].extensions)
        return printableExtensions

    def conversionStatus(self, annex):
        """
          Returns the conversion status of current MeetingFile.
          Status can be :
          - not_convertable : the MeetingFile is not convertable by collective.documentviewer
          - under_conversion : or awaiting conversion, the MeetingFile is convertable but is not yet converted
          - conversion_error : there was an error during MeetingFile conversion.
                               Manager have access in the UI to more infos.
          - successfully_converted : the MeetingFile is converted correctly
        """
        annotations = IAnnotations(annex)
        # not_convertable or awaiting conversion?
        if 'collective.documentviewer' not in annotations.keys() or not self.isConvertable(annex):
            return 'not_convertable'
        # under conversion?
        if 'successfully_converted' not in annotations['collective.documentviewer']:
            return 'under_conversion'

        if not annotations['collective.documentviewer']['successfully_converted'] is True:
            return 'conversion_error'

        return 'successfully_converted'


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
      - if user is Manager, this will remove the meeting including items;
      - if user is MeetingManager, the meeting must be empty to be removed.
    """
    def __init__(self, context):
        self.context = context

    def mayDelete(self):
        '''See docstring in interfaces.py.'''
        if not super(MeetingContentDeletableAdapter, self).mayDelete():
            return False

        if not self.context.getRawItems():
            return True

        member = api.user.get_current()
        if member.has_role('Manager'):
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
        parent = self.context.getParentNode()
        if checkPermission(ModifyPortalContent, parent):
            return True
        return False


class ItemPrettyLinkAdapter(PrettyLinkAdapter):
    """
      Override to take into account PloneMeeting use cases...
    """

    def _leadingIcons(self):
        """
          Manage icons to display before the icons managed by PrettyLink._icons.
        """
        res = []

        meeting = getCurrentMeetingObject(self.context)
        inAvailableItems = False
        if meeting:
            inAvailableItems = meeting._displayingAvailableItems()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedItemAttributes = cfg.getUsedItemAttributes()

        if inAvailableItems:
            # Item is in the list of available items, check if we
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
        elif itemState == 'accepted_but_modified':
            res.append(('accepted_but_modified.png', translate('icon_help_accepted_but_modified',
                                                               domain="PloneMeeting",
                                                               context=self.request)))
        elif itemState == 'pre_accepted':
            res.append(('pre_accepted.png', translate('icon_help_pre_accepted',
                                                      domain="PloneMeeting",
                                                      context=self.request)))
        elif itemState == 'waiting_advices':
            res.append(('wait_advices_from_proposed.png',
                        translate('icon_help_waiting_advices',
                                  domain="PloneMeeting",
                                  context=self.request)))
        elif itemState == 'itemcreated_waiting_advices':
            res.append(('wait_advices_from_itemcreated.png',
                        translate('icon_help_waiting_advices_from_itemcreated',
                                  domain="PloneMeeting",
                                  context=self.request)))
        elif itemState == 'proposed_waiting_advices':
            res.append(('wait_advices_from_proposed.png',
                        translate('icon_help_waiting_advices_from_proposed',
                                  domain="PloneMeeting",
                                  context=self.request)))
        elif itemState == 'prevalidated_waiting_advices':
            res.append(('wait_advices_from_prevalidated.png',
                        translate('icon_help_waiting_advices_from_prevalidated',
                                  domain="PloneMeeting",
                                  context=self.request)))

        # Display icons about sent/cloned to other meetingConfigs
        clonedToOtherMCIds = self.context._getOtherMeetingConfigsImAmClonedIn()
        toLocalizedTime = None
        for clonedToOtherMCId in clonedToOtherMCIds:
            # Append a tuple with name of the icon and a list containing
            # the msgid and the mapping as a dict
            # if item sent to the other mc is inserted into a meeting,
            # we display the meeting date
            emergency = clonedToOtherMCId in self.context.getOtherMeetingConfigsClonableToEmergency()
            msgid = emergency and 'sentto_othermeetingconfig_emergency' or 'sentto_othermeetingconfig'
            msg = translate(msgid,
                            mapping={'meetingConfigTitle': safe_unicode(getattr(tool,
                                                                        clonedToOtherMCId).Title())},
                            domain="PloneMeeting",
                            context=self.request)

            clonedBrain = self.context.getItemClonedToOtherMC(clonedToOtherMCId, theObject=False)
            if clonedBrain.linkedMeetingDate:
                # avoid instantiating toLocalizedTime more than once
                toLocalizedTime = toLocalizedTime or self.context.restrictedTraverse('@@plone').toLocalizedTime
                long_format = clonedBrain.linkedMeetingDate.hour() and True or False
                msg = msg + u' ({0})'.format(toLocalizedTime(clonedBrain.linkedMeetingDate, long_format=long_format))
            iconName = emergency and "clone_to_other_mc_emergency.png" or "clone_to_other_mc.png"
            res.append((iconName, msg))

        # if not already cloned to another mc, maybe it will be?
        # we could have an item to clone to 2 other MCs, one already sent, not the other...
        otherMeetingConfigsClonableTo = self.context.getOtherMeetingConfigsClonableTo()
        for otherMeetingConfigClonableTo in otherMeetingConfigsClonableTo:
            # already cloned?
            if otherMeetingConfigClonableTo in clonedToOtherMCIds:
                continue
            # Append a tuple with name of the icon and a list containing
            # the msgid and the mapping as a dict
            emergency = otherMeetingConfigClonableTo in self.context.getOtherMeetingConfigsClonableToEmergency()
            msgid = emergency and 'will_be_sentto_othermeetingconfig_emergency' or \
                'will_be_sentto_othermeetingconfig'
            iconName = emergency and "will_be_cloned_to_other_mc_emergency.png" or "will_be_cloned_to_other_mc.png"
            res.append((iconName,
                        translate(msgid,
                                  mapping={'meetingConfigTitle': safe_unicode(
                                           getattr(tool, otherMeetingConfigClonableTo).Title())},
                                  domain="PloneMeeting",
                                  context=self.request)))

        # display an icon if item is sent from another mc
        predecessor = self.context.getPredecessor()
        if predecessor and predecessor.portal_type != self.context.portal_type:
            predecessorCfg = tool.getMeetingConfig(predecessor)
            predecessorMeeting = predecessor.getMeeting()
            predecessor_state = predecessor.queryState()
            translated_state = translate(predecessor_state, domain='plone', context=self.request)
            if not predecessorMeeting:
                res.append(('cloned_not_decided.png',
                            translate('icon_help_cloned_not_presented',
                                      domain="PloneMeeting",
                                      mapping={'meetingConfigTitle': safe_unicode(predecessorCfg.Title()),
                                               'predecessorState': translated_state},
                                      context=self.request,
                                      default="Sent from ${meetingConfigTitle}, "
                                      "original item is \"${predecessorState}\".")))
            else:
                if predecessor_state in predecessorCfg.getItemPositiveDecidedStates():
                    res.append(('cloned_and_decided.png',
                                translate(
                                    'icon_help_cloned_and_decided',
                                    mapping={'meetingDate': tool.formatMeetingDate(predecessorMeeting),
                                             'meetingConfigTitle': safe_unicode(predecessorCfg.Title()),
                                             'predecessorState': translated_state},
                                    domain="PloneMeeting",
                                    context=self.request,
                                    default="Sent from ${meetingConfigTitle} (${meetingDate}), original item is "
                                    "\"${predecessorState}\".")))
                else:
                    res.append(('cloned_not_decided.png',
                                translate('icon_help_cloned_not_decided',
                                          mapping={'meetingDate': tool.formatMeetingDate(predecessorMeeting),
                                                   'meetingConfigTitle': safe_unicode(predecessorCfg.Title()),
                                                   'predecessorState': translated_state},
                                          domain="PloneMeeting",
                                          context=self.request,
                                          default="Sent from ${meetingConfigTitle} (${meetingDate}), original item is "
                                          "\"${predecessorState}\".")))

        # display icons if element is down the workflow or up for at least second time...
        # display it only for items before state 'validated'
        downOrUpWorkflowAgain = self.context.downOrUpWorkflowAgain()
        if downOrUpWorkflowAgain == "down":
            res.append(('wf_down.png', translate('icon_help_wf_down',
                                                 domain="PloneMeeting",
                                                 context=self.request)))
        elif downOrUpWorkflowAgain == "up":
            res.append(('wf_up.png', translate('icon_help_wf_up',
                                               domain="PloneMeeting",
                                               context=self.request)))

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
                res.append((iconName, translate(u'Taken over by ${fullname}',
                                                domain="PloneMeeting",
                                                mapping={'fullname': safe_unicode(tool.getUserName(takenOverBy))},
                                                context=self.request)))
        return res


class MeetingPrettyLinkAdapter(PrettyLinkAdapter):
    """
      Override to take into account PloneMeeting use cases...
    """

    def _leadingIcons(self):
        """
          Manage icons to display before the icons managed by PrettyLink._icons.
        """
        res = []
        if self.context.getExtraordinarySession():
            res.append(('extraordinarySession.png',
                        translate('this_meeting_is_extraodrinary_session',
                                  domain="PloneMeeting",
                                  context=self.request)))
        return res


class PMWfHistoryAdapter(ImioWfHistoryAdapter):
    """
      Override the imio.history ImioHistoryAdapter.
    """
    def ignorableHistoryComments(self):
        """Add some more ignorable history comments."""
        ignorable_history_comment = super(PMWfHistoryAdapter, self).ignorableHistoryComments()
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
            tool = api.portal.get_tool('portal_plonemeeting')
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
    """
      Override method that gets criteria to be able to manage various use cases :
      - for meetings : get the criteria from the MeetingConfig (searches_items) and filter
        out elements not in MeetingConfig.getDashboardAvailableItemsFilters and not in
        MeetingConfig.getDashboardPresentedItemsFilters;
      - for listing of items : filter out criteria no in MeetingConfig.getDashboardItemsFilters;
      - for listing of meetings : filter out criteria no in MeetingConfig.getDashboardMeetingsFilters.
    """

    def __init__(self, context):
        """ """
        super(Criteria, self).__init__(context)
        # return really stored widgets when necessary
        if 'portal_plonemeeting' in context.absolute_url() or \
           context.REQUEST.get('enablingFacetedDashboard', False):
            return
        try:
            tool = api.portal.get_tool('portal_plonemeeting')
        except InvalidParameterError:
            # in case 'portal_plonemeeting' is not available, keep classing criteria behaviour
            return
        cfg = tool.getMeetingConfig(context)
        if not cfg:
            return
        # meeting view
        kept_filters = []
        resultsperpagedefault = "20"
        if IMeeting.providedBy(context):
            self.context = cfg.searches.searches_items
            if context._displayingAvailableItems():
                kept_filters = cfg.getDashboardMeetingAvailableItemsFilters()
                resultsperpagedefault = cfg.getMaxShownAvailableItems()
            else:
                kept_filters = cfg.getDashboardMeetingLinkedItemsFilters()
                resultsperpagedefault = cfg.getMaxShownMeetingItems()
        else:
            # on a faceted?  it is a pmFolder or a subFolder of the pmFolder
            resultsperpagedefault = cfg.getMaxShownListings()
            if IFacetedNavigable.providedBy(context):
                # listings of items has some configuration but not listings of meetings
                if context.getId() == 'searches_items':
                    kept_filters = cfg.getDashboardItemsListingsFilters()
                    self.context = cfg.searches.searches_items
                elif context.getId() == 'searches_meetings':
                    self.context = cfg.searches.searches_meetings
                    self.criteria = self._criteria()
                    return
                elif context.getId() == 'searches_decisions':
                    self.context = cfg.searches.searches_decisions
                    self.criteria = self._criteria()
                    return
                else:
                    self.context = cfg.searches
                    self.criteria = self._criteria()
                    return

        self.criteria = self._criteria()

        res = PersistentList()
        for criterion in self.criteria:
            if criterion.section != u'advanced' or \
               criterion.__name__ in kept_filters:
                res.append(criterion)
            # manage default value for the 'resultsperpage' criterion
            if criterion.widget == ResultsPerPageWidget.widget_type:
                criterion.default = resultsperpagedefault
        self.criteria = res


class CompoundCriterionBaseAdapter(object):

    def __init__(self, context):
        self.context = context
        self.request = self.context.REQUEST
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def query(self):
        ''' '''
        return {}


class ItemsOfMyGroupsAdapter(CompoundCriterionBaseAdapter):

    def itemsofmygroups_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemsofmygroups_cachekey)
    def query_itemsofmygroups(self):
        '''Queries all items of groups of the current user, no matter wich suffix
           of the group the user is in.'''
        userGroupIds = [mGroup.getId() for mGroup in self.tool.getGroupsForUser()]
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                'getProposingGroup': {'query': userGroupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemsofmygroups


class MyItemsTakenOverAdapter(CompoundCriterionBaseAdapter):

    def myitemstakenover_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(myitemstakenover_cachekey)
    def query_myitemstakenover(self):
        '''Queries all items that current user take over.'''
        member = api.user.get_current()
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                'getTakenOverBy': {'query': member.getId()}, }

    # we may not ram.cache methods in same file with same name...
    query = query_myitemstakenover


class ItemsInCopyAdapter(CompoundCriterionBaseAdapter):

    def itemsincopy_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemsincopy_cachekey)
    def query_itemsincopy(self):
        '''Queries all items for which the current user is in copyGroups.'''
        groupsTool = api.portal.get_tool('portal_groups')
        member = api.user.get_current()
        userGroups = groupsTool.getGroupsForPrincipal(member)
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'getCopyGroups' use 'OR' by default
                'getCopyGroups': {'query': userGroups}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemsincopy


class ItemsToValidateOfHighestHierarchicLevelAdapter(CompoundCriterionBaseAdapter):

    def itemstovalidateofhighesthierarchiclevel_query_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstovalidateofhighesthierarchiclevel_query_cachekey)
    def query_itemstovalidateofhighesthierarchiclevel(self):
        '''Return a list of items that the user can validate regarding his highest hierarchic level.
           So if a user is 'prereviewer' and 'reviewier', the search will only return items
           in state corresponding to his 'reviewer' role.'''
        member = api.user.get_current()
        groupsTool = api.portal.get_tool('portal_groups')
        groupIds = groupsTool.getGroupsForPrincipal(member)
        res = []
        highestReviewerLevel = self.cfg._highestReviewerLevel(groupIds)
        if not highestReviewerLevel:
            # in this case, we do not want to display a result
            # we return an unknown review_state
            return FIND_NOTHING_QUERY
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

        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                'getProposingGroup': {'query': res},
                'review_state': {'query': review_state}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstovalidateofhighesthierarchiclevel


class ItemsToValidateOfEveryReviewerLevelsAndLowerLevelsAdapter(CompoundCriterionBaseAdapter):

    def itemstovalidateofeveryreviewerlevelsandlowerlevels_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstovalidateofeveryreviewerlevelsandlowerlevels_cachekey)
    def query_itemstovalidateofeveryreviewerlevelsandlowerlevels(self):
        '''This will check for user highest reviewer level of each of his groups and return these items and
           items of lower reviewer levels.
           This search works if the workflow manage reviewer levels where higher reviewer level
           can validate lower reviewer levels EVEN IF THE USER IS NOT IN THE CORRESPONDING PLONE SUBGROUP.
           For example with a 3 levels reviewer workflow, called review1 (lowest level),
           review2 and review3 (highest level) :
           - reviewer1 may validate items in reviewer1;
           - reviewer2 may validate items in reviewer1 and reviewer2;
           - reviewer3 may validate items in reviewer1, reviewer2 and reviewer3.
           So get highest hierarchic level of each group of the user and
           take into account lowest levels too.'''
        # search every highest reviewer level for each group of the user
        member = api.user.get_current()
        groupsTool = api.portal.get_tool('portal_groups')
        userMeetingGroups = self.tool.getGroupsForUser()
        groupIds = groupsTool.getGroupsForPrincipal(member)
        reviewProcessInfos = []
        for mGroup in userMeetingGroups:
            ploneGroups = []
            # find Plone groups of the mGroup the user is in
            mGroupId = mGroup.getId()
            for groupId in groupIds:
                if groupId.startswith('%s_' % mGroupId):
                    ploneGroups.append(groupId)
            # now that we have Plone groups of the mGroup
            # we can get highest hierarchic level and find sub levels
            highestReviewerLevel = self.cfg._highestReviewerLevel(ploneGroups)
            if not highestReviewerLevel:
                continue
            foundLevel = False
            for reviewer_suffix, review_state in MEETINGREVIEWERS.items():
                if not foundLevel and not reviewer_suffix == highestReviewerLevel:
                    continue
                foundLevel = True
                # specific management for workflows using the 'pre_validation' or
                # 'pre_validation_keep_reviewer_permissions' wfAdaptation
                if reviewer_suffix == 'reviewers' and \
                    ('pre_validation' in self.cfg.getWorkflowAdaptations() or
                     'pre_validation_keep_reviewer_permissions' in self.cfg.getWorkflowAdaptations()):
                    review_state = 'prevalidated'
                reviewProcessInfos.append('%s__reviewprocess__%s' % (mGroupId,
                                                                     review_state))
        if not reviewProcessInfos:
            # in this case, we do not want to display a result
            # we return an unknown review_state
            return FIND_NOTHING_QUERY

        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                'reviewProcessInfo': {'query': reviewProcessInfos}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstovalidateofeveryreviewerlevelsandlowerlevels


class ItemsToValidateOfMyReviewerGroupsAdapter(CompoundCriterionBaseAdapter):

    def itemstovalidateofmyreviewergroups_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstovalidateofmyreviewergroups_cachekey)
    def query_itemstovalidateofmyreviewergroups(self):
        '''Return a list of items that the user could validate.  So it returns every items the current
           user is able to validate at any state of the validation process.  So if a user is 'prereviewer'
           and 'reviewer' for a group, the search will return items in both states.'''
        member = api.user.get_current()
        groupsTool = api.portal.get_tool('portal_groups')
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
            return FIND_NOTHING_QUERY

        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                'reviewProcessInfo': {'query': reviewProcessInfos}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstovalidateofmyreviewergroups


class ItemsToCorrectAdapter(CompoundCriterionBaseAdapter):

    def itemstocorrect_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstocorrect_cachekey)
    def query_itemstocorrect(self):
        '''Queries all items that current user may correct.'''
        # get the state 'returned_to_proposing_group' and check what roles are able edit
        # so we will get groups suffixes linked to these roles and find relevant proposingGroups
        wfTool = api.portal.get_tool('portal_workflow')
        itemWF = wfTool.getWorkflowsFor(self.cfg.getItemTypeName())[0]
        if 'returned_to_proposing_group' in itemWF.states:
            roles = itemWF.states['returned_to_proposing_group'].permission_roles[ModifyPortalContent]
            suffixes = [suffix for suffix, role in MEETINGROLES.items() if role in roles]
            userGroupIds = [mGroup.getId() for mGroup in self.tool.getGroupsForUser(suffixes=suffixes)]
            if not userGroupIds:
                return FIND_NOTHING_QUERY
            # Create query parameters
            return {'portal_type': {'query': self.cfg.getItemTypeName()},
                    'review_state': {'query': ['returned_to_proposing_group', ]},
                    'getProposingGroup': {'query': userGroupIds}, }

        return FIND_NOTHING_QUERY

    # we may not ram.cache methods in same file with same name...
    query = query_itemstocorrect


class ItemsToAdviceAdapter(CompoundCriterionBaseAdapter):

    def itemstoadvice_cachekey(method, self):
        '''cachekey method for query.'''
        return str(self.context.REQUEST._debug)

    @property
    @ram.cache(itemstoadvice_cachekey)
    def query_itemstoadvice(self):
        '''Queries all items for which the current user must give an advice.'''
        groups = self.tool.getGroupsForUser(suffixes=['advisers'])
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will return 'not delay-aware' and 'delay-aware' advices
        groupIds = [g.getId() + '_advice_not_given' for g in groups] + \
                   ['delay__' + g.getId() + '_advice_not_given' for g in groups] + \
                   [g.getId() + '_advice_asked_again' for g in groups] + \
                   ['delay__' + g.getId() + '_advice_asked_again' for g in groups]
        # Create query parameters
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': {'query': groupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstoadvice


class ItemsToAdviceWithoutDelayAdapter(CompoundCriterionBaseAdapter):

    def itemstoadvicewithoutdelay_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstoadvicewithoutdelay_cachekey)
    def query_itemstoadvicewithoutdelay(self):
        '''Queries all items for which the current user must give an advice without delay.'''
        groups = self.tool.getGroupsForUser(suffixes=['advisers'])
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will only return 'not delay-aware' advices
        groupIds = [g.getId() + '_advice_not_given' for g in groups] + \
                   [g.getId() + '_advice_asked_again' for g in groups]
        # Create query parameters
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': {'query': groupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstoadvicewithoutdelay


class ItemsToAdviceWithDelayAdapter(CompoundCriterionBaseAdapter):

    def itemstoadvicewithdelay_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstoadvicewithdelay_cachekey)
    def query_itemstoadvicewithdelay(self):
        '''Queries all items for which the current user must give an advice with delay.'''

        groups = self.tool.getGroupsForUser(suffixes=['advisers'])
        # Add a '_advice_not_given' at the end of every group id: we want "not given" advices.
        # this search will only return 'delay-aware' advices
        groupIds = ['delay__' + g.getId() + '_advice_not_given' for g in groups] + \
                   ['delay__' + g.getId() + '_advice_asked_again' for g in groups]
        # Create query parameters
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': {'query': groupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstoadvicewithdelay


class ItemsToAdviceWithExceededDelayAdapter(CompoundCriterionBaseAdapter):

    def itemstoadvicewithexceededdelay_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(itemstoadvicewithexceededdelay_cachekey)
    def query_itemstoadvicewithexceededdelay(self):
        '''Queries all items for which the current user must give an advice with exceeded delay.'''
        groups = self.tool.getGroupsForUser(suffixes=['advisers'])
        # Add a '_delay_exceeded' at the end of every group id: we want "not given" advices.
        # this search will only return 'delay-aware' advices for wich delay is exceeded
        groupIds = ['delay__' + g.getId() + '_advice_delay_exceeded' for g in groups]
        # Create query parameters
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': {'query': groupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_itemstoadvicewithexceededdelay


class AdvisedItemsAdapter(CompoundCriterionBaseAdapter):

    def adviseditems_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(adviseditems_cachekey)
    def query_adviseditems(self):
        '''Queries items for which an advice has been given.'''
        groups = self.tool.getGroupsForUser(suffixes=['advisers'])
        # advised items are items that has an advice in a particular review_state
        # just append every available meetingadvice state: we want "given" advices.
        # this search will return every advices
        wfTool = api.portal.get_tool('portal_workflow')
        adviceStates = []
        # manage multiple 'meetingadvice' portal_types
        for portal_type in self.tool.getAdvicePortalTypes():
            adviceWF = wfTool.getWorkflowsFor(portal_type.id)[0]
            adviceStates += adviceWF.states.keys()
        # remove duplicates
        adviceStates = tuple(set(adviceStates))
        groupIds = []
        for adviceState in adviceStates:
            groupIds += [g.getId() + '_%s' % adviceState for g in groups]
            groupIds += ['delay__' + g.getId() + '_%s' % adviceState for g in groups]
        # Create query parameters
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': {'query': groupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_adviseditems


class AdvisedItemsWithDelayAdapter(CompoundCriterionBaseAdapter):

    def adviseditemswithdelay_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(adviseditemswithdelay_cachekey)
    def query_adviseditemswithdelay(self):
        '''Queries items for which an advice has been given with delay.'''
        groups = self.tool.getGroupsForUser(suffixes=['advisers'])
        # advised items are items that has an advice in a particular review_state
        # just append every available meetingadvice state: we want "given" advices.
        # this search will only return 'delay-aware' advices
        wfTool = api.portal.get_tool('portal_workflow')
        adviceStates = []
        # manage multiple 'meetingadvice' portal_types
        for portal_type in self.tool.getAdvicePortalTypes():
            adviceWF = wfTool.getWorkflowsFor(portal_type.id)[0]
            adviceStates += adviceWF.states.keys()
        # remove duplicates
        adviceStates = tuple(set(adviceStates))
        groupIds = []
        for adviceState in adviceStates:
            groupIds += ['delay__' + g.getId() + '_%s' % adviceState for g in groups]
        # Create query parameters
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                # KeywordIndex 'indexAdvisers' use 'OR' by default
                'indexAdvisers': {'query': groupIds}, }

    # we may not ram.cache methods in same file with same name...
    query = query_adviseditemswithdelay


class DecidedItemsAdapter(CompoundCriterionBaseAdapter):

    def decideditems_cachekey(method, self):
        '''cachekey method for every CompoundCriterion adapters.'''
        return str(self.request._debug)

    @property
    @ram.cache(decideditems_cachekey)
    def query_decideditems(self):
        '''Queries decided items.'''
        return {'portal_type': {'query': self.cfg.getItemTypeName()},
                'review_state': {'query': self.cfg.getItemDecidedStates()}, }

    # we may not ram.cache methods in same file with same name...
    query = query_decideditems
