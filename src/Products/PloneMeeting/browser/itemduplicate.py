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
from imio.helpers.content import get_vocab
from plone import api
from plone.z3cform.layout import wrap_form
from Products.PloneMeeting.config import DUPLICATE_AND_KEEP_LINK_EVENT_ACTION
from Products.PloneMeeting.config import DUPLICATE_EVENT_ACTION
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from z3c.form import button
from z3c.form import field
from z3c.form import form as z3c_form
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.i18n import translate
from zope.interface import provider
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from plone.directives import form
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


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
    description = u''
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

    def _doApply(self, data):
        """ """
        user = api.user.get_current()
        cloneEventAction = DUPLICATE_EVENT_ACTION
        setCurrentAsPredecessor = False
        manualLinkToPredecessor = False
        if data['keep_link']:
            cloneEventAction = DUPLICATE_AND_KEEP_LINK_EVENT_ACTION
            setCurrentAsPredecessor = True
            manualLinkToPredecessor = True

        # as passing empty keptAnnexIds/keptDecisionAnnexIds ignores it
        # if we unselect every annexes, we force copyAnnexes/copyDecisionAnnexes to False
        copyAnnexes = data['annex_ids'] and True or False
        copyDecisionAnnexes = data['annex_decision_ids'] and True or False
        newItem = self.context.clone(
            copyAnnexes=copyAnnexes,
            copyDecisionAnnexes=copyDecisionAnnexes,
            newOwnerId=user.id,
            cloneEventAction=cloneEventAction,
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
