# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 by Imio.be
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

from zope.contentprovider.provider import ContentProviderBase
from zope.i18n import translate
from zope import interface, schema
from zope.component.hooks import getSite
from zope.interface import implements
from z3c.form import form, field, button
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from z3c.form.contentprovider import ContentProviders

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from Products.PloneMeeting import PMMessageFactory as _


def item_assembly_default():
    """
      Returns the itemAssembly of the item.
      As from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory
      does not seem to work, we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssembly = context.getRawItemAssembly(content_type='text/plain')
    if not isinstance(itemAssembly, unicode):
        itemAssembly = unicode(itemAssembly, 'utf-8')
    return itemAssembly


class IManageItemAssembly(interface.Interface):
    item_assembly = schema.Text(title=_(u"Item assembly"),
                                defaultFactory=item_assembly_default,)


class DisplayAssemblyFromMeetingProvider(ContentProviderBase):
    """
    """
    template = ViewPageTemplateFile('templates/display_assembly_from_meeting.pt')

    def __init__(self, context, request, view):
        super(DisplayAssemblyFromMeetingProvider, self).__init__(context, request, view)
        self.__parent__ = view

    def getMeetingAssembly(self):
        """
          Return Meeting.assembly
        """
        meeting = self.context.getMeeting()
        return meeting.getAssembly()

    def render(self):
        return self.template()


class ManageItemAssemblyForm(form.Form):
    implements(IFieldsAndContentProvidersForm)

    fields = field.Fields(IManageItemAssembly)
    ignoreContext = True  # don't use context to get widget data

    contentProviders = ContentProviders()
    contentProviders['meetingAssembly'] = DisplayAssemblyFromMeetingProvider
    # put the 'meetingAssembly' in first position
    contentProviders['meetingAssembly'].position = 0
    label = _(u"Manage item assembly")
    description = u''

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Manage item assembly',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Proceed'), name='proceed_item_assembly')
    def handleProceedItemAssembly(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do adapt item assembly
        self._doProceedItemAssembly()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def update(self):
        """ """
        super(ManageItemAssemblyForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        form.Form.updateWidgets(self)

    def render(self):
        return super(ManageItemAssemblyForm, self).render()

    def _doSendToPloneMeeting(self):
        """
          The method actually do the job, set the itemAssembly on self.context
          and following items if defined
        """
        self.context.setItemAssembly(self.itemAssembly)


from plone.z3cform.layout import wrap_form
ManageItemAssemblyFormWrapper = wrap_form(ManageItemAssemblyForm)
