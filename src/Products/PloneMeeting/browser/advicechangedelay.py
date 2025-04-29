# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from copy import deepcopy
from DateTime import DateTime
from imio.helpers.cache import get_current_user_id
from imio.helpers.content import get_user_fullname
from plone import api
from plone.z3cform.layout import wrap_form
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.config import PMMessageFactory as _
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import interface
from zope import schema
from zope.component.hooks import getSite
from zope.i18n import translate


class AdviceDelaysView(BrowserView):
    '''Render the advice available delays HTML on the advices list.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self._initAttributes(self.request.get('advice', None))

    def _initAttributes(self, advice_uid):
        ''' '''
        self.portal = api.portal.get()
        self.portal_url = self.portal.absolute_url()
        self.advice = None
        self.row_id = None
        if advice_uid:
            self.advice = self.context.adviceIndex[advice_uid]
            self.row_id = self.advice['row_id']
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def listSelectableDelays(self):
        '''Returns a list of delays the current user can change the given p_row_id advice delay to.'''
        # find linked rows in the MeetingConfig.customAdvisers
        isAutomatic, linkedRows = self.cfg._findLinkedRowsFor(self.row_id)
        # check if current user may change delays for advice
        mayEdit = not self.context.adviceIsInherited(self.advice['id']) and self._mayEditDelays(isAutomatic)
        return self._availableDelays(linkedRows, mayEdit)

    def _mayEditDelays(self, isAutomatic):
        '''Check if current user may edit delays for advice.  Given p_isAutomatic
           is a boolean specifying if the advice is an automatic one or not.
           The rule managed here is :
           - An optional (not isAutomatic) advice can be edited if the user, may edit the item;
           - An automatic advice delay can only be edited by Managers (and MeetingManagers).'''
        # advice is not automatic, the user must have 'Modify portal content' permission
        if not isAutomatic:
            if not _checkPermission(ModifyPortalContent, self.context):
                return False
        else:
            # advice is automatic, only Managers and MeetingManagers can change an automatic advice delay
            # and only if the advice still could not be given or if it is currently editable
            if not self.tool.isManager(self.cfg) or \
               not _checkPermission(ModifyPortalContent, self.context):
                return False

        return True

    def _availableDelays(self, linkedRows, mayEdit):
        '''Returns available delays.
           p_mayEdit is passed so it can be used in the expression,
           indeed, we have 2 usecases here :
           - either we have users able to edit and we want to restrict some values;
           - or we have users not able to edit but we want to let them the possibility
             to change an advice delay.'''
        res = []
        # evaluate the 'available_on' TAL expression defined on each linkedRows
        availableLinkedRows = []
        # set a special value in the request usable in the TAL expression
        # that just specify that we are managing available delays
        # this way, it is easy to protect a custom adviser by just checking
        # this value in the REQUEST
        self.request.set('managing_available_delays', True)
        for linkedRow in linkedRows:
            eRes = mayEdit
            if linkedRow['available_on']:
                eRes = self.context._evalAdviceAvailableOn(linkedRow['available_on'], mayEdit=mayEdit)
            if eRes:
                availableLinkedRows.append(linkedRow)
        self.request.set('managing_available_delays', False)

        # no delay to change to, return
        if not availableLinkedRows:
            return res

        for linkedRow in availableLinkedRows:
            if linkedRow['row_id'] == self.row_id:
                continue
            res.append(
                (linkedRow['row_id'],
                 linkedRow['delay'],
                 safe_unicode(linkedRow['delay_label']),
                 linkedRow['is_delay_calendar_days'] == '1'))
        return res

    def _mayAccessDelayChangesHistory(self):
        '''May current user access delay changes history?
           By default it is shown to MeetingManagers, advisers of p_advice_uid
           and members of the proposingGroup.'''
        advice_uid = self.advice['id']
        # MeetingManagers and advisers of the group
        # can access the delay changes history
        userAdviserOrgUids = self.tool.get_orgs_for_user(suffixes=['advisers'])
        if self.tool.isManager(self.cfg) or \
           advice_uid in userAdviserOrgUids or \
           self.context.getProposingGroup() in self.tool.get_orgs_for_user():
            return True

    def _mayReinitializeDelay(self, advice_uid=None):
        '''May current user reinitialize delau for given advice_uid?
           By default it is available if current user may edit the item.'''
        if not advice_uid:
            advice_uid = self.advice['id']
        return _checkPermission(ModifyPortalContent, self.context)


def current_delay_row_id_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?current_delay_row_id=new_value.
    """
    request = getSite().REQUEST
    return request.get('current_delay_row_id', u'')


def new_delay_row_id_default():
    """
      Get the value from the REQUEST as it is passed when calling the
      form : form?new_delay_row_id=new_value.
    """
    request = getSite().REQUEST
    return request.get('new_delay_row_id', u'')


class IAdviceChangeDelayComment(interface.Interface):
    comment = schema.Text(
        title=_(u"Comment"),
        description=_(u""),
        required=True)

    current_delay_row_id = schema.TextLine(
        title=_(u"Current delay row_id"),
        description=_(u""),
        defaultFactory=current_delay_row_id_default,
        required=False)

    new_delay_row_id = schema.TextLine(
        title=_(u"New delay row_id"),
        description=_(u""),
        defaultFactory=new_delay_row_id_default,
        required=False)


class AdviceChangeDelayForm(form.EditForm):
    """
      This form will give the possibility to add a
      required comment while changing advice delay.
    """
    label = _(u"Change delay")
    description = u''

    fields = field.Fields(IAdviceChangeDelayComment)
    ignoreContext = True  # don't use context to get widget data

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate(self.label,
                               domain='PloneMeeting',
                               context=self.request)

    def getDataForRowId(self, row_id):
        '''Return relevant advice infos for given p_row_id.'''
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return cfg._dataForCustomAdviserRowId(row_id)

    @button.buttonAndHandler(_('save'), name='save_advice_delay')
    def handleSaveAdviceDelay(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        # check that given 'new_advice_delay' is available
        # if not available, just raise Unauthorized
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        newAdviceData = self.getDataForRowId(data['new_delay_row_id'])
        currentAdviceData = self.getDataForRowId(data['current_delay_row_id'])
        listAvailableDelaysView = self.context.unrestrictedTraverse('@@advice-available-delays')
        listAvailableDelaysView._initAttributes(currentAdviceData['org'])
        isAutomatic, linkedRows = cfg._findLinkedRowsFor(data['current_delay_row_id'])
        selectableDelays = listAvailableDelaysView.listSelectableDelays()
        # selectableDelays is a list of tuple containing 3 elements, the first is the row_id
        selectableDelays = [selectableDelay[0] for selectableDelay in selectableDelays]
        if not data['new_delay_row_id'] in selectableDelays:
            raise Unauthorized
        # update the advice with new delay and relevant data

        # just keep relevant infos
        dataToUpdate = ('delay',
                        'delay_label',
                        'gives_auto_advice_on_help_message',
                        'row_id')
        for elt in dataToUpdate:
            self.context.adviceIndex[currentAdviceData['org']][elt] = newAdviceData[elt]
        # if the advice was already given, we need to update row_id on the given advice object too
        if not self.context.adviceIndex[currentAdviceData['org']]['type'] == NOT_GIVEN_ADVICE_VALUE:
            adviceObj = getattr(self.context, self.context.adviceIndex[currentAdviceData['org']]['advice_id'])
            adviceObj.advice_row_id = newAdviceData['row_id']
        # if it is an optional advice, update the MeetingItem.optionalAdvisers
        if not isAutomatic:
            optionalAdvisers = list(self.context.getOptionalAdvisers(computed=True))
            # remove old value
            optionalAdvisers.remove('%s__rowid__%s' % (currentAdviceData['org'],
                                                       currentAdviceData['row_id']))
            # append new value
            optionalAdvisers.append('%s__rowid__%s' % (newAdviceData['org'],
                                                       newAdviceData['row_id']))
            self.context.setOptionalAdvisers(tuple(optionalAdvisers))
        else:
            # if it is an automatic advice, set the 'delay_for_automatic_adviser_changed_manually' to True
            self.context.adviceIndex[currentAdviceData['org']]['delay_for_automatic_adviser_changed_manually'] = True
        self.context.update_local_roles()
        # add a line to the item's adviceIndex advice delay_changes_history
        history_data = {'action': (currentAdviceData['delay'], newAdviceData['delay']),
                        'actor': get_current_user_id(),
                        'time': DateTime(),
                        'comments': data['comment']}
        self.context.adviceIndex[currentAdviceData['org']]['delay_changes_history'].append(history_data)
        self.request.response.redirect(self.context.absolute_url() + '/#adviceAndAnnexes')

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.RESPONSE.redirect(self.context.absolute_url())

    def update(self):
        """ """
        super(AdviceChangeDelayForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # hide fields '..._row_id'
        self.fields['current_delay_row_id'].mode = 'hidden'
        self.fields['new_delay_row_id'].mode = 'hidden'

        super(AdviceChangeDelayForm, self).updateWidgets()
        newAdviceData = self.getDataForRowId(self.widgets['new_delay_row_id'].value)
        if not newAdviceData:
            raise Unauthorized

        is_delay_calendar_days = ''
        if newAdviceData['is_delay_calendar_days'] == '1':
            is_delay_calendar_days = \
                "<span title='%s' class='far fa-calendar-alt pmHelp'></span>" % \
                translate('Delay computed in calendar days',
                          domain="PloneMeeting",
                          context=self.request)
        self.fields['comment'].field.description = translate(
            'change_advice_delay_descr',
            domain='PloneMeeting',
            mapping={'new_advice_delay': safe_unicode(newAdviceData['delay']),
                     'new_advice_delay_label': safe_unicode(newAdviceData['delay_label']),
                     'new_advice_is_delay_calendar_days': is_delay_calendar_days,
                     },
            context=self.request)


AdviceChangeDelayFormWrapper = wrap_form(AdviceChangeDelayForm)


class AdviceChangeDelayHistoryView(BrowserView):
    '''Display history of advice delay value changes.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')

    def renderComments(self, comments, mimetype='text/plain'):
        """
          Borrowed from imio.history.
        """
        transformsTool = api.portal.get_tool('portal_transforms')
        data = transformsTool.convertTo('text/x-html-safe', comments, mimetype=mimetype)
        return data.getData()

    def getHistoryInfos(self):
        '''
          Return history of delay changes for an advice.
        '''
        delayChangesView = self.context.unrestrictedTraverse('@@advice-available-delays')
        advice_uid = self.request.get('advice')
        if not delayChangesView._mayAccessDelayChangesHistory():
            raise Unauthorized
        return deepcopy(self.context.adviceIndex[advice_uid])

    def get_user_fullname(self, user_id):
        return get_user_fullname(user_id)


def _reinit_advice_delay(item, advice_uid):
    '''Reinitialize advice delay for given p_item p_advice_uid.'''
    advice_infos = item.adviceIndex[advice_uid]
    advice_infos['delay_started_on'] = None
    advice_infos['delay_stopped_on'] = None


class AdviceReinitializeDelayView(BrowserView):
    '''Reinitialize delay of given advice_uid.'''

    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request

    def __call__(self):
        ''' '''
        delayChangesView = self.context.unrestrictedTraverse('@@advice-available-delays')
        advice_uid = self.request.get('advice')
        if not delayChangesView._mayReinitializeDelay(advice_uid):
            raise Unauthorized
        # reinit delay and add a line to the item's adviceIndex advice delay_changes_history
        _reinit_advice_delay(self.context, advice_uid)
        history_data = {'action': 'Reinitiatlize delay',
                        'actor': get_current_user_id(),
                        'time': DateTime(),
                        'comments': None}
        adviceInfos = self.context.adviceIndex[advice_uid]
        adviceInfos['delay_changes_history'].append(history_data)
        # update local roles that will update adviceIndex
        self.context.update_local_roles()
        api.portal.show_message(_('Advice delay have been reinitialized for advice "${advice}"',
                                  mapping={'advice': adviceInfos['name']}), request=self.request)
