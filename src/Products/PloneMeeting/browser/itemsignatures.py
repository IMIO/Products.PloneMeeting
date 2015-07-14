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


def item_signatures_default():
    """
      Returns the itemSignatures of the item.
      As from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory
      does not seem to work, we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemSignatures = context.getRawItemSignatures(content_type='text/plain')
    if not isinstance(itemSignatures, unicode):
        itemSignatures = unicode(itemSignatures, 'utf-8')
    return itemSignatures


class IManageItemSignatures(interface.Interface):
    item_signatures = schema.Text(title=_(u"Item signatures to apply"),
                                  description=_(u"Enter the item signatures to be applied.  The value displayed "
                                                u"by default is the value of the current item."),
                                  defaultFactory=item_signatures_default,
                                  required=False,)
    apply_until_item_number = schema.Int(title=_(u"Apply until item number"),
                                         description=_(u"If you specify a number, the item signatures entered "
                                                       u"here above will be applied from current item to the item "
                                                       u"number entered.  Leave empty to only apply for current item."),
                                         required=False,)


class DisplaySignaturesFromMeetingProvider(ContentProviderBase):
    """
      This ContentProvider will just display the signatures defined on the linked meeting.
    """
    template = ViewPageTemplateFile('templates/display_signatures_from_meeting.pt')

    def __init__(self, context, request, view):
        super(DisplaySignaturesFromMeetingProvider, self).__init__(context, request, view)
        self.__parent__ = view

    def getMeetingSignatures(self):
        """
          Return Meeting.signatures
        """
        meeting = self.context.getMeeting()
        return meeting.getSignatures().replace('\n', '<br />')

    def render(self):
        return self.template()


class ManageItemSignaturesForm(form.Form):
    """
      This form will help MeetingManagers manage itemSignatures by being able to redefine it on a single
      item without having to use the edit form and to apply redefined value until the item number he wants.
    """
    implements(IFieldsAndContentProvidersForm)

    fields = field.Fields(IManageItemSignatures)
    ignoreContext = True  # don't use context to get widget data

    contentProviders = ContentProviders()
    contentProviders['meetingSignatures'] = DisplaySignaturesFromMeetingProvider
    # put the 'meetingSignatures' in first position
    contentProviders['meetingSignatures'].position = 0
    label = _(u"Manage item signatures")
    description = u''
    _finishedSent = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Manage item signatures',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Apply'), name='apply_item_signatures')
    def handleApplyItemSignatures(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do adapt item signatures
        self.item_signatures = self.request.form.get('form.widgets.item_signatures')
        self.apply_until_item_number = self.request.form.get('form.widgets.apply_until_item_number') and \
            int(self.request.form.get('form.widgets.apply_until_item_number')) or 0
        self._doApplyItemSignatures()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def update(self):
        """ """
        # raise Unauthorized if current user can not manage itemAssembly
        if not self.context.mayQuickEdit('itemAssembly'):
            raise Unauthorized

        super(ManageItemSignaturesForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        form.Form.updateWidgets(self)

    def render(self):
        if self._finishedSent:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ManageItemSignaturesForm, self).render()

    def _doApplyItemSignatures(self):
        """
          The method actually do the job, set the itemSignatures on self.context
          and following items if defined
        """
        if not self.context.mayQuickEdit('itemAssembly'):
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
            itemToUpdate.setItemSignatures(self.item_signatures)

        plone_utils = getToolByName(self.context, 'plone_utils')
        plone_utils.addPortalMessage(_("Item signatures have been updated."))
        self._finishedSent = True


from plone.z3cform.layout import wrap_form
ManageItemSignaturesFormWrapper = wrap_form(ManageItemSignaturesForm)
