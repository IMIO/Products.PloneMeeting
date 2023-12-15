# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_plone_group_id
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_vocab
from plone import api
from plone.directives import form
from plone.z3cform.layout import wrap_form
from Products.CMFPlone import PloneMessageFactory as PMF
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
        u"Products.PloneMeeting.vocabularies.item_duplication_contained_annexes_vocabulary")
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
            vocabulary=u"Products.PloneMeeting.vocabularies.item_duplication_contained_annexes_vocabulary"),
    )

    annex_decision_ids = schema.List(
        title=_(u"Decision annexes to keep"),
        description=_(u""),
        required=False,
        value_type=schema.Choice(
            vocabulary=u"Products.PloneMeeting.vocabularies.item_duplication_contained_decision_annexes_vocabulary"),
    )


class DuplicateItemForm(z3c_form.Form):
    """ """
    fields = field.Fields(IDuplicateItem)
    fields["keep_link"].widgetFactory = RadioFieldWidget
    fields["annex_ids"].widgetFactory = PMCheckBoxFieldWidget
    fields["annex_decision_ids"].widgetFactory = PMCheckBoxFieldWidget

    ignoreContext = True  # don't use context to get widget data

    label = PMF(u"Duplicate")
    description = _('Disabled (greyed) annexes will not be kept on the new duplicated item.')
    _finished = False

    def __init__(self, context, request):
        self.context = context
        self.request = request

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
        user_id = get_current_user_id()
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
        if get_plone_group_id(proposingGroup, 'creators') in get_plone_groups_for_user():
            keepProposingGroup = True
        newItem = self.context.clone(
            copyAnnexes=copyAnnexes,
            copyDecisionAnnexes=copyDecisionAnnexes,
            newOwnerId=user_id,
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
        # disable values if current user not able to add annex or annexDecision
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
        # does user have Add annex when item created?
        typesTool = api.portal.get_tool('portal_types')
        wfTool = api.portal.get_tool('portal_workflow')
        item_wf = wfTool.getWorkflowsFor(self.context)[0]
        initial_state = item_wf.states.get(item_wf.initial_state)
        add_permission = typesTool.get(annex_portal_type).add_permission
        # add_permission is a z3 like permission (PloneMeeting.AddAnnex),
        # need the permission title (u'PloneMeeting: Add annex')
        add_permission = queryUtility(IPermission, add_permission).title
        permission_roles = initial_state.permission_roles[add_permission]
        res = False
        # Editor is the role that may add annex, Contributor is used to add annex decision
        if 'Editor' in permission_roles or \
           'Contributor' in permission_roles:
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
