# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 by Imio.be
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

from collections import OrderedDict
from collective.contact.core.utils import get_gender_and_number
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from collective.documentgenerator.helper.dexterity import DXDocumentGenerationHelperView
from collective.eeafaceted.batchactions import _ as _CEBA
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from eea.facetednavigation.browser.app.view import FacetedContainerView
from eea.facetednavigation.interfaces import ICriteria
from ftw.labels.interfaces import ILabeling
from imio.helpers.xhtml import addClassToContent
from imio.helpers.xhtml import CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT
from imio.helpers.xhtml import imagesToPath
from plone import api
from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless
from Products.CMFCore.permissions import ModifyPortalContent
from Products.Five import BrowserView
from Products.PloneMeeting import logger
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import ITEM_SCAN_ID_NAME
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.indexes import _to_coded_adviser_index
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import signatureNotAlone
from Products.PloneMeeting.utils import toHTMLStrikedContent
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

    def __call__(self, visibleColumns):
        """ """
        self.visibleColumns = visibleColumns
        return super(ItemMoreInfosView, self).__call__()

    @memoize_contextless
    def getItemsListVisibleFields(self):
        """ """
        visibleFields = self.cfg.getItemsListVisibleFields()
        # keep order of displayed fields
        res = OrderedDict()
        for visibleField in visibleFields:
            visibleFieldName = visibleField.split('.')[1]
            # if nothing is defined, the default rendering macro will be used
            # this is made to be overrided
            res[visibleFieldName] = self._rendererForField(visibleFieldName)
        return res

    def _rendererForField(self, fieldName):
        """Return the renderer to use for given p_fieldName, this returns nothing
           by default and is made to be overrided by subproduct."""
        return None

    @memoize_contextless
    def showMoreInfos(self):
        """ """
        return self.request.cookies.get('pmShowDescriptions', 'false') == 'true' and True or False


class ItemStaticInfosView(BrowserView):
    """
      This manage the view displaying static infos about an item in the PrettyLink column
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, visibleColumns):
        """ """
        self.visibleColumns = visibleColumns
        return super(ItemStaticInfosView, self).__call__()

    @property
    def active_labels(self):
        return ILabeling(self.context).active_labels()


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
                availableTransitions = wfTool.getTransitionsFor(obj)
                if not availableTransitions or not changedState:
                    break
                changedState = False
                for tr in availableTransitions:
                    if tr['id'].startswith('back'):
                        wfTool.doActionFor(obj, tr['id'])
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

    def mayChangeOrder(self):
        """ """
        return self.context.getMeeting().wfConditions().mayChangeItemsOrder()

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

    def mayEdit(self):
        """ """
        member = api.user.get_current()
        toDiscuss_write_perm = self.context.getField('toDiscuss').write_permission
        return member.has_permission(toDiscuss_write_perm, self.context) and \
            self.context.showToDiscuss()

    @memoize_contextless
    def userIsReviewer(self):
        """ """
        return self.tool.userIsAmong(['reviewers'])

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

    def __call__(self):
        """ """
        # initialize member in call because it is Anonymous in __init__ of view...
        self.member = api.user.get_current()
        return super(MeetingView, self).__call__()

    def showPage(self):
        """Display page to current user?"""
        return self.tool.showMeetingView()

    def showAvailableItems(self):
        """Show the available items part?"""
        return self.member.has_permission(ModifyPortalContent, self.context) and \
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


class MeetingInsertingMethodsHelpMsgView(BrowserView):
    """ """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def showSelectablePrivaciesField(self):
        """In case we use the 'on_privacy' inserting method, it relies on the
           order of selectablePrivacies and we will show the information."""
        inserting_methods = [
            method['insertingMethod']
            for method in self.cfg.getInsertingMethodsOnAddItem()]
        if 'on_privacy' in inserting_methods:
            return True
        return False


class MeetingUpdateItemReferences(BrowserView):
    """Call Meeting.updateItemReferences from a meeting."""

    def index(self):
        """ """
        self.context.updateItemReferences()
        msg = _('References of contained items have been updated.')
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
    def __call__(self, itemNumber):
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
        tool = api.portal.get_tool('portal_plonemeeting')
        # compute the indexAdvisers index, take every groups, including disabled ones
        # then constuct every possibles cases, by default there is 2 possible values :
        # delay__groupId1__advice_not_given, delay__groupId1__advice_under_edit
        # delay__groupId2__advice_not_given, delay__groupId2__advice_under_edit
        # ...
        meetingGroups = tool.getMeetingGroups(onlyActive=False)
        groupIds = [meetingGroup.getId() for meetingGroup in meetingGroups]
        indexAdvisers = []
        for groupId in groupIds:
            # advice giveable but not given
            indexAdvisers.append("delay__%s_advice_not_given" % groupId)
            # now advice given and still editable
            for advice_state in ADVICE_STATES_ALIVE:
                indexAdvisers.append("delay__%s_%s" % (groupId, advice_state))
        query = {}
        query['indexAdvisers'] = indexAdvisers
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
        for brain in brains:
            item = brain.getObject()
            logger.info('%d/%d Updating adviceIndex of item at %s' % (i,
                                                                      numberOfBrains,
                                                                      '/'.join(item.getPhysicalPath())))
            i = i + 1
            item.updateLocalRoles()


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

        manager = getUtility(IPortletManager,
                             name='plone.leftcolumn',
                             context=self.context)
        # we use IPortletManagerRenderer so parameters
        # batch_size and title_length are taken into account
        renderer = queryMultiAdapter(
            (self.context, self.request, self, manager), IPortletManagerRenderer)

        for portlet in renderer.portletsToShow():
            if portlet['name'] == 'portlet_todo':
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
                   use_safe_html=True):
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
                        tree = lxml.html.fromstring(unicode(preparedXhtmlContent, 'utf-8'))
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
        if image_src_to_paths:
            xhtmlFinal = imagesToPath(context, xhtmlFinal)

        # manage keepWithNext
        if keepWithNext:
            xhtmlFinal = signatureNotAlone(xhtmlFinal, numberOfChars=keepWithNextNumberOfChars)

        # manage addCSSClass
        if addCSSClass:
            xhtmlFinal = addClassToContent(xhtmlFinal, addCSSClass)

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

    def printAdvicesInfos(self,
                          item,
                          withAdvicesTitle=True,
                          withDelay=False,
                          withDelayLabel=True,
                          withAuthor=True):
        '''Helper method to have a printable version of advices.'''
        itemAdvicesByType = item.getAdvicesByType()
        res = ""
        if withAdvicesTitle:
            res += "<p class='pmAdvices'><u><b>%s :</b></u></p>" % \
                translate('PloneMeeting_label_advices',
                          domain='PloneMeeting',
                          context=self.request)
        for adviceType in itemAdvicesByType:
            for advice in itemAdvicesByType[adviceType]:
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
                                                         unicode(advice['delay_label'], 'utf-8'))
                        else:
                            delayAwareMsg = "%s" % unicode(advice['delay_label'], 'utf-8')
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
                                                                  cgi.escape(unicode(author, 'utf-8')), )

                    adviceComment = 'comment' in advice and self.printXhtml(adviceObj, advice['comment']) or '-'
                    res = res + (u"<br /><u>%s :</u> %s<p></p>" % (translate('Advice comment',
                                                                             domain='PloneMeeting',
                                                                             context=self.request),
                                                                   unicode(adviceComment, 'utf-8')))
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
        # make the 'item_scan_id' value available in the REQUEST
        self.request.set(ITEM_SCAN_ID_NAME, scan_id)
        return scan_id

    def printFullname(self, user_id):
        """ """
        user = api.user.get(user_id)
        return user and user.getProperty('fullname') or user_id

    def printAssembly(self, striked=True):
        '''Returns the assembly for this meeting or item.
           If p_striked is True, return striked assembly.'''
        if self.context.meta_type == 'Meeting':
            res = self.context.getAssembly()
        else:
            res = self.context.getItemAssembly()
        if striked:
            res = toHTMLStrikedContent(res)
        return res

    def _get_attendees(self):
        """ """
        if self.context.meta_type == 'Meeting':
            meeting = self.context
            attendees = meeting.getAttendees()
            item_absents = []
        else:
            # MeetingItem
            meeting = self.context.getMeeting()
            attendees = self.context.getAttendees()
            item_absents = self.context.getItemAbsents()
        # generate content then group by sub organization if necessary
        contacts = meeting.getAllUsedHeldPositions()
        excused = meeting.getExcused()
        absents = meeting.getAbsents()
        lateAttendees = meeting.getLateAttendees()
        replaced = meeting.getReplacements()
        return meeting, attendees, item_absents, contacts, excused, absents, lateAttendees, replaced

    def printAttendees(self,
                       groupByAttendeeType=False,
                       groupByParentOrg=False,
                       render_as_html=True,
                       attendee_value_format=u"{0}, {1}",
                       attendee_type_format=u"<strong>{0}</strong>",
                       custom_attendee_type_values={},
                       custom_grouped_attendee_type_patterns={},
                       show_replaced_by=True,
                       replaced_by_format={'M': u'<strong>remplacé par {0}</strong>',
                                           'F': u'<strong>remplacée par {0}</strong>'},
                       include_replace_by_held_position_label=True):
        """ """

        def _render_as_html(tree, groupByParentOrg=False):
            """ """
            res = []
            for org, contact_infos in tree.items():
                if groupByParentOrg:
                    res.append(u"<strong><u>{0}</u></strong>".format(org.title))
                for contact_value in contact_infos.values():
                    res.append(contact_value)
            return u'<br />'.join(res)

        attendee_type_values = {'attendee': {'M': u'présent', 'F': u'présente'},
                                'excused': {'M': u'excusé', 'F': u'excusée'},
                                'absent': {'M': u'absent', 'F': u'absente'},
                                'replaced': {'M': u'remplacé', 'F': u'remplacée'},
                                'late_attendee': {'M': u'présent en retard', 'F': u'présente en retard'},
                                'item_absent': {'M': u'absent pour ce point', 'F': u'absente pour ce point'}}
        attendee_type_values.update(custom_attendee_type_values)

        # initial values
        meeting, attendees, item_absents, contacts, excused, absents, lateAttendees, replaced = self._get_attendees()

        res = OrderedDict()
        for contact in contacts:
            res[contact] = contact.get_short_title(include_sub_organizations=False)

        # manage group by sub organization
        if groupByParentOrg:
            by_suborg_res = OrderedDict()
            for contact, contact_short_title in res.items():
                orga = contact.get_organization()
                if orga not in by_suborg_res:
                    by_suborg_res[orga] = OrderedDict()
                by_suborg_res[orga][contact] = contact_short_title
            res = by_suborg_res
        else:
            # get same format for rest of the treatment
            res = OrderedDict({self.portal.contacts.get(PLONEGROUP_ORG):
                               OrderedDict(res.items())})

        # append presence to end of value
        for orga, contact_infos in res.items():
            for contact, contact_value in contact_infos.items():
                contact_uid = contact.UID()
                contact_gender = contact.gender or 'M'
                if contact_uid in attendees:
                    res[orga][contact] = attendee_value_format.format(
                        res[orga][contact],
                        attendee_type_format.format(attendee_type_values['attendee'][contact_gender]))
                elif contact_uid in excused and contact_uid not in replaced:
                    res[orga][contact] = attendee_value_format.format(
                        res[orga][contact],
                        attendee_type_format.format(attendee_type_values['excused'][contact_gender]))
                elif contact_uid in absents and contact_uid not in replaced:
                    res[orga][contact] = attendee_value_format.format(
                        res[orga][contact],
                        attendee_type_format.format(attendee_type_values['absent'][contact_gender]))
                elif contact_uid in lateAttendees:
                    res[orga][contact] = attendee_value_format.format(
                        res[orga][contact],
                        attendee_type_format.format(attendee_type_values['late_attendee'][contact_gender]))
                elif contact_uid in item_absents:
                    res[orga][contact] = attendee_value_format.format(
                        res[orga][contact],
                        attendee_type_format.format(attendee_type_values['item_absent'][contact_gender]))
                elif contact_uid in replaced:
                    if show_replaced_by:
                        res[orga][contact] = attendee_value_format.format(
                            res[orga][contact], replaced_by_format[contact_gender].format(
                                meeting.displayUserReplacement(
                                    replaced[contact_uid],
                                    include_held_position_label=include_replace_by_held_position_label,
                                    include_sub_organizations=False)))
                    else:
                        res[contact_uid][1] = attendee_value_format.format(
                            res[contact_uid][1],
                            attendee_type_format.format(attendee_type_values['replaced'][contact_gender]))

        if render_as_html:
            res = _render_as_html(res, groupByParentOrg=groupByParentOrg)
        return res

    def printAttendeesByType(self,
                             groupByParentOrg=False,
                             groupByPositionType=False,
                             pos_attendee_separator=', ',
                             single_pos_attendee_ender=';',
                             render_as_html=True,
                             position_type_format=u", {0};",
                             custom_grouped_attendee_type_patterns={},
                             show_replaced_by=True,
                             replaced_by_format={'M': u'<strong>remplacé par {0}</strong>',
                                                 'F': u'<strong>remplacée par {0}</strong>'},
                             include_replace_by_held_position_label=True,
                             ignored_pos_type_ids=['default'],
                             include_person_title=True,
                             included_attendee_types=['attendee', 'excused', 'absent',
                                                      'replaced', 'late_attendee', 'item_absent'],
                             striked_attendee_types=['excused'],
                             striked_attendee_pattern=u'<strike>{0}</strike>'):

        def _render_as_html(tree, groupByParentOrg=False, groupByPositionType=False):
            """ """
            res = []
            for attendee_type, global_contact_infos in tree.items():
                every_contacts = []
                sub_res = []
                for org, contact_infos in global_contact_infos.items():
                    if groupByParentOrg:
                        sub_res.append(u"<strong><u>{0}</u></strong>".format(org.title))
                    if groupByPositionType:
                        for position_type, contacts in contact_infos.items():
                            every_contacts.extend(contacts)
                            position_type_value = u''
                            if not position_type.startswith('__no_position_type__'):
                                gn = get_gender_and_number(contacts)
                                position_type_value = contacts[0].gender_and_number_from_position_type()[gn]
                            grouped_contacts_value = []
                            for contact in contacts:
                                if position_type_value:
                                    contact_value = contact.get_person_short_title(include_person_title=include_person_title)
                                else:
                                    contact_value = contact.get_short_title(include_sub_organizations=False)
                                if contact.UID() in striked_contact_uids:
                                    contact_value = striked_attendee_pattern.format(contact_value)
                                grouped_contacts_value.append(contact_value)
                            grouped_contacts_value = pos_attendee_separator.join(grouped_contacts_value)
                            if position_type_value:
                                grouped_contacts_value = grouped_contacts_value + position_type_format.format(
                                    position_type_value)
                            else:
                                grouped_contacts_value = grouped_contacts_value + single_pos_attendee_ender
                            sub_res.append(grouped_contacts_value)
                    else:
                        grouped_contacts_value = pos_attendee_separator.join(
                            [contact.get_short_title(include_sub_organizations=False)
                             for contact in contact_infos]) + single_pos_attendee_ender
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

        grouped_attendee_type_patterns = {
             'attendee': {'MS': u'<strong><u>Présent&nbsp;:</u></strong>',
                          'MP': u'<strong><u>Présents&nbsp;:</u></strong>',
                          'FS': u'<strong><u>Présente&nbsp;:</u></strong>',
                          'FP': u'<strong><u>Présentes&nbsp;:</u></strong>',
                          '*':  u'<strong><u>Présents&nbsp;:</u></strong>'},
             'excused': {'MS': u'<strong><u>Excusé&nbsp;:</u></strong>',
                         'MP': u'<strong><u>Excusés&nbsp;:</u></strong>',
                         'FS': u'<strong><u>Excusée&nbsp;:</u></strong>',
                         'FP': u'<strong><u>Excusées&nbsp;:</u></strong>',
                         '*':  u'<strong><u>Excusés&nbsp;:</u></strong>'},
             'absent': {'MS': u'<strong><u>Absent&nbsp;:</u></strong>',
                        'MP': u'<strong><u>Absents&nbsp;:</u></strong>',
                        'FS': u'<strong><u>Absente&nbsp;:</u></strong>',
                        'FP': u'<strong><u>Absentes&nbsp;:</u></strong>',
                        '*':  u'<strong><u>Absents&nbsp;:</u></strong>'},
             'replaced': {'MS': u'<strong><u>Remplacé&nbsp;:</u></strong>',
                          'MP': u'<strong><u>Remplacés&nbsp;:</u></strong>',
                          'FS': u'<strong><u>Remplacée&nbsp;:</u></strong>',
                          'FP': u'<strong><u>Remplacées&nbsp;:</u></strong>',
                          '*':  u'<strong><u>Remplacés&nbsp;:</u></strong>'},
             'late_attendee': {'MS': u'<strong><u>Présent en retard&nbsp;:</u></strong>',
                               'MP': u'<strong><u>Présents en retard&nbsp;:</u></strong>',
                               'FS': u'<strong><u>Présente en retard&nbsp;:</u></strong>',
                               'FP': u'<strong><u>Présentes en retard&nbsp;:</u></strong>',
                               '*':  u'<strong><u>Présents en retard&nbsp;:</u></strong>'},
             'item_absent': {'MS': u'<strong><u>Absent pour ce point&nbsp;:</u></strong>',
                             'MP': u'<strong><u>Absents pour ce point&nbsp;:</u></strong>',
                             'FS': u'<strong><u>Absente pour ce point&nbsp;:</u></strong>',
                             'FP': u'<strong><u>Absentes pour ce point&nbsp;:</u></strong>',
                             '*':  u'<strong><u>Absents pour ce point&nbsp;:</u></strong>'},
        }
        grouped_attendee_type_patterns.update(custom_grouped_attendee_type_patterns)

        # initial values
        meeting, attendees, item_absents, contacts, excused, absents, lateAttendees, replaced = self._get_attendees()

        res = OrderedDict({key: [] for key in grouped_attendee_type_patterns.keys()})
        striked_contact_uids = []
        for contact in contacts:
            contact_uid = contact.UID()
            contact_attendee_type = contact_uid in item_absents and 'item_absent' or \
                contact_uid in attendees and 'attendee' or \
                contact_uid in excused and 'excused' or \
                contact_uid in absents and 'absent' or \
                contact_uid in lateAttendees and 'late_attendee' or \
                contact_uid in replaced and 'replaced'
            if (contact_attendee_type == 'attendee' or contact_attendee_type in striked_attendee_types) and \
                    'attendee' in included_attendee_types:
                if contact_attendee_type in striked_attendee_types:
                    striked_contact_uids.append(contact.UID())
                res['attendee'].append(contact)
            elif contact_attendee_type in included_attendee_types and \
                    contact_attendee_type not in striked_attendee_types:
                res[contact_attendee_type].append(contact)

        # manage groupByParentOrg
        # if used or not, we output the same format to continue process easier
        for attendee_type, contacts in res.items():
            by_suborg_res = OrderedDict()
            for contact in contacts:
                # include orga to have same format when using groupByParentOrg or not
                orga = groupByParentOrg and contact.get_organization() or self.portal.contacts.get(PLONEGROUP_ORG)
                if orga not in by_suborg_res:
                    by_suborg_res[orga] = []
                by_suborg_res[orga].append(contact)
            res[attendee_type] = by_suborg_res

        if groupByPositionType:
            for attendee_type, contact_infos in res.items():
                for orga, contacts in contact_infos.items():
                    by_pos_type_res = OrderedDict()
                    for contact in contacts:
                        used_contact_position_type = contact.position_type
                        if contact.position_type in ignored_pos_type_ids:
                            # in this case, we use the special value prefixed by __no_position_type__
                            # so contacts are still ordered
                            used_contact_position_type = '__no_position_type__{0}'.format(contact.UID())
                            by_pos_type_res[used_contact_position_type] = []
                        elif contact.position_type not in by_pos_type_res:
                            by_pos_type_res[used_contact_position_type] = []
                        by_pos_type_res[used_contact_position_type].append(contact)
                    res[attendee_type][orga] = by_pos_type_res

        if render_as_html:
            res = _render_as_html(res, groupByParentOrg=groupByParentOrg, groupByPositionType=groupByPositionType)
        return res


    def printAttendeesWithStrikedByType(self,
                             groupByParentOrg=False,
                             groupByPositionType=False,
                             pos_attendee_separator=', ',
                             single_pos_attendee_ender=';',
                             render_as_html=True,
                             position_type_format=u", {0};",
                             custom_grouped_attendee_type_patterns={},
                             show_replaced_by=True,
                             replaced_by_format={'M': u'<strong>remplacé par {0}</strong>',
                                                 'F': u'<strong>remplacée par {0}</strong>'},
                             include_replace_by_held_position_label=True,
                             ignored_pos_type_ids=['default'],
                             include_person_title=True):

        def _render_as_html(tree, groupByParentOrg=False, groupByPositionType=False):
            """ """
            res = []
            for attendee_type, global_contact_infos in tree.items():
                every_contacts = []
                sub_res = []
                for org, contact_infos in global_contact_infos.items():
                    if groupByParentOrg:
                        sub_res.append(u"<strong><u>{0}</u></strong>".format(org.title))
                    if groupByPositionType:
                        for position_type, contacts in contact_infos.items():
                            every_contacts.extend(contacts)
                            position_type_value = u''
                            if not position_type.startswith('__no_position_type__'):
                                gn = get_gender_and_number(contacts)
                                position_type_value = contacts[0].gender_and_number_from_position_type()[gn]
                            grouped_contacts_value = pos_attendee_separator.join(
                                [position_type_value and contact.get_person_short_title(include_person_title=include_person_title)
                                 or contact.get_short_title(include_sub_organizations=False) for contact in contacts])
                            if position_type_value:
                                grouped_contacts_value = grouped_contacts_value + position_type_format.format(
                                    position_type_value)
                            else:
                                grouped_contacts_value = grouped_contacts_value + single_pos_attendee_ender
                            sub_res.append(grouped_contacts_value)
                    else:
                        grouped_contacts_value = pos_attendee_separator.join(
                            [contact.get_short_title(include_sub_organizations=False) for contact in contact_infos]) + single_pos_attendee_ender
                        every_contacts.extend(contact_infos)
                        sub_res.append(grouped_contacts_value)
                if every_contacts:
                    gn = get_gender_and_number(every_contacts)
                    res.append(grouped_attendee_type_patterns[attendee_type][gn])
                    res.extend(sub_res)
            return u'<br />'.join(res)

        grouped_attendee_type_patterns = {
             'attendee': {'MS': u'<strong><u>Présent&nbsp;:</u></strong>',
                          'MP': u'<strong><u>Présents&nbsp;:</u></strong>',
                          'FS': u'<strong><u>Présente&nbsp;:</u></strong>',
                          'FP': u'<strong><u>Présentes&nbsp;:</u></strong>'},
             'excused': {'MS': u'<strong><u>Excusé&nbsp;:</u></strong>',
                         'MP': u'<strong><u>Excusés&nbsp;:</u></strong>',
                         'FS': u'<strong><u>Excusée&nbsp;:</u></strong>',
                         'FP': u'<strong><u>Excusées&nbsp;:</u></strong>'},
             'absent': {'MS': u'<strong><u>Absent&nbsp;:</u></strong>',
                        'MP': u'<strong><u>Absents&nbsp;:</u></strong>',
                        'FS': u'<strong><u>Absente&nbsp;:</u></strong>',
                        'FP': u'<strong><u>Absentes&nbsp;:</u></strong>'},
             'replaced': {'MS': u'<strong><u>Remplacé&nbsp;:</u></strong>',
                          'MP': u'<strong><u>Remplacés&nbsp;:</u></strong>',
                          'FS': u'<strong><u>Remplacée&nbsp;:</u></strong>',
                          'FP': u'<strong><u>Remplacées&nbsp;:</u></strong>'},
             'late_attendee': {'MS': u'<strong><u>Présent en retard&nbsp;:</u></strong>',
                               'MP': u'<strong><u>Présents en retard&nbsp;:</u></strong>',
                               'FS': u'<strong><u>Présente en retard&nbsp;:</u></strong>',
                               'FP': u'<strong><u>Présentes en retard&nbsp;:</u></strong>'},
             'item_absent': {'MS': u'<strong><u>Absent pour ce point&nbsp;:</u></strong>',
                             'MP': u'<strong><u>Absents pour ce point&nbsp;:</u></strong>',
                             'FS': u'<strong><u>Absente pour ce point&nbsp;:</u></strong>',
                             'FP': u'<strong><u>Absentes pour ce point&nbsp;:</u></strong>'},
        }
        grouped_attendee_type_patterns.update(custom_grouped_attendee_type_patterns)

        # initial values
        meeting, attendees, item_absents, contacts, excused, absents, lateAttendees, replaced = self._get_attendees()

        res = OrderedDict({key: [] for key in grouped_attendee_type_patterns.keys()})
        for contact in contacts:
            contact_uid = contact.UID()
            if contact_uid in item_absents:
                res['item_absent'].append(contact)
            elif contact_uid in attendees:
                res['attendee'].append(contact)
            elif contact_uid in excused:
                res['excused'].append(contact)
            elif contact_uid in absents:
                res['absent'].append(contact)
            elif contact_uid in lateAttendees:
                res['late_attendee'].append(contact)
            elif contact_uid in replaced:
                res['replaced'].append(contact)

        # manage groupByParentOrg
        # if used or not, we output the same format to continue process easier
        for attendee_type, contacts in res.items():
            by_suborg_res = OrderedDict()
            for contact in contacts:
                # include orga to have same format when using groupByParentOrg or not
                orga = groupByParentOrg and contact.get_organization() or self.portal.contacts.get(PLONEGROUP_ORG)
                if orga not in by_suborg_res:
                    by_suborg_res[orga] = []
                by_suborg_res[orga].append(contact)
            res[attendee_type] = by_suborg_res

        if groupByPositionType:
            for attendee_type, contact_infos in res.items():
                for orga, contacts in contact_infos.items():
                    by_pos_type_res = OrderedDict()
                    for contact in contacts:
                        used_contact_position_type = contact.position_type
                        if contact.position_type in ignored_pos_type_ids:
                            # in this case, we use the special value prefixed by __no_position_type__
                            # so contacts are still ordered
                            used_contact_position_type = '__no_position_type__{0}'.format(contact.UID())
                            by_pos_type_res[used_contact_position_type] = []
                        elif contact.position_type not in by_pos_type_res:
                            by_pos_type_res[used_contact_position_type] = []
                        by_pos_type_res[used_contact_position_type].append(contact)
                    res[attendee_type][orga] = by_pos_type_res

        if render_as_html:
            res = _render_as_html(res, groupByParentOrg=groupByParentOrg, groupByPositionType=groupByPositionType)
        return res


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
                for groupId, advice in item.adviceIndex.iteritems():
                    if adviser in _to_coded_adviser_index(item, groupId, advice):
                        # we must keep this adviser
                        advisers_data.append(item.getAdviceDataFor(item, groupId))
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

    def get_all_items_dghv_with_advice(self, brains, adviserIds=[]):
        """
        :param brains: the brains collection representing @Product.PloneMeeting.MeetingItem
        :param adviserIds : list of adviser Ids to keep. By default it empty. Which means all advisers are kept.
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
            if adviserIds:
                itemInserted = False
                for adviserId in adviserIds:
                    advice = item.getAdviceDataFor(item, adviserId)
                    if advice:
                        res.append({'itemView': self.getDGHV(item), 'advice': advice})
                        itemInserted = True
                if not itemInserted:
                    res.append({'itemView': self.getDGHV(item), 'advice': None})
            else:
                advices = item.getAdviceDataFor(item)
                if advices:
                    for advice in advices:
                        res.append({'itemView': self.getDGHV(item), 'advice': advices[advice]})
                else:
                    res.append({'itemView': self.getDGHV(item), 'advice': None})
        return res


class MeetingDocumentGenerationHelperView(FolderDocumentGenerationHelperView):
    """ """


class ItemDocumentGenerationHelperView(ATDocumentGenerationHelperView, BaseDGHV):
    """ """

    def printMeetingDate(self, returnDateTime=False, noMeetingMarker='-'):
        """Print meeting date, manage fact that item is not linked to a meeting,
           in this case p_noMeetingMarker is returned.
           If p_returnDateTime is True, it returns the meeting date DateTime,
           otherwise it returns the meeting title containing formatted date."""
        meeting = self.context.getMeeting()
        if meeting:
            if returnDateTime:
                return meeting.getDate()
            return meeting.Title()
        else:
            return noMeetingMarker


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
        messages['clean'] = []

        for pod_template in self.cfg.podtemplates.objectValues():

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
                view = obj.restrictedTraverse('@@document-generation')
                self.request.set('template_uid', pod_template.UID())
                self.request.set('output_format', pod_template.pod_formats[0])
                view()
                try:
                    view()
                    view._render_document(pod_template,
                                          output_format='odt',
                                          sub_documents=[],
                                          raiseOnError=True)
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


class DisplayGroupUsersView(BrowserView):
    """
      View that display the users of a Plone group.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, group_id):
        """ """
        # manage auto groups
        self.group_id = group_id
        self.group = api.group.get(group_id)
        return self.index()

    def group_title(self):
        """ """
        return self.group.getProperty('title')

    def group_users(self):
        """ """
        res = []
        for member in self.group.getAllGroupMembers():
            res.append(member.getProperty('fullname') or member.getId())
        res.sort()
        return "<br />".join(res)


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
        if self.cfg.getMeetingItemTemplateToStoreAsAnnex() and \
           api.user.get_current().has_permission(ModifyPortalContent, self.context):
            return True

    def _apply(self, **data):
        """ """
        template_id, output_format = \
            self.cfg.getMeetingItemTemplateToStoreAsAnnex().split('__output_format__')
        pod_template = getattr(self.cfg.podtemplates, template_id)

        num_of_generated_templates = 0
        for brain in self.brains:
            item = brain.getObject()
            generation_view = item.restrictedTraverse('@@document-generation')
            generated_template = generation_view(template_uid=pod_template.UID(),
                                                 output_format=output_format)
            res = generation_view.storePodTemplateAsAnnex(
                generated_template,
                pod_template,
                output_format,
                return_portal_msg_code=True)
            if not res:
                num_of_generated_templates += 1
                logger.info(
                    'Generated POD template {0} using output format {1} for item at {2}'.format(
                        template_id, output_format, '/'.join(item.getPhysicalPath())))
            else:
                # print error code
                msg = translate(msgid=res, domain='PloneMeeting', context=self.request)
                logger.info(u'Could not generate POD template {0} using output format {1} for item at {2} : {3}'.format(
                    template_id, output_format, '/'.join(item.getPhysicalPath()), msg))

        msg = translate('stored_item_template_as_annex',
                        domain="PloneMeeting",
                        mapping={'number_of_annexes': num_of_generated_templates},
                        context=self.request,
                        default="Stored ${number_of_annexes} annexes")
        api.portal.show_message(msg, request=self.request)


class DisplayMeetingConfigsOfConfigGroup(BrowserView):
    """This view will display the MeetingConfigs of a ConfigGroup."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, config_group):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.config_group = config_group
        return self.index()

    def getViewableMeetingConfigs(self):
        """Returns the list of MeetingConfigs the current user has access to."""
        grouped_configs = self.tool.getGroupedConfigs(config_group=self.config_group)
        return [getattr(self.tool, config_info['id']) for config_info in grouped_configs.values()[0]]


class DisplayMeetingItemAbsents(BrowserView):
    """This view will display the items a given absent is absent for."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, absent_uid):
        """ """
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.absent_uid = absent_uid
        return self.index()

    def getAbsentForItems(self):
        """Returns the list of items the absent_uid is absent for."""
        item_uids = self.context.getItemAbsents(by_absents=True).get(self.absent_uid, [])
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog(UID=item_uids, sort_on='getItemNumber')
        objs = [brain.getObject() for brain in brains]
        return objs
