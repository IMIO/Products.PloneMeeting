import logging
logger = logging.getLogger('PloneMeeting')
from DateTime import DateTime

from Products.Five import BrowserView
from Products.PloneMeeting.interfaces import IAnnexable


class AnnexesView(BrowserView):
    """
      Make some functionalities related to IAnnexable available in templates
      and other untrusted places (do_annex_add.cpy, ...).
    """

    def addAnnex(self, idCandidate, annex_title, annex_file,
                 relatedTo, meetingFileType, **kwargs):
        '''Call IAnnexable.addAnnex.'''
        return IAnnexable(self.context).addAnnex(idCandidate,
                                                 annex_title,
                                                 annex_file,
                                                 relatedTo,
                                                 meetingFileType,
                                                 **kwargs)

    def isValidAnnexId(self, idCandidate):
        '''Call IAnnexable.isValidAnnexId.'''
        return IAnnexable(self.context).isValidAnnexId(idCandidate)

    def getAnnexesByType(self, relatedTo, makeSubLists=True, typesIds=[], realAnnexes=False):
        return IAnnexable(self.context).getAnnexesByType(relatedTo, makeSubLists, typesIds, realAnnexes)


class AnnexesMacros(BrowserView):
    """
      Manage macros used for annexes
    """

    def now(self):
        return DateTime()
