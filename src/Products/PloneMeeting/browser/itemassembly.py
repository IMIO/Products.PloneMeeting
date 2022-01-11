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
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import notifyModifiedAndReindex
from Products.PloneMeeting.utils import validate_item_assembly_value
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


USING_ABSENTS_OR_EXCUSED_MSGID = u"Enter the item attendees to be applied. By default, the value of the field is " \
    "what is defined on the meeting. If you do not change this value, nothing will be applied on the item. If you " \
    "already edited this field before and you want to fallback to meeting value, remove the entire value."
USING_ONLY_ASSEMBLY_MSGID = u"Enter the item assembly to be applied. By default, the value of the field is what is " \
    "defined on the meeting. If you do not change this value, nothing will be applied on the item. If you already " \
    "edited this field before and you want to fallback to meeting value, remove the entire value.  You may add [[ ]] " \
    "around absent people (like [[Mister Sample Peter]])."


def item_assembly_default():
    """
      Returns the itemAssembly of the item.
      As from zope.schema._bootstrapinterfaces import
      IContextAwareDefaultFactory does not seem to work,
      we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssembly = context.getItemAssembly(for_display=False)
    # need to strip because extractData strips
    return safe_unicode(itemAssembly).strip()


def item_excused_default():
    """
      Returns the itemAssemblyExcused of the item.
      As from zope.schema._bootstrapinterfaces import
      IContextAwareDefaultFactory does not seem to work,
      we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssemblyExcused = context.getItemAssemblyExcused(for_display=False)
    # need to strip because extractData strips
    return safe_unicode(itemAssemblyExcused).strip()


def item_absents_default():
    """
      Returns the itemAssemblyAbsents of the item.
      As from zope.schema._bootstrapinterfaces import
      IContextAwareDefaultFactory does not seem to work,
      we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssemblyAbsents = context.getItemAssemblyAbsents(for_display=False)
    # need to strip because extractData strips
    return safe_unicode(itemAssemblyAbsents).strip()


def item_guests_default():
    """
      Returns the itemAssemblyGuests of the item.
      As from zope.schema._bootstrapinterfaces import
      IContextAwareDefaultFactory does not seem to work,
      we have to get current context manually...
    """
    context = getSite().REQUEST['PUBLISHED'].context
    itemAssemblyGuests = context.getItemAssemblyGuests(for_display=False)
    # need to strip because extractData strips
    return safe_unicode(itemAssemblyGuests).strip()


def validate_apply_until_item_number(value):
    '''This method does validate the 'apply_until_item_number' field.
       It will check that given number is a number among existing item numbers
       using a correct format.'''
    try:
        _itemNumber_to_storedItemNumber(value)
    except ValueError:
        raise interface.Invalid(_(u'Please provide a valid number.'))
    return True


def validate_item_assembly(value):
    '''This method does validate the 'item_assembly' field.
       It will check that [[]] are correct.'''
    if not validate_item_assembly_value(value):
        raise interface.Invalid(_(u'Please check that opening "[[" have corresponding closing "]]".'))
    return True


class IManageItemAssembly(interface.Interface):
    item_assembly = schema.Text(
        title=_(u"Item assembly to apply"),
        description=_(USING_ONLY_ASSEMBLY_MSGID),
        defaultFactory=item_assembly_default,
        required=False,
        constraint=validate_item_assembly)
    item_excused = schema.Text(
        title=_(u"Item excused to apply"),
        description=_(u"Enter the item excused to be applied. "
                      u"By default, the value of the field is what is defined on the meeting. "
                      u"If you do not change this value, nothing will be applied on the item. "
                      u"If you already edited this field before and you want to fallback to meeting value, "
                      u"remove the entire value."),
        defaultFactory=item_excused_default,
        required=False,)
    item_absents = schema.Text(
        title=_(u"Item absents to apply"),
        description=_(u"Enter the item absents to be applied. "
                      u"By default, the value of the field is what is defined on the meeting. "
                      u"If you do not change this value, nothing will be applied on the item. "
                      u"If you already edited this field before and you want to fallback to meeting value, "
                      u"remove the entire value."),
        defaultFactory=item_absents_default,
        required=False,)
    item_guests = schema.Text(
        title=_(u"Item guests to apply"),
        description=_(u"Enter the item guests to be applied. "
                      u"By default, the value of the field is what is defined on the meeting. "
                      u"If you do not change this value, nothing will be applied on the item. "
                      u"If you already edited this field before and you want to fallback to meeting value, "
                      u"remove the entire value."),
        defaultFactory=item_guests_default,
        required=False,)

    apply_until_item_number = schema.TextLine(
        title=_(u"Apply until item number"),
        description=_(u"If you specify a number, the values entered here above will be applied from current "
                      u"item to the item number entered. Leave empty to only apply for current item."),
        required=False,
        constraint=validate_apply_until_item_number,)


class DisplayAssemblyFromMeetingProvider(ContentProviderBase):
    """
      This ContentProvider will just display
      the assembly defined on the linked meeting.
    """
    template = \
        ViewPageTemplateFile('templates/display_assembly_from_meeting.pt')

    def __init__(self, context, request, view):
        super(DisplayAssemblyFromMeetingProvider, self).__init__(context,
                                                                 request,
                                                                 view)
        self.__parent__ = view

    def get_meeting_assembly(self):
        """
          Return Meeting.assembly
        """
        meeting = self.context.getMeeting()
        nothing_defined_msg = translate('nothing_defined_on_meeting',
                                        domain='PloneMeeting',
                                        context=self.request)
        return meeting.get_assembly(
            for_display=True, striked=False, mark_empty_tags=True) or \
            u'<p class="discreet">{0}</p>'.format(nothing_defined_msg)

    def get_msgid_assembly_or_attendees(self):
        """
          Return the msgid to translate, either 'Assembly' or
          'Attendees' defined on the meeting.
        """
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        if 'assembly_excused' in usedMeetingAttributes or \
           'assembly_absents' in usedMeetingAttributes:
            return 'display_meeting_attendees_legend'
        else:
            return 'display_meeting_assembly_legend'

    def render(self):
        # field may not be used and form is used to manage guests
        if self.context.is_assembly_field_used('itemAssembly'):
            return self.template()
        else:
            return ''


class DisplayExcusedFromMeetingProvider(ContentProviderBase):
    """
      This ContentProvider will just display
      the excused defined on the linked meeting.
    """
    template = \
        ViewPageTemplateFile('templates/display_excused_from_meeting.pt')

    def __init__(self, context, request, view):
        super(DisplayExcusedFromMeetingProvider, self).__init__(context,
                                                                request,
                                                                view)
        self.__parent__ = view

    def get_assembly_excused(self):
        """
          Return Meeting.assembly_excused
        """
        meeting = self.context.getMeeting()
        nothing_defined_msg = translate('nothing_defined_on_meeting',
                                        domain='PloneMeeting',
                                        context=self.request)
        return meeting.get_assembly_excused(
            for_display=True, striked=False, mark_empty_tags=True) or \
            u'<p class="discreet">{0}</p>'.format(nothing_defined_msg)

    def render(self):
        if self.context.is_assembly_field_used('itemAssemblyExcused'):
            return self.template()
        else:
            return ''


class DisplayAbsentsFromMeetingProvider(ContentProviderBase):
    """
      This ContentProvider will just display
      the absents defined on the linked meeting.
    """
    template = \
        ViewPageTemplateFile('templates/display_absents_from_meeting.pt')

    def __init__(self, context, request, view):
        super(DisplayAbsentsFromMeetingProvider, self).__init__(
            context, request, view)
        self.__parent__ = view

    def get_assembly_absents(self):
        """
          Return Meeting.assembly_absents
        """
        meeting = self.context.getMeeting()
        nothing_defined_msg = translate('nothing_defined_on_meeting',
                                        domain='PloneMeeting',
                                        context=self.request)
        return meeting.get_assembly_absents(
            for_display=True, striked=False, mark_empty_tags=True) or \
            u'<p class="discreet">{0}</p>'.format(nothing_defined_msg)

    def render(self):
        if self.context.is_assembly_field_used('itemAssemblyAbsents'):
            return self.template()
        else:
            return ''


def _itemsToUpdate(from_item_number, until_item_number, meeting):
    """
      Return items we want to update regarding the number
      defined in apply_until_item_number
    """
    catalog = api.portal.get_tool('portal_catalog')
    if not until_item_number:
        until_item_number = from_item_number
    brains = catalog.unrestrictedSearchResults(
        meeting_uid=meeting.UID(),
        getItemNumber={'query': (from_item_number,
                                 until_item_number),
                       'range': 'minmax'},
        sort_on='getItemNumber')
    return [brain.getObject() for brain in brains]


class ManageItemAssemblyForm(form.Form):
    """
      This form will help MeetingManagers manage itemAssembly
      by being able to redefine it on a single
      item without having to use the edit form and to apply
      redefined value until the item number he wants.
    """
    implements(IFieldsAndContentProvidersForm)

    fields = field.Fields(IManageItemAssembly)
    ignoreContext = True  # don't use context to get widget data

    contentProviders = ContentProviders()
    contentProviders['assembly'] = DisplayAssemblyFromMeetingProvider
    contentProviders['assembly'].position = 0
    contentProviders['excused'] = DisplayExcusedFromMeetingProvider
    contentProviders['excused'].position = 2
    contentProviders['absents'] = DisplayAbsentsFromMeetingProvider
    contentProviders['absents'].position = 2

    label = _(u"Manage item assembly")
    description = u''
    _finished = False

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
        self.item_assembly = data.get('item_assembly')
        self.item_excused = data.get('item_excused')
        self.item_absents = data.get('item_absents')
        self.item_guests = data.get('item_guests')
        # we receive '5' or '5.2' but we want 500 or 502
        self.apply_until_item_number = \
            _itemNumber_to_storedItemNumber(
                data.get('apply_until_item_number') or u'0'
            )
        self.meeting = self.context.getMeeting()
        self._doApplyItemAssembly()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def _check_auth(self):
        """Raise Unauthorized if current user can not manage itemAssembly."""
        if not self.context.mayQuickEditItemAssembly():
            raise Unauthorized

    def update(self):
        """ """
        self._check_auth()
        super(ManageItemAssemblyForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        # show only relevant fields
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        usedMeetingAttributes = cfg.getUsedMeetingAttributes()
        self.fields['item_assembly'].mode = 'hidden'
        self.fields['item_excused'].mode = 'hidden'
        self.fields['item_absents'].mode = 'hidden'
        self.fields['item_guests'].mode = 'hidden'
        changeItemAssemblyTitleAndDescr = False
        # this form is also used to edit only 'guests' when using attendees
        # manage also when switching from assembly to attendees
        # "assembly" field may be disabled but assembly used on meeting
        if 'assembly' in usedMeetingAttributes or \
                self.context.getItemAssembly():
            self.fields['item_assembly'].mode = 'input'
        if 'assembly_excused' in usedMeetingAttributes or \
                self.context.getItemAssemblyExcused():
            changeItemAssemblyTitleAndDescr = True
            self.fields['item_excused'].mode = 'input'
        if 'assembly_absents' in usedMeetingAttributes or \
                self.context.getItemAssemblyAbsents():
            changeItemAssemblyTitleAndDescr = True
            self.fields['item_absents'].mode = 'input'
        if 'assembly_guests' in usedMeetingAttributes or \
                self.context.getItemAssemblyGuests():
            changeItemAssemblyTitleAndDescr = True
            self.fields['item_guests'].mode = 'input'
        if changeItemAssemblyTitleAndDescr:
            self.fields['item_assembly'].field.title = \
                _('Item attendees to apply')
            self.fields['item_assembly'].field.description = \
                _(USING_ABSENTS_OR_EXCUSED_MSGID)
        else:
            self.fields['item_assembly'].field.title = \
                _('Item assembly to apply')
            self.fields['item_assembly'].field.description = \
                _(USING_ONLY_ASSEMBLY_MSGID)
        form.Form.updateWidgets(self)

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(ManageItemAssemblyForm, self).render()

    def _doApplyItemAssembly(self):
        """
          The method actually do the job, set the itemAssembly on self.context
          and following items if defined
        """
        self._check_auth()
        # only update if default proposed value was changed
        item_assembly_def = item_assembly_default()
        item_excused_def = item_excused_default()
        item_absents_def = item_absents_default()
        item_guests_def = item_guests_default()
        from_item_number = self.context.getItemNumber(relativeTo='meeting')
        until_item_number = self.apply_until_item_number
        items_to_update = _itemsToUpdate(
            from_item_number=from_item_number,
            until_item_number=until_item_number,
            meeting=self.meeting)
        for itemToUpdate in items_to_update:
            # only update if we changed default value
            if self.item_assembly != item_assembly_def:
                itemToUpdate.setItemAssembly(self.item_assembly)
            if self.item_excused != item_excused_def:
                itemToUpdate.setItemAssemblyExcused(self.item_excused)
            if self.item_absents != item_absents_def:
                itemToUpdate.setItemAssemblyAbsents(self.item_absents)
            if self.item_guests != item_guests_def:
                itemToUpdate.setItemAssemblyGuests(self.item_guests)
            notifyModifiedAndReindex(itemToUpdate)

        # invalidate assembly async load on item
        invalidate_cachekey_volatile_for(
            'Products.PloneMeeting.browser.async.AsyncLoadItemAssemblyAndSignaturesRawFields',
            get_again=True)

        first_item_number = items_to_update[0].getItemNumber(for_display=True)
        last_item_number = items_to_update[-1].getItemNumber(for_display=True)
        extras = 'item={0} from_item_number={1} until_item_number={2}'.format(
            repr(self.context), first_item_number, last_item_number)
        fplog('manage_item_assembly', extras=extras)
        api.portal.show_message(_("Item assemblies have been updated."), request=self.request)
        self._finished = True


ManageItemAssemblyFormWrapper = wrap_form(ManageItemAssemblyForm)
