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

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_plone_group_id
from imio.helpers.content import get_vocab
from plone import api
from plone.directives import form
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.config import DUPLICATE_AND_KEEP_LINK_EVENT_ACTION
from Products.PloneMeeting.config import DUPLICATE_EVENT_ACTION
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.form import button
from z3c.form import field
from z3c.form import form as z3c_form
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.component import queryUtility
from zope.i18n import translate
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory
from zope.security.interfaces import IPermission


@provider(IContextAwareDefaultFactory)
def annex_ids_default(context):
    """Select every annexes by default."""
    vocab = get_vocab(
        context,
        u"Products.PloneMeeting.vocabularies.contained_annexes_vocabulary")
    return vocab.by_token.keys()


class IDuplicateItem(form.Schema):
    """ """

    keep_link = schema.Bool(
        title=_(u'Keep link?'),
        description=_(""),
        required=False,
        default=False,
    )

    annex_ids = schema.List(
        title=_(u"Annexes to keep"),
        description=_(u""),
        required=False,
        defaultFactory=annex_ids_default,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.contained_annexes_vocabulary"),
    )

    annex_decision_ids = schema.List(
        title=_(u"Decision annexes to keep"),
        description=_(u""),
        required=False,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.contained_decision_annexes_vocabulary"),
    )


class DuplicateItemForm(z3c_form.Form):
    """ """
    fields = field.Fields(IDuplicateItem)
    fields["keep_link"].widgetFactory = RadioFieldWidget
    fields["annex_ids"].widgetFactory = PMCheckBoxFieldWidget
    fields["annex_decision_ids"].widgetFactory = PMCheckBoxFieldWidget

    ignoreContext = True  # don't use context to get widget data

    label = _(u"Duplicate item")
    description = _('Disabled (greyed) annexes will not be kept on the new duplicated item.')
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.label = translate('Duplicate item',
                               domain='PloneMeeting',
                               context=self.request)

    @button.buttonAndHandler(_('Apply'), name='apply_duplicate_item')
    def handleApply(self, action):
        self._check_auth()
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self._doApply(data)

    def _check_data(self, data):
        """Make sure annex_ids/annex_decision_ids are correct.
           As some values are disabled in the UI, a user could try
           to surround this, raise Unauthorized in this case."""
        annex_terms = self.widgets['annex_ids'].terms
        annex_term_ids = [term.token for term in annex_terms
                          if not term.disabled]
        for annex_id in data['annex_ids']:
            if annex_id not in annex_term_ids:
                raise Unauthorized
        decision_annex_terms = self.widgets['annex_decision_ids'].terms
        decision_annex_term_ids = [term.token for term in decision_annex_terms
                                   if not term.disabled]
        for decision_annex_id in data['annex_decision_ids']:
            if decision_annex_id not in decision_annex_term_ids:
                raise Unauthorized

    def _doApply(self, data):
        """ """
        tool = api.portal.get_tool('portal_plonemeeting')
        user = api.user.get_current()
        cloneEventAction = DUPLICATE_EVENT_ACTION
        setCurrentAsPredecessor = False
        manualLinkToPredecessor = False
        if data['keep_link']:
            cloneEventAction = DUPLICATE_AND_KEEP_LINK_EVENT_ACTION
            setCurrentAsPredecessor = True
            manualLinkToPredecessor = True
        # make sure data is correct
        self._check_data(data)

        # as passing empty keptAnnexIds/keptDecisionAnnexIds ignores it
        # if we unselect every annexes, we force copyAnnexes/copyDecisionAnnexes to False
        copyAnnexes = data['annex_ids'] and True or False
        copyDecisionAnnexes = data['annex_decision_ids'] and True or False
        # keep proposingGroup if current user creator for it
        keepProposingGroup = False
        proposingGroup = self.context.getProposingGroup()
        if get_plone_group_id(proposingGroup, 'creators') in tool.get_plone_groups_for_user():
            keepProposingGroup = True
        newItem = self.context.clone(
            copyAnnexes=copyAnnexes,
            copyDecisionAnnexes=copyDecisionAnnexes,
            newOwnerId=user.id,
            cloneEventAction=cloneEventAction,
            keepProposingGroup=keepProposingGroup,
            setCurrentAsPredecessor=setCurrentAsPredecessor,
            manualLinkToPredecessor=manualLinkToPredecessor,
            keptAnnexIds=data['annex_ids'],
            keptDecisionAnnexIds=data['annex_decision_ids'])
        self.new_item_url = newItem.absolute_url()
        api.portal.show_message(
            translate('item_duplicated', domain='PloneMeeting', context=self.request),
            request=self.request)
        self._finished = True
        return newItem

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finished = True

    def update(self):
        """ """
        self._check_auth()
        super(DuplicateItemForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    def updateWidgets(self):
        # XXX manipulate self.fields BEFORE doing form.Form.updateWidgets
        z3c_form.Form.updateWidgets(self)
        # disable values if current user not able to add annex ou annexDecision
        if not self._user_able_to_add():
            for term in self.widgets['annex_ids'].terms:
                term.disabled = True
                term.title = term.title + u' [Not allowed by application permissions]'
        elif not self._user_able_to_add(annex_portal_type='annexDecision'):
            for term in self.widgets['annex_decision_ids'].terms:
                term.disabled = True
                term.title = term.title + u' [Not allowed by application permissions]'

    def _user_able_to_add(self, annex_portal_type='annex'):
        """Is current user able to add given p_annex_portal_type
           on newly created item?"""
        # does MeetingMember have Add annex when item created?
        typesTool = api.portal.get_tool('portal_types')
        wfTool = api.portal.get_tool('portal_workflow')
        item_wf = wfTool.getWorkflowsFor(self.context)[0]
        initial_state = item_wf.states.get(item_wf.initial_state)
        add_permission = typesTool.get(annex_portal_type).add_permission
        # add_permission is a z3 like permission (PloneMeeting.AddAnnex),
        # need the permission title (u'PloneMeeting: Add annex')
        add_permission = queryUtility(IPermission, add_permission).title
        permission_roles = initial_state.permission_roles[add_permission]
        # compatibility PM4.1/PM4.2
        # XXX to be adapted in PM4.2, remove 'MeetingMember' and be more accurate
        # indeed maybe Editor does not have permission, but another role of current
        # user has it...
        res = False
        if 'MeetingMember' in permission_roles or \
           'Editor' in permission_roles:
            res = True
        return res

    def _check_auth(self):
        """Raise Unauthorized if current user may not duplicate the item."""
        if not self.context.showDuplicateItemAction():
            raise Unauthorized

    def render(self):
        if self._finished:
            IRedirect(self.request).redirect(
                getattr(self, 'new_item_url', self.context.absolute_url()))
            return ""
        return super(DuplicateItemForm, self).render()


DuplicateItemFormWrapper = wrap_form(DuplicateItemForm)
