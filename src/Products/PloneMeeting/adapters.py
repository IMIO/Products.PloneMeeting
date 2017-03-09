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
from zope.globalrequest import getRequest

from plone.memoize import ram
from plone.memoize.instance import memoize

from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.MimetypesRegistry.common import MimeTypeException
from Products.CMFPlone.utils import safe_unicode
from plone import api
from plone.api.exc import InvalidParameterError

from collective.documentviewer.settings import GlobalSettings
from collective.iconifiedcategory.adapter import CategorizedObjectAdapter
from collective.iconifiedcategory.adapter import CategorizedObjectInfoAdapter
from collective.iconifiedcategory.utils import get_categories
from eea.facetednavigation.criteria.handler import Criteria as eeaCriteria
from eea.facetednavigation.interfaces import IFacetedNavigable
from eea.facetednavigation.widgets.resultsperpage.widget import Widget as ResultsPerPageWidget
from imio.actionspanel.adapters import ContentDeletableAdapter as APContentDeletableAdapter
from imio.history.adapters import ImioWfHistoryAdapter
from imio.prettylink.adapters import PrettyLinkAdapter
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import AddAnnexDecision
from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.config import MEETINGROLES
from Products.PloneMeeting.config import READER_USECASES
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.utils import displaying_available_items
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.MeetingConfig import CONFIGGROUPPREFIX
from Products.PloneMeeting.MeetingConfig import PROPOSINGGROUPPREFIX
from Products.PloneMeeting.MeetingConfig import READERPREFIX
from Products.PloneMeeting.MeetingConfig import SUFFIXPROFILEPREFIX

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
        self.request = getRequest()

    def addAnnex(self, idCandidate, annex_title, annex_file,
                 relatedTo, meetingFileTypeUID, **kwargs):
        '''See docstring in interfaces.py'''
        # first of all, check if we can actually add the annex
        if relatedTo == 'item_decision' and \
           not _checkPermission("PloneMeeting: Write decision annex", self.context):
            raise Unauthorized
        elif (not relatedTo == 'item_decision' and
              not _checkPermission("PloneMeeting: Add annex", self.context)):
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
        userId = api.user.get_current().getId()
        logger.info('Annex at %s uploaded by "%s".' % (newAnnex.absolute_url_path(), userId))
        return newAnnex

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
        if False and annexInfo['isConfidential'] and \
            ((isPowerObserver and 'power_observers' in cfg.getAnnexConfidentialFor()) or
             (isRestrictedPowerObserver and 'restricted_power_observers' in cfg.getAnnexConfidentialFor())):
            return False
        return True

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
        useConfidentiality = False
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


class AnnexDecisionContentDeletableAdapter(APContentDeletableAdapter):
    """
      Manage the mayDelete for annexDecision.
      A decision annex is deletable by the annexDecision Owner ad vitam.
    """
    def __init__(self, context):
        self.context = context

    def mayDelete(self):
        '''See docstring in interfaces.py.'''
        # check 'Delete objects' permission
        mayDelete = super(AnnexDecisionContentDeletableAdapter, self).mayDelete()
        if not mayDelete:
            # a 'Owner' may still remove an 'annexDecision' if enabled
            # in the cfg and if still able to add 'annexDecision'
            if self.context.portal_type == 'annexDecision':
                tool = api.portal.get_tool('portal_plonemeeting')
                cfg = tool.getMeetingConfig(self.context)
                if cfg.getOwnerMayDeleteAnnexDecision() and \
                   _checkPermission(AddAnnexDecision, self.context):
                    member = api.user.get_current()
                    if 'Owner' in member.getRolesInContext(self.context):
                        return True
        return mayDelete


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
        if _checkPermission(ModifyPortalContent, parent):
            return True
        return False


class ItemPrettyLinkAdapter(PrettyLinkAdapter):
    """
      Override to take into account PloneMeeting use cases...
    """

    def getLink_cachekey(method, self):
        '''cachekey method for self.getLink.'''
        res = super(ItemPrettyLinkAdapter, self).getLink_cachekey(self)
        # manage when displayed in availableItems on the meeting_view
        meeting_modified = None
        if displaying_available_items(self.context):
            meeting = getCurrentMeetingObject(self.context)
            if meeting:
                meeting_modified = meeting.modified()
        # manage takenOverBy
        current_member = None
        takenOverBy = self.context.getTakenOverBy()
        if takenOverBy:
            current_member = self.request['AUTHENTICATED_USER'].getId()
        # manage when displaying the icon with informations about
        # the predecessor living in another MC
        predecessor_modified = None
        predecessor = self._predecessorFromOtherMC()
        if predecessor:
            predecessor_modified = predecessor.modified()
        # manage otherMC to send to
        ann = IAnnotations(self.context)
        other_mc_to_clone_to_ann_keys = [
            self.context._getSentToOtherMCAnnotationKey(destMeetingConfigId)
            for destMeetingConfigId in self.context.getOtherMeetingConfigsClonableTo()
            if self.context._getSentToOtherMCAnnotationKey(destMeetingConfigId) in ann]
        return res + (meeting_modified,
                      takenOverBy,
                      current_member,
                      predecessor_modified,
                      other_mc_to_clone_to_ann_keys)

    @ram.cache(getLink_cachekey)
    def getLink(self):
        """Necessary to be able to override the cachekey."""
        return self._getLink()

    def _predecessorFromOtherMC(self):
        predecessor = self.context.getPredecessor()
        if predecessor and predecessor.portal_type != self.context.portal_type:
            return predecessor
        return None

    def _leadingIcons(self):
        """
          Manage icons to display before the icons managed by PrettyLink._icons.
        """
        res = []

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedItemAttributes = cfg.getUsedItemAttributes()

        if displaying_available_items(self.context):
            meeting = getCurrentMeetingObject(self.context)
            # there could be no meeting if we opened an item from the available items view
            if meeting:
                # Item is in the list of available items, check if we
                # must show a deadline- or late-related icon.
                if self.context.wfConditions().isLateFor(meeting):
                    # A late item, or worse: a late item not respecting the freeze deadline.
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
            res.append(('return_to_proposing_group.png',
                        translate('icon_help_returned_to_proposing_group',
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
        elif itemState == 'postponed_next_meeting':
            res.append(('postponed_next_meeting.png',
                        translate('icon_help_postponed_next_meeting',
                                  domain="PloneMeeting",
                                  context=self.request)))
        elif itemState == 'marked_not_applicable':
            res.append(('marked_not_applicable.png',
                        translate('icon_help_marked_not_applicable',
                                  domain="PloneMeeting",
                                  context=self.request)))
        elif itemState == 'removed':
            res.append(('removed.png',
                        translate('icon_help_removed',
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
            clonedToOtherMC = getattr(tool, clonedToOtherMCId)
            msgid = emergency and 'sentto_othermeetingconfig_emergency' or 'sentto_othermeetingconfig'
            msg = translate(msgid,
                            mapping={'meetingConfigTitle': safe_unicode(clonedToOtherMC.Title())},
                            domain="PloneMeeting",
                            context=self.request)

            clonedBrain = self.context.getItemClonedToOtherMC(clonedToOtherMCId, theObject=False)
            # do not check on linkedMeetingDate because it may contains '1950/01/01',
            # see linkedMeetingDate indexer in indexes.py
            if clonedBrain.linkedMeetingUID:
                # avoid instantiating toLocalizedTime more than once
                toLocalizedTime = toLocalizedTime or self.context.restrictedTraverse('@@plone').toLocalizedTime
                long_format = clonedBrain.linkedMeetingDate.hour() and True or False
                msg = msg + u' ({0})'.format(toLocalizedTime(clonedBrain.linkedMeetingDate, long_format=long_format))
            iconName = emergency and "clone_to_other_mc_emergency" or "clone_to_other_mc"
            # manage the otherMeetingConfigsClonableToPrivacy
            if 'privacy' in clonedToOtherMC.getUsedItemAttributes():
                iconName += "_{0}".format(clonedBrain.privacy)
                msg = msg + u' ({0})'.format(translate(clonedBrain.privacy,
                                                       domain="PloneMeeting",
                                                       context=self.request))
            res.append(("{0}.png".format(iconName), msg))

        # if not already cloned to another mc, maybe it will be?
        # we could have an item to clone to 2 other MCs, one already sent, not the other...
        otherMeetingConfigsClonableTo = self.context.getOtherMeetingConfigsClonableTo()
        for otherMeetingConfigClonableToId in otherMeetingConfigsClonableTo:
            # already cloned?
            if otherMeetingConfigClonableToId in clonedToOtherMCIds:
                continue

            # Append a tuple with name of the icon and a list containing
            # the msgid and the mapping as a dict
            otherMeetingConfigClonableTo = getattr(tool, otherMeetingConfigClonableToId)
            emergency = otherMeetingConfigClonableToId in self.context.getOtherMeetingConfigsClonableToEmergency()
            msgid = emergency and 'will_be_sentto_othermeetingconfig_emergency' or \
                'will_be_sentto_othermeetingconfig'
            iconName = emergency and "will_be_cloned_to_other_mc_emergency" or "will_be_cloned_to_other_mc"
            msg = translate(msgid,
                            mapping={'meetingConfigTitle': safe_unicode(
                                     otherMeetingConfigClonableTo.Title())},
                            domain="PloneMeeting",
                            context=self.request)
            # manage the otherMeetingConfigsClonableToPrivacy
            suffix = ''
            if 'otherMeetingConfigsClonableToPrivacy' in usedItemAttributes and \
               'privacy' in otherMeetingConfigClonableTo.getUsedItemAttributes():
                if otherMeetingConfigClonableToId in self.context.getOtherMeetingConfigsClonableToPrivacy():
                    suffix = "_secret"
                else:
                    suffix = "_public"
                msg = msg + u' ({0})'.format(translate(suffix[1:],
                                                       domain="PloneMeeting",
                                                       context=self.request))
            res.append(("{0}{1}.png".format(iconName, suffix),
                        msg))

        # display an icon if item is sent from another mc
        predecessor = self._predecessorFromOtherMC()
        if predecessor:
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

    def manage_criteria_cachekey(method, self, context):
        '''cachekey method for self.compute_criteria.'''
        return context, str(context.REQUEST._debug)

    def __init__(self, context):
        """ """
        self.context, self.criteria = self.compute_criteria(context)

    @ram.cache(manage_criteria_cachekey)
    def compute_criteria(self, context):
        """ """
        # return really stored widgets when necessary
        if 'portal_plonemeeting' in context.absolute_url() or \
           context.REQUEST.get('enablingFacetedDashboard', False):
            super(Criteria, self).__init__(context)
            return self.context, self.criteria
        try:
            tool = api.portal.get_tool('portal_plonemeeting')
        except InvalidParameterError:
            # in case 'portal_plonemeeting' is not available, use original criteria behaviour
            super(Criteria, self).__init__(context)
            return self.context, self.criteria
        cfg = tool.getMeetingConfig(context)
        if not cfg:
            super(Criteria, self).__init__(context)
            return self.context, self.criteria
        # meeting view
        kept_filters = []
        resultsperpagedefault = "20"
        meeting_view = False
        if IMeeting.providedBy(context):
            meeting_view = True
            self.context = cfg.searches.searches_items
            if displaying_available_items(context):
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
                    return self.context, self.criteria
                elif context.getId() == 'searches_decisions':
                    self.context = cfg.searches.searches_decisions
                    self.criteria = self._criteria()
                    return self.context, self.criteria
                else:
                    self.context = cfg.searches
                    self.criteria = self._criteria()
                    return self.context, self.criteria

        res = PersistentList()
        for criterion in self._criteria():
            # do not keep sorting criterion on the meeting_view
            if meeting_view and criterion.widget == u'sorting':
                continue
            if criterion.section != u'advanced' or \
               criterion.__name__ in kept_filters:
                res.append(criterion)
            # manage default value for the 'resultsperpage' criterion
            if criterion.widget == ResultsPerPageWidget.widget_type:
                criterion.default = resultsperpagedefault
        self.criteria = res
        return self.context, self.criteria


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


class PMCategorizedObjectInfoAdapter(CategorizedObjectInfoAdapter):
    """ """

    def __init__(self, context):
        super(PMCategorizedObjectInfoAdapter, self).__init__(context)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)
        self.parent = self.context.getParentNode()

    def get_infos(self, category, limited=False):
        """A the 'visible_for_groups' info."""
        infos = super(PMCategorizedObjectInfoAdapter, self).get_infos(
            category, limited=limited)
        infos['visible_for_groups'] = self._visible_for_groups()
        return infos

    def _apply_visible_groups_security(self, group_ids):
        """Compute 'View' permission if annex is confidential,
           apply local_roles and give 'View' to 'AnnexReader' either,
           remove every local_roles and acquire 'View'."""
        if self.parent.meta_type == 'MeetingItem' or \
           self.parent.portal_type in self.tool.getAdvicePortalTypes(as_ids=True):
            # reinitialize permissions in case no more confidential
            # or confidentiality configuration changed
            self.context.__ac_local_roles_block__ = False
            self.context.manage_permission("View", (), acquire=True)
            self.context.manage_permission("Access contents information", (), acquire=True)
            grp_reader_localroles = [
                grp_id for grp_id in self.context.__ac_local_roles__
                if self.context.__ac_local_roles__[grp_id] == [READER_USECASES['confidentialannex']]]
            self.context.manage_delLocalRoles(grp_reader_localroles)
            if self.context.confidential:
                self.context.manage_permission(
                    "View",
                    (READER_USECASES['confidentialannex'], 'Manager', 'MeetingManager'),
                    acquire=False)
                self.context.manage_permission(
                    "Access contents information",
                    (READER_USECASES['confidentialannex'], 'Manager', 'MeetingManager'),
                    acquire=False)
                for grp_id in group_ids:
                    self.context.manage_addLocalRoles(
                        grp_id, (READER_USECASES['confidentialannex'], ))
            self.context.reindexObjectSecurity()

    def _visible_for_groups(self):
        """ """
        groups = []
        if self.context.confidential:
            parent_meta_type = self.parent.meta_type
            if parent_meta_type == 'MeetingItem':
                groups = self._item_visible_for_groups()
            elif parent_meta_type == 'Meeting':
                groups = self._meeting_visible_for_groups()
            else:
                # advice
                groups = self._advice_visible_for_groups()
        self._apply_visible_groups_security(groups)
        return groups

    def _item_visible_for_groups(self):
        """ """
        visible_fors = self.cfg.getItemAnnexConfidentialVisibleFor()
        res = []
        res += self._configgroup_groups(visible_fors)
        res += self._reader_groups(visible_fors)
        res += self._suffix_proposinggroup(visible_fors)
        return res

    def _meeting_visible_for_groups(self):
        """ """
        visible_fors = self.cfg.getMeetingAnnexConfidentialVisibleFor()
        res = []
        res += self._configgroup_groups(visible_fors)
        res += self._suffix_profile_proposinggroup(visible_fors)
        return res

    def _advice_visible_for_groups(self):
        """ """
        visible_fors = self.cfg.getAdviceAnnexConfidentialVisibleFor()
        res = []
        res += self._configgroup_groups(visible_fors)
        res += self._reader_groups(visible_fors)
        res += self._suffix_proposinggroup(visible_fors)
        if 'adviser_group' in visible_fors:
            group = self.tool[self.parent.advice_group]
            res.append(group.getPloneGroupId(suffix='advisers'))
        return res

    def _configgroup_groups(self, visible_fors):
        """ """
        res = []
        for visible_for in visible_fors:
            if visible_for.startswith(CONFIGGROUPPREFIX):
                suffix = visible_for.replace(CONFIGGROUPPREFIX, '')
                res.append('{0}_{1}'.format(self.cfg.getId(), suffix))
        return res

    def _suffix_proposinggroup(self, visible_fors):
        """ """
        res = []
        proposingGroup = self.parent.getProposingGroup(theObject=True)
        for visible_for in visible_fors:
            if visible_for.startswith(PROPOSINGGROUPPREFIX):
                suffix = visible_for.replace(PROPOSINGGROUPPREFIX, '')
                res.append(proposingGroup.getPloneGroupId(suffix))
        return res

    def _suffix_profile_proposinggroup(self, visible_fors):
        """ """
        res = []
        for visible_for in visible_fors:
            if visible_for.startswith(SUFFIXPROFILEPREFIX):
                res.append(visible_for)
        return res

    def _reader_groups(self, visible_fors):
        """ """
        res = []
        for visible_for in visible_fors:
            if visible_for == '{0}advices'.format(READERPREFIX):
                for groupId in self.parent.adviceIndex.keys():
                    group = self.tool[groupId]
                    res.append(group.getPloneGroupId(suffix='advisers'))
            elif visible_for == '{0}copy_groups'.format(READERPREFIX):
                res = res + list(self.parent.getAllCopyGroups(auto_real_group_ids=True))
            elif visible_for == '{0}groupincharge'.format(READERPREFIX):
                proposingGroup = self.parent.getProposingGroup(True)
                groupInCharge = proposingGroup.getGroupInChargeAt()
                if groupInCharge:
                    res.append(groupInCharge.getPloneGroupId(suffix='observers'))
        return res


class PMCategorizedObjectAdapter(CategorizedObjectAdapter):
    """ """

    def __init__(self, context, request, brain):
        super(PMCategorizedObjectAdapter, self).__init__(context, request, brain)

    def _user_groups_cachekey(method, self, as_ids=False):
        '''cachekey method for self._user_groups.'''
        return str(self.request._debug)

    @ram.cache(_user_groups_cachekey)
    def _user_groups(self):
        user = api.user.get_current()
        return user.getGroups()

    def _use_isPrivacyViewable_cachekey(method, self):
        '''cachekey method for self._use_isPrivacyViewable.'''
        return str(self.request._debug)

    @ram.cache(_use_isPrivacyViewable_cachekey)
    def _use_isPrivacyViewable(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if cfg.getRestrictAccessToSecretItems():
            return True
        return False

    def can_view(self):
        # bypass for MeetingManagers
        tool = api.portal.get_tool('portal_plonemeeting')
        if tool.isManager(self.context):
            return True

        # is the context a MeetingItem and privacy viewable?
        if self.context.meta_type == 'MeetingItem' and \
           self._use_isPrivacyViewable() and \
           not self.context.adapted().isPrivacyViewable():
            return False

        elif self.context.meta_type == 'Meeting':
            # if we have a SUFFIXPROFILEPREFIX prefixed group,
            # check using "userIsAmong", this is only done for Meetings
            infos = self.context.categorized_elements[self.brain.UID]
            if set(self._user_groups()).intersection(infos['visible_for_groups']):
                return True
            tool = api.portal.get_tool('portal_plonemeeting')
            for group in infos['visible_for_groups']:
                if group.startswith(SUFFIXPROFILEPREFIX):
                    suffix = group.replace(SUFFIXPROFILEPREFIX, '')
                    if tool.userIsAmong(suffix):
                        return True
            return False

        return True


class IconifiedCategoryConfigAdapter(object):
    """ """
    def __init__(self, context):
        """ """
        self.context = context

    @memoize
    def get_config(self):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        # manage the css.py file generation necessary CSS, in this case, context is the portal
        referer = self.context.REQUEST['HTTP_REFERER']
        if self.context.portal_type == 'Plone Site' and 'mymeetings' in referer:
            referer_path = referer.lstrip(self.context.absolute_url())
            try:
                referer_obj = self.context.unrestrictedTraverse(referer_path)
            except:
                referer_obj = None
            # in case we are adding/editing annex, referer_obj is the form
            if referer_obj and referer_obj.__module__ in ('Products.Five.metaclass',
                                                          'plone.dexterity.browser.add'):
                referer_obj = referer_obj.context
            self.context = referer_obj
        # if self.context is finally not what we want, getMeetingConfig will raise an AttributeError
        try:
            cfg = tool.getMeetingConfig(self.context)
        except AttributeError:
            cfg = None
        return cfg and cfg.annexes_types or None


class IconifiedCategoryGroupAdapter(object):
    """ """
    def __init__(self, config, context):
        """ """
        self.config = config
        self.context = context

    @memoize
    def get_group(self):
        """Return right group, depends on :
           - while adding in an item, annex or decisionAnnex;
           - while adding in a meeting or an advice."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        parent = self.context.getParentNode()
        # adding annex to an item
        if self.context.meta_type == 'MeetingItem' or \
           (self.context.portal_type in ('annex', 'annexDecision') and parent.meta_type == 'MeetingItem'):
            isItemDecisionAnnex = False
            if self.context.meta_type == 'MeetingItem':

                # it is possible to force to use the item_decision_annexes group
                if self.context.REQUEST.get('force_use_item_decision_annexes_group', False):
                    return cfg.annexes_types.item_decision_annexes

                # we are adding a new annex, get annex portal_type from form_instance
                # manage also the InlineValidation view
                if hasattr(self.context.REQUEST.get('PUBLISHED'), 'form_instance'):
                    form_instance = self.context.REQUEST.get('PUBLISHED').form_instance
                elif (hasattr(self.context.REQUEST.get('PUBLISHED'), 'context',) and
                      hasattr(self.context.REQUEST.get('PUBLISHED').context, 'form_instance')):
                    form_instance = self.context.REQUEST.get('PUBLISHED').context.form_instance
                else:
                    # calling with MeetingItem as context, this is the case when checking
                    # if categories exist and if annexes tab should be displayed
                    return cfg.annexes_types.item_annexes

                if getattr(form_instance, 'portal_type', '') == 'annexDecision':
                    isItemDecisionAnnex = True
            else:
                if self.context.portal_type == 'annexDecision':
                    isItemDecisionAnnex = True

            if not isItemDecisionAnnex:
                return cfg.annexes_types.item_annexes
            else:
                return cfg.annexes_types.item_decision_annexes

        # adding annex to an advice
        advicePortalTypeIds = tool.getAdvicePortalTypes(as_ids=True)
        if self.context.portal_type in advicePortalTypeIds \
           or parent.portal_type in advicePortalTypeIds:
            return cfg.annexes_types.advice_annexes

        # adding annex to a meeting
        if self.context.meta_type == 'Meeting' or parent.meta_type == 'Meeting':
            return cfg.annexes_types.meeting_annexes

    def get_every_categories(self):
        categories = get_categories(self.context)
        self.context.REQUEST.set('force_use_item_decision_annexes_group', True)
        categories = categories + get_categories(self.context)
        self.context.REQUEST.set('force_use_item_decision_annexes_group', False)
        return categories
