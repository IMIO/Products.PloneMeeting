# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from collections import OrderedDict
from collective.behavior.talcondition.utils import _evaluateExpression
from collective.contact.core.utils import get_gender_and_number
from collective.contact.plonegroup.browser.tables import DisplayGroupUsersView
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organization
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.eeafaceted.batchactions import _ as _CEBA
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.eeafaceted.batchactions.browser.views import DeleteBatchActionForm
from collective.eeafaceted.batchactions.utils import listify_uids
from eea.facetednavigation.interfaces import ICriteria
from ftw.labels.interfaces import ILabeling
from imio.actionspanel.interfaces import IContentDeletable
from imio.annex.browser.views import DownloadAnnexesBatchActionForm
from imio.helpers.content import uuidToObject
from imio.helpers.xhtml import CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT
from imio.zamqp.core.utils import scan_id_barcode
from plone import api
from plone.app.caching.operations.utils import getContext
from plone.app.textfield.value import RichTextValue
from plone.dexterity.interfaces import IDexterityContent
from plone.memoize import ram
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
from Products.PloneMeeting.browser.itemvotes import _get_linked_item_vote_numbers
from Products.PloneMeeting.columns import render_item_annexes
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import REINDEX_NEEDED_MARKER
from Products.PloneMeeting.content.meeting import get_all_used_held_positions
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.indexes import _to_coded_adviser_index
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import convert2xhtml
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_dx_field
from Products.PloneMeeting.utils import get_dx_widget
from Products.PloneMeeting.utils import get_item_validation_wf_suffixes
from Products.PloneMeeting.utils import get_person_from_userid
from z3c.form.field import Fields
from z3c.form.interfaces import DISPLAY_MODE
from zope import schema
from zope.i18n import translate

import cgi
import json
import lxml


SEVERAL_SAME_BARCODE_ERROR = \
    'You can not generate several times same QR Code in same template!!!'


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
                                      expression=self.cfg.getItemsNotViewableVisibleFieldsTALExpr(),
                                      roles_bypassing_expression=[],
                                      extra_expr_ctx=extra_expr_ctx)
            if res:
                self.visibleFields = self.cfg.getField('itemsNotViewableVisibleFields').get(self.cfg)
                with api.env.adopt_roles(roles=['Manager']):
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
        return render_item_annexes(
            self.context, self.tool, show_nothing=True, check_can_view=True)


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
        self.static_infos_field_names = self._static_infos_field_names()
        if self.static_infos_field_names and IDexterityContent.providedBy(self.context):
            view = self.context.restrictedTraverse('@@view')
            view.update()
            self.dx_view = view
            # if we ask to display a field that is not enabled, it could
            # not be in dx_view.w, will only be shown if not None
            # (check BaseMeetingView.show_field)
            self.static_infos_field_names = [
                field_name for field_name in self.static_infos_field_names
                if field_name in self.dx_view.w]

        return super(BaseStaticInfosView, self).__call__()

    def _static_infos_field_names(self):
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


class ItemNumberView(BrowserView):
    """
      This manage the view displaying the itemNumber on the meeting view
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, may_change_items_order):
        self.may_change_items_order = may_change_items_order
        return super(ItemNumberView, self).__call__()

    def is_integer(self, number):
        """ """
        return _is_integer(number)


class ItemIsSignedView(BrowserView):
    """
      This manage the view displaying itemIsSigned widget
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__parent_cachekey(method, self):
        '''cachekey method for self.__call__.'''
        return self.context.getItemIsSigned(), \
            self.context.adapted().maySignItem(), self.context.showItemIsSigned()

    @ram.cache(__call__parent_cachekey)
    def ItemIsSignedView__call__parent(self):
        """ """
        self.portal_url = api.portal.get().absolute_url()
        return super(ItemIsSignedView, self).__call__()

    def __call__(self):
        """ """
        result = self.__call__parent()
        result = self._patch_html_content(result)
        return result

    def _patch_html_content(self, html_content):
        """To be able to use caching, we need to
           change UID and baseURL after __call__ is rendered."""
        html_content = html_content.replace("[uid]", self.context.UID())
        html_content = html_content.replace("[baseUrl]", self.context.absolute_url())
        return html_content

    # do ram.cache have a different key name
    __call__parent = ItemIsSignedView__call__parent


class ItemToDiscussView(BrowserView):
    """
      This manage the view displaying toDiscuss widget
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__parent_cachekey(method, self):
        '''cachekey method for self.__call__.'''
        return self.context.getToDiscuss(), self.mayEdit()

    @ram.cache(__call__parent_cachekey)
    def ItemToDiscussView__call__parent(self):
        """ """
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        return super(ItemToDiscussView, self).__call__()

    def __call__(self):
        """ """
        result = self.__call__parent()
        result = self._patch_html_content(result)
        return result

    def _patch_html_content(self, html_content):
        """To be able to use caching, we need to
           change UID and baseURL after __call__ is rendered."""
        html_content = html_content.replace("[uid]", self.context.UID())
        html_content = html_content.replace("[baseUrl]", self.context.absolute_url())
        return html_content

    def mayEdit(self):
        """ """
        toDiscuss_write_perm = self.context.getField('toDiscuss').write_permission
        return _checkPermission(toDiscuss_write_perm, self.context) and \
            self.context.showToDiscuss()

    @memoize_contextless
    def userIsReviewer(self):
        """ """
        return self.tool.userIsAmong(['reviewers'], cfg=self.cfg)

    @memoize_contextless
    def useToggleDiscuss(self):
        """ """
        return self.context.restrictedTraverse('@@toggle_to_discuss').isAsynchToggleEnabled()

    # do ram.cache have a different key name
    __call__parent = ItemToDiscussView__call__parent


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
    def __call__(self, way=None, itemNumber=None):
        """
          p_itemNumber is the number of the item we want to go to.  This item
          is in the same meeting than self.context.
        """
        not_accessible_item_found = False
        meeting = self.context.getMeeting()
        # got to meeting view on relevant item?
        if way == 'meeting':
            item_uids = [brain.UID for brain
                         in meeting.get_items(ordered=True, the_objects=False)]
            # find on which page item will be displayed
            # when displayed by 20, item number 10 is on page 1
            # item number 20 is on page 1, item number 22 is on page 2
            # but page 1 b_start is 0...
            # warning, item number 22 is on page 2 if more than 24 items
            # (batch_size + 20%) so take it into account also...
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            context_uid = self.context.UID()
            # use index position so element 20 index is 19 and is < 20
            item_pos = tuple(item_uids).index(context_uid)
            items_by_page = cfg.getMaxShownMeetingItems()
            page_num = float(item_pos) / items_by_page
            # round 0.85 to 0 or 1.05 to 1
            int_page_num = int(page_num)
            # if item_pos on last page, then we remove 20% of batch size to the item_post
            real_item_pos = item_pos + 1
            # over this, the 20% are not used
            tot_num_items = len(item_uids)
            tot_num_of_pages = int(tot_num_items / items_by_page)
            treshold = (tot_num_of_pages * items_by_page) + items_by_page * 0.2
            if tot_num_items <= treshold and \
                real_item_pos > tot_num_of_pages * items_by_page and \
                    real_item_pos <= treshold:
                int_page_num -= 1
            # we pass a custom_b_start as URL parameter and retrieve it
            # in Faceted.Query JS on the meeting view
            # this way parameters are computed like number of elements by page
            url = "{0}?custom_b_start={1}".format(
                meeting.absolute_url(), int_page_num * items_by_page)
            return self.request.RESPONSE.redirect(url)

        # navigate thru items
        elif way:
            brain = self.context.getSiblingItem(whichItem=way, itemNumber=False)
            if brain is None:
                not_accessible_item_found = True
            else:
                obj = brain.getObject()
                # check if obj isPrivacyViewable, if not, find the previous/next viewable item
                next_obj = None
                # if on last or first item, change way
                if way == 'last':
                    way = 'previous'
                elif way == 'first':
                    way = 'next'
                not_accessible_item_found = False
                while not obj.adapted().isPrivacyViewable() and \
                        not next_obj == obj and \
                        not next_obj == self.context:
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
        else:
            # itemNumber
            catalog = api.portal.get_tool('portal_catalog')
            itemNumber = _itemNumber_to_storedItemNumber(itemNumber)
            brains = catalog(meeting_uid=meeting.UID(), getItemNumber=int(itemNumber))
            if not brains:
                not_accessible_item_found = True
            else:
                obj = brains[0].getObject()
                return self.request.RESPONSE.redirect(obj.absolute_url())

        # fallback when item not accessible (no previous, no next, no asked item number, ...)
        if not_accessible_item_found:
            self.context.plone_utils.addPortalMessage(
                translate(msgid='item_number_not_accessible',
                          domain='PloneMeeting',
                          context=self.request),
                type='warning')
            return self.request.RESPONSE.redirect(self.context.absolute_url())


class NightTasksView(BrowserView):
    """
      This is a view that is called as a maintenance task by Products.cron4plone.
    """

    def __call__(self):
        self.context.restrictedTraverse('@@update-delay-aware-advices')()
        self.context.restrictedTraverse('@@update-items-to-reindex')()


class UpdateDelayAwareAdvicesView(BrowserView):
    """
      As we use clear days to compute advice delays, this is launched at 0:00
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
        brains = catalog.unrestrictedSearchResults(**query)
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
            item.update_local_roles()
        logger.info('Done.')


class UpdateItemsToReindexView(BrowserView):
    """
      When adding annexes, we avoid reindexing the SearchableText.
      It will be nevertheless most of times updated by another reindex
      made on item (modified rich text).  But if any are still to reindex, we
      do this during the night.
    """
    def __call__(self):
        """ """
        catalog = api.portal.get_tool('portal_catalog')
        query = {'pm_technical_index': [REINDEX_NEEDED_MARKER]}
        brains = catalog.unrestrictedSearchResults(**query)
        numberOfBrains = len(brains)
        i = 1
        logger.info('Reindexing %s items' % str(numberOfBrains))
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Reindexing of item at %s' % (
                i,
                numberOfBrains,
                '/'.join(item.getPhysicalPath())))
            i = i + 1
            setattr(item, REINDEX_NEEDED_MARKER, False)
            item.reindexObject()
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
        from plone.portlets.interfaces import IPortletManager
        from plone.portlets.interfaces import IPortletManagerRenderer
        from zope.component import getUtility
        from zope.component import queryMultiAdapter

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

    def __init__(self, context, request):
        self.printed_scan_id_barcode = []

    def _print_special_value(self, field_name, empty_marker=u'', **kwargs):
        """Overridable method to manage some specific usecases for self.print_value."""
        return None

    def print_value(self, field_name, empty_marker=u'', **kwargs):
        """Convenient method that print more or less everything."""
        # special handling for some values
        value = self._print_special_value(field_name, empty_marker, **kwargs)
        if value is None:
            # get attribute in schema
            value = getattr(self.real_context, field_name)
            field = get_dx_field(self.real_context, field_name)
            class_name = field.__class__.__name__
            # Datetime
            if class_name == 'Datetime':
                if 'custom_format' not in kwargs:
                    kwargs['custom_format'] = '%-d %B %Y'
                value = self.display_date(date=getattr(self.real_context, field_name), **kwargs)
            # RichText
            elif class_name == 'RichText':
                value = value and value.output
                if value:
                    value = self.printXhtml(self.context, xhtmlContents=value, **kwargs)
            # List/Choice
            elif getattr(field, 'vocabulary', None):
                value = self.display_voc(field_name, **kwargs)

        # if a p_empty_marker is given and no value, use it
        # it may be "???" or "-" for example
        if not value:
            value = empty_marker
        return value

    def image_orientation(self, image):
        """Compute image orientation, if orientation is landscape, we rotate
           the image from 90° so it is displayed on the full page.
           This is used by the appy.pod 'import from document' method
           as 'convertOptions' parameter."""
        if image.width > image.height:
            return '-rotate 90'

    def is_not_empty(self, field_name):
        """Check if given field_name is not empty."""
        res = True
        value = getattr(self.context, field_name, None)
        if value is None or \
           (isinstance(value, RichTextValue) and not value.raw):
            res = False
        return res

    def printXhtml(self,
                   context,
                   xhtmlContents,
                   image_src_to_paths=True,
                   image_src_to_data=False,
                   separatorValue='<p>&nbsp;</p>',
                   keepWithNext=False,
                   keepWithNextNumberOfChars=CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT,
                   checkNeedSeparator=True,
                   addCSSClass=None,
                   anonymize=False,
                   use_safe_html=False,
                   use_appy_pod_preprocessor=False,
                   clean=True):
        """p_anonymize may be a boolean (False/True), then it will use default values,
           or a dict with specific "css_class" and "new_content" values."""
        return convert2xhtml(obj=context,
                             xhtmlContents=xhtmlContents,
                             image_src_to_paths=image_src_to_paths,
                             image_src_to_data=image_src_to_data,
                             separatorValue=separatorValue,
                             keepWithNext=keepWithNext,
                             keepWithNextNumberOfChars=keepWithNextNumberOfChars,
                             checkNeedSeparator=checkNeedSeparator,
                             addCSSClass=addCSSClass,
                             anonymize=anonymize,
                             use_safe_html=use_safe_html,
                             use_appy_pod_preprocessor=use_appy_pod_preprocessor,
                             clean=clean)

    def print_history(self):
        """Return the history view for templates. """
        historyView = self.context.restrictedTraverse('@@historyview')()
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

    def print_advices_infos(self,
                            item,
                            withAdvicesTitle=True,
                            withDelay=False,
                            withDelayLabel=True,
                            withAuthor=True,
                            ordered=True):
        '''Helper method to have a printable version of advices.'''
        tool = api.portal.get_tool('portal_plonemeeting')
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
                    author = tool.getUserName(adviceObj.Creator())
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

    def print_scan_id_barcode(self, **kwargs):
        """Helper that will call scan_id_barcode from imio.zamqp.core
           and that will make sure that it is not called several times."""
        context_uid = self.context.UID()
        if context_uid in self.printed_scan_id_barcode:
            raise Exception(SEVERAL_SAME_BARCODE_ERROR)
        self.printed_scan_id_barcode.append(context_uid)
        barcode = scan_id_barcode(self.context, **kwargs)
        return barcode

    def print_fullname(self, user_id):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        return tool.getUserName(user_id)

    def print_assembly(self, striked=True, use_print_attendees_by_type=True, **kwargs):
        '''Returns the assembly for this meeting or item.
           If p_striked is True, return striked assembly.
           If use_print_attendees_by_type is True, we use print_attendees_by_type method instead of
           print_attendees.'''

        class_name = self.real_context.__class__.__name__
        if class_name == 'MeetingItem' and not self.context.hasMeeting():
            # There is nothing to print in this case
            return ''

        assembly = None
        committee_id = kwargs.get('committee_id', None)
        if committee_id:
            assembly = self.context.get_committee_assembly(
                row_id=committee_id, for_display=True, striked=striked)
        elif class_name == 'Meeting' and self.context.get_assembly():
            assembly = self.context.get_assembly(for_display=True, striked=striked)
        elif class_name == 'MeetingItem' and self.context.getItemAssembly(for_display=False):
            assembly = self.context.getItemAssembly(for_display=True, striked=striked)

        if assembly:
            return assembly

        if use_print_attendees_by_type:
            return self.print_attendees_by_type(
                # We set group_position_type at True by default because that's the most common case
                group_position_type=kwargs.pop('group_position_type', True),
                **kwargs
            )
        return self.print_attendees(**kwargs)

    def _get_attendees(self, committee_id=None):
        """ """
        attendees = []
        item_absents = []
        item_excused = []
        item_non_attendees = []
        if committee_id:
            meeting = self.context
            attendees = self.context.get_committee_attendees(committee_id)
        elif self.context.getTagName() == 'Meeting':
            meeting = self.context
            attendees = meeting.get_attendees()
            item_non_attendees = meeting.get_item_non_attendees()
        else:
            # MeetingItem
            meeting = self.context.getMeeting()
            if meeting:
                attendees = self.context.get_attendees()
                item_absents = self.context.get_item_absents()
                item_excused = self.context.get_item_excused()
            item_non_attendees = self.context.get_item_non_attendees()
        # generate content then group by sub organization if necessary
        contacts = []
        absents = []
        excused = []
        replaced = []
        if meeting:
            if committee_id:
                contacts = self.context.get_committee_attendees(committee_id, the_objects=True)
            else:
                contacts = get_all_used_held_positions(meeting)
            excused = meeting.get_excused()
            absents = meeting.get_absents()
            replaced = meeting.get_replacements()
        return meeting, attendees, item_absents, item_excused, item_non_attendees, \
            contacts, excused, absents, replaced

    def _update_patterns_for_videoconference(self, meeting, patterns, value):
        if hasattr(meeting, "videoconference") and meeting.videoconference:
            patterns.update(value)

    def print_attendees(self,
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
                        adapt_for_videoconference=True,
                        custom_grouped_attendee_type_patterns={},
                        replaced_by_format={'M': u'<strong>remplacé par {0}</strong>',
                                            'F': u'<strong>remplacée par {0}</strong>'},
                        ignore_non_attendees=True,
                        committee_id=None):
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
            contacts, excused, absents, replaced = self._get_attendees(committee_id)
        context_uid = self.context.UID()

        if adapt_for_videoconference:
            self._update_patterns_for_videoconference(meeting, attendee_type_values, {'attendee': {
                'M': u'connecté',
                'F': u'connectée',
            }})

        res = OrderedDict()
        for contact in contacts:
            contact_uid = contact.UID()
            if ignore_non_attendees and contact_uid in item_non_attendees:
                continue
            forced_position_type_value = None
            if self.context.getTagName() == "MeetingItem":
                forced_position_type_value = meeting.get_attendee_position_for(
                    context_uid, contact_uid)
            contact_short_title = contact.get_short_title(include_sub_organizations=False,
                                                          abbreviate_firstname=abbreviate_firstname,
                                                          forced_position_type_value=forced_position_type_value)
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
                                meeting.display_user_replacement(
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
                                unbreakable_contact_value=False,
                                end_type_character=None,
                                show_grouped_attendee_type=True,
                                show_item_grouped_attendee_type=True,
                                custom_grouped_attendee_type_patterns={},
                                adapt_for_videoconference=True,
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
                                ignore_non_attendees=True,
                                committee_id=None):

        context_uid = self.context.UID()
        is_item = self.context.getTagName() == "MeetingItem"

        def _buildContactsValue(meeting, contacts):
            """ """
            grouped_contacts_value = []
            for contact in contacts:
                forced_position_type_value = None
                contact_uid = contact.UID()
                if is_item:
                    forced_position_type_value = meeting.get_attendee_position_for(
                        context_uid, contact_uid)
                contact_value = contact.get_person_short_title(
                    include_person_title=include_person_title,
                    abbreviate_firstname=abbreviate_firstname,
                    include_held_position_label=not group_position_type,
                    forced_position_type_value=forced_position_type_value)
                if escape_for_html:
                    contact_value = cgi.escape(contact_value)
                if contact_uid in striked_contact_uids:
                    contact_value = striked_attendee_pattern.format(contact_value)
                if contact_uid in replaced and show_replaced_by:
                    contact_value = replaced_by_format[contact.gender].format(
                        contact_value,
                        meeting.display_user_replacement(
                            replaced[contact_uid],
                            include_held_position_label=include_replace_by_held_position_label,
                            include_sub_organizations=False))
                if unbreakable_contact_value:
                    contact_value = contact_value.replace(" ", "&nbsp;")
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
                                hp_uid = hp.UID()
                                if position_type == u'default' and u'default' not in ignored_pos_type_ids:
                                    if is_item:
                                        position_type_value = meeting.get_attendee_position_for(
                                            context_uid, hp_uid)
                                    else:
                                        position_type_value = hp.get_label()
                                    if escape_for_html:
                                        position_type_value = cgi.escape(position_type_value)
                                else:
                                    forced_position_type_value = None
                                    if is_item:
                                        forced_position_type_value = meeting.get_attendee_position_for(
                                            context_uid, hp_uid)
                                    position_type_value = contacts[0].gender_and_number_from_position_type(
                                        forced_position_type_value=forced_position_type_value)[gn]
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
                    if end_type_character and global_contact_infos.keys()[-1] == org:
                        # If there is an end_type_character defined and we are at the last contact
                        # for a given attendee_type, swap the last char with end_type_character
                        sub_res[-1] = sub_res[-1][:-1] + end_type_character
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
            contacts, excused, absents, replaced = self._get_attendees(committee_id)

        if adapt_for_videoconference:
            self._update_patterns_for_videoconference(meeting, grouped_attendee_type_patterns, {
                'attendee': {
                    'MS': u'<strong><u>Connecté&nbsp;:</u></strong>',
                    'MP': u'<strong><u>Connectés&nbsp;:</u></strong>',
                    'FS': u'<strong><u>Connectée&nbsp;:</u></strong>',
                    'FP': u'<strong><u>Connectées&nbsp;:</u></strong>',
                    '*': u'<strong><u>Connectés&nbsp;:</u></strong>'
                }
            })

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
                        if is_item:
                            used_contact_position_type = meeting.get_attendee_position_for(
                                context_uid, contact.UID())
                        else:
                            used_contact_position_type = contact.position_type
                        if not used_contact_position_type or used_contact_position_type in ignored_pos_type_ids:
                            # in this case, we use the special value prefixed by __no_position_type__
                            # so contacts are still ordered
                            used_contact_position_type = '__no_position_type__{0}'.format(contact.UID())
                            by_pos_type_res[used_contact_position_type] = []
                        # if u'default' not in ignored_pos_type_ids, use the label
                        if used_contact_position_type == u'default':
                            used_contact_position_type = contact.get_label()
                        # create entry on result if not already existing
                        if used_contact_position_type not in by_pos_type_res:
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

    def print_signatures_by_position(self, committee_id=None, **kwargs):
        """
        Print signatures by position
        :return: a dict with position as key and signature as value
        like this {1 : 'The mayor,', 2: 'John Doe'}.
        A dict is used to safely get a signature with the get method
        """
        signatures = None
        if committee_id:
            signatures = self.context.get_committee_signatures(committee_id)
        elif self.context.getTagName() == 'Meeting' and self.context.get_signatures():
            signatures = self.context.get_signatures()
        elif self.context.getTagName() == 'MeetingItem' and self.context.getItemSignatures():
            signatures = self.context.getItemSignatures()

        if signatures:
            return OrderedDict({i: signature for i, signature in enumerate(signatures.split('\n'))})
        else:
            return self.print_signatories_by_position(committee_id=committee_id, **kwargs)

    def print_signatories_by_position(self,
                                      signature_format=(u'prefixed_secondary_position_type', u'person'),
                                      separator=u',',
                                      ender=u'',
                                      committee_id=None):
        """
        Print signatories by position
        :param signature_format: tuple representing a single signature format
        containing these possible values:
            - 'position_type' -> 'Mayor'
            - 'prefixed_position_type' -> 'The Mayor'
            - 'person' -> 'John Doe'
            - 'abbreviated_person' -> 'J. Doe'
            - 'person_with_title' -> 'Mister John Doe'
            - 'abbreviated_person_with_title' -> 'Mister J. Doe'
            - 'secondary_position_type' -> 'President'
            - 'prefixed_secondary_position_type' -> 'The President'
            - 'person_signature' -> Person signature's [NamedImage]
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
        forced_position_type_values = {}
        if committee_id:
            signatories = self.context.get_committee_signatories(
                committee_id, the_objects=True, by_signature_number=True)
        elif self.context.getTagName() == 'Meeting':
            signatories = self.context.get_signatories(the_objects=True, by_signature_number=True)
        else:
            signatories = self.context.get_item_signatories(the_objects=True, by_signature_number=True)
            if self.context.hasMeeting():
                # if we have redefined signatories, use the selected position_type
                meeting = self.context.getMeeting()
                item_uid = self.context.UID()
                item_signatories = meeting.get_item_signatories(include_position_type=True)
                if item_uid in item_signatories:
                    forced_position_type_values = {
                        k: v['position_type'] for k, v in
                        item_signatories[item_uid].items()}

        line = 0
        sorted_signatories = [(v, forced_position_type_values.get(k, None))
                              for k, v in sorted(signatories.items(),
                                                 key=lambda item: int(item[0]))]
        for signatory, forced_position_type_value in sorted_signatories:
            for attr in signature_format:
                if u'position_type' == attr:
                    signature_lines[line] = signatory.get_label(
                        position_type_attr=attr,
                        forced_position_type_value=forced_position_type_value)
                elif u'prefixed_position_type' == attr:
                    signature_lines[line] = signatory.get_prefix_for_gender_and_number(
                        include_value=True,
                        position_type_attr='position_type',
                        forced_position_type_value=forced_position_type_value)
                elif u'secondary_position_type' == attr:
                    signature_lines[line] = signatory.get_label(
                        position_type_attr=attr,
                        forced_position_type_value=forced_position_type_value)
                elif u'prefixed_secondary_position_type' == attr:
                    signature_lines[line] = signatory.get_prefix_for_gender_and_number(
                        include_value=True,
                        position_type_attr='secondary_position_type',
                        forced_position_type_value=forced_position_type_value)
                elif attr == u'person':
                    signature_lines[line] = signatory.get_person_title(include_person_title=False)
                elif attr == u'abbreviated_person':
                    signature_lines[line] = signatory.get_person_short_title(abbreviate_firstname=True)
                elif attr == u'person_with_title':
                    signature_lines[line] = signatory.get_person_title(include_person_title=True)
                elif attr == u'abbreviated_person_with_title':
                    signature_lines[line] = signatory.get_person_short_title(
                        abbreviate_firstname=True, include_person_title=True
                    )
                elif attr == u'person_signature':
                    signature_lines[line] = signatory.get_person().signature
                elif hasattr(signatory, attr):
                    signature_lines[line] = getattr(signatory, attr)
                else:  # Just put the attr if it doesn't match anything above
                    signature_lines[line] = attr

                if attr != signature_format[-1] \
                        and separator is not None \
                        and isinstance(signature_lines[line], unicode):
                    # if not last line of signatory
                    signature_lines[line] += separator
                elif ender is not None and isinstance(signature_lines[line], unicode):  # it is the last line
                    signature_lines[line] += ender

                line += 1

        return signature_lines

    def vote_infos(self, used_vote_values=[], include_null_vote_count_values=[], keep_vote_numbers=[]):
        """ """
        item_votes = self.context.get_item_votes(include_unexisting=False)
        if not used_vote_values:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            used_vote_values = cfg.getUsedVoteValues()
        # there may have several votes
        votes = []
        i = 0
        for item_vote in item_votes:
            if keep_vote_numbers and i not in keep_vote_numbers:
                continue
            i = i + 1
            counts = OrderedDict()
            for vote_value in used_vote_values:
                vote_count = self.context.getVoteCount(
                    vote_value=vote_value, vote_number=item_vote['vote_number'])
                # keep 0 vote_counts?
                if vote_count == 0 and vote_value not in include_null_vote_count_values:
                    continue
                counts[vote_value] = vote_count
            infos = {}
            infos['counts'] = counts
            infos['label'] = item_vote['label']
            infos['voters'] = item_vote.get('voters', {})
            infos['linked_to_previous'] = item_vote['linked_to_previous']
            votes.append(infos)
        return votes

    def is_all_count(self,
                     vote_info=None,
                     vote_number=0,
                     vote_value='yes',
                     used_vote_values=[],
                     include_null_vote_count_values=[]):
        """ """
        if vote_info is None:
            vote_infos = self.vote_infos(used_vote_values, include_null_vote_count_values)
            vote_info = vote_infos[vote_number]
        counts = vote_info['counts']
        return len(counts) == 1 and vote_value in counts

    def print_votes(self,
                    main_pattern=u"<p>Par {0},</p>",
                    separator=u", ",
                    last_separator=u" et ",
                    single_vote_value=u"une",
                    secret_intro=u"<p>Au scrutin secret,</p>",
                    public_intro=u"",
                    custom_patterns={},
                    vote_label_pattern=u"<p><strong>{0}</strong></p>",
                    used_vote_values=[],
                    include_null_vote_count_values=[],
                    all_yes_render=u"<p>À l'unanimité,</p>",
                    used_patterns="sentence",
                    include_voters=False,
                    include_person_title=True,
                    include_hp=True,
                    abbreviate_firstname=False,
                    voters_pattern=u"<p>{0}</p>",
                    voter_separator=u", ",
                    voter_pattern=u"{0}",
                    keep_vote_numbers=[],
                    render_as_html=True,
                    escape_for_html=True):
        """Function for printing votes :
           When using p_render_as_html=True :
           - p_main_pattern is the main pattern the votes will be rendered;
           - p_separator is used to separate vote values;
           - p_last_separator is used to separate last vote value from others;
           - p_secret_intro will be included before rendered vote_values if votes are secret;
           - p_public_intro will be included before rendered vote_values if votes are public;
           - p_custom_patterns will override internal patterns;
           - p_vote_label_pattern used to render vote label, by default is None so not rendered,
             but could be u"<p><strong>{0}</strong></p>" for example;
           - p_used_vote_values if given, will be used, if not, will use MeetingConfig.usedVoteValues;
           - p_include_null_vote_count_values, by default null (0) vote counts are not shown,
             define a list of used vote values to keep;
           - p_all_yes_render, rendered instead vote values when every values are 'yes';
           - render_as_html=True
           """

        def _render_voters(vote_value, voters, meeting):
            """ """
            voter_uids = [voter_uid for voter_uid, voter_vote_value in voters.items()
                          if voter_vote_value == vote_value]
            # _get_contacts return ordered contacts
            voters = meeting._get_contacts(uids=voter_uids, the_objects=True)
            res = []
            for voter in voters:
                forced_position_type_value = None
                if self.context.getTagName() == "MeetingItem":
                    forced_position_type_value = meeting.get_attendee_position_for(
                        self.context.UID(), voter.UID())
                if include_hp:
                    voter_short_title = voter.get_short_title(
                        include_sub_organizations=False,
                        include_person_title=include_person_title,
                        abbreviate_firstname=abbreviate_firstname,
                        forced_position_type_value=forced_position_type_value)
                else:
                    voter_short_title = voter.get_person_short_title(
                        include_person_title=include_person_title,
                        abbreviate_firstname=abbreviate_firstname,
                        forced_position_type_value=forced_position_type_value)
                if escape_for_html:
                    voter_short_title = cgi.escape(voter_short_title)
                res.append(voter_pattern.format(voter_short_title))
            return voters_pattern.format(voter_separator.join(res))

        if used_patterns == "sentence":
            patterns = {
                'yes': u"{0} voix pour",
                'yes_multiple': u"{0} voix pour",
                'no': u"{0} voix contre",
                'no_multiple': u"{0} voix contre",
                'abstain': u"{0} abstention",
                'abstain_multiple': u"{0} abstentions"}
        elif used_patterns == "counts":
            patterns = {
                'yes': u"<p><strong>Pour: {0}</strong></p>",
                'yes_multiple': u"<p><strong>Pour: {0}</strong></p>",
                'no': u"<p><strong>Contre: {0}</strong></p>",
                'no_multiple': u"<p><strong>Contre: {0}</strong></p>",
                'abstain': u"<p><strong>Abstention: {0}</strong></p>",
                'abstain_multiple': u"<p><strong>Abstentions: {0}</strong></p>"}
        elif used_patterns == "counts_persons":
            patterns = {
                'yes': u"<p><strong>A voté pour: {0}</strong></p>",
                'yes_multiple': u"<p><strong>Ont votés pour: {0}</strong></p>",
                'no': u"<p><strong>A voté contre: {0}</strong></p>",
                'no_multiple': u"<p><strong>Ont votés contre: {0}</strong></p>",
                'abstain': u"<p><strong>S'est abstenu(e): {0}</strong></p>",
                'abstain_multiple': u"<p><strong>Se sont abstenu(e)s: {0}</strong></p>"}
        patterns.update(custom_patterns)
        # get votes
        rendered = u""
        secret = self.context.get_votes_are_secret()
        meeting = self.context.getMeeting()
        vote_infos = self.vote_infos(
            used_vote_values, include_null_vote_count_values, keep_vote_numbers)
        for vote_info in vote_infos:
            counts = vote_info['counts']
            label = vote_info['label']
            voters = vote_info['voters']
            if render_as_html:
                # vote label
                if vote_label_pattern and label:
                    rendered += vote_label_pattern.format(label)
                # intro
                if secret and secret_intro:
                    rendered += secret_intro
                elif public_intro:
                    rendered += public_intro
                # all yes or detailled
                if all_yes_render and \
                   not vote_info['linked_to_previous'] and \
                   self.is_all_count(vote_info, 'yes'):
                    rendered += all_yes_render
                else:
                    values = []
                    for vote_value, vote_count in counts.items():
                        # use _multiple suffixed pattern?
                        pattern_value = vote_count > 1 and vote_value + '_multiple' or vote_value
                        if vote_count == 1:
                            vote_count = single_vote_value
                        value = patterns[pattern_value].format(vote_count)
                        # prepare voters if necessary
                        if include_voters and not secret:
                            value += _render_voters(vote_value, voters, meeting)
                        values.append(value)

                    # render text taking into account last_separator
                    last_rendered = u""
                    two_last_values = values[-2:]
                    all = []
                    if len(two_last_values) == 2:
                        last_rendered = last_separator.join(two_last_values)
                        values = values[:-2]
                        all.append(last_rendered)
                    # after last_rendered management, still values?
                    if values:
                        begin_rendered_values = separator.join(values)
                        all.insert(0, begin_rendered_values)
                    rendered += main_pattern.format(separator.join(all))

        return render_as_html and (rendered or u"-") or vote_infos


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

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)

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
        for contact in cfg.getOrderedContacts():
            position = uuidToObject(contact, unrestricted=True)
            attendances[contact] = {'name': position.get_person_title(),
                                    'function': position.get_label(),
                                    'present': 0,
                                    'absent': 0,
                                    'excused': 0,
                                    'contexts': set()}

        for brain in brains:
            meeting = brain.getObject()
            presents = meeting.get_attendees(True)

            if presents:  # if there is no attendee it's useless to continue
                excused = meeting.get_excused(True)
                absents = meeting.get_absents(True)
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
        def _add_attendances_for_items(attendances,
                                       meeting_items,
                                       presents,
                                       excused,
                                       item_excused,
                                       absents,
                                       item_absents):
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

            _add_attendance(attendances, meeting_items, presents, 'present')
            _add_attendance(attendances, meeting_items, excused, 'excused')
            _add_attendance(attendances, meeting_items, absents, 'absent')

            for attendance in attendances:
                if attendance in item_excused:
                    _remove_attendances(attendance, 'excused')
                if attendance in item_absents:
                    _remove_attendances(attendance, 'absent')

        res = []

        for brain in brains:
            meeting = brain.getObject()
            presents = list(meeting.get_attendees(True))
            excused = list(meeting.get_excused(True))
            absents = list(meeting.get_absents(True))
            item_excused = meeting.get_item_excused(True)
            item_absents = meeting.get_item_absents(True)
            # as 'title' is used for generated file sheet name
            # make sure it does not contain forbidden letters
            # especially when meeting hours is displayed between ()
            meeting_data = {'title': meeting.Title().replace(':', 'h')}
            attendances = OrderedDict({})
            _add_attendances_for_items(attendances,
                                       meeting.get_items(ordered=True),
                                       presents,
                                       excused,
                                       item_excused,
                                       absents,
                                       item_absents)

            meeting_data['attendances'] = attendances.values()
            self._compute_attendances_proportion(meeting_data['attendances'])
            res.append(meeting_data)

        return res


class MeetingDocumentGenerationHelperView(DXDocumentGenerationHelperView, FolderDocumentGenerationHelperView):
    """ """

    def _print_special_value(self, field_name, empty_marker='', **kwargs):
        """Manage 'place' manually."""
        # 'place' may be stored in 'place' or 'place_other'
        if field_name == 'place':
            return self.real_context.get_place()


class ItemDocumentGenerationHelperView(ATDocumentGenerationHelperView, BaseDGHV):
    """ """

    def deliberation_for_restapi(self, deliberation_types=[]):
        '''Return some formatted deliberation useful for external services.'''
        result = {}
        # motivation + decision
        if not deliberation_types or "deliberation" in deliberation_types:
            result['deliberation'] = self.print_deliberation()
        if not deliberation_types or "public_deliberation" in deliberation_types:
            result['public_deliberation'] = self.print_public_deliberation()
        if not deliberation_types or "public_deliberation_decided" in deliberation_types:
            result['public_deliberation_decided'] = self.print_public_deliberation_decided()
        # motivation only
        if not deliberation_types or "deliberation_motivation" in deliberation_types:
            result['deliberation_motivation'] = \
                self.print_deliberation(xhtmlContents=[self.context.getMotivation()])
        # decision only
        if not deliberation_types or "deliberation_decision" in deliberation_types:
            result['deliberation_decision'] = \
                self.print_deliberation(xhtmlContents=[self.context.getDecision()])
        return result

    def print_meeting_date(self, returnDateTime=False, noMeetingMarker='-', unrestricted=True, **kwargs):
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
            return meeting.date
        else:
            dghv = self.getDGHV(meeting)
            return dghv.print_value("date", **kwargs)

    def print_preferred_meeting_date(self, returnDateTime=False, noMeetingMarker='-', unrestricted=True, **kwargs):
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
            return preferred_meeting.date
        else:
            dghv = self.getDGHV(preferred_meeting)
            return dghv.print_value("date", **kwargs)

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
            html_pattern=u'<p>{0}</p>',
            ignore_before_first_item=True,
            include_hp=False,
            abbreviate_firstname=False):
        """Print in an out moves depending on the previous/next item.
           If p_in_and_out_types is given, only given types are considered among
           patterns keys ('left_before', 'entered_before', ...).
           p_merge_in_and_out_types=True (default) will merge in_and_out_types for absent/excused and non_attendee
           types so for example key 'left_before' will also contain elements of key 'non_attendee_before'.
           p_patterns rendering informations may be overrided.
           If person_full_title is True, include full_title in sentence, aka include 'Mister' prefix.
           If p_render_as_html is True, informations is returned with value as HTML, else,
           we return a list of sentences.
           p_html_pattern is the way HTML is rendered when p_render_as_html is True.
           If p_ignore_before_first_item is True (default), "before" sentences will
           not be rendered for first item of the meeting."""

        patterns = {'left_before': u'{0} quitte la séance avant la discussion du point.',
                    'entered_before': u'{0} entre en séance avant la discussion du point.',
                    'left_after': u'{0} quitte la séance après la discussion du point.',
                    'entered_after': u'{0} entre en séance après la discussion du point.',
                    'non_attendee_before': u'{0} ne participe plus à la séance avant la discussion du point.',
                    'attendee_again_before': u'{0} participe à la séance avant la discussion du point.',
                    'non_attendee_after': u'{0} ne participe plus à la séance après la discussion du point.',
                    'attendee_again_after': u'{0} participe à la séance après la discussion du point.'}
        patterns.update(custom_patterns)

        meeting = self.context.getMeeting()
        context_uid = self.context.UID()
        in_and_out = self.context.get_in_and_out_attendees(
            ignore_before_first_item=ignore_before_first_item)
        person_res = {in_and_out_type: [] for in_and_out_type in in_and_out.keys()
                      if (not in_and_out_types or in_and_out_type in in_and_out_types)}
        for in_and_out_type, held_positions in in_and_out.items():
            for held_position in held_positions:
                forced_position_type_value = meeting.get_attendee_position_for(
                    context_uid, held_position.UID())
                if include_hp:
                    person_short_title = held_position.get_short_title(
                        include_sub_organizations=False,
                        include_person_title=include_person_title,
                        abbreviate_firstname=abbreviate_firstname,
                        forced_position_type_value=forced_position_type_value)
                else:
                    person_short_title = held_position.get_person_short_title(
                        include_person_title=include_person_title,
                        abbreviate_firstname=abbreviate_firstname,
                        forced_position_type_value=forced_position_type_value)
                person_res[in_and_out_type].append(person_short_title)

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
            anonymize=True,
            image_src_to_paths=False,
            image_src_to_data=True,
            use_appy_pod_preprocessor=True,
            **kwargs)

    def print_public_deliberation(self, xhtmlContents=[], **kwargs):
        '''Overridable method to return public deliberation.'''
        return self.print_deliberation(xhtmlContents, **kwargs)

    def print_public_deliberation_decided(self, xhtmlContents=[], **kwargs):
        '''Overridable method to return public deliberation when decided.'''
        return self.print_deliberation(xhtmlContents, **kwargs)


class AdviceDocumentGenerationHelperView(DXDocumentGenerationHelperView, BaseDGHV):
    """ """


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
        cfg_suffixes = get_item_validation_wf_suffixes(cfg)
        suffixes = [suffix for suffix in suffixes if suffix in cfg_suffixes]
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
        super(MeetingStoreItemsPodTemplateAsAnnexBatchActionForm, self).__init__(
            context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        if self.cfg.getMeetingItemTemplatesToStoreAsAnnex() and \
           _checkPermission(ModifyPortalContent, self.context):
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
        """Only available to Managers."""
        return _checkPermission(ManagePortal, self.context)

    def _apply(self, **data):
        """ """
        uids = listify_uids(data['uids'])
        self.tool.update_all_local_roles(**{'UID': uids, 'log': False})
        msg = translate('update_selected_elements',
                        domain="PloneMeeting",
                        mapping={'number_of_elements': len(uids)},
                        context=self.request,
                        default="Updated accesses for ${number_of_elements} element(s).")
        api.portal.show_message(msg, request=self.request)


class PMDeleteBatchActionForm(DeleteBatchActionForm):
    """ """

    section = "annexes"

    def __init__(self, context, request):
        super(PMDeleteBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        return "delete" in self.cfg.getEnabledAnnexesBatchActions() and \
               _checkPermission(ModifyPortalContent, self.context)

    def _get_deletable_elements(self):
        """Get deeltable elements using IContentDeletable."""
        deletables = [obj for obj in self.objs
                      if IContentDeletable(obj).mayDelete()]
        return deletables


class PMDownloadAnnexesBatchActionForm(DownloadAnnexesBatchActionForm):
    """ """

    def __init__(self, context, request):
        super(PMDownloadAnnexesBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        return "download-annexes" in self.cfg.getEnabledAnnexesBatchActions()


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
        current_url = self.request['URL']
        for config_info in grouped_configs.values()[0]:
            cfg_id = config_info['id']
            cfg = getattr(tool, cfg_id)
            css_class = ""
            if "/mymeetings/%s/" % cfg_id in current_url or \
               "/portal_plonemeeting/%s/" % cfg_id in current_url:
                css_class = "fa selected"
            res.append(
                {'config': cfg,
                 'url': tool.getPloneMeetingFolder(cfg_id).absolute_url() + '/searches_items',
                 'css_class': css_class})
        # make sure 'content-type' header of response is correct because during
        # faceted initialization, 'content-type' is turned to 'text/xml' and it
        # breaks to tooltipster displaying the result in the tooltip...
        self.request.RESPONSE.setHeader('content-type', 'text/html')
        return res


class DisplayMeetingItemRedefinedPosition(BrowserView):
    """This view will display the items a given attendee position was redefined for."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        # this view is called on meeting or item
        self.meeting = IMeeting.providedBy(self.context) and \
            self.context or self.context.getMeeting()

    def __call__(self, attendee_uid):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.attendee_uid = attendee_uid
        self.attendee = uuidToObject(attendee_uid, unrestricted=True)
        return self.index()

    def get_items_for_redefined_position(self):
        """Returns the list of items the attendee_uid position was redefined for."""
        item_uids = []
        redefined_positions = self.meeting._get_item_redefined_positions()
        for item_uid, infos in redefined_positions.items():
            if self.attendee_uid in infos:
                item_uids.append(item_uid)
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(UID=item_uids, sort_on='getItemNumber')
        objs = [brain.getObject() for brain in brains]
        return objs


class DisplayMeetingItemNotPresent(BrowserView):
    """This view will display the items a given attendee was defined
       as not present for (absent/excused)."""

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
            item_uids = self.meeting.get_item_absents(by_persons=True).get(self.not_present_uid, [])
        elif self.not_present_type == 'excused':
            item_uids = self.meeting.get_item_excused(by_persons=True).get(self.not_present_uid, [])
        elif self.not_present_type == 'non_attendee':
            item_uids = self.meeting.get_item_non_attendees(by_persons=True).get(self.not_present_uid, [])
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

    def get_items_for_signatory(self):
        """Returns the list of items the signatory_uid is signatory for."""
        item_uids = self.meeting.get_item_signatories(by_signatories=True).get(self.signatory_uid, [])
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(UID=item_uids, sort_on='getItemNumber')
        objs = [brain.getObject() for brain in brains]
        return objs


class DisplayMeetingItemVoters(BrowserView):
    """This view will display the items a given voter did not vote for."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, show_voted_items=False):
        """ """
        self.show_voted_items = show_voted_items
        return self.index()

    def getNonVotedItems(self):
        """Returns the list of items the voter_uid did not vote for."""
        items = self.context.get_items(ordered=True)
        res = {'public': [],
               'secret': []}
        for item in items:
            if not item.get_votes_are_secret():
                if set(item.get_item_voters()).difference(item.get_voted_voters()):
                    res['public'].append(item)
            else:
                data = {}
                total_voters = item.getVoteCount('any_votable')
                for item_vote in item.get_item_votes():
                    vote_number = item_vote['vote_number']
                    i = vote_number
                    linked_numbers = _get_linked_item_vote_numbers(
                        item, self.context, vote_number=vote_number)
                    # aggregate linked votes to original one
                    if linked_numbers:
                        i = min(linked_numbers)
                    if i not in data:
                        data[i] = 0
                    vote_count = item.getVoteCount('any_voted', vote_number=vote_number)
                    data[i] += vote_count
                # now if we have an element in res < total_voters, we miss some votes
                for count in data.values():
                    if count < total_voters:
                        res['secret'].append(item)
                        break
        return res

    def getVotedItems(self):
        """ """
        non_voted_items = self.getNonVotedItems()
        items = self.context.get_items(ordered=True)
        res = {
            'public': [
                item for item in items
                if item not in non_voted_items['public'] and not item.get_votes_are_secret()],
            'secret': [
                item for item in items
                if item not in non_voted_items['secret'] and item.get_votes_are_secret()]}
        return res


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


class RenderSingleWidgetView(BrowserView):
    """ """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, field_name, mode=DISPLAY_MODE):
        """ """
        self.field_name = field_name
        self.mode = mode
        widget = get_dx_widget(self.context, field_name, mode)
        rendered = widget.render()
        return rendered
