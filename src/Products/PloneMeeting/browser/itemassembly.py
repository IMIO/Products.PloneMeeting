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

from AccessControl import Unauthorized
from zope.contentprovider.provider import ContentProviderBase
from zope.i18n import translate
from zope import interface, schema
from zope.component.hooks import getSite
from zope.interface import implements
from z3c.form import form, field, button
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from z3c.form.contentprovider import ContentProviders

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect


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


def item_excused_default():
    """
      Returns the itemAssemblyExcused of the item.
      As from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory
      does not seem to work, we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssemblyExcused = context.getRawItemAssemblyExcused(content_type='text/plain')
    if not isinstance(itemAssemblyExcused, unicode):
        itemAssemblyExcused = unicode(itemAssemblyExcused, 'utf-8')
    return itemAssemblyExcused


def item_absents_default():
    """
      Returns the itemAssemblyAbsents of the item.
      As from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory
      does not seem to work, we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssemblyAbsents = context.getRawItemAssemblyAbsents(content_type='text/plain')
    if not isinstance(itemAssemblyAbsents, unicode):
        itemAssemblyAbsents = unicode(itemAssemblyAbsents, 'utf-8')
    return itemAssemblyAbsents


class IManageItemAssembly(interface.Interface):
    item_assembly = schema.Text(title=_(u"Item assembly to apply"),
                                description=_(u"Enter the item assembly to be applied.  The value displayed "
                                              u"by default is the value of the current item.  Add [[ ]] around absent "
                                              u"people (like [[Mister Sample Peter]])."),
                                defaultFactory=item_assembly_default,
                                required=False,)
    item_excused = schema.Text(title=_(u"Item excused to apply"),
                               description=_(u"Enter the item excused to be applied.  The value "
                                             u"displayed by default is the value of the current item."),
                               defaultFactory=item_excused_default,
                               required=False,)
    item_absents = schema.Text(title=_(u"Item absents to apply"),
                               description=_(u"Enter the item absents to be applied.  The value "
                                             u"displayed by default is the value of the current item."),
                               defaultFactory=item_absents_default,
                               required=False,)
    apply_until_item_number = schema.Int(title=_(u"Apply until item number"),
                                         description=_(u"If you specify a number, the item assembly entered here "
                                                       u"above will be applied from current item to the item number "
                                                       u"entered.  Leave empty to only apply for current item."),
                                         required=False,)


class DisplayAssemblyFromMeetingProvider(ContentProviderBase):
    """
      This ContentProvider will just display the assembly defined on the linked meeting.
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

    def get_msgid_assembly_or_attendees(self):
        """
          Return the msgid to translate, either 'Assembly' or 'Attendees' defined on the meeting.
        """
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'assemblyExcused' in usedMeetingAttributes or \
           'assemblyExcused' in usedMeetingAttributes:
            return 'display_meeting_attendees_legend'
        else:
            return 'display_meeting_assembly_legend'

    def render(self):
        return self.template()


class ManageItemAssemblyForm(form.Form):
    """
      This form will help MeetingManagers manage itemAssembly by being able to redefine it on a single
      item without having to use the edit form and to apply redefined value until the item number he wants.
    """
    implements(IFieldsAndContentProvidersForm)

    fields = field.Fields(IManageItemAssembly)
    ignoreContext = True  # don't use context to get widget data

    contentProviders = ContentProviders()
    contentProviders['meetingAssembly'] = DisplayAssemblyFromMeetingProvider
    # put the 'meetingAssembly' content provider in first position
    contentProviders['meetingAssembly'].position = 0
    label = _(u"Manage item assembly")
    description = u''
    _finishedSent = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Manage item assembly',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Apply'), name='apply_item_assembly')
    def handleApplyItemAssembly(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do adapt item assembly
        self.item_assembly = self.request.form.get('form.widgets.item_assembly')
        self.item_excused = self.request.form.get('form.widgets.item_excused')
        self.item_absents = self.request.form.get('form.widgets.item_absents')
        self.apply_until_item_number = self.request.form.get('form.widgets.apply_until_item_number') and \
            int(self.request.form.get('form.widgets.apply_until_item_number')) or 0
        self._doApplyItemAssembly()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def update(self):
        """ """
        # raise Unauthorized if current user can not manage itemAssembly
        if not self.context.mayQuickEdit('itemAssembly', bypassWritePermissionCheck=True):
            raise Unauthorized

        super(ManageItemAssemblyForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        # show only relevant fields
        tool = getToolByName(self.context, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        self.fields['item_excused'].mode = 'hidden'
        self.fields['item_absents'].mode = 'hidden'
        changeItemAssemblyTitleAndDescr = False
        if 'assemblyExcused' in usedMeetingAttributes:
            changeItemAssemblyTitleAndDescr = True
            self.fields['item_excused'].mode = 'input'
        if 'assemblyAbsents' in usedMeetingAttributes:
            changeItemAssemblyTitleAndDescr = True
            self.fields['item_absents'].mode = 'input'
        if changeItemAssemblyTitleAndDescr:
            self.fields['item_assembly'].field.title = _('Item attendees to apply')
            self.fields['item_assembly'].field.description = _(u"Enter the item attendees to be applied.  "
                                                               u"The value displayed by default is the value "
                                                               u"of the current item.")
        form.Form.updateWidgets(self)

    def render(self):
        if self._finishedSent:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ManageItemAssemblyForm, self).render()

    def _doApplyItemAssembly(self):
        """
          The method actually do the job, set the itemAssembly on self.context
          and following items if defined
        """
        if not self.context.mayQuickEdit('itemAssembly', bypassWritePermissionCheck=True):
            raise Unauthorized

        def _itemsToUpdate():
            """
              Return items we want to update regarding the number defined in apply_until_item_number
            """
            currentItemNumber = self.context.getItemNumber(relativeTo='meeting')
            if not self.apply_until_item_number or \
               self.apply_until_item_number < currentItemNumber:
                return [self.context, ]
            else:
                meeting = self.context.getMeeting()
                return meeting.getItems(ordered=True)[currentItemNumber-1:self.apply_until_item_number]

        for itemToUpdate in _itemsToUpdate():
            itemToUpdate.setItemAssembly(self.item_assembly)
            itemToUpdate.setItemAssemblyExcused(self.item_excused)
            itemToUpdate.setItemAssemblyAbsents(self.item_absents)

        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage(_("Item assemblies have been updated."))
        self._finishedSent = True


from plone.z3cform.layout import wrap_form
ManageItemAssemblyFormWrapper = wrap_form(ManageItemAssemblyForm)
