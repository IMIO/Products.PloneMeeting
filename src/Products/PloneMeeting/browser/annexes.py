# -*- coding: utf-8 -*-
#
# File: annexes.py
#
# Copyright (c) 2015 by Imio.be
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
#

import logging
logger = logging.getLogger('PloneMeeting')

from Products.CMFCore.utils import getToolByName
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
      Manage macros used for annexes.
    """


class AnnexesIcons(BrowserView):
    """
      Annexes displayed as icons.
    """
    def __init__(self, context, request):
        """ """
        super(AnnexesIcons, self).__init__(context, request)
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self, relatedTo):
        self.relatedTo = relatedTo
        return super(AnnexesIcons, self).__call__()

    def getAnnexesByType(self):
        """ """
        return self.context.restrictedTraverse('@@annexes').getAnnexesByType(self.relatedTo)


class AnnexToPrintView(BrowserView):
    """
      toPrint related functionnality.
    """

    def __init__(self, context, request):
        """ """
        super(AnnexToPrintView, self).__init__(context, request)
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()

    def isPrintable(self):
        """Is meetingFile printable?"""
        annex = IAnnexable(self.context)
        return annex.isConvertable() and not annex.conversionFailed()


class AnnexTitleView(BrowserView):
    """
      Render the annex title depending on preview is enabled or not.
    """
    def __init__(self, context, request):
        """ """
        super(AnnexTitleView, self).__init__(context, request)
        self.tool = getToolByName(self.context, 'portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal_url = getToolByName(self.context, 'portal_url').getPortalObject().absolute_url()

    def __call__(self, annexInfo):
        """p_annexInfo is either a real annex object or an annexInfo dict."""
        self.annexInfo = annexInfo
        return super(AnnexTitleView, self).__call__()

    def conversionStatus(self):
        """ """
        if isinstance(self.annexInfo, dict):
            return self.annexInfo['conversionStatus']
        else:
            return IAnnexable(self.context).conversionStatus()

    def appendToUrl(self, toAppend):
        """ """
        if isinstance(self.annexInfo, dict):
            return "/{0}{1}".format(self.annexInfo['id'], toAppend)
        else:
            return toAppend
