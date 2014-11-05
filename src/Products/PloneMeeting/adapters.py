# -*- coding: utf-8 -*-
#
# File: adapters.py
#
# Copyright (c) 2013 by Imio.be
#
# GNU General Public License (GPL)
#

import logging
logger = logging.getLogger('PloneMeeting')
from AccessControl import Unauthorized

from zope.annotation import IAnnotations

from plone.memoize import ram

from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.utils import checkPermission

from imio.actionspanel.adapters import ContentDeletableAdapter as APContentDeletableAdapter
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
        isRestrictedPowerObserver = False
        if useConfidentiality:
            isRestrictedPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=True)
        for fileType in meetingFileTypes:
            annexes = []
            for annexInfo in self.context.annexIndex:
                if (annexInfo['relatedTo'] == relatedTo) and \
                   (annexInfo['meetingFileTypeObjectUID'] == fileType['meetingFileTypeObjectUID']):
                    # manage annex confidentiality, do not consider annex not to show
                    if useConfidentiality and annexInfo['isConfidential'] and isRestrictedPowerObserver:
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
