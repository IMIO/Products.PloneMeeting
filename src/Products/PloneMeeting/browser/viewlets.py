# -*- coding: utf-8 -*-
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

from plone.app.layout.viewlets import ViewletBase
from zope.component import getMultiAdapter
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting.utils import displaying_available_items


class WorkflowState(ViewletBase):
    '''This viewlet displays the workflow state.'''

    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')

    def getObjectState(self):
        wfTool = getToolByName(self.context, 'portal_workflow')
        return wfTool.getInfoFor(self.context, 'review_state')

    index = ViewPageTemplateFile("templates/viewlet_workflowstate.pt")


class ForceInsertNormal(ViewletBase):
    '''This viewlet displays the forceInsertNormal button under the available
       items to present in a meeting on the meeting view.'''

    def available(self):
        """ """
        return displaying_available_items(self.context) and self.view.brains

    def render(self):
        if self.available():
            return self.index()
        else:
            return ''

    def update(self):
        self.context_state = getMultiAdapter((self.context, self.request),
                                             name=u'plone_context_state')

    index = ViewPageTemplateFile("templates/viewlet_force_insert_normal.pt")
