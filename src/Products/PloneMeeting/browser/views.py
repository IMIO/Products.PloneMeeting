# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.core.utils import get_gender_and_number
from collective.contact.plonegroup.browser.tables import DisplayGroupUsersView
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organization
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.eeafaceted.batchactions import _ as _CEBA
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.eeafaceted.batchactions.utils import listify_uids
from eea.facetednavigation.browser.app.view import FacetedContainerView
from eea.facetednavigation.interfaces import ICriteria
from ftw.labels.interfaces import ILabeling
from imio.helpers.xhtml import addClassToContent
from imio.helpers.xhtml import CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT
from imio.helpers.xhtml import imagesToPath
from imio.helpers.xhtml import separate_images
from imio.history.utils import getLastWFAction
from plone import api
from plone.app.caching.operations.utils import getContext
from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import _checkPermission
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from Products.PloneMeeting import logger
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.columns import render_item_annexes
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import ITEM_INSERT_METHODS
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.indexes import _to_coded_adviser_index
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.MeetingConfig import POWEROBSERVERPREFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_person_from_userid
from Products.PloneMeeting.utils import signatureNotAlone
from Products.PloneMeeting.utils import toHTMLStrikedContent
from z3c.form.field import Fields
from zope import schema
from zope.i18n import translate

import cgi
import json
import lxml


class PloneMeetingAjaxView(BrowserView):
    """
      Manage ajax PloneMeeting functionnalities.
    """


class ItemNavigationWidgetView(BrowserView):
    """
      This manage the view displaying the navigation widget on the item view
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.portal_url = api.portal.get().absolute_url()

    @memoize
    def __call__(self):
        """Memoize as this widget is displayed identically at the top and the bottom of the item view."""
        return super(ItemNavigationWidgetView, self).__call__()

    def display_number(self, itemNumber):
        """Show the displayable version of the p_itemNumber."""
        return _storedItemNumber_to_itemNumber(itemNumber, forceShowDecimal=False)


class ItemMoreInfosView(BrowserView):
    """
      This manage the view displaying more infos about an item in the PrettyLink column
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self, visibleColumns=[], fieldsConfigAttr='itemsListVisibleFields', currentCfgId=None):
        """ """
        self.visibleColumns = visibleColumns
        self.visibleFields = self.cfg.getField(fieldsConfigAttr).get(self.cfg)
        # if current user may not see the item, use another fieldsConfigAttr
        if not _checkPermission(View, self.context):
            # check it item fields should be visible nevertheless
            extra_expr_ctx = _base_extra_expr_ctx(self.context)
            currentCfg = currentCfgId and self.tool.get(currentCfgId) or self.cfg
            extra_expr_ctx.update({'item': self.context})
            extra_expr_ctx.update({'cfg': currentCfg})
            extra_expr_ctx.update({'item_cfg': self.cfg})
            res = _evaluateExpression(self.context,
                                      expression=currentCfg.getItemsNotViewableVisibleFieldsTALExpr(),
                                      roles_bypassing_expression=[],
                                      extra_expr_ctx=extra_expr_ctx)
            if res:
                self.visibleFields = self.cfg.getField('itemsNotViewableVisibleFields').get(self.cfg)
                with api.env.adopt_roles(['Manager']):
                    return super(ItemMoreInfosView, self).__call__()
            else:
                self.visibleFields = ()
        return super(ItemMoreInfosView, self).__call__()

    @memoize
    def getVisibleFields(self):
        """ """
        # keep order of displayed fields
        res = OrderedDict()
        for visibleField in self.visibleFields:
            visibleFieldName = visibleField.split('.')[1]
            # if nothing is defined, the default rendering macro will be used
            # this is made to be overrided
            res[visibleFieldName] = self._rendererForField(visibleFieldName)
        return res

    def _rendererForField(self, fieldName):
        """Return the renderer to use for given p_fieldName, this returns nothing
           by default and is made to be overrided by subproduct."""
        return None

    def render_annexes(self):
        """ """
        return render_item_annexes(self.context, self.tool, show_nothing=True)


class BaseStaticInfosView(BrowserView):
    """
      Base class managing static infos displayed in the PrettyLink column
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, visibleColumns):
        """ """
        self.visibleColumns = visibleColumns
        return super(BaseStaticInfosView, self).__call__()

    def static_infos_field_names(self):
        """Field names displayed as static infos.
           These are selected values starting with 'static_'."""
        field_names = [field_name.replace('static_', '') for field_name in self.visibleColumns
                       if field_name.startswith('static_')]
        return field_names


class ItemStaticInfosView(BaseStaticInfosView):
    """
      Static infos on MeetingItem.
    """
    @property
    def active_labels(self):
        available_labels = ILabeling(self.context).available_labels()
        active_personal_labels = [label for label in available_labels[0] if label['active']]
        active_labels = [label for label in available_labels[1] if label['active']]
        return active_personal_labels, active_labels


class MeetingStaticInfosView(BaseStaticInfosView):
    """
      Static infos on Meeting.
    """


class ItemIsSignedView(BrowserView):
    """
      This manage the view displaying itemIsSigned widget
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()


class PresentSeveralItemsView(BrowserView):
    """
      This manage the view that presents several items into a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, uids):
        """ """
        uid_catalog = api.portal.get_tool('uid_catalog')
        wfTool = api.portal.get_tool('portal_workflow')
        # defer call to Meeting.updateItemReferences
        self.request.set('defer_Meeting_updateItemReferences', True)
        lowest_itemNumber = 0
        for uid in uids:
            obj = uid_catalog.searchResults(UID=uid)[0].getObject()
            wfTool.doActionFor(obj, 'present')
            if not lowest_itemNumber or obj.getItemNumber() < lowest_itemNumber:
                lowest_itemNumber = obj.getItemNumber()
        self.request.set('defer_Meeting_updateItemReferences', False)
        # now we may call updateItemReferences
        self.context.updateItemReferences(startNumber=lowest_itemNumber)
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
        # defer call to Meeting.updateItemReferences
        self.request.set('defer_Meeting_updateItemReferences', True)
        lowest_itemNumber = 0
        for uid in uids:
            obj = uid_catalog(UID=uid)[0].getObject()
            # save lowest_itemNumber for call to Meeting.updateItemReferences here under
            if not lowest_itemNumber or obj.getItemNumber() < lowest_itemNumber:
                lowest_itemNumber = obj.getItemNumber()
            # execute every 'back' transitions until item is in state 'validated'
            changedState = True
            while not obj.queryState() == 'validated':
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

        self.request.set('defer_Meeting_updateItemReferences', False)
        # now we may call updateItemReferences
        self.context.updateItemReferences(startNumber=lowest_itemNumber)
        msg = translate('remove_several_items_done',
                        domain='PloneMeeting',
                        context=self.request)
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(msg)


class ItemNumberView(BrowserView):
    """
      This manage the view displaying the itemNumber on the meeting view
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, mayChangeItemsOrder):
        self.mayChangeItemsOrder = mayChangeItemsOrder
        return super(ItemNumberView, self).__call__()

    def is_integer(self, number):
        """ """
        return _is_integer(number)


class ItemToDiscussView(BrowserView):
    """
      This manage the view displaying toDiscuss widget
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def mayEdit(self):
        """ """
        member = api.user.get_current()
        toDiscuss_write_perm = self.context.getField('toDiscuss').write_permission
        return member.has_permission(toDiscuss_write_perm, self.context) and \
            self.context.showToDiscuss()

    @memoize_contextless
    def userIsReviewer(self):
        """ """
        return self.tool.userIsAmong(['reviewers'], cfg=self.cfg)

    @memoize_contextless
    def useToggleDiscuss(self):
        """ """
        return self.context.restrictedTraverse('@@toggle_to_discuss').isAsynchToggleEnabled()


class MeetingView(FacetedContainerView):
    """The meeting_view."""

    def __init__(self, context, request):
        """ """
        super(MeetingView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def update(self):
        """ """
        # initialize member in call because it is Anonymous in __init__ of view...
        self.member = api.user.get_current()

    def __call__(self):
        """ """
        self.update()
        return super(MeetingView, self).__call__()

    def showPage(self):
        """Display page to current user?"""
        return self.tool.showMeetingView()

    def _displayAvailableItemsTo(self):
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

    def showAvailableItems(self):
        """Show the available items part?"""
        return (
            self.member.has_permission(ModifyPortalContent, self.context) or
            self._displayAvailableItemsTo()) and \
            self.context.wfConditions().mayAcceptItems()


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
        # initialize member in call because it is Anonymous in __init__ of view...
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
    """Call Meeting.updateItemReferences from a meeting."""

    def index(self):
        """ """
        self.context.updateItemReferences()
        msg = _('References of contained items have been updated.')
        api.portal.show_message(msg, request=self.request)
        return self.request.RESPONSE.redirect(self.context.absolute_url())


class MeetingReorderItems(BrowserView):
    """Reorder items on the meeting depending on itemInsertOrder."""

    def _recompute_items_order(self):
        """Get every items and order it by getItemInsertOrder."""
        items = self.context.getItems(ordered=True)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        # sort items by insertOrder then by date it was presented
        # so items with same insert order will be sorted by WF transition 'present' time
        items = sorted([
            (self.context.getItemInsertOrder(item, cfg), getLastWFAction(item, 'present')['time'], item)
            for item in items]
        )
        # get items
        items = [item[2] for item in items]
        # set items itemNumber
        itemNumber = 100
        for item in items:
            item.setItemNumber(itemNumber)
            itemNumber = itemNumber + 100
        self.context._finalize_item_insert(items, items_to_update=items)

    def index(self):
        """ """
        self._recompute_items_order()
        msg = _('Items have been reordered.')
        api.portal.show_message(msg, request=self.request)
        return self.request.RESPONSE.redirect(self.context.absolute_url())


class PloneMeetingRedirectToAppView(BrowserView):
    """
      This manage the view set on the Plone Site that redirects the connected user
      to the default MeetingConfig after connection.
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def __call__(self):
        '''
          Add a specific portal_message if we have no active meetingConfig to redirect the connected member to.
        '''
        if not api.user.is_anonymous():
            defaultMeetingConfig = self.tool.getDefaultMeetingConfig()
            member = api.user.get_current()
            if not defaultMeetingConfig and member.has_role('Manager'):
                plone_utils = api.portal.get_tool('plone_utils')
                plone_utils.addPortalMessage(
                    translate('Please specify a default meeting config upon active existing '
                              'meeting configs to be automaatically redirected to it.',
                              domain='PloneMeeting',
                              context=self.request), type='warning')
            # redirect the user to the default meeting config if possible
            if defaultMeetingConfig:
                pmFolder = self.tool.getPloneMeetingFolder(defaultMeetingConfig.getId())
                return self.request.RESPONSE.redirect(pmFolder.absolute_url() + "/searches_items")
        return self.index()


class ObjectGoToView(BrowserView):
    """
      Manage go to a given itemNumber.  This method is used
      in the item navigation widget (go to previous item, go to next item, ...)
    """
    def __call__(self, itemNumber, way='previous'):
        """
          p_itemNumber is the number of the item we want to go to.  This item
          is in the same meeting than self.context.
        """
        catalog = api.portal.get_tool('portal_catalog')
        meeting = self.context.getMeeting()
        itemNumber = _itemNumber_to_storedItemNumber(itemNumber)
        brains = catalog(linkedMeetingUID=meeting.UID(), getItemNumber=itemNumber)
        if not brains:
            self.context.plone_utils.addPortalMessage(
                translate(msgid='item_number_not_accessible',
                          domain='PloneMeeting',
                          context=self.request),
                type='warning')
            return self.request.RESPONSE.redirect(self.context.absolute_url())
        else:
            obj = brains[0].getObject()
            # check if obj isPrivacyViewable, if not, find the previous/next viewable item
            next_obj = None
            # if on last or first item, change way
            if way == 'last':
                way = 'previous'
            elif way == 'first':
                way = 'next'
            not_accessible_item_found = False
            while not obj.adapted().isPrivacyViewable() and not next_obj == obj and not next_obj == self.context:
                not_accessible_item_found = True
                next_obj = obj.getSiblingItem(whichItem=way, itemNumber=False)
                if next_obj:
                    next_obj = next_obj.getObject()
                else:
                    next_obj = self.context
                obj = next_obj
            if not_accessible_item_found:
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_number_not_accessible_redirected_to_closest_item',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
            return self.request.RESPONSE.redirect(obj.absolute_url())


class UpdateDelayAwareAdvicesView(BrowserView):
    """
      This is a view that is called as a maintenance task by Products.cron4plone.
      As we use clear days to compute advice delays, it will be launched at 0:00
      each night and update relevant items containing delay-aware advices still addable/editable.
      It will also update the indexAdvisers portal_catalog index.
    """
    def __call__(self):
        query = self._computeQuery()
        self._updateAllAdvices(query=query)

    def _computeQuery(self):
        '''
          Compute the catalog query to execute to get only relevant items to update,
          so items with delay-aware advices still addable/editable.
        '''
        # compute the indexAdvisers index, take every customAdvisers, including disabled ones
        # then construct every possibles cases, by default there is 2 possible values :
        # delay__orgUid1__advice_not_given, delay__orgUid1__advice_under_edit
        # delay__orgUid2__advice_not_given, delay__orgUid2__advice_under_edit
        # ...
        indexAdvisers = []
        tool = api.portal.get_tool('portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            for row in cfg.getCustomAdvisers():
                isDelayAware = bool(row['delay'])
                if isDelayAware:
                    org_uid = row['org']
                    # advice giveable but not given
                    advice_not_given_value = "delay__{0}_advice_not_given".format(org_uid)
                    # avoid duplicates
                    if advice_not_given_value in indexAdvisers:
                        continue
                    indexAdvisers.append(advice_not_given_value)
                    # now advice given and still editable
                    for advice_state in ADVICE_STATES_ALIVE:
                        indexAdvisers.append("delay__{0}_{1}".format(org_uid, advice_state))
        query = {}
        # if no indexAdvisers, query on 'dummy' to avoid query on empty value
        query['indexAdvisers'] = indexAdvisers or ['dummy']
        return query

    def _updateAllAdvices(self, query={}):
        '''Update adviceIndex for every items.
           If a p_query is given, it will be used by the portal_catalog query
           we do to restrict update of advices to some subsets of items...'''
        catalog = api.portal.get_tool('portal_catalog')
        if 'meta_type' not in query:
            query['meta_type'] = 'MeetingItem'
        brains = catalog(**query)
        numberOfBrains = len(brains)
        i = 1
        logger.info('Updating adviceIndex for %s items' % str(numberOfBrains))
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Updating adviceIndex of item at %s' % (
                i,
                numberOfBrains,
                '/'.join(item.getPhysicalPath())))
            i = i + 1
            item.updateLocalRoles()
        logger.info('Done.')


class DeleteHistoryEventView(BrowserView):
    """
      Delete an event in an object's history.
    """
    def __call__(self, object_uid, event_time):
        # Get the object
        # try to get it from the portal_catalog
        catalog_brains = self.context.portal_catalog(UID=object_uid)
        # if not found, try to get it from the uid_catalog
        if not catalog_brains:
            catalog_brains = self.context.uid_catalog(UID=object_uid)
        # if not found at all, raise
        if not catalog_brains:
            raise KeyError('The given uid could not be found!')
        obj = catalog_brains[0].getObject()

        # now get the event to delete and delete it...
        tool = api.portal.get_tool('portal_plonemeeting')
        tool.deleteHistoryEvent(obj, event_time)
        return self.request.RESPONSE.redirect(self.request['HTTP_REFERER'])


class PortletTodoUpdateView(BrowserView):

    """Produce json to update portlet_todo."""

    def __call__(self):
        """Render portlet_todo and return the entire HTML tree."""
        from zope.component import getUtility
        from zope.component import queryMultiAdapter
        from plone.portlets.interfaces import IPortletManager
        from plone.portlets.interfaces import IPortletManagerRenderer

        # self.context is sometimes a view, like when editing a Collection
        context = getContext(self.context)

        manager = getUtility(IPortletManager,
                             name='plone.leftcolumn',
                             context=context)
        # we use IPortletManagerRenderer so parameters
        # batch_size and title_length are taken into account
        renderer = queryMultiAdapter(
            (context, self.request, self, manager), IPortletManagerRenderer)

        for portlet in renderer.portletsToShow():
            if portlet['name'] == 'portlet_todo':
                self.request.set('load_portlet_todo', True)
                return portlet['renderer'].render()

        return ''


class BaseDGHV(object):
    """ """

    def imageOrientation(self, image):
        """Compute image orientation, if orientation is landscape, we rotate
           the image from 90° so it is displayed on the full page.
           This is used by the appy.pod 'import from document' method
           as 'convertOptions' parameter."""
        if image.width > image.height:
            return '-rotate 90'

    def printXhtml(self, context, xhtmlContents,
                   image_src_to_paths=True,
                   separatorValue='<p>&nbsp;</p>',
                   keepWithNext=False,
                   keepWithNextNumberOfChars=CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT,
                   checkNeedSeparator=True,
                   addCSSClass=None,
                   use_safe_html=True,
                   clean=False):
        """Helper method to format a p_xhtmlContents.  The xhtmlContents is a list or a string containing
           either XHTML content or some specific recognized words like :
           - 'separator', in this case, it is replaced with the p_separatorValue;
           Given xhtmlContents are all merged together to be printed in the document.
           If p_keepWithNext is True, signatureNotAlone is applied on the resulting XHTML.
           If p_image_src_to_paths is True, if some <img> are contained in the XHTML, the link to the image
           is replaced with a path to the .blob of the image of the server so LibreOffice may access it.
           Indeed, private images not accessible by anonymous may not be reached by LibreOffice.
           If p_checkNeedSeparator is True, it will only add the separator if previous
           xhtmlContent did not contain empty lines at the end.
           If addCSSClass is given, a CSS class will be added to every tags of p_chtmlContents.
           Finally, the separatorValue is used when word 'separator' is encountered in xhtmlContents.
           A call to printXHTML in a POD template with an item as context could be :
           view.printXHTML(self.getMotivation(), 'separator', '<p>DECIDE :</p>', 'separator', self.getDecision())
        """
        xhtmlFinal = ''
        # list or tuple?
        if hasattr(xhtmlContents, '__iter__'):
            for xhtmlContent in xhtmlContents:
                if xhtmlContent == 'separator':
                    hasSeparation = False
                    if checkNeedSeparator:
                        preparedXhtmlContent = "<special_tag>%s</special_tag>" % xhtmlContent
                        tree = lxml.html.fromstring(safe_unicode(preparedXhtmlContent))
                        children = tree.getchildren()
                        if children and not children[-1].text:
                            hasSeparation = True
                    if not hasSeparation:
                        xhtmlFinal += separatorValue
                else:
                    xhtmlFinal += xhtmlContent
        else:
            xhtmlFinal = xhtmlContents

        # manage image_src_to_paths
        # turning http link to image to blob path will avoid unauthorized by appy.pod
        if image_src_to_paths:
            xhtmlFinal = imagesToPath(context, xhtmlFinal)

        # manage keepWithNext
        if keepWithNext:
            xhtmlFinal = signatureNotAlone(xhtmlFinal, numberOfChars=keepWithNextNumberOfChars)

        # manage addCSSClass
        if addCSSClass:
            xhtmlFinal = addClassToContent(xhtmlFinal, addCSSClass)

        if clean:
            xhtmlFinal = separate_images(xhtmlFinal)

        # finally use_safe_html to clean the HTML, it does not only clean
        # but turns the result into a XHTML compliant HTML, by replacing <br> with <br /> for example
        if use_safe_html:
            pt = api.portal.get_tool('portal_transforms')
            xhtmlFinal = pt.convert('safe_html', xhtmlFinal).getData()

        return xhtmlFinal

    def printHistory(self):
        """Return the history view for templates. """
        historyView = self.context.restrictedTraverse('historyview')()
        historyViewRendered = lxml.html.fromstring(historyView)
        return lxml.html.tostring(historyViewRendered.get_element_by_id('content-core'), method='xml')

    def get_contact_infos(self, position_types=[], userid=None):
        """Return informations for given userid, if not given, we take current element creator,
           this is useful to manage signature on advice.
           Given position_types will be used to get correct held_position related to signature.
           We can receive several position_types and we return the first we get."""
        infos = {'person': None,
                 'person_title': None,
                 'person_fullname': None,
                 'held_position': None,
                 'held_position_label': None,
                 'label_prefix': None,
                 'held_position_prefixed_label': None,
                 'label_prefix_by': None,
                 'held_position_prefixed_label_by': None,
                 'label_prefix_to': None,
                 'held_position_prefixed_label_to': None,
                 }
        person = get_person_from_userid(userid or self.context.Creator())
        if person:
            infos['person'] = person
            infos['person_title'] = person.get_title()
            infos['person_fullname'] = person.get_title(include_person_title=False)
            if not position_types:
                hp = person.get_held_position_by_type(position_type=None)
            else:
                for position_type in position_types:
                    hp = person.get_held_position_by_type(position_type)
                    if hp:
                        break
            if hp:
                infos['held_position'] = hp
                infos['held_position_label'] = hp.get_label()
                infos['label_prefix'] = hp.get_prefix_for_gender_and_number(include_value=False)
                infos['held_position_prefixed_label'] = \
                    hp.get_prefix_for_gender_and_number(include_value=True)
                infos['label_prefix_by'] = \
                    hp.get_prefix_for_gender_and_number(include_value=False, use_by=True)
                infos['held_position_prefixed_label_by'] = \
                    hp.get_prefix_for_gender_and_number(include_value=True, use_by=True)
                infos['label_prefix_to'] = \
                    hp.get_prefix_for_gender_and_number(include_value=False, use_to=True)
                infos['held_position_prefixed_label_to'] = \
                    hp.get_prefix_for_gender_and_number(include_value=True, use_to=True)
        return infos

    def printAdvicesInfos(self,
                          item,
                          withAdvicesTitle=True,
                          withDelay=False,
                          withDelayLabel=True,
                          withAuthor=True,
                          ordered=True):
        '''Helper method to have a printable version of advices.'''
        res = ""
        if withAdvicesTitle:
            res += "<p class='pmAdvices'><u><b>%s :</b></u></p>" % \
                translate('PloneMeeting_label_advices',
                          domain='PloneMeeting',
                          context=self.request)
        itemAdvicesByType = item.getAdvicesByType(ordered=ordered)
        itemAdvicesByType = OrderedDict(itemAdvicesByType)
        itemAdvicesByType = sorted(itemAdvicesByType.items())
        for adviceType, advices in itemAdvicesByType:
            for advice in advices:
                res += "<p class='pmAdvices'>"
                # if we have a delay and delay_label, we display it
                delayAwareMsg = u''
                if withDelay and advice['delay']:
                    delayAwareMsg = u"%s" % (translate('delay_of_x_days',
                                             domain='PloneMeeting',
                                             mapping={'delay': advice['delay']},
                                             context=self.request))
                if withDelayLabel and advice['delay'] and advice['delay_label']:
                    if delayAwareMsg:
                        delayAwareMsg = "%s - %s" % (delayAwareMsg,
                                                     safe_unicode(advice['delay_label']))
                    else:
                        delayAwareMsg = "%s" % safe_unicode(advice['delay_label'])
                if delayAwareMsg:
                    delayAwareMsg = u" <i>(%s)</i>" % cgi.escape(delayAwareMsg)
                    res = res + u"<u>%s %s:</u>" % (cgi.escape(advice['name']),
                                                    delayAwareMsg, )
                else:
                    res = res + u"<u>%s:</u>" % cgi.escape(advice['name'])

                # add advice type
                res = res + u"<br /><u>%s :</u> <i>%s</i>" % (translate('Advice type',
                                                              domain='PloneMeeting',
                                                              context=self.request),
                                                              translate([advice['type']][0],
                                                                        domain='PloneMeeting',
                                                                        context=self.request), )

                # display the author if advice was given
                if withAuthor and not adviceType == NOT_GIVEN_ADVICE_VALUE:
                    adviceHolder = advice.get('adviceHolder', item)
                    adviceObj = adviceHolder.getAdviceObj(advice['id'])
                    membershipTool = api.portal.get_tool('portal_membership')
                    author = membershipTool.getMemberInfo(adviceObj.Creator())
                    if author:
                        author = author['fullname']
                    else:
                        author = adviceObj.Creator()
                    res = res + u"<br /><u>%s :</u> <i>%s</i>" % (translate('Advice given by',
                                                                  domain='PloneMeeting',
                                                                  context=self.request),
                                                                  cgi.escape(safe_unicode(author)), )

                    adviceComment = advice['comment'] and self.printXhtml(adviceObj, advice['comment']) or '-'
                    res = res + (u"<br /><u>%s :</u> %s<p></p>" % (translate('Advice comment',
                                                                             domain='PloneMeeting',
                                                                             context=self.request),
                                                                   safe_unicode(adviceComment)))
                res += u"</p>"
        if not itemAdvicesByType:
            res += "<p class='pmAdvices'>-</p>"

        return res.encode('utf-8')

    def get_scan_id(self):
        """We get scan_id to use on the template.
           - either we have a stored annex having a used_pod_template_id that corresponds
           to self.pod_template.id;
           - or we get the next_scan_id."""
        for annex in get_annexes(self.context):
            if getattr(annex, 'used_pod_template_id', None) == self.pod_template.getId():
                # annex must have a scan_id in this case or something went wrong
                if not annex.scan_id:
                    raise Exception(
                        "Found annex at {0} with correct 'used_pod_template_id' "
                        "but without a 'scan_id'!".format(
                            '/'.join(annex.getPhysicalPath())))
                # make the 'item_scan_id' value available in the REQUEST
                self.request.set(ITEM_SCAN_ID_NAME, annex.scan_id)
                return annex.scan_id
        # no annex found we get the next_scan_id
        # we import here because imio.zamqp.core could not be there
        # as amqp is activated when necessary
        from imio.zamqp.core.utils import next_scan_id
        scan_id = next_scan_id(file_portal_types=['annex', 'annexDecision'])
        # append a special value to scan_id stored in REQUEST if it is not a stored value
        if self.request.get('store_as_annex', '0') != '1':
            temp_qr_code_msg = translate(
                "Temporary QR code!", domain='PloneMeeting', context=self.request)
            scan_id = u'{0}\n[{1}]'.format(scan_id, temp_qr_code_msg)
        # make the 'item_scan_id' value available in the REQUEST
        self.request.set(ITEM_SCAN_ID_NAME, scan_id)
        return scan_id

    def printFullname(self, user_id):
        """ """
        user = api.user.get(user_id)
        return user and user.getProperty('fullname') or user_id

    def printAssembly(self, striked=True, use_print_attendees_by_type=True, **kwargs):
        '''Returns the assembly for this meeting or item.
           If p_striked is True, return striked assembly.
           If use_print_attendees_by_type is True, we use print_attendees_by_type method instead of
           print_attendees.'''

        if self.context.meta_type == 'MeetingItem' and not self.context.hasMeeting():
            # There is nothing to print in this case
            return ''

        assembly = None
        if self.context.meta_type == 'Meeting' and self.context.getAssembly():
            assembly = self.context.getAssembly()
        elif self.context.meta_type == 'MeetingItem' and self.context.getItemAssembly():
            assembly = self.context.getItemAssembly()

        if assembly:
            if striked:
                return toHTMLStrikedContent(assembly)
            return assembly

        if use_print_attendees_by_type:
            return self.print_attendees_by_type(
                # We set group_position_type at True by default because that's the most common case
                group_position_type=kwargs.pop('group_position_type', True),
                **kwargs
            )
        return self.print_attendees(**kwargs)

    def _get_attendees(self):
        """ """
        attendees = []
        item_absents = []
        item_excused = []
        item_non_attendees = []
        if self.context.meta_type == 'Meeting':
            meeting = self.context
            attendees = meeting.getAttendees()
            item_non_attendees = meeting.getItemNonAttendees()
        else:
            # MeetingItem
            meeting = self.context.getMeeting()
            if meeting:
                attendees = self.context.getAttendees()
                item_absents = self.context.getItemAbsents()
                item_excused = self.context.getItemExcused()
            item_non_attendees = self.context.getItemNonAttendees()
        # generate content then group by sub organization if necessary
        contacts = []
        absents = []
        excused = []
        replaced = []
        if meeting:
            contacts = meeting.getAllUsedHeldPositions()
            excused = meeting.getExcused()
            absents = meeting.getAbsents()
            replaced = meeting.getReplacements()
        return meeting, attendees, item_absents, item_excused, item_non_attendees, \
            contacts, excused, absents, replaced

    def print_attendees(self,
                        by_attendee_type=False,
                        by_parent_org=False,
                        render_as_html=True,
                        escape_for_html=True,
                        show_replaced_by=True,
                        include_replace_by_held_position_label=True,
                        attendee_value_format=u"{0}, {1}",
                        attendee_type_format=u"<strong>{0}</strong>",
                        abbreviate_firstname=False,
                        by_parent_org_first_format=None,
                        by_parent_org_format=u"<br /><strong><u>{0}</u></strong>",
                        custom_attendee_type_values={},
                        custom_grouped_attendee_type_patterns={},
                        replaced_by_format={'M': u'<strong>remplacé par {0}</strong>',
                                            'F': u'<strong>remplacée par {0}</strong>'},
                        ignore_non_attendees=True):
        """ """

        def _render_as_html(tree, by_parent_org=False):
            """ """
            res = []
            first = True
            for org, contact_infos in tree.items():
                if by_parent_org:
                    render_format = by_parent_org_format
                    if first and by_parent_org_first_format is not None:
                        render_format = by_parent_org_first_format
                    res.append(render_format.format(org.title))
                for contact_value in contact_infos.values():
                    res.append(contact_value)
                first = False
            return u'<br />'.join(res)

        attendee_type_values = {'attendee': {'M': u'présent',
                                             'F': u'présente'},
                                'excused': {'M': u'excusé',
                                            'F': u'excusée'},
                                'absent': {'M': u'absent',
                                           'F': u'absente'},
                                'replaced': {'M': u'remplacé',
                                             'F': u'remplacée'},
                                'item_absent': {'M': u'absent pour ce point',
                                                'F': u'absente pour ce point'},
                                'item_excused': {'M': u'excusé pour ce point',
                                                 'F': u'excusée pour ce point'},
                                'item_non_attendee': {'M': u'ne participe pas à ce point',
                                                      'F': u'ne participe pas à ce point'},
                                }
        attendee_type_values.update(custom_attendee_type_values)

        # initial values
        meeting, attendees, item_absents, item_excused, item_non_attendees, \
            contacts, excused, absents, replaced = self._get_attendees()

        res = OrderedDict()
        for contact in contacts:
            contact_uid = contact.UID()
            if ignore_non_attendees and contact_uid in item_non_attendees:
                continue
            contact_short_title = contact.get_short_title(include_sub_organizations=False,
                                                          abbreviate_firstname=abbreviate_firstname)
            if escape_for_html:
                contact_short_title = cgi.escape(contact_short_title)
            res[contact] = contact_short_title

        # manage group by sub organization
        if by_parent_org:
            by_suborg_res = OrderedDict()
            for contact, contact_short_title in res.items():
                org = contact.get_organization()
                if org not in by_suborg_res:
                    by_suborg_res[org] = OrderedDict()
                by_suborg_res[org][contact] = contact_short_title
            res = by_suborg_res
        else:
            # get same format for rest of the treatment
            res = OrderedDict({self.portal.contacts.get(PLONEGROUP_ORG):
                               OrderedDict(res.items())})

        # append presence to end of value
        for org, contact_infos in res.items():
            for contact, contact_value in contact_infos.items():
                contact_uid = contact.UID()
                contact_gender = contact.gender or 'M'
                if contact_uid in item_non_attendees:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['item_non_attendee'][contact_gender]))
                elif contact_uid in attendees:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['attendee'][contact_gender]))
                elif contact_uid in excused and contact_uid not in replaced:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['excused'][contact_gender]))
                elif contact_uid in absents and contact_uid not in replaced:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['absent'][contact_gender]))
                elif contact_uid in item_absents:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['item_absent'][contact_gender]))
                elif contact_uid in item_absents:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['item_absent'][contact_gender]))
                elif contact_uid in item_excused:
                    res[org][contact] = attendee_value_format.format(
                        res[org][contact],
                        attendee_type_format.format(attendee_type_values['item_excused'][contact_gender]))
                elif contact_uid in replaced:
                    if show_replaced_by:
                        res[org][contact] = attendee_value_format.format(
                            res[org][contact], replaced_by_format[contact_gender].format(
                                meeting.displayUserReplacement(
                                    replaced[contact_uid],
                                    include_held_position_label=include_replace_by_held_position_label,
                                    include_sub_organizations=False)))
                    else:
                        res[contact_uid][1] = attendee_value_format.format(
                            res[contact_uid][1],
                            attendee_type_format.format(attendee_type_values['replaced'][contact_gender]))

        if render_as_html:
            res = _render_as_html(res, by_parent_org=by_parent_org)
        return res

    def print_attendees_by_type(self,
                                by_parent_org=False,
                                group_position_type=False,
                                pos_attendee_separator=', ',
                                single_pos_attendee_ender=';',
                                render_as_html=True,
                                escape_for_html=True,
                                position_type_format=u", {0};",
                                show_grouped_attendee_type=True,
                                show_item_grouped_attendee_type=True,
                                custom_grouped_attendee_type_patterns={},
                                show_replaced_by=True,
                                replaced_by_format={'M': u'{0}, <strong>remplacé par {1}</strong>',
                                                    'F': u'{0}, <strong>remplacée par {1}</strong>'},
                                include_replace_by_held_position_label=True,
                                ignored_pos_type_ids=['default'],
                                include_person_title=True,
                                abbreviate_firstname=False,
                                included_attendee_types=['attendee', 'excused', 'absent', 'replaced',
                                                         'item_excused', 'item_absent', 'item_non_attendee'],
                                striked_attendee_types=[],
                                striked_attendee_pattern=u'<strike>{0}</strike>',
                                ignore_non_attendees=True):

        def _buildContactsValue(meeting, contacts):
            """ """
            grouped_contacts_value = []
            for contact in contacts:
                contact_value = contact.get_person_short_title(
                    include_person_title=include_person_title,
                    abbreviate_firstname=abbreviate_firstname,
                    include_held_position_label=not group_position_type)
                if escape_for_html:
                    contact_value = cgi.escape(contact_value)
                contact_uid = contact.UID()
                if contact_uid in striked_contact_uids:
                    contact_value = striked_attendee_pattern.format(contact_value)
                if contact_uid in replaced and show_replaced_by:
                    contact_value = replaced_by_format[contact.gender].format(
                        contact_value,
                        meeting.displayUserReplacement(
                            replaced[contact_uid],
                            include_held_position_label=include_replace_by_held_position_label,
                            include_sub_organizations=False))
                grouped_contacts_value.append(contact_value)
            return grouped_contacts_value

        def _render_as_html(tree, by_parent_org=False, group_position_type=False):
            """ """
            res = []
            for attendee_type, global_contact_infos in tree.items():
                every_contacts = []
                sub_res = []
                for org, contact_infos in global_contact_infos.items():
                    if by_parent_org:
                        sub_res.append(u"<strong><u>{0}</u></strong>".format(org.title))
                    if group_position_type:
                        for position_type, contacts in contact_infos.items():
                            every_contacts.extend(contacts)
                            position_type_value = u''
                            if not position_type.startswith('__no_position_type__'):
                                gn = get_gender_and_number(contacts)
                                hp = contacts[0]
                                # manage when we have no position_type but a label
                                if hp.position_type == u'default' and u'default' not in ignored_pos_type_ids:
                                    position_type_value = hp.get_label()
                                    if escape_for_html:
                                        position_type_value = cgi.escape(position_type_value)
                                else:
                                    position_type_value = contacts[0].gender_and_number_from_position_type()[gn]
                            grouped_contacts_value = _buildContactsValue(meeting, contacts)
                            grouped_contacts_value = pos_attendee_separator.join(grouped_contacts_value)
                            if position_type_value:
                                grouped_contacts_value = grouped_contacts_value + position_type_format.format(
                                    position_type_value)
                            else:
                                grouped_contacts_value = grouped_contacts_value + single_pos_attendee_ender
                            sub_res.append(grouped_contacts_value)
                    else:
                        grouped_contacts_value = _buildContactsValue(meeting, contact_infos)
                        grouped_contacts_value = pos_attendee_separator.join(grouped_contacts_value) + \
                            single_pos_attendee_ender
                        every_contacts.extend(contact_infos)
                        sub_res.append(grouped_contacts_value)
                if every_contacts:
                    gn = get_gender_and_number(every_contacts)
                    attendee_type_value = grouped_attendee_type_patterns[attendee_type].get(
                        gn, grouped_attendee_type_patterns[attendee_type]['*'])
                    if attendee_type_value:
                        res.append(attendee_type_value)
                    res.extend(sub_res)
            return u'<br />'.join(res)

        grouped_attendee_type_patterns = OrderedDict([
            ('attendee', {'MS': u'<strong><u>Présent&nbsp;:</u></strong>',
                          'MP': u'<strong><u>Présents&nbsp;:</u></strong>',
                          'FS': u'<strong><u>Présente&nbsp;:</u></strong>',
                          'FP': u'<strong><u>Présentes&nbsp;:</u></strong>',
                          '*': u'<strong><u>Présents&nbsp;:</u></strong>'}),
            ('excused', {'MS': u'<strong><u>Excusé&nbsp;:</u></strong>',
                         'MP': u'<strong><u>Excusés&nbsp;:</u></strong>',
                         'FS': u'<strong><u>Excusée&nbsp;:</u></strong>',
                         'FP': u'<strong><u>Excusées&nbsp;:</u></strong>',
                         '*': u'<strong><u>Excusés&nbsp;:</u></strong>'}),
            ('absent', {'MS': u'<strong><u>Absent&nbsp;:</u></strong>',
                        'MP': u'<strong><u>Absents&nbsp;:</u></strong>',
                        'FS': u'<strong><u>Absente&nbsp;:</u></strong>',
                        'FP': u'<strong><u>Absentes&nbsp;:</u></strong>',
                        '*': u'<strong><u>Absents&nbsp;:</u></strong>'}),
            ('replaced', {'MS': u'<strong><u>Remplacé&nbsp;:</u></strong>',
                          'MP': u'<strong><u>Remplacés&nbsp;:</u></strong>',
                          'FS': u'<strong><u>Remplacée&nbsp;:</u></strong>',
                          'FP': u'<strong><u>Remplacées&nbsp;:</u></strong>',
                          '*': u'<strong><u>Remplacés&nbsp;:</u></strong>'}),
            ('item_excused', {'MS': u'<strong><u>Excusé pour ce point&nbsp;:</u></strong>',
                              'MP': u'<strong><u>Excusés pour ce point&nbsp;:</u></strong>',
                              'FS': u'<strong><u>Excusée pour ce point&nbsp;:</u></strong>',
                              'FP': u'<strong><u>Excusées pour ce point&nbsp;:</u></strong>',
                              '*': u'<strong><u>Excusés pour ce point&nbsp;:</u></strong>'}),
            ('item_absent', {'MS': u'<strong><u>Absent pour ce point&nbsp;:</u></strong>',
                             'MP': u'<strong><u>Absents pour ce point&nbsp;:</u></strong>',
                             'FS': u'<strong><u>Absente pour ce point&nbsp;:</u></strong>',
                             'FP': u'<strong><u>Absentes pour ce point&nbsp;:</u></strong>',
                             '*': u'<strong><u>Absents pour ce point&nbsp;:</u></strong>'}),
            ('item_non_attendee',
             {'MS': u'<strong><u>Ne participe pas à ce point&nbsp;:</u></strong>',
              'MP': u'<strong><u>Ne participent pas à ce point&nbsp;:</u></strong>',
              'FS': u'<strong><u>Ne participe pas à ce point&nbsp;:</u></strong>',
              'FP': u'<strong><u>Ne participent pas à ce point&nbsp;:</u></strong>',
              '*': u'<strong><u>Ne participent pas à ce point&nbsp;:</u></strong>'}),
        ])
        if not show_grouped_attendee_type:
            grouped_attendee_type_patterns.update(OrderedDict([
                ('attendee', {'*': u''}),
                ('excused', {'*': u''}),
                ('absent', {'*': u''}),
                ('replaced', {'*': u''})]))
        if not show_item_grouped_attendee_type:
            grouped_attendee_type_patterns.update(OrderedDict([
                ('item_absent', {'*': u''}),
                ('item_excused', {'*': u''}),
                ('item_non_attendee', {'*': u''})]))
        grouped_attendee_type_patterns.update(custom_grouped_attendee_type_patterns)

        # initial values
        meeting, attendees, item_absents, item_excused, item_non_attendees, \
            contacts, excused, absents, replaced = self._get_attendees()

        res = OrderedDict([(key, []) for key in grouped_attendee_type_patterns.keys()])
        striked_contact_uids = []
        for contact in contacts:
            contact_uid = contact.UID()
            if ignore_non_attendees and contact_uid in item_non_attendees:
                continue
            contact_attendee_type = contact_uid in item_non_attendees and 'item_non_attendee' or \
                contact_uid in item_absents and 'item_absent' or \
                contact_uid in item_excused and 'item_excused' or \
                contact_uid in attendees and 'attendee' or \
                contact_uid in excused and 'excused' or \
                contact_uid in absents and 'absent' or \
                contact_uid in replaced and 'replaced'
            if (contact_attendee_type == 'attendee' or contact_attendee_type in striked_attendee_types) and \
                    'attendee' in included_attendee_types:
                if contact_attendee_type in striked_attendee_types:
                    striked_contact_uids.append(contact.UID())
                res['attendee'].append(contact)
            elif contact_attendee_type in included_attendee_types and \
                    contact_attendee_type not in striked_attendee_types:
                res[contact_attendee_type].append(contact)

        # manage by_parent_org
        # if used or not, we output the same format to continue process easier
        for attendee_type, contacts in res.items():
            by_suborg_res = OrderedDict()
            for contact in contacts:
                # include organization to have same format when using by_parent_org or not
                org = by_parent_org and contact.get_organization() or \
                    self.portal.contacts.get(PLONEGROUP_ORG)
                if org not in by_suborg_res:
                    by_suborg_res[org] = []
                by_suborg_res[org].append(contact)
            res[attendee_type] = by_suborg_res

        if group_position_type:
            for attendee_type, contact_infos in res.items():
                for org, contacts in contact_infos.items():
                    by_pos_type_res = OrderedDict()
                    for contact in contacts:
                        used_contact_position_type = contact.position_type
                        if not contact.position_type or contact.position_type in ignored_pos_type_ids:
                            # in this case, we use the special value prefixed by __no_position_type__
                            # so contacts are still ordered
                            used_contact_position_type = '__no_position_type__{0}'.format(contact.UID())
                            by_pos_type_res[used_contact_position_type] = []
                        # if u'default' not in ignored_pos_type_ids, use the label
                        if used_contact_position_type == u'default':
                            used_contact_position_type = contact.get_label()
                        # create entry on result if not already existing
                        if contact.position_type not in by_pos_type_res:
                            by_pos_type_res[used_contact_position_type] = []
                        by_pos_type_res[used_contact_position_type].append(contact)
                    res[attendee_type][org] = by_pos_type_res

        if render_as_html:
            res = _render_as_html(res,
                                  by_parent_org=by_parent_org,
                                  group_position_type=group_position_type)
        return res

    def sub_context(self, obj, sub_pod_template):
        helperView = obj.restrictedTraverse('@@document-generation')
        generation_helper_view = helperView._get_generation_context(self.getDGHV(obj), sub_pod_template)
        return generation_helper_view

    def print_signatures_by_position(self, **kwargs):
        """
        Print signatures by position
        :return: a dict with position as key and signature as value
        like this {1 : 'The mayor,', 2: 'John Doe'}.
        A dict is used to safely get a signature with the get method
        """
        signatures = None
        if self.context.meta_type == 'Meeting' and self.context.getSignatures():
            signatures = self.context.getSignatures()
        elif self.context.meta_type == 'MeetingItem' and self.context.getItemSignatures():
            signatures = self.context.getItemSignatures()

        if signatures:
            return OrderedDict({i: signature for i, signature in enumerate(signatures.split('\n'))})
        else:
            return self.print_signatories_by_position(**kwargs)

    def print_signatories_by_position(self,
                                      signature_format=(u'prefixed_secondary_position_type', u'person'),
                                      separator=u',',
                                      ender=u''):
        """
        Print signatories by position
        :param signature_format: tuple representing a single signature format
        containing these possible values:
            - 'position_type' -> 'Mayor'
            - 'prefixed_position_type' -> 'The Mayor'
            - 'person' -> 'John Doe'
            - 'person_with_title' -> 'Mister John Doe'
            - 'secondary_position_type' -> 'President'
            - 'prefixed_secondary_position_type' -> 'The President'
            - [PMHeldPosition attribute] e.g. 'gender' -> 'M'
            - [str] e.g. 'My String' -> 'My String' (in this case it just print the str)
        When using 'prefixed_secondary_position_type' (default), if no 'secondary_position_type'
        was defined, it falls back to 'prefixed_position_type' by default
        (same for 'secondary_position_type' that will fall back to 'position_type')
        :param separator: str that will be appended at the end of each line (except the last one)
        :param ender: str that will be appended at the end of the last one
        :return: a dict with position as key and signature as value
        like this {0 : 'The Manager,', 1 : "Jane Doe", 2 : 'The mayor,', 3: 'John Doe'}
        A dict is used to safely retrieve a signature with the '.get()' method in the PODTemplates
        --------------------------------------------------------------------------------------------
        Disclaimer: If a signatory has a label it will be used instead of his
        (secondary_)position_type and thus it can't be prefixed. If signatory has no gender,
        it will not be prefixed either. If person_with_title is used but signatory
        has no title defined, it will be printed without it.
        --------------------------------------------------------------------------------------------
        """
        signature_lines = OrderedDict()
        if self.context.meta_type == 'Meeting':
            signatories = self.context.getSignatories(theObjects=True, by_signature_number=True)
        else:
            signatories = self.context.getItemSignatories(theObjects=True, by_signature_number=True)

        line = 0
        sorted_signatories = [v for k, v in sorted(signatories.items(), key=lambda item: int(item[0]))]
        for signatory in sorted_signatories:
            for attr in signature_format:
                if u'position_type' == attr:
                    signature_lines[line] = signatory.get_label(position_type_attr=attr)
                elif u'prefixed_position_type' == attr:
                    signature_lines[line] = signatory.get_prefix_for_gender_and_number(
                        include_value=True,
                        position_type_attr='position_type')
                elif u'secondary_position_type' == attr:
                    signature_lines[line] = signatory.get_label(position_type_attr=attr)
                elif u'prefixed_secondary_position_type' == attr:
                    signature_lines[line] = signatory.get_prefix_for_gender_and_number(
                        include_value=True,
                        position_type_attr='secondary_position_type')
                elif attr == u'person':
                    signature_lines[line] = signatory.get_person_title(include_person_title=False)
                elif attr == u'person_with_title':
                    signature_lines[line] = signatory.get_person_title(include_person_title=True)
                elif hasattr(signatory, attr):
                    signature_lines[line] = getattr(signatory, attr)
                else:  # Just put the attr if it doesn't match anything above
                    signature_lines[line] = attr

                if attr != signature_format[-1] and separator is not None:
                    # if not last line of signatory
                    signature_lines[line] += separator
                elif ender is not None:  # it is the last line
                    signature_lines[line] += ender

                line += 1

        return signature_lines


class FolderDocumentGenerationHelperView(ATDocumentGenerationHelperView, BaseDGHV):
    """ """

    def selected_indexAdvisers_data(self, brains):
        """Compute advices data depending on what is selected in the current
           faceted regarding the 'indexAdvisers' index."""
        # get selected 'indexAdvisers' by finding the right faceted criterion
        criteria = ICriteria(self.real_context)._criteria()
        # get the 'indexAdvisers' value where adviser ids are stored
        advisers = []
        for criterion in criteria:
            if criterion.index == 'indexAdvisers':
                facetedQuery = json.loads(self.request.get('facetedQuery', '{}'))
                advisers = facetedQuery[criterion.__name__]

        # now build data
        # we will build following structure :
        # - a list of lists where :
        #   - first element is item;
        #   - next elements are a list of relevant advices data.
        # [
        #   [MeetingItemObject1, ['adviser_data_1', 'adviser_data_2', ]],
        #   [MeetingItemObject2, ['adviser_data_1', ]],
        #   ...
        # ]
        res = []
        for brain in brains:
            subres = {}
            item = brain.getObject()
            subres['item'] = item
            advisers_data = []
            # only keep relevant adviser data and keep order also
            for adviser in advisers:
                for org_uid, advice in item.adviceIndex.iteritems():
                    if adviser in _to_coded_adviser_index(item, org_uid, advice):
                        # we must keep this adviser
                        advisers_data.append(item.getAdviceDataFor(item, org_uid))
            subres['advices'] = advisers_data
            res.append(subres)
        return res

    def get_all_items_dghv(self, brains):
        """
        :param brains: the brains collection representing @Product.PloneMeeting.MeetingItem
        :return: the list of DocumentGeneratorHelperViews for these MeetingItems
        """
        res = []
        for brain in brains:
            item = brain.getObject()
            res.append(self.getDGHV(item))
        return res

    def get_all_items_dghv_with_advice(self, brains, adviserUids=[]):
        """
        :param brains: the brains collection representing @Product.PloneMeeting.MeetingItem
        :param adviserIds : list of adviser Uids to keep. By default it empty. Which means all advisers are kept.
        :return: an array of dictionary which contains 2 keys.
                 itemView : the documentgenerator helper view of a MeetingItem.
                 advice   : the data from a single advice linked to this MeetingItem as extracted with getAdviceDataFor.

                 If a MeetingItem doesn't have any advices the key advice is given with None value.
                 If a MeetingItem has more than 1 advice. The same Helper View is returned each time with a different
                 advice.
        """
        res = []
        for brain in brains:
            item = brain.getObject()
            if adviserUids:
                itemInserted = False
                for adviserUid in adviserUids:
                    advice = item.getAdviceDataFor(item, adviserUid)
                    if advice:
                        res.append({'itemView': self.getDGHV(item), 'advice': advice})
                        itemInserted = True
                if not itemInserted:
                    res.append({'itemView': self.getDGHV(item), 'advice': None})
            else:
                advices = item.getAdviceDataFor(item, ordered=True)
                if advices:
                    for advice in advices:
                        res.append({'itemView': self.getDGHV(item), 'advice': advices[advice]})
                else:
                    res.append({'itemView': self.getDGHV(item), 'advice': None})
        return res

    def _compute_attendances_proportion(self, attendances_list):
        """
        Computes The percentage of attendance for each contact in attendances_list as a float (ex 75.0 is 75%).

        :param attendances_list: A list of dict representing the attendance on a context (Meeting or MeetingItem)
               by held position in the assembly.
        """
        for attendance in attendances_list:
            nb_present = float(attendance['present'])
            nb_contexts = float(len(attendance['contexts']))
            if nb_contexts > 0:
                value = (nb_present / nb_contexts) * 100
            else:
                value = 0
            attendance['proportion'] = round(value, 2)

    def get_meeting_assembly_stats(self, brains):
        """
        :param brains: a list of brain of Meeting Objects
        :return: A list of dict representing the attendance on a bunch of Meetings organized by held position.
        """

        def _add_attendances_for_meeting(attendances, meeting, presents, excused, absents):
            """
            Populates the statistics for a Meeting or a MeetingItem by held position in the assembly.

            :param attendances: A list of dict representing the attendance on a context (Meeting or MeetingItem)
                                by held position in the assembly.
            :param context: A Meeting or a MeetingItem
            :param presents: the list of presence
            :param excused: the list of excused
            :param absents: the list of absents
            """

            def _add_attendance(attendances, meeting, assembly, counter):
                for held_position in assembly:
                    if held_position.UID() not in attendances or not attendances[held_position.UID()]:
                        attendances[held_position.UID()] = {'name': held_position.get_person_title(),
                                                            'function': held_position.get_label(),
                                                            'present': 0,
                                                            'absent': 0,
                                                            'excused': 0,
                                                            'contexts': set()}

                    attendances[held_position.UID()][counter] += 1
                    attendances[held_position.UID()]['contexts'].add(meeting)

            _add_attendance(attendances, meeting, presents, 'present')
            _add_attendance(attendances, meeting, excused, 'excused')
            _add_attendance(attendances, meeting, absents, 'absent')

        attendances = OrderedDict({})
        cfg = self.appy_renderer.originalContext['meetingConfig']

        for contact in cfg.getOrderedContacts():
            position = api.content.uuidToObject(contact)
            attendances[contact] = {'name': position.get_person_title(),
                                    'function': position.get_label(),
                                    'present': 0,
                                    'absent': 0,
                                    'excused': 0,
                                    'contexts': set()}

        for brain in brains:
            meeting = brain.getObject()
            presents = meeting.getAttendees(True)

            if presents:  # if there is no attendee it's useless to continue
                excused = meeting.getExcused(True)
                absents = meeting.getAbsents(True)
                _add_attendances_for_meeting(attendances, meeting, presents, excused, absents)

        res = attendances.values()
        self._compute_attendances_proportion(res)
        return res

    def get_meeting_assembly_stats_by_meeting(self, brains):
        """
        :param brains: a list of brain of Meeting Objects
        :return: A list of list of dict representing the attendance on a bunch of Meetings
                 organized by Meeting and by held position on every MeetingItems in each of the given Meetings.
        """
        def _add_attendances_for_items(attendances, meetingItems, presents, excused, itemExcused, absents, itemAbsents):
            """
            Populates the statistics for a Meeting or a MeetingItem by held position in the assembly.

            :param attendances: A list of dict representing the attendance on a context (Meeting or MeetingItem)
                                by held position in the assembly.
            :param context: A Meeting or a MeetingItem
            :param presents: the list of presence
            :param excused: the list of excused
            :param absents: the list of absents
            """

            def _add_attendance(attendances, meetingItems, assembly, counter):
                for held_position in assembly:
                    if held_position.UID() not in attendances or not attendances[held_position.UID()]:
                        attendances[held_position.UID()] = {'name': held_position.get_person_title(),
                                                            'function': held_position.get_label(),
                                                            'present': 0,
                                                            'absent': 0,
                                                            'excused': 0,
                                                            'contexts': set(meetingItems)}
                    if held_position in assembly:
                        attendances[held_position.UID()][counter] = len(meetingItems)

            def _remove_attendances(attendance, counter):
                attendances[attendance]['present'] -= 1
                attendances[attendance][counter] += 1

            _add_attendance(attendances, meetingItems, presents, 'present')
            _add_attendance(attendances, meetingItems, excused, 'excused')
            _add_attendance(attendances, meetingItems, absents, 'absent')

            for attendance in attendances:
                if attendance in itemExcused:
                    _remove_attendances(attendance, 'excused')
                if attendance in itemAbsents:
                    _remove_attendances(attendance, 'absent')

        res = []

        for brain in brains:
            meeting = brain.getObject()
            presents = list(meeting.getAttendees(True))
            excused = list(meeting.getExcused(True))
            absents = list(meeting.getAbsents(True))
            itemExcused = meeting.getItemExcused(True)
            itemAbsents = meeting.getItemAbsents(True)
            meetingData = {'title': meeting.Title()}
            attendances = OrderedDict({})
            _add_attendances_for_items(attendances,
                                       meeting.getItems(ordered=True),
                                       presents,
                                       excused,
                                       itemExcused,
                                       absents,
                                       itemAbsents)

            meetingData['attendances'] = attendances.values()
            self._compute_attendances_proportion(meetingData['attendances'])
            res.append(meetingData)

        return res


class MeetingDocumentGenerationHelperView(FolderDocumentGenerationHelperView):
    """ """


class ItemDocumentGenerationHelperView(ATDocumentGenerationHelperView, BaseDGHV):
    """ """

    def output_for_restapi(self):
        ''' '''
        result = {}
        result['deliberation'] = self.print_deliberation()
        result['public_deliberation'] = self.print_public_deliberation()
        result['public_deliberation_decided'] = self.print_public_deliberation_decided()
        return result

    def print_meeting_date(self, returnDateTime=False, noMeetingMarker='-', unrestricted=True):
        """Print meeting date, manage fact that item is not linked to a meeting,
           in this case p_noMeetingMarker is returned.
           If p_returnDateTime is True, it returns the meeting date DateTime,
           otherwise it returns the meeting title containing formatted date.
           If unrestricted is True, don't check if the current user has access to the meeting
        """
        meeting = self.context.getMeeting()

        if not meeting or (not unrestricted and not _checkPermission(View, meeting)):
            return noMeetingMarker

        if returnDateTime:
            return meeting.getDate()
        return meeting.Title()

    def printMeetingDate(self, returnDateTime=False, noMeetingMarker='-', unrestricted=True):
        """
        Allow backward compatibility with old PODTemplates.
        See print_meeting_date for docstring.
        """
        return self.print_meeting_date(returnDateTime, noMeetingMarker, unrestricted)

    def print_preferred_meeting_date(self, returnDateTime=False, noMeetingMarker='-', unrestricted=True):
        """
        Print preferred meeting date, manage fact that item has no preferred meeting date
        :param returnDateTime if True, returns the preferred meeting date DateTime, otherwise it returns the
        meeting title containing formatted date.
        :param noMeetingMarker is returned when there is no preferredMeeting.
        :param unrestricted if True, don't check if the current user has access to the meeting
        :return: Preferred meeting date
        """
        preferred_meeting = self.context.getPreferredMeeting(theObject=True)

        if not preferred_meeting or (not unrestricted and not _checkPermission(View, preferred_meeting)):
            return noMeetingMarker

        if returnDateTime:
            return preferred_meeting.getDate()
        return preferred_meeting.Title()

    def print_in_and_out_attendees(
            self,
            in_and_out_types=[],
            merge_in_and_out_types=True,
            merge_config={'left_before': 'non_attendee_before',
                          'entered_before': 'attendee_again_before',
                          'left_after': 'non_attendee_after',
                          'entered_after': 'attendee_again_after'},
            custom_patterns={},
            include_person_title=True,
            render_as_html=True,
            html_pattern=u'<p>{0}</p>'):
        """Print in an out moves depending on the previous/next item.
           If p_in_and_out_types is given, only given types are considered among
           'left_before', 'entered_before', 'left_after' and 'entered_after'.
           p_merge_in_and_out_types=True (default) will merge in_and_out_types for absent/excused and non_attendee
           types so for example key 'left_before' will also contain elements of key 'non_attendee_before'.
           p_patterns rendering informations may be overrided.
           If person_full_title is True, include full_title in sentence, aka include 'Mister' prefix.
           If p_render_as_html is True, informations is returned with value as HTML, else,
           we return a list of sentences.
           p_html_pattern is the way HTML is rendered when p_render_as_html is True."""

        patterns = {'left_before': u'{0} quitte la séance avant la discussion du point.',
                    'entered_before': u'{0} rentre en séance avant la discussion du point.',
                    'left_after': u'{0} quitte la séance après la discussion du point.',
                    'entered_after': u'{0} entre en séance après la discussion du point.',
                    'non_attendee_before': u'{0} ne participe plus à la séance avant la discussion du point.',
                    'attendee_again_before': u'{0} participe à nouveau à la séance avant la discussion du point.',
                    'non_attendee_after': u'{0} ne participe plus à la séance après la discussion du point.',
                    'attendee_again_after': u'{0} participe à nouveau à la séance après la discussion du point.'}
        patterns.update(custom_patterns)

        in_and_out = self.context.getInAndOutAttendees()
        person_res = {in_and_out_type: [] for in_and_out_type in in_and_out.keys()
                      if (not in_and_out_types or in_and_out_type in in_and_out_types)}
        for in_and_out_type, held_positions in in_and_out.items():
            for held_position in held_positions:
                person_res[in_and_out_type].append(
                    held_position.get_person().get_full_title(
                        include_person_title=include_person_title))

        if render_as_html:
            html_res = person_res.copy()
            for in_and_out_type, person_titles in person_res.items():
                html_res[in_and_out_type] = '\n'.join(
                    [html_pattern.format(patterns[in_and_out_type].format(person_title))
                     for person_title in person_titles])
            res = html_res
        else:
            res = person_res.copy()

        if merge_in_and_out_types:
            tmp_res = {}
            for k, v in merge_config.items():
                tmp_res[k] = res[k]
                tmp_res[k] += res[v]
            res = tmp_res.copy()

        return res

    def print_copy_groups(self, suffixes=[], separator=', ', render_as_html=True, html_pattern='<p>{0}</p>'):
        """
        Print the item's copy groups.
        suffixes is a list of suffixes of plone groups that we want to print: e.g. ['reviewers', 'oberservers']
        separator is used when render_as_html == True to specify how to separate the groups.
        render_as_html when False, return the list of Organization objects, otherwise return a html representation.
        html_pattern is used to add a html pattern around the list of groups.
        """
        res = []
        copy_groups = self.context.getCopyGroups()
        for copy_group in copy_groups:
            if copy_group.endswith(tuple(suffixes)):
                group = get_organization(copy_group)
                res.append(group)
        if render_as_html:
            res = separator.join(group.Title() for group in res)
            return html_pattern.format(res)
        return res

    def print_deliberation(self, xhtmlContents=[], **kwargs):
        '''Print the full item deliberation.'''
        if not xhtmlContents:
            xhtmlContents = [self.context.getMotivation(), self.context.getDecision()]
        return self.printXhtml(
            self.context,
            xhtmlContents,
            **kwargs)

    def print_public_deliberation(self, xhtmlContents=[], **kwargs):
        '''Overridable method to return public deliberation.'''
        return self.print_deliberation(xhtmlContents, **kwargs)

    def print_public_deliberation_decided(self, xhtmlContents=[], **kwargs):
        '''Overridable method to return public deliberation when decided.'''
        return self.print_deliberation(xhtmlContents, **kwargs)


class AdviceDocumentGenerationHelperView(DXDocumentGenerationHelperView, BaseDGHV):
    """ """


class CheckPodTemplatesView(BrowserView):
    """
      Check existing pod templates to try to find one out that is generating errors.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def __call__(self):
        '''Generate Pod Templates and check if some are genering errors.'''
        self.messages = self.manageMessages()
        return self.index()

    def manageMessages(self):
        ''' '''
        messages = OrderedDict()
        messages['error'] = []
        messages['no_obj_found'] = []
        messages['no_pod_portal_types'] = []
        messages['not_enabled'] = []
        messages['dashboard_templates_not_managed'] = []
        messages['style_templates_not_managed'] = []
        messages['clean'] = []

        for pod_template in self.cfg.podtemplates.objectValues():

            # we do not manage 'DashboardPODTemplate' automatically for now...
            if pod_template.portal_type == 'StyleTemplate':
                messages['style_templates_not_managed'].append((pod_template, None))
                continue

            # we do not manage 'DashboardPODTemplate' automatically for now...
            if pod_template.portal_type == 'DashboardPODTemplate':
                messages['dashboard_templates_not_managed'].append((pod_template, None))
                continue

            # here we have a 'ConfigurablePODTemplate'
            if not pod_template.pod_portal_types:
                messages['no_pod_portal_types'].append((pod_template, None))
                continue

            if not pod_template.pod_portal_types:
                messages['no_pod_portal_types'].append((pod_template, None))
                continue

            if not pod_template.enabled:
                messages['not_enabled'].append((pod_template, None))
                continue

            objs = self.findObjsFor(pod_template)
            if not objs:
                messages['no_obj_found'].append((pod_template, None))
                continue

            for obj in objs:
                if obj.meta_type == 'Meeting':
                    self.request.form['facetedQuery'] = []
                elif 'facetedQuery' in self.request.form:
                    del self.request.form['facetedQuery']
                view = obj.restrictedTraverse('@@document-generation')
                self.request.set('template_uid', pod_template.UID())
                output_format = pod_template.pod_formats[0]
                self.request.set('output_format', pod_template.pod_formats[0])
                view()
                try:
                    view()
                    view._generate_doc(pod_template, output_format=output_format, raiseOnError=True)
                    messages['clean'].append((pod_template, obj))
                except Exception, exc:
                    messages['error'].append((pod_template, obj, ('Error', exc.message)))
        return messages

    def findObjsFor(self, pod_template):
        '''This will find objs working with given p_pod_template.
           We return one obj of each pod_portal_types respecting the TAL condition.'''
        catalog = api.portal.get_tool('portal_catalog')
        res = []
        for pod_portal_type in pod_template.pod_portal_types:
            # get an element for which the TAL condition is True
            brains = catalog(portal_type=pod_portal_type)
            found = False
            for brain in brains:
                if found:
                    break
                obj = brain.getObject()
                if pod_template.can_be_generated(obj):
                    found = True
                    res.append(obj)
        return res


class PMDisplayGroupUsersView(DisplayGroupUsersView):
    """
      View that display the users of a Plone group.
    """

    def __init__(self, context, request):
        super(PMDisplayGroupUsersView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def _check_auth(self, group_id):
        """Only members of proposingGroup or (MeetingManagers)."""
        if not self.context.displayProposingGroupUsers():
            raise Unauthorized

    def _get_suffixes(self, group_id):
        """ """
        suffixes = get_all_suffixes(group_id)
        cfg = self.tool.getMeetingConfig(self.context)
        if 'prereviewers' in suffixes and \
           not [wfa for wfa in cfg.getWorkflowAdaptations()
                if wfa.startswith('pre_validation')]:
            suffixes.remove('prereviewers')
        return suffixes


class DisplayInheritedAdviceItemInfos(BrowserView):
    """
      View that display the users of a Plone group.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, advice_id):
        """ """
        self.advice_id = advice_id
        return self.index()

    @property
    def adviceHolder(self):
        return self.context.getInheritedAdviceInfo(self.advice_id)['adviceHolder']


class DisplayAnnexesView(BrowserView):
    """ """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, annex_portal_type='annex', fieldset_legend="annexes"):
        """ """
        self.annex_portal_type = annex_portal_type
        self.fieldset_legend = fieldset_legend
        return self.index()

    def show(self):
        """ """
        return self.tool.showAnnexesTab(self.context)


class AdviceHeaderView(BrowserView):
    """ """


class ItemHeaderView(BrowserView):
    """ """


class MeetingHeaderView(BrowserView):
    """ """


class MeetingStoreItemsPodTemplateAsAnnexBatchActionForm(BaseBatchActionForm):

    label = _CEBA("Store POD template as annex for selected elements")
    button_with_icon = True

    def __init__(self, context, request):
        super(MeetingStoreItemsPodTemplateAsAnnexBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        if self.cfg.getMeetingItemTemplatesToStoreAsAnnex() and \
           api.user.get_current().has_permission(ModifyPortalContent, self.context):
            return True

    def _update(self):
        self.fields += Fields(schema.Choice(
            __name__='pod_template',
            title=_(u'POD template to annex'),
            vocabulary='Products.PloneMeeting.vocabularies.itemtemplatesstorableasannexvocabulary'))

    def _apply(self, **data):
        """ """
        template_id, output_format = data['pod_template'].split('__output_format__')
        pod_template = getattr(self.cfg.podtemplates, template_id)
        num_of_generated_templates = 0
        self.request.set('store_as_annex', '1')
        for brain in self.brains:
            item = brain.getObject()
            generation_view = item.restrictedTraverse('@@document-generation')
            res = generation_view(
                template_uid=pod_template.UID(),
                output_format=output_format,
                return_portal_msg_code=True)
            if not res:
                num_of_generated_templates += 1
            else:
                # log error
                msg = translate(msgid=res, domain='PloneMeeting', context=self.request)
                logger.info(u'Could not generate POD template {0} using output format {1} for item at {2} : {3}'.format(
                    template_id, output_format, '/'.join(item.getPhysicalPath()), msg))
                api.portal.show_message(msg, request=self.request, type='error')

        msg = translate('stored_item_template_as_annex',
                        domain="PloneMeeting",
                        mapping={'number_of_annexes': num_of_generated_templates},
                        context=self.request,
                        default="Stored ${number_of_annexes} annexes.")
        api.portal.show_message(msg, request=self.request)
        self.request.set('store_as_annex', '0')


class UpdateLocalRolesBatchActionForm(BaseBatchActionForm):

    label = _CEBA("Update accesses for selected elements")
    button_with_icon = False

    def __init__(self, context, request):
        super(UpdateLocalRolesBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """Hide it on meetings as it uses IMeetingBatchActionsMarker."""
        return _checkPermission(ManagePortal, self.context) and not IMeeting.providedBy(self.context)

    def _apply(self, **data):
        """ """
        uids = listify_uids(data['uids'])
        self.tool.updateAllLocalRoles(**{'UID': uids})
        msg = translate('update_selected_elements',
                        domain="PloneMeeting",
                        mapping={'number_of_elements': len(uids)},
                        context=self.request,
                        default="Updated accesses for ${number_of_elements} element(s).")
        api.portal.show_message(msg, request=self.request)


class DisplayMeetingConfigsOfConfigGroup(BrowserView):
    """This view will display the MeetingConfigs of a ConfigGroup."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, config_group):
        """ """
        self.config_group = config_group
        return self.index()

    def getViewableMeetingConfigs(self):
        """Returns the list of MeetingConfigs the current user has access to."""
        tool = api.portal.get_tool('portal_plonemeeting')
        grouped_configs = tool.getGroupedConfigs(config_group=self.config_group)
        res = []
        for config_info in grouped_configs.values()[0]:
            cfg_id = config_info['id']
            cfg = getattr(tool, cfg_id)
            res.append(
                {'config': cfg,
                 'url': tool.getPloneMeetingFolder(cfg_id).absolute_url() + '/searches_items'})
        # make sure 'content-type' header of response is correct because during
        # faceted initialization, 'content-type' is turned to 'text/xml' and it
        # breaks to tooltipster displaying the result in the tooltip...
        self.request.RESPONSE.setHeader('content-type', 'text/html')
        return res


class DisplayMeetingItemNotPresent(BrowserView):
    """This view will display the items a given attendee was defined as not present for (absent/excused)."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # this view is called on meeting or item
        self.meeting = IMeeting.providedBy(self.context) and self.context or self.context.getMeeting()

    def __call__(self, not_present_uid, not_present_type):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.not_present_uid = not_present_uid
        self.not_present_type = not_present_type
        return self.index()

    def getItemsForNotPresent(self):
        """Returns the list of items the not_present_uid is absent for."""
        item_uids = []
        if self.not_present_type == 'absent':
            item_uids = self.meeting.getItemAbsents(by_persons=True).get(self.not_present_uid, [])
        elif self.not_present_type == 'excused':
            item_uids = self.meeting.getItemExcused(by_persons=True).get(self.not_present_uid, [])
        elif self.not_present_type == 'non_attendee':
            item_uids = self.meeting.getItemNonAttendees(by_persons=True).get(self.not_present_uid, [])
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(UID=item_uids, sort_on='getItemNumber')
        objs = [brain.getObject() for brain in brains]
        return objs


class DisplayMeetingItemSignatories(BrowserView):
    """This view will display the items a given attendee was defined as signatory for."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # this view is called on meeting or item
        self.meeting = IMeeting.providedBy(self.context) and self.context or self.context.getMeeting()

    def __call__(self, signatory_uid):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.signatory_uid = signatory_uid
        return self.index()

    def getItemsForSignatory(self):
        """Returns the list of items the signatory_uid is signatory for."""
        item_uids = self.meeting.getItemSignatories(by_signatories=True).get(self.signatory_uid, [])
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(UID=item_uids, sort_on='getItemNumber')
        objs = [brain.getObject() for brain in brains]
        return objs


class PODTemplateMailingLists(BrowserView):
    """ """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, template_uid, output_format):
        """ """
        self.template_uid = template_uid
        self.output_format = output_format
        return self.index()

    def getAvailableMailingLists(self):
        '''Gets the names of the (currently active) mailing lists defined for template_uid.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        pod_template = api.content.find(UID=self.template_uid)[0].getObject()
        return tool.getAvailableMailingLists(self.context, pod_template)
