# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.security import fplog
from plone import api
from plone.z3cform.layout import wrap_form
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.itemassembly import _itemsToUpdate
from Products.PloneMeeting.browser.itemassembly import validate_apply_until_item_number
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.contentprovider import ContentProviders
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from zope import interface
from zope import schema
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component.hooks import getSite
from zope.contentprovider.provider import ContentProviderBase
from zope.i18n import translate
from zope.interface import implements


def item_signatures_default():
    """
      Returns the itemSignatures of the item.
      As from zope.schema._bootstrapinterfaces import
      IContextAwareDefaultFactory does not seem to work,
      we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemSignatures = context.getItemSignatures(mimetype='text/plain')
    return safe_unicode(itemSignatures)


class IManageItemSignatures(interface.Interface):
    item_signatures = schema.Text(
        title=_(u"Item signatures to apply"),
        description=_(u"Enter the item signatures to be applied. By default, the value of the field is what is "
                      u"defined on the meeting. If you do not change this value, nothing will be applied on the item. "
                      u"If you already edited this field before and you want to fallback to meeting value, "
                      u"remove the entire value."),
        defaultFactory=item_signatures_default,
        required=False,)
    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, the values entered here above will be applied from current "
                      "item to the item number entered. Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class DisplaySignaturesFromMeetingProvider(ContentProviderBase):
    """
      This ContentProvider will just display
      the signatures defined on the linked meeting.
    """
    template = \
        ViewPageTemplateFile('templates/display_signatures_from_meeting.pt')

    def __init__(self, context, request, view):
        super(DisplaySignaturesFromMeetingProvider, self).__init__(context,
                                                                   request,
                                                                   view)
        self.__parent__ = view

    def getMeetingSignatures(self):
        """
          Return Meeting.signatures
        """
        meeting = self.context.getMeeting()
        return meeting.get_signatures(for_display=True)

    def render(self):
        return self.template()


class ManageItemSignaturesForm(form.Form):
    """
      This form will help MeetingManagers manage itemSignatures
      by being able to redefine it on a single
      item without having to use the edit form and to apply
      redefined value until the item number he wants.
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
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Manage item signatures',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Apply'), name='apply_item_signatures')
    def handleApplyItemSignatures(self, action):
        data, errors = self.extractData()
        # extra data for 'item_signatures' manually because default converter
        # strip the value and we lose empty lines at end of the field
        data['item_signatures'] = self.widgets['item_signatures'].extract()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do adapt item signatures
        self.item_signatures = data.get('item_signatures')
        self.apply_until_item_number = \
            _itemNumber_to_storedItemNumber(
                data.get('apply_until_item_number') or u'0'
            )
        self._doApplyItemSignatures()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def _check_auth(self):
        """Raise Unauthorized if current user can not manage itemSignatures."""
        if not self.context.mayQuickEditItemSignatures():
            raise Unauthorized

    def update(self):
        """ """
        self._check_auth()
        super(ManageItemSignaturesForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        form.Form.updateWidgets(self)

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ManageItemSignaturesForm, self).render()

    def _doApplyItemSignatures(self):
        """
          The method actually do the job, set the itemSignatures
          on self.context and following items if defined
        """
        self._check_auth()
        # only apply if different from meeting
        item_signatures_def = item_signatures_default()
        if self.item_signatures != item_signatures_def:
            items_to_update = _itemsToUpdate(
                from_item_number=self.context.getItemNumber(relativeTo='meeting'),
                until_item_number=self.apply_until_item_number,
                meeting=self.context.getMeeting())
            for itemToUpdate in items_to_update:
                itemToUpdate.setItemSignatures(self.item_signatures)

            first_item_number = items_to_update[0].getItemNumber(for_display=True)
            last_item_number = items_to_update[-1].getItemNumber(for_display=True)
            extras = 'item={0} from_item_number={1} until_item_number={2}'.format(
                repr(self.context), first_item_number, last_item_number)
            fplog('manage_item_signatures', extras=extras)

        # invalidate assembly async load on item
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields',
            get_again=True)

        api.portal.show_message(_("Item signatures have been updated."), request=self.request)
        self._finished = True


ManageItemSignaturesFormWrapper = wrap_form(ManageItemSignaturesForm)
