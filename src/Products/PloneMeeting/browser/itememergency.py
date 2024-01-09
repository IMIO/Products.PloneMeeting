# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.content import get_user_fullname
from imio.history.interfaces import IImioHistory
from imio.history.utils import add_event_to_history
from plone import api
from plone.z3cform.layout import wrap_form
from Products.Archetypes import DisplayList
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import PMMessageFactory as _
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import interface
from zope import schema
from zope.component import getAdapter
from zope.component.hooks import getSite
from zope.i18n import translate


class ItemEmergencyView(BrowserView):
    '''Render the item emergency HTML on the meetingitem_view.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.portal_url = getToolByName(self, 'portal_url').getPortalObject().absolute_url()

    def listSelectableEmergencies(self):
        '''Returns a list of emergencies the current user can set the item to.'''
        # we base our actions on avaialble terms in the MeetingItem.emergency field vocabulary
        emergencies = self.context.listEmergencies()
        emergencyKeys = emergencies.keys()
        currentEmergency = self.context.getEmergency()
        # now check if user can ask emergency if it is not already the case
        if not self.context.adapted().mayAskEmergency():
            emergencyKeys.remove('emergency_asked')
            emergencyKeys.remove('no_emergency')
        # now check if user can accept/refuse and asked emergency if it is not already the case
        if not self.context.adapted().mayAcceptOrRefuseEmergency() or currentEmergency == 'no_emergency':
            emergencyKeys.remove('emergency_accepted')
            emergencyKeys.remove('emergency_refused')
        elif not currentEmergency == 'emergency_asked':
            if currentEmergency in emergencyKeys:
                emergencyKeys.remove(currentEmergency)
        # now if currentEmergency is still in emergencies, we remove it
        if currentEmergency in emergencyKeys:
            emergencyKeys.remove(currentEmergency)
        # now build a vocabulary with left values
        res = []
        for emergency in emergencies.items():
            if emergency[0] in emergencyKeys:
                res.append(emergency)
        return DisplayList(tuple(res))


class ItemEmergencyHistoryView(BrowserView):
    '''Display history of emergency value changes.'''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def getHistory(self, checkMayViewEvent=True, checkMayViewComment=True):
        """ """
        adapter = getAdapter(self.context, IImioHistory, 'emergency_changes')
        history = adapter.getHistory(
            checkMayViewEvent=checkMayViewEvent,
            checkMayViewComment=checkMayViewComment)
        if not history:
            return []
        history.sort(key=lambda x: x["time"], reverse=True)
        return history

    def renderComments(self, comments, mimetype='text/plain'):
        """
          Borrowed from imio.history.
        """
        transformsTool = api.portal.get_tool('portal_transforms')
        data = transformsTool.convertTo('text/x-html-safe', comments, mimetype=mimetype)
        return data.getData()

    def get_user_fullname(self, user_id):
        return get_user_fullname(user_id)


def new_emergency_value_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?new_emergency_value=new_value.
    """
    request = getSite().REQUEST
    return request.get('new_emergency_value', '')


class IItemEmergencyComment(interface.Interface):
    comment = schema.Text(
        title=_(u"Comment"),
        description=_(u""),
        required=True,)

    new_emergency_value = schema.TextLine(
        title=_(u"New emergency value"),
        description=_(u""),
        defaultFactory=new_emergency_value_default)


class ItemEmergencyChangeForm(form.Form):
    """
      This form will give the possibility to add a
      required comment while changing item emergency.
    """
    label = _(u"Manage item emergency")
    description = u''

    fields = field.Fields(IItemEmergencyComment)
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label,
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('save'), name='save_item_emergency')
    def handleSaveItemEmergency(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        # check that given 'new_emergency_value' is available in the field vocabulary
        # if not available, just raise Unauthorized
        new_emergency_value = data.get('new_emergency_value')
        itemEmergencyView = self.context.unrestrictedTraverse('@@item-emergency')
        if new_emergency_value not in itemEmergencyView.listSelectableEmergencies():
            raise Unauthorized
        self.context.setEmergency(new_emergency_value)
        # add a line to the item's emergency_change_history
        add_event_to_history(
            self.context,
            'emergency_changes_history',
            action=new_emergency_value,
            comments=data['comment'])
        # update item
        self.context._update_after_edit(idxs=[])
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(_("Item emergency changed."))
        self.request.RESPONSE.redirect(self.context.absolute_url())

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.RESPONSE.redirect(self.context.absolute_url())

    def update(self):
        """ """
        # raise Unauthorized if current user can not manage itemAssembly
        if not self.context.mayQuickEdit('emergency'):
            raise Unauthorized
        super(ItemEmergencyChangeForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # hide field 'new_emergency_value'
        self.fields['new_emergency_value'].mode = 'hidden'
        translate_new_emergency_value = translate(new_emergency_value_default(),
                                                  domain='PloneMeeting',
                                                  context=self.request)
        self.fields['comment'].field.description = translate(
            'change_emergency_descr',
            domain='PloneMeeting',
            mapping={'new_emergency_value': translate_new_emergency_value},
            context=self.request,
            default=u"You are about to change emergency for this item to <span style='font-weight: bold;'>"
            u"${new_emergency_value}</span>, please enter a comment.")
        super(ItemEmergencyChangeForm, self).updateWidgets()


ItemEmergencyChangeFormWrapper = wrap_form(ItemEmergencyChangeForm)
