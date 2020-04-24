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

from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from z3c.form import button
from z3c.form import form
from zope import interface
from zope.i18n import translate


class IDuplicateItem(interface.Interface):
    """ """


class DuplicateItemForm(form.Form):
    """ """
    label = _(u"Duplicate item")
    description = u''

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Duplicate item',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Apply'), name='apply_duplicate_item')
    def handleApplyItemAssembly(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def update(self):
        """ """
        self._check_auth()
        super(DuplicateItemForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(DuplicateItemForm, self).render()


DuplicateItemFormWrapper = wrap_form(DuplicateItemForm)
