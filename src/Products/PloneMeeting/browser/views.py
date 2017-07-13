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

import cgi
import json
import lxml

from collections import OrderedDict

from zope.component import getMultiAdapter
from zope.i18n import translate

from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless

from Products.Five import BrowserView
from Products.CMFCore.WorkflowCore import WorkflowException
from plone import api
from eea.facetednavigation.interfaces import ICriteria
from collective.documentgenerator.helper.archetypes import ATDocumentGenerationHelperView
from imio.helpers.xhtml import CLASS_TO_LAST_CHILDREN_NUMBER_OF_CHARS_DEFAULT
from imio.helpers.xhtml import addClassToContent
from imio.helpers.xhtml import imagesToPath
from Products.PloneMeeting import logger
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import ADVICE_STATES_ALIVE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.browser.itemchangeorder import _is_integer
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber
from Products.PloneMeeting.utils import signatureNotAlone
from Products.PloneMeeting.indexes import _to_coded_adviser_index


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


class DecideSeveralItemsView(BrowserView):
    """
      This manage the view that devide several items at once in a meeting
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_url = api.portal.get().absolute_url()

    def __call__(self, uids, transition):
        """ """
        uid_catalog = api.portal.get_tool('uid_catalog')
        wfTool = api.portal.get_tool('portal_workflow')
        # make sure we have a list of uids, in some case, as it is called
        # by jQuery, we receive only one uid, as a string...
        if isinstance(uids, str):
            uids = [uids]

        for uid in uids:
            obj = uid_catalog(UID=uid)[0].getObject()
            try:
                wfTool.doActionFor(obj, transition)
            except WorkflowException:
                continue
        msg = translate('decide_several_items_done', domain='PloneMeeting', context=self.request)
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

    def showDecideSeveralItems(self):
        """Show the 'decide several items' widget?"""
        return self.tool.isManager(self.context) and \
            self.context.adapted().isDecided() and \
            self.context.queryState() not in self.context.meetingClosedStates


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
        self.portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = self.portal_state.portal()

    def __call__(self):
        '''
          Add a specific portal_message if we have no active meetingConfig to redirect the connected member to.
        '''
        defaultMeetingConfig = self.defaultMeetingConfig()
        member = api.user.get_current()
        if not self.defaultMeetingConfig() and member.has_role('Manager'):
            plone_utils = api.portal.get_tool('plone_utils')
            plone_utils.addPortalMessage(
                translate('Please specify a default meeting config upon active existing '
                          'meeting configs to be automaatically redirected to it.',
                          domain='PloneMeeting',
                          context=self.request), type='warning')
        # redirect the user to the default meeting config if possible
        if defaultMeetingConfig:
            pmFolder = self.getPloneMeetingTool().getPloneMeetingFolder(defaultMeetingConfig.getId())
            return self.request.RESPONSE.redirect(pmFolder.absolute_url() + "/searches_items")

        return self.index()

    @memoize
    def defaultMeetingConfig(self):
        '''Returns the default MeetingConfig.
           getDefaultMeetingConfig takes care of current member being able to access the MeetingConfig.'''
        return self.getPloneMeetingTool().getDefaultMeetingConfig()

    @memoize
    def getPloneMeetingTool(self):
        '''Returns the tool.'''
        return api.portal.get_tool('portal_plonemeeting')


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


class PMDocumentGenerationHelperView(ATDocumentGenerationHelperView):
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
                   addCSSClass=None):
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
        membershipTool = api.portal.get_tool('portal_membership')
        itemAdvicesByType = item.getAdvicesByType()
        res = ""
        if withAdvicesTitle:
            res += "<p class='pmAdvices'><u><b>%s :</b></u></p>" % translate('PloneMeeting_label_advices',
                                                          domain='PloneMeeting',
                                                          context=self.request)
        for adviceType in itemAdvicesByType:
            for advice in itemAdvicesByType[adviceType]:

                res+="<p class='pmAdvices'>"
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


class FolderDocumentGenerationHelperView(PMDocumentGenerationHelperView):
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

    def get_all_items_dghv_with_single_advice(self, brains):
        """
        :param brains: the brains collection representing @Product.PloneMeeting.MeetingItem
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
            advices = item.getAdviceDataFor(item)
            if advices:
                for advice in advices:
                    res.append({'itemView': self.getDGHV(item), 'advice': advices[advice]})
            else:
                res.append({'itemView': self.getDGHV(item), 'advice': None})

        return res


class MeetingDocumentGenerationHelperView(FolderDocumentGenerationHelperView):
    """ """


class ItemDocumentGenerationHelperView(PMDocumentGenerationHelperView):
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


class AdviceDocumentGenerationHelperView(PMDocumentGenerationHelperView):
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
            if pod_template.meta_type == 'DashboardPODTemplate':
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
                self.request.set('output_format', 'odt')
                try:
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

    def show(self):
        """ """
        return self.tool.showAnnexesTab(self.context)


class AdviceHeaderView(BrowserView):
    """ """


class ItemHeaderView(BrowserView):
    """ """


class MeetingHeaderView(BrowserView):
    """ """
