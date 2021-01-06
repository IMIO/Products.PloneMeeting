# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from eea.facetednavigation.browser.app.view import FacetedContainerView
from imio.helpers.content import uuidsToObjects
from imio.history.utils import getLastWFAction
from plone import api
from plone.supermodel.interfaces import FIELDSETS_KEY
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import ITEM_INSERT_METHODS
from Products.PloneMeeting.utils import get_dx_schema
from Products.PloneMeeting.MeetingConfig import POWEROBSERVERPREFIX
from zope.i18n import translate


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
        # initialize z3c form view widgets
        view = self.context.restrictedTraverse('content-core')
        view.update()
        self.view_data = view

    def __call__(self):
        """ """
        self._init()
        return super(MeetingView, self).__call__()

    def get_fields_for_fieldset(self, fieldset):
        """Return widgets of not optional fields and optional fields enabled in MeetingConfig."""
        optional_fields = self.cfg.get_dx_attrs(self.context.FIELD_INFOS, optional_only=True)
        used_meeting_attrs = self.cfg.getUsedMeetingAttributes()
        schema = get_dx_schema(self.context)
        base_class = schema.getBases()[0]
        fieldset_fields = [fieldset_field for fieldset_field in base_class.queryTaggedValue(FIELDSETS_KEY)
                           if fieldset_field.__name__ == fieldset][0].fields
        enabled_field_names = [
            field for field in fieldset_fields
            if field not in optional_fields or field in used_meeting_attrs]
        widgets = []
        for field_name in enabled_field_names:
            widgets.append(self.view_data.w[field_name])
        return widgets

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


class MeetingBeforeFacetedInfosView(BrowserView):
    """Informations displayed before the faceted on the meeting_view."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)


class MeetingAfterFacetedInfosView(BrowserView):
    """Informations displayed after the faceted on the meeting_view."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self):
        """ """
        # initialize in call because user is Anonymous in __init__ of view...
        self.member = api.user.get_current()
        return super(MeetingAfterFacetedInfosView, self).__call__()


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
