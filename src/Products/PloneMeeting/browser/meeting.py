# -*- coding: utf-8 -*-

from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from eea.facetednavigation.browser.app.view import FacetedContainerView
from imio.helpers.content import uuidsToObjects
from imio.history.utils import getLastWFAction
from plone import api
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.browser.edit import DefaultEditForm
from plone.dexterity.browser.view import DefaultView
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import ITEM_INSERT_METHODS
from Products.PloneMeeting.content.meeting import Meeting
from Products.PloneMeeting.MeetingConfig import POWEROBSERVERPREFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from z3c.form.contentprovider import ContentProviders
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
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(the_form.context)

    to_remove = []

    used_meeting_attrs = cfg.getUsedMeetingAttributes()

    extra_expr_ctx = _base_extra_expr_ctx(the_form.context)
    extra_expr_ctx.update({'view': the_form})

    for field_name, field_info in Meeting.FIELD_INFOS.items():
        if field_info['optional'] and \
           field_name not in used_meeting_attrs and \
           not field_info['force_eval_condition']:
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


def manage_label_assembly(the_form):
    '''
      Depending on the fact that we use 'assembly' alone or
      'assembly, excused, absents', we will translate the 'assembly' label
      a different way.
    '''
    widgets = getattr(the_form, 'w', None) or the_form.widgets
    if 'assembly' in widgets:
        if 'assembly_excused' in widgets or \
           'assembly_absents' in widgets:
            widgets['assembly'].label = _('assembly_attendees_title')


def manage_field_attendees(the_form):
    """Move ContentProvider from the_form.widgets to the 'assembly' group."""
    the_form.groups[1].widgets._data_keys.append('attendees')
    the_form.groups[1].widgets._data_values.append(the_form.widgets['attendees_edit_provider'])
    the_form.widgets._data_keys = []
    the_form.widgets._data_values = []


class MeetingConditions(object):
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
        res = self.tool.isManager(self.context)
        if not res:
            res = self.tool.isPowerObserverForCfg(self.cfg) or \
                (self.context.__class__.__name__ == 'Meeting' and
                 self.context.adapted().is_decided())
        return res

    def show_field(self, field_name):
        '''Show the p_field_name field?
           Must be enabled and or not empty.'''
        return field_name in self.used_attrs or \
            (self.context.__class__.__name__ == 'Meeting' and
             getattr(self.context, field_name, None))

    def show_attendees_fields(self):
        '''Display attendee related fields in view/edit?'''
        return ('attendees' in self.used_attrs or
                (self.context.__class__.__name__ == 'Meeting' and
                 self.context.get_attendees() and not self.context.get_assembly()))


class MeetingDefaultView(DefaultView, MeetingConditions):
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


class AttendeesEditProvider(ContentProviderBase, MeetingConditions):

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
        return get_all_used_held_positions(self.context, include_new=True)

    def get_attendees(self):
        """ """
        is_meeting = self.context.__class__.__name__ == 'Meeting'
        attendees = []
        if is_meeting:
            attendees = self.context.get_attendees()
        else:
            attendees = self._get_default_attendees()
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
            signatories = self._get_default_signatories()
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
            voters = self._get_default_voters()
        return voters

    def _get_default_attendees(self):
        '''The default attendees are the active held_positions
           with 'present' in defaults.'''
        res = []
        used_held_positions = get_all_used_held_positions(self.context, include_new=True)
        res = [held_pos.UID() for held_pos in used_held_positions
               if held_pos.defaults and 'present' in held_pos.defaults]
        return res

    def _get_default_signatories(self):
        '''The default signatories are the active held_positions
           with a defined signature_number.'''
        res = []
        used_held_positions = get_all_used_held_positions(self.context, include_new=True)
        res = [held_pos for held_pos in used_held_positions
               if held_pos.defaults and 'present' in held_pos.defaults and held_pos.signature_number]
        return {signer.UID(): signer.signature_number for signer in res}

    def _get_default_voters(self):
        '''The default voters are the active held_positions
           with 'voter' in defaults.'''
        res = []
        used_held_positions = get_all_used_held_positions(self.context, include_new=True)
        res = [held_pos.UID() for held_pos in used_held_positions
               if held_pos.defaults and 'voter' in held_pos.defaults]
        return res


def get_all_used_held_positions(obj, include_new=False, the_objects=True):
    '''This will return every currently stored held_positions.
       If include_new=True, extra held_positions newly selected in the
       configuration are added.
       If p_the_objects=True, we return held_position objects, UID otherwise.
       '''
    # used Persons are held_positions stored in orderedContacts
    contacts = hasattr(obj.aq_base, 'ordered_contacts') and list(obj.ordered_contacts) or []
    if include_new:
        # now getOrderedContacts from MeetingConfig and append new contacts at the end
        # this is the case while adding new contact and editing existing meeting
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(obj)
        selectable_contacts = cfg.getOrderedContacts()
        new_selectable_contacts = [c for c in selectable_contacts if c not in contacts]
        contacts = contacts + new_selectable_contacts

    if the_objects:
        # query held_positions
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(UID=contacts)

        # make sure we have correct order because query was not sorted
        # we need to sort found brains according to uids
        def get_key(item):
            return contacts.index(item.UID)
        brains = sorted(brains, key=get_key)
        contacts = [brain.getObject() for brain in brains]
    return tuple(contacts)


class MeetingEdit(DefaultEditForm, MeetingConditions):
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

    def update(self):
        super(MeetingEdit, self).update()
        # shortcut 'widget' dictionary for all fieldsets
        # like in plone.autoform
        self.w = {}
        for group in self.groups:
            for k, v in group.widgets.items():
                self.w[k] = v
        manage_label_assembly(self)
        if 'attendees' in self.used_attrs:
            manage_field_attendees(self)


class MeetingAddForm(DefaultAddForm, MeetingConditions):

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

    def update(self):
        super(MeetingAddForm, self).update()
        # shortcut 'widget' dictionary for all fieldsets
        # like in plone.autoform
        self.w = {}
        for group in self.groups:
            for k, v in group.widgets.items():
                self.w[k] = v
        manage_label_assembly(self)
        if 'attendees' in self.used_attrs:
            manage_field_attendees(self)


class MeetingAdd(DefaultAddView):

    form = MeetingAddForm


class MeetingView(FacetedContainerView):
    """ """

    section_widgets = {
        'dates_and_data': ['date', 'start_date', 'mid_date', 'end_date'],
        'assembly': ['assembly', 'assembly_excused', 'assembly_absents', 'assembly_guests'],
        'details': [],
        'managers_parameters': []
    }

    def __init__(self, context, request):
        """ """
        super(MeetingView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self._canonical = '<NOT SET>'

    def _init(self):
        """ """
        # initialize member in call because it is Anonymous in __init__ of view...
        self.member = api.user.get_current()
        # make the 'view' widget available on faceted view
        view = self.context.restrictedTraverse('view')
        view.update()
        self.view_data = view

    def __call__(self):
        """ """
        self._init()
        return super(MeetingView, self).__call__()

    def show_page(self):
        """Display page to current user?"""
        return self.tool.showMeetingView()

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
            res = bool(set(groups).intersection(self.tool.get_plone_groups_for_user()))
        return res

    def show_available_items(self):
        """Show the available items part?"""
        return (
            self.member.has_permission(ModifyPortalContent, self.context) or
            self._display_available_items_to()) and \
            self.context.wfConditions().may_accept_items()


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
        return self.request.RESPONSE.redirect(self.context.absolute_url())


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
        for item in items:
            item.setItemNumber(itemNumber)
            itemNumber = itemNumber + 100
        self.context._finalize_item_insert(items_to_update=items)

    def index(self):
        """ """
        self._recompute_items_order()
        msg = _('Items have been reordered.')
        api.portal.show_message(msg, request=self.request)
        return self.request.RESPONSE.redirect(self.context.absolute_url())


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
        uid_catalog = api.portal.get_tool('uid_catalog')
        wfTool = api.portal.get_tool('portal_workflow')
        # make sure we have a list of uids, in some case, as it is called
        # by jQuery, we receive only one uid, as a string...
        if isinstance(uids, str):
            uids = [uids]
        # defer call to Meeting.update_item_references
        self.request.set('defer_Meeting_update_item_references', True)
        lowest_itemNumber = 0
        for uid in uids:
            obj = uid_catalog(UID=uid)[0].getObject()
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
