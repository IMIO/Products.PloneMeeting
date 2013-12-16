import logging
logger = logging.getLogger('PloneMeeting')
from DateTime import DateTime
from AccessControl import Unauthorized

from zope.annotation import IAnnotations

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.utils import checkPermission
from collective.documentviewer.settings import GlobalSettings


class AnnexesView(BrowserView):
    """
      Manage every related annexes management functionnalities.
    """

    def addAnnex(self, idCandidate, annex_title, annex_file,
                 decisionRelated, meetingFileType, **kwargs):
        '''Create an annex (MeetingFile) with given parameters and adds it to
           this item.'''
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
        newAnnex.setMeetingFileType(meetingFileType)
        if decisionRelated == 'True':
            if not checkPermission("PloneMeeting: Write decision annex", self.context):
                raise Unauthorized
            annexes = self.context.getAnnexesDecision()
            annexes.append(newAnnex)
            self.context.setAnnexesDecision(annexes)
        else:
            if not checkPermission("PloneMeeting: Add annex", self.context):
                raise Unauthorized
            annexes = self.context.getAnnexes()
            annexes.append(newAnnex)
            self.context.setAnnexes(annexes)
            if self.context.wfConditions().meetingIsPublished():
                # Potentially I must notify MeetingManagers through email.
                self.context.sendMailIfRelevant(
                    'annexAdded', 'MeetingManager', isRole=True)

        # Add the annex creation to item history
        self.context.updateHistory('add',
                                   newAnnex,
                                   decisionRelated=(decisionRelated == 'True'))
        # Invalidate advices if needed
        if self.context.willInvalidateAdvices():
            self.context.updateAdvices(invalidate=True)
        # After processForm that itself calls at_post_create_script,
        # current user may loose permission to edit
        # the object because we copy item permissions.
        newAnnex.processForm()
        userId = self.context.portal_membership.getAuthenticatedMember().getId()
        logger.info('Annex at %s uploaded by "%s".' % (newAnnex.absolute_url_path(), userId))

    def isValidAnnexId(self, idCandidate):
        '''May p_idCandidate be used for a new annex that will be linked to
           this item?'''
        res = True
        if hasattr(self.context.aq_base, idCandidate) or \
           (idCandidate in self.context.alreadyUsedAnnexNames):
            res = False
        return res

    def getAnnexesToPrint(self, decisionRelated=False):
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

        """
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        global_settings = GlobalSettings(portal)
        annexes = self.context.getAnnexesInOrder(decisionRelated)
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
        '''This method updates self.annexIndex (see doc in
           MeetingItem.__init__). If p_annex is None, this method recomputes the
           whole annexIndex. If p_annex is not None:
           - if p_remove is False, info about the newly created p_annex is added
             to self.annexIndex;
           - if p_remove is True, info about the deleted p_annex is removed from
             self.annexIndex.'''
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
            annexes = self.context.objectValues('MeetingFile')
            normalAnnexes = [mfile for mfile in annexes if (mfile and not mfile.isDecisionRelated())]
            decisionAnnexes = [mfile for mfile in annexes if (mfile and mfile.isDecisionRelated())]
            for annex in normalAnnexes:
                sortableList.append(annex.getAnnexInfo())
            for annex in decisionAnnexes:
                sortableList.append(annex.getAnnexInfo())
            sortableList.sort(key=lambda x: x['modification_date'])
            for a in sortableList:
                self.context.annexIndex.append(a)

    def getAnnexesInOrder(self, decisionRelated=False):
        '''Returns contained annexes respecting order (container is oerdered).
           XXX first step to remove annexes/annexesDeicision fields as ReferenceFields
           as taking contained annexes should be sufficient...
           If p_decisionRelated is False, it returns item-related annexes
           only; if True, it returns decision-related annexes.'''
        annexes = self.context.objectValues('MeetingFile')
        if not decisionRelated:
            return [annex for annex in annexes if not annex.isDecisionRelated()]
        else:
            return [annex for annex in annexes if annex.isDecisionRelated()]

    def getLastInsertedAnnex(self):
        '''Gets the last inserted annex on this item, be it decision-related
           or not.'''
        res = None
        if self.context.annexIndex:
            annexUid = self.context.annexIndex[-1]['UID']
            res = self.context.uid_catalog(UID=annexUid)[0].getObject()
        return res

    def getAnnexesByType(self, decisionRelated=False, makeSubLists=True,
                         typesIds=[], realAnnexes=False):
        '''Returns an annexInfo dict (or real annex objects if p_realAnnexes is
           True) for every annex linked to me:
           - if p_decisionRelated is False, it returns item-related annexes
             only; if True, it returns decision-related annexes.
           - if p_makeSubLists is True, the result (a list) contains a
             subList containing all annexes of a given type; if False,
             the result is a single list containing all requested annexes,
             sorted by annex type.
           If p_typesIds in not empty, only annexes of types having ids
           listed in this param will be returned.
           In all cases, within each annex type annexes are sorted by
           creation date (more recent last).'''
        meetingFileTypes = self.context.portal_plonemeeting.getMeetingConfig(self.context). \
            getFileTypes(decisionRelated, typesIds=typesIds, onlyActive=False)
        res = []
        if not hasattr(self.context, 'annexIndex'):
            self.updateAnnexIndex()
        for fileType in meetingFileTypes:
            annexes = []
            for annexInfo in self.context.annexIndex:
                if (annexInfo['decisionRelated'] == decisionRelated) and \
                   (annexInfo['fileTypeId'] == fileType.id):
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


class AnnexesMacros(BrowserView):
    """
      Manage macros used for annexes
    """

    def now(self):
        return DateTime()

