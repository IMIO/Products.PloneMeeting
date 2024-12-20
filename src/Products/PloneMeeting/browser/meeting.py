# -*- coding: utf-8 -*-

from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from eea.facetednavigation.browser.app.view import FacetedContainerView
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import uuidsToObjects
from imio.helpers.security import fplog
from imio.history.utils import getLastWFAction
from imio.pyutils.utils import sort_by_indexes
from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.browser.edit import DefaultEditForm
from plone.dexterity.browser.view import DefaultView
from plone.supermodel.directives import FIELDSETS_KEY
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.PloneMeeting.config import ITEM_INSERT_METHODS
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.content.meeting import get_all_usable_held_positions
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.content.meeting import Meeting
from Products.PloneMeeting.MeetingConfig import POWEROBSERVERPREFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import field_is_empty
from Products.PloneMeeting.utils import get_attendee_short_title
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.PloneMeeting.utils import redirect
from z3c.form.contentprovider import ContentProviders
from z3c.form.interfaces import HIDDEN_MODE
from z3c.form.interfaces import IFieldsAndContentProvidersForm
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.contentprovider.provider import ContentProviderBase
from zope.i18n import translate
from zope.interface import implements


def manage_fields(the_form):
    """
        Wipeout not enabled optional fields and fields
        for which condition is False
    """
    to_remove = []

    extra_expr_ctx = _base_extra_expr_ctx(the_form.context)
    extra_expr_ctx.update({'view': the_form})

    for field_name, field_info in Meeting.FIELD_INFOS.items():
        if field_info['optional'] and \
           not the_form.show_field(field_name):
            to_remove.append(field_name)
        elif field_info['condition'] and \
                not _evaluateExpression(the_form.context,
                                        expression=field_info['condition'],
                                        extra_expr_ctx=extra_expr_ctx,
                                        raise_on_error=True,
                                        trusted=True):
            to_remove.append(field_name)

    # now remove fields
    for group in [the_form] + the_form.groups:
        for field_name in group.fields:
            if field_name in to_remove:
                group.fields = group.fields.omit(field_name)


def reorder_groups(the_form):
    """Reorder groups/fieldsets because when adding custom fields to an existing
       group, fieldset is duplicated and when merged for display,
       the overrided fieldset is displayed first."""
    order = {fieldset.__name__: i for i, fieldset in
             enumerate(IMeeting.getTaggedValue(FIELDSETS_KEY))}
    # in case group does not exist (new group added by custom plugin)
    # it will be displayed at the end
    indexes = [order.get(group.__name__, 9) for group in the_form.groups]
    # avoid useless reorder
    if indexes != sorted(indexes):
        the_form.groups = sort_by_indexes(the_form.groups, indexes)


def manage_label_assembly(the_form):
    """Depending on the fact that we use "assembly" alone or
       "assembly, excused, absents", we will translate the "assembly" label
       a different way.
    """
    widgets = getattr(the_form, 'w', None) or the_form.widgets
    if 'assembly' in widgets:
        if 'assembly_excused' in widgets or \
           'assembly_absents' in widgets:
            widgets['assembly'].label = _('title_attendees')


def manage_committees(the_form):
    """Depending on configuration, hide not used optional columns."""
    # not using committees?
    if "committees" not in the_form.used_attrs:
        return

    hidden_columns = []
    widget = the_form.w.get('committees')

    # check what columns to hide
    for optional_column in Meeting.FIELD_INFOS['committees']['optional_columns']:
        if not the_form.show_datagrid_column(widget, "committees", optional_column):
            hidden_columns.append(optional_column)

    # special behavior for assembly/attendees and signatures/signatories
    # in case config was switched if both fields are shown,
    # we keep the one not in the config
    if "assembly" not in hidden_columns and "attendees" not in hidden_columns:
        if "assembly" in the_form.used_attrs:
            hidden_columns.append("attendees")
        else:
            hidden_columns.append("assembly")
    if "signatures" not in hidden_columns and "signatories" not in hidden_columns:
        if "signatures" in the_form.used_attrs:
            hidden_columns.append("signatories")
        else:
            hidden_columns.append("signatures")

    # hide columns
    for column in widget.columns:
        if column['name'] in hidden_columns:
            column['mode'] = HIDDEN_MODE

    # hide widgets in rows
    for hidden_column_name in hidden_columns:
        for row in widget.widgets:
            for wdt in row.subform.widgets.values():
                if wdt.__name__ == hidden_column_name:
                    wdt.mode = HIDDEN_MODE


def manage_field_attendees(the_form):
    """Move ContentProvider from the_form.widgets to the 'assembly' group."""
    if the_form.show_attendees_fields() or \
       not the_form.show_field("assembly"):
        the_form.groups[1].widgets._data_keys.insert(0, "attendees")
        the_form.groups[1].widgets._data_values.insert(0, the_form.widgets["attendees_edit_provider"])
    # remove "attendees_edit_provider" from the_form.widgets
    # as it was either moved just here above or is not used
    the_form.widgets._data_keys.data.remove("attendees_edit_provider")
    the_form.widgets._data_values = [v for v in the_form.widgets._data_values
                                     if not v.__name__ == "attendees_edit_provider"]


def manage_groups(the_form):
    """Hide empty groups (fieldsets)."""
    groups = the_form.groups
    groups = [group for group in the_form.groups if group.widgets]
    the_form.groups = groups


class BaseMeetingView(object):
    """ """

    def shown_assembly_fields(self):
        '''Return the list of shown assembly field :
           - used assembly fields;
           - not empty assembly fields.'''
        cached_value = getattr(self, '_shown_assembly_fields', None)
        if cached_value is None:
            # get assembly fields
            field_names = self.cfg._assembly_field_names()
            return [field_name for field_name in field_names
                    if self.show_field(field_name)]

    def show_votes_observations(self):
        '''Show the votes_observations field to
           meeting managers and power observers.'''
        res = self.tool.isManager(self.cfg)
        if not res:
            res = isPowerObserverForCfg(self.cfg) or \
                (self.context.__class__.__name__ == 'Meeting' and
                 self.context.adapted().is_decided())
        return res

    def show_field(self, field_name):
        '''Show the p_field_name field?
           Must be enabled or not empty.'''
        is_used = field_name in self.used_attrs
        if not is_used and self.context.__class__.__name__ == 'Meeting':
            value = getattr(self.context, field_name, None)
            # special case for place that rely also on place_other
            if field_name == "place":
                if value != "other" or self.context.place_other is not None:
                    is_used = True
            elif value not in (None, -1, False):
                # None for empty RichTextFields
                # -1 for meeting_number/first_item_number
                # False for boolean fields
                is_used = True
        return is_used

    def show_datagrid_column(self, widget, field_name, column_name):
        '''Show the p_column_name or p_field_name DataGridField?
           Must be enabled or not empty.'''
        res = True
        used_attr_name = "{0}_{1}".format(field_name, column_name)
        if used_attr_name not in self.used_attrs and \
           field_is_empty(widget, column_name):
            res = False
        return res

    def show_attendees_fields(self):
        '''Display attendee related fields in view/edit?'''
        # caching
        show = getattr(self, "_show_attendees_fields_cache", None)
        if show is not None:
            return show
        # new meeting or existing meeting then manage history
        show = (self.context.__class__.__name__ != 'Meeting' and 'attendees' in self.used_attrs) or \
               (self.context.__class__.__name__ == 'Meeting' and
                (self.context.get_attendees() or not self.show_field("assembly")))
        show = bool(show)
        setattr(self, "_show_attendees_fields_cache", show)
        return show

    def _is_rich(self, widget):
        """Does given p_widget use a RichText field?"""
        return widget.field.__class__.__name__ == 'RichText' and \
            widget.__class__.__name__ != 'PMTextAreaWidget'

    def _is_datagrid(self, widget):
        """Does given p_widget use a DataGrid field?"""
        return widget.__class__.__name__ == 'BlockDataGridField'

    def view_widget(self, widget, empty_value="-"):
        """Render an empty_value instead nothing when field empty."""
        value = getattr(self.context, widget.__name__, None)
        if value is None and not self._is_rich(widget):
            rendered = "-"
        else:
            rendered = widget.render()
        return rendered

    def is_fieldset_not_empty(self, fieldset):
        """Is there a field of given p_fieldset that is not empty?"""
        is_not_empty = False
        for widget in self.fieldsets[fieldset].widgets.values():
            is_empty = field_is_empty(widget)
            if not is_empty:
                is_not_empty = True
                break
        return is_not_empty


class MeetingDefaultView(DefaultView, BaseMeetingView):
    """ """

    def updateFieldsFromSchemata(self):
        super(MeetingDefaultView, self).updateFieldsFromSchemata()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.used_attrs = self.cfg.getUsedMeetingAttributes()
        manage_fields(self)

    def _update(self):
        super(MeetingDefaultView, self)._update()
        manage_label_assembly(self)
        manage_committees(self)


def get_default_attendees(cfg):
    '''The default attendees are the active held_positions
       with 'present' in defaults.'''
    res = [held_pos.UID() for held_pos in get_all_usable_held_positions(cfg)
           if held_pos.defaults and 'present' in held_pos.defaults]
    return res


def get_default_signatories(cfg):
    '''The default signatories are the active held_positions
       with a defined signature_number.'''
    res = {}
    if "signatories" in cfg.getUsedMeetingAttributes():
        signers = [held_pos for held_pos in get_all_usable_held_positions(cfg)
                   if held_pos.defaults and 'present' in
                   held_pos.defaults and held_pos.signature_number]
        res = {signer.UID(): signer.signature_number for signer in signers}
    return res


def get_default_voters(cfg):
    '''The default voters are the active held_positions
       with 'voter' in defaults.'''
    res = []
    if cfg.getUseVotes():
        res = [held_pos.UID() for held_pos in get_all_usable_held_positions(cfg)
               if held_pos.defaults and 'voter' in held_pos.defaults]
    return res


class AttendeesEditProvider(ContentProviderBase, BaseMeetingView):

    template = \
        ViewPageTemplateFile('templates/meeting_attendees_edit.pt')

    def __init__(self, context, request, view):
        super(AttendeesEditProvider, self).__init__(context, request, view)
        self.__parent__ = view
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.used_attrs = self.cfg.getUsedMeetingAttributes()
        self.portal_url = api.portal.get().absolute_url()

    def render(self):
        return self.template()

    def get_all_users(self):
        """ """
        return get_all_usable_held_positions(self.context)

    def get_attendees(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        attendees = []
        if is_meeting:
            attendees = self.context.get_attendees()
        else:
            attendees = get_default_attendees(self.cfg)
        return attendees

    def get_excused(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        excused = []
        if is_meeting:
            excused = self.context.get_excused()
        return excused

    def get_absents(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        absents = []
        if is_meeting:
            absents = self.context.get_absents()
        return absents

    def get_signatories(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        signatories = []
        if is_meeting:
            signatories = self.context.get_signatories()
        else:
            signatories = get_default_signatories(self.cfg)
        return signatories

    def get_user_replacements(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        replacers = []
        if is_meeting:
            replacers = self.context.get_user_replacements()
        return replacers

    def get_voters(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        voters = []
        if is_meeting:
            voters = self.context.get_voters()
        else:
            voters = get_default_voters(self.cfg)
        return voters

    def checked(self, cbid, muid, stored_value, req_key="meeting_attendees"):
        """Helper to manage checked checkboxes, especially when an error
           occured and the form is reloaded."""
        # case reloaded, check if checked in request
        if req_key in self.request:
            is_checked = cbid in self.request.get(req_key, [])
        # initial form load, nothing in request
        else:
            is_checked = muid in stored_value
        return is_checked

    def disabled(self, attendee_id, muid, stored_value, req_key="meeting_attendees"):
        """Helper to manage checked checkboxes, especially when an error
           occured and the form is reloaded."""
        # case reloaded, check if checked in request
        if req_key in self.request:
            is_disabled = attendee_id not in self.request.get(req_key, [])
        # initial form load, nothing in request
        else:
            is_disabled = muid not in stored_value
        return is_disabled

    def get_attendee_short_title(self, hp, cfg):
        """Helper to manage attendee short title."""
        return get_attendee_short_title(hp, cfg)


class MeetingEdit(DefaultEditForm, BaseMeetingView):
    """
        Edit form redefinition to customize fields.
    """
    implements(IFieldsAndContentProvidersForm)
    contentProviders = ContentProviders()
    contentProviders['attendees_edit_provider'] = AttendeesEditProvider
    # defining a contentProvider position is mandatory...
    contentProviders['attendees_edit_provider'].position = 0

    def updateFields(self):
        super(MeetingEdit, self).updateFields()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.used_attrs = self.cfg.getUsedMeetingAttributes()
        manage_fields(self)
        reorder_groups(self)

    def update(self):
        super(MeetingEdit, self).update()
        # shortcut 'widget' dictionary for all fieldsets
        # like in plone.autoform
        self.w = {}
        for group in self.groups:
            for k, v in group.widgets.items():
                self.w[k] = v
        manage_label_assembly(self)
        manage_field_attendees(self)
        manage_committees(self)
        manage_groups(self)


class MeetingAddForm(DefaultAddForm, BaseMeetingView):

    implements(IFieldsAndContentProvidersForm)
    contentProviders = ContentProviders()
    contentProviders['attendees_edit_provider'] = AttendeesEditProvider
    # defining a contentProvider position is mandatory...
    contentProviders['attendees_edit_provider'].position = 0

    def updateFields(self):
        super(MeetingAddForm, self).updateFields()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.used_attrs = self.cfg.getUsedMeetingAttributes()
        manage_fields(self)
        reorder_groups(self)

    def update(self):
        super(MeetingAddForm, self).update()
        # shortcut 'widget' dictionary for all fieldsets
        # like in plone.autoform
        self.w = {}
        for group in self.groups:
            for k, v in group.widgets.items():
                self.w[k] = v
        manage_label_assembly(self)
        manage_field_attendees(self)
        manage_committees(self)
        manage_groups(self)


class MeetingAdd(DefaultAddView):

    form = MeetingAddForm


class BaseMeetingFacetedView(FacetedContainerView):

    def __init__(self, context, request):
        """ """
        super(BaseMeetingFacetedView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self._canonical = '<NOT SET>'


class MeetingFacetedAvailableItemsView(BaseMeetingFacetedView):
    """ """


class MeetingFacetedView(BaseMeetingFacetedView):
    """ """

    def _init(self):
        """ """
        # initialize member in call because it is Anonymous in __init__ of view...
        self.member = api.user.get_current()
        self.is_manager = self.tool.isManager(self.cfg)
        # make the 'view' widget available on faceted view
        view = self.context.restrictedTraverse('@@view')
        view.update()
        self.meeting_view = view

    def __call__(self):
        """ """
        self._init()
        return super(MeetingFacetedView, self).__call__()

    def show_page(self):
        '''If PloneMeeting is in "Restrict users" mode, the "Meeting view" page
           must not be shown to some users: users that do not have role
           MeetingManager and are not listed in a specific list.'''
        restrictMode = self.tool.getRestrictUsers()
        res = True
        if restrictMode:
            if not self.is_manager:
                # Check if the user is in specific list
                if self.member.getId() not in [
                        u.strip() for u in self.tool.getUnrestrictedUsers().split('\n')]:
                    res = False
        return res

    def _display_available_items_to(self):
        """Check if current user profile is selected in MeetingConfig.displayAvailableItemsTo."""
        displayAvailableItemsTo = self.cfg.getDisplayAvailableItemsTo()
        suffixes = []
        groups = []
        res = False
        cfgId = self.cfg.getId()
        for value in displayAvailableItemsTo:
            if value == 'app_users':
                suffixes = get_all_suffixes()
            elif value.startswith(POWEROBSERVERPREFIX):
                groups.append(get_plone_group_id(cfgId, value.split(POWEROBSERVERPREFIX)[1]))
        if suffixes:
            res = self.tool.userIsAmong(suffixes)
        if not res and groups:
            res = bool(set(groups).intersection(get_plone_groups_for_user()))
        return res

    def show_available_items(self):
        """Show the available items part?"""
        return (
            _checkPermission(ModifyPortalContent, self.context) or
            self._display_available_items_to()) and \
            self.context.wfConditions().may_accept_items()

    def warn_assembly(self, using_attendees=False):
        """Check if need to draw attention to the assembly fields to MeetingManagers.
           Warn if :
           - when using signatories, sufficient number of signatories must be defined;
           - when using assembly/signatures, assembly must be encoded and
             signatures must contain at least relevant lines of data."""
        warn = False
        if self.is_manager:
            if using_attendees:
                signature_numbers = self.context.get_signatories().values()
                # if we do not have signatures '1' and '2' we go further
                if u'1' not in signature_numbers or u'2' not in signature_numbers:
                    # double check, maybe we are in a case
                    # where we only have one signatory
                    default_signatories = get_default_signatories(self.cfg)
                    if sorted(default_signatories.values()) != sorted(signature_numbers):
                        warn = True
            else:
                if (len(self.context.get_signatures().split('\n')) <
                    len(self.cfg.getSignatures().split('\n'))) or \
                   not self.context.get_assembly(for_display=False, striked=False):
                    warn = True
        return warn


class MeetingInsertingMethodsHelpMsgView(BrowserView):
    """ """

    def __init__(self, context, request):
        """Initialize relevant data in index instead __init__
           because errors are hidden when occuring in __init__..."""
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self):
        """Do business code in __call__ because errors are swallowed in __init__."""
        self.inserting_methods_fields_mapping = ITEM_INSERT_METHODS.copy()
        self.inserting_methods_fields_mapping.update(
            self.cfg.adapted().extraInsertingMethods().copy())
        return super(MeetingInsertingMethodsHelpMsgView, self).__call__()

    def fieldsToDisplay(self):
        """Depending on used inserting methods, display relevant fields."""
        res = []
        for method in self.cfg.getInsertingMethodsOnAddItem():
            for mapping in self.inserting_methods_fields_mapping[method['insertingMethod']]:
                if mapping.startswith('field_'):
                    res.append(mapping[6:])
        return res

    def orderedOrgs(self):
        """Display organizations if one of the selected inserting methods relies on organizations.
           Returns a list of tuples, with organization title as first element and
           goupsInCharge organizations titles as second element."""
        res = []
        orgs_inserting_methods = [
            method['insertingMethod'] for method in self.cfg.getInsertingMethodsOnAddItem()
            if 'organization' in self.inserting_methods_fields_mapping[method['insertingMethod']]]
        if orgs_inserting_methods:
            orgs = get_organizations(only_selected=True)
            res = [(org.Title(), ', '.join([gic.Title() for gic in org.get_groups_in_charge(the_objects=True)] or ''))
                   for org in orgs]
        return res

    def orderedCategories(self):
        """Display categories if one of the selected inserting methods relies on it."""
        categories = []
        categories_inserting_methods = [
            method['insertingMethod'] for method in self.cfg.getInsertingMethodsOnAddItem()
            if 'category' in self.inserting_methods_fields_mapping[method['insertingMethod']]]
        if categories_inserting_methods:
            categories = self.cfg.getCategories()
        return categories

    def orderedClassifiers(self):
        """Display classifiers if one of the selected inserting methods relies on it."""
        classifiers = []
        classifiers_inserting_methods = [
            method['insertingMethod'] for method in self.cfg.getInsertingMethodsOnAddItem()
            if 'classifier' in self.inserting_methods_fields_mapping[method['insertingMethod']]]
        if classifiers_inserting_methods:
            classifiers = self.cfg.getCategories(catType='classifiers')
        return classifiers


class MeetingUpdateItemReferences(BrowserView):
    """Call Meeting.update_item_references from a meeting."""

    def index(self):
        """ """
        self.context.update_item_references()
        msg = _('References of contained items have been updated.')
        api.portal.show_message(msg, request=self.request)
        return redirect(self.request, self.context.absolute_url())


class MeetingReorderItems(BrowserView):
    """Reorder items on the meeting depending on itemInsertOrder."""

    def _recompute_items_order(self):
        """Get every items and order it by get_item_insert_order."""
        items = self.context.get_items(ordered=True)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        # sort items by insertOrder then by date it was presented
        # so items with same insert order will be sorted by WF transition 'present' time
        items = sorted([
            (self.context.get_item_insert_order(item, cfg), getLastWFAction(item, 'present')['time'], item)
            for item in items]
        )
        # get items
        items = [item[2] for item in items]
        # set items itemNumber
        itemNumber = 100
        self._orig_order = []
        for item in items:
            self._orig_order.append(item.getItemNumber(for_display=True))
            item.setItemNumber(itemNumber)
            itemNumber = itemNumber + 100
        self.context._finalize_item_insert(items_to_update=items)

    def index(self):
        """ """
        self._recompute_items_order()
        msg = _('Items have been reordered.')
        api.portal.show_message(msg, request=self.request)
        # add logging message to fingerpointing log
        extras = 'object={0} original_order={1}'.format(
            repr(self.context),
            ','.join(self._orig_order))
        fplog('meeting_items_reorder', extras=extras)
        return redirect(self.request, self.context.absolute_url())


class PresentSeveralItemsView(BrowserView):
    """
      This manage the view that presents several items into a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, uids):
        """ """
        wfTool = api.portal.get_tool('portal_workflow')
        # defer call to Meeting.update_item_references
        self.request.set('defer_Meeting_update_item_references', True)
        lowest_itemNumber = 0
        objs = uuidsToObjects(uids, ordered=True)
        for obj in objs:
            try:
                wfTool.doActionFor(obj, 'present')
            except WorkflowException:
                # sometimes an item may not be presented,
                # even if shown in presentable items
                api.portal.show_message(
                    _('Item \"${item_title}\" could not be presented!',
                      mapping={'item_title': safe_unicode(obj.Title())}),
                    request=self.request,
                    type='warning')
            if not lowest_itemNumber or obj.getItemNumber() < lowest_itemNumber:
                lowest_itemNumber = obj.getItemNumber()
        self.request.set('defer_Meeting_update_item_references', False)
        # now we may call update_item_references
        self.context.update_item_references(start_number=lowest_itemNumber)
        msg = translate('present_several_items_done',
                        domain='PloneMeeting',
                        context=self.request)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(msg)


class RemoveSeveralItemsView(BrowserView):
    """
      This manage the view that removes several items from a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, uids):
        """ """
        wfTool = api.portal.get_tool('portal_workflow')
        # make sure we have a list of uids, in some case, as it is called
        # by jQuery, we receive only one uid, as a string...
        if isinstance(uids, str):
            uids = [uids]
        # defer call to Meeting.update_item_references
        self.request.set('defer_Meeting_update_item_references', True)
        lowest_itemNumber = 0
        objs = uuidsToObjects(uids, ordered=True, unrestricted=True)
        for obj in objs:
            # save lowest_itemNumber for call to Meeting.update_item_references here under
            if not lowest_itemNumber or obj.getItemNumber() < lowest_itemNumber:
                lowest_itemNumber = obj.getItemNumber()
            # execute every 'back' transitions until item is in state 'validated'
            changedState = True
            while not obj.query_state() == 'validated':
                availableTransitions = [tr['id'] for tr in wfTool.getTransitionsFor(obj)]
                if not availableTransitions or not changedState:
                    break
                changedState = False
                # if several back transitions (like when WFAdaptation 'presented_item_back_to_xxx'
                # is selected), are available, give the priority to 'backToValidated'
                if 'backToValidated' in availableTransitions:
                    availableTransitions = ['backToValidated']
                for tr in availableTransitions:
                    if tr.startswith('back'):
                        wfTool.doActionFor(obj, tr)
                        changedState = True
                        break

        self.request.set('defer_Meeting_update_item_references', False)
        # now we may call update_item_references
        self.context.update_item_references(start_number=lowest_itemNumber)
        msg = translate('remove_several_items_done',
                        domain='PloneMeeting',
                        context=self.request)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(msg)
