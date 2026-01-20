# -*- coding: utf-8 -*-

from collective.eeafaceted.batchactions import _ as _CEBA
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from collective.eeafaceted.batchactions.browser.views import BaseARUOBatchActionForm
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.eeafaceted.batchactions.browser.views import DeleteBatchActionForm
from collective.eeafaceted.batchactions.browser.views import LabelsBatchActionForm
from collective.eeafaceted.batchactions.browser.views import TransitionBatchActionForm
from collective.eeafaceted.batchactions.utils import listify_uids
from collective.z3cform.select2.widget.widget import SingleSelect2FieldWidget
from imio.actionspanel.interfaces import IContentDeletable
from imio.annex.browser.views import ConcatenateAnnexesBatchActionForm
from imio.annex.browser.views import DownloadAnnexesBatchActionForm
from imio.esign.adapters import ISignable
from imio.esign.config import get_registry_enabled
from imio.helpers.content import get_vocab
from plone import api
from plone.app.textfield import RichText
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.content.advice import _advice_type_default
from Products.PloneMeeting.ftw_labels.utils import filter_access_global_labels
from Products.PloneMeeting.utils import _add_advice
from Products.PloneMeeting.utils import displaying_available_items
from Products.PloneMeeting.utils import is_operational_user
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.field import Fields
from zope import schema
from zope.i18n import translate
from zope.interface import provider
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


#
#
#  New batch actions
#
#
class MeetingStoreItemsPodTemplateAsAnnexBatchActionForm(BaseBatchActionForm):

    label = _CEBA("Store POD template as annex for selected elements")
    button_with_icon = True
    available_permission = ModifyPortalContent

    def __init__(self, context, request):
        super(MeetingStoreItemsPodTemplateAsAnnexBatchActionForm, self).__init__(
            context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        # super() will check for self.available_permission
        if self.cfg.getMeetingItemTemplatesToStoreAsAnnex() and \
           super(MeetingStoreItemsPodTemplateAsAnnexBatchActionForm, self).available():
            return True

    def _update(self):
        self.fields += Fields(schema.Choice(
            __name__='pod_template',
            title=_(u'POD template to annex'),
            vocabulary='Products.PloneMeeting.vocabularies.itemtemplatesstorableasannexvocabulary'))
        # eSign
        if get_registry_enabled():
            self.fields += Fields(schema.Bool(
                __name__='add_to_sign_session',
                title=_(u'title_add_to_sign_session'),
                description=_(
                    "This will add stored annexes to a e-signing session."),
                required=False,
                default=True))
            self.fields["add_to_sign_session"].widgetFactory = RadioFieldWidget
            self.fields += Fields(schema.Bool(
                __name__='add_annexes_to_sign_session',
                title=_(u'title_add_annexes_to_sign_session'),
                description=_(
                    "This will add existing annexes marked \"To sign\" to a e-signing session."),
                required=False,
                default=True))
            self.fields["add_annexes_to_sign_session"].widgetFactory = RadioFieldWidget

    def _apply(self, **data):
        """ """
        template_id, output_format = data['pod_template'].split('__output_format__')
        pod_template = getattr(self.cfg.podtemplates, template_id)
        num_of_generated_templates = 0
        self.request.set('store_as_annex', '1')
        for brain in self.brains:
            item = brain.getObject()
            generation_view = item.restrictedTraverse('@@document-generation')
            # res is a string (error msg) or an annex
            res = generation_view(
                template_uid=pod_template.UID(),
                output_format=output_format,
                return_portal_msg_code=True)
            # we received an annex, meaning it was created
            if base_hasattr(res, 'portal_type'):
                num_of_generated_templates += 1
                # eSign
                add_to_sign_session = data.get('add_to_sign_session', False)
                if add_to_sign_session:
                    signatories = ISignable(res).get_signers()
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
    available_permission = ManagePortal
    button_with_icon = False

    def __init__(self, context, request):
        super(UpdateLocalRolesBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def _apply(self, **data):
        """ """
        uids = listify_uids(data['uids'])
        self.tool.update_all_local_roles(brains=self.brains, log=False, redirect=False)
        msg = translate('update_selected_elements',
                        domain="PloneMeeting",
                        mapping={'number_of_elements': len(uids)},
                        context=self.request,
                        default="Updated accesses for ${number_of_elements} element(s).")
        api.portal.show_message(msg, request=self.request)


class PMBaseARUOBatchActionForm(BaseARUOBatchActionForm):
    """ """

    # we manage reindex with update_local_roles in _apply here under
    indexes = []

    def available(self):
        """Only available when using the item attr to users having operational
           roles in the application.
           This is essentially done to hide this to (restricted)powerobservers
           and to non MeetingManagers on the meeting_view."""
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        return self.modified_attr_name in self.cfg.getUsedItemAttributes() and \
            is_operational_user(self.context)

    def _apply(self, **data):
        updated = super(PMBaseARUOBatchActionForm, self)._apply(**data)
        for item in updated:
            item.update_local_roles()


class UpdateGroupsInChargeBatchActionForm(PMBaseARUOBatchActionForm):
    """ """

    label = _CEBA("Update groups in charge for selected elements")
    modified_attr_name = "groupsInCharge"
    required = True

    def available(self):
        """If not available, check if it should be made available to
        MeetingManagers when using
        MeetingConfig.includeGroupsInChargeDefinedOnProposingGroup or
        MeetingConfig.includeGroupsInChargeDefinedOnCategory."""
        res = super(UpdateGroupsInChargeBatchActionForm, self).available()
        if not res:
            if (self.cfg.getIncludeGroupsInChargeDefinedOnProposingGroup() or
                self.cfg.getIncludeGroupsInChargeDefinedOnCategory()) and \
               self.tool.isManager(self.cfg):
                res = True
        return res

    def _vocabulary(self):
        return 'Products.PloneMeeting.vocabularies.itemgroupsinchargevocabulary'


class UpdateCopyGroupsBatchActionForm(PMBaseARUOBatchActionForm):
    """ """

    label = _CEBA("Update copy groups for selected elements")
    modified_attr_name = "copyGroups"
    required = False

    def _vocabulary(self):
        return 'Products.PloneMeeting.vocabularies.copygroupsvocabulary'


class UpdateCommitteesBatchActionForm(PMBaseARUOBatchActionForm):
    """ """

    label = _CEBA("Update committees for selected elements")
    modified_attr_name = "committees"
    indexes = ["committees_index"]
    required = True

    def available(self):
        """Field "committees" is not an optionnal field, this is controlled
           from the attributes enabled on the meeting.
           Make it available only to MeetingManagers."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return self.modified_attr_name in cfg.getUsedMeetingAttributes() and \
            tool.isManager(cfg)

    def _validate(self, obj, values):
        """Can not use NO_COMMITTEE together with another value."""
        res = super(UpdateCommitteesBatchActionForm, self)._validate(obj, values)
        if res:
            if len(values) > 1 and NO_COMMITTEE in values:
                api.portal.show_message(
                    _("can_not_select_no_committee_and_committee"),
                    request=self.request)
                res = False
        return res

    def _vocabulary(self):
        return 'Products.PloneMeeting.vocabularies.item_selectable_committees_vocabulary'


@provider(IContextAwareDefaultFactory)
def advice_type_default(context):
    """
      Default value is the current item number.
    """
    return _advice_type_default(
        context.REQUEST['PUBLISHED'].advice_portal_type, context)


class AddAdviceBatchActionForm(BaseBatchActionForm):
    """ """

    label = _CEBA("Add common advice for selected elements")
    button_with_icon = True
    advice_portal_type = "meetingadvice"
    overlay = None

    def __init__(self, context, request):
        super(AddAdviceBatchActionForm, self).__init__(
            context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """Available if using advices and current user is an adviser
           able to add a self.advice_portal_type."""
        # super() will check for self.available_permission
        res = super(AddAdviceBatchActionForm, self).available() and \
            self.cfg.getUseAdvices()
        if res:
            # check if user can add a "meetingadvice" portal_type
            # so it is not displayed to advisers able to add other
            # advice_portal_types than "meetingadvice"
            custom_adviser_org_uids = [
                k for k, v in self.tool.get_extra_adviser_infos().items()
                if v['portal_type'] != self.advice_portal_type]
            adviser_org_uids = self.tool.get_orgs_for_user(suffixes=['advisers'])
            return bool(set(adviser_org_uids).difference(custom_adviser_org_uids))

    def _advice_group_vocabulary(self):
        """ """
        res = []
        for brain in self.brains:
            item = brain.getObject()
            res.append(item.getAdvicesGroupsInfosForUser(
                compute_to_edit=False, compute_power_advisers=False)[0])
        # keep intersection, so advices addable on every items
        adviser_uids = []
        if res:
            adviser_uids = list(set(res[0]).intersection(*res))
        return get_vocab(
            self.context,
            'Products.PloneMeeting.content.advice.advice_group_vocabulary',
            advice_portal_type=self.advice_portal_type,
            alterable_advice_org_uids=adviser_uids)

    def _advice_type_vocabulary(self):
        """ """
        return get_vocab(
            self.context,
            'Products.PloneMeeting.content.advice.advice_type_vocabulary',
            advice_portal_type=self.advice_portal_type)

    def _update(self):
        advice_groups = self._advice_group_vocabulary()
        self.do_apply = len(advice_groups) > 0
        self.fields += Fields(schema.Choice(
            __name__='advice_group',
            title=_(u'title_advice_group'),
            description=(
                len(advice_groups) == 0 and
                _(u'No common or available advice group. Modify your selection.') or u''),
            vocabulary=advice_groups,
            required=len(advice_groups) > 0))

        self.fields += Fields(schema.Choice(
            __name__='advice_type',
            title=_(u'title_advice_type'),
            defaultFactory=advice_type_default,
            vocabulary=self._advice_type_vocabulary()))
        self.fields["advice_type"].widgetFactory = SingleSelect2FieldWidget

        self.fields += Fields(schema.Bool(
            __name__='advice_hide_during_redaction',
            title=_(u'title_advice_hide_during_redaction'),
            description=_(
                "If you do not want the advice to be shown immediately after redaction, you can check this "
                "box.  This will let you or other member of your group work on the advice before showing it.  "
                "Note that if you lose access to the advice (for example if the item state evolve), "
                "the advice will be considered 'Not given, was under edition'.  A manager will be able "
                "to publish it nevertheless."),
            required=False,
            default=False))
        self.fields["advice_hide_during_redaction"].widgetFactory = RadioFieldWidget

        self.fields += Fields(RichText(
            __name__='advice_comment',
            title=_(u'title_advice_comment'),
            description=_("Enter the official comment."),
            allowed_mime_types=(u"text/html", ),
            required=False))
        self.fields['advice_comment'].widgetFactory = PMRichTextFieldWidget
        self.fields += Fields(RichText(
            __name__='advice_observations',
            title=_(u'title_advice_observations'),
            description=_("Enter optionnal observations if necessary."),
            allowed_mime_types=(u"text/html", ),
            required=False))
        self.fields['advice_observations'].widgetFactory = PMRichTextFieldWidget

    def _apply(self, **data):
        """ """
        for brain in self.brains:
            _add_advice(
                brain.getObject(),
                advice_group=data['advice_group'],
                advice_type=data['advice_type'],
                advice_hide_during_redaction=data['advice_hide_during_redaction'],
                advice_comment=data['advice_comment'],
                advice_observations=data['advice_observations'],
                advice_portal_type=self.advice_portal_type)
        return


#
#
#  Overrides
#
#
class PMDeleteBatchActionForm(DeleteBatchActionForm):
    """ """

    section = "annexes"
    available_permission = ModifyPortalContent

    def __init__(self, context, request):
        super(PMDeleteBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        # super() will check for self.available_permission
        return "delete" in self.cfg.getEnabledAnnexesBatchActions() and \
            super(PMDeleteBatchActionForm, self).available()

    def _get_deletable_elements(self):
        """Get deletable elements using IContentDeletable."""
        return [obj for obj in self.objs
                if IContentDeletable(obj).mayDelete()]


class PMConcatenateAnnexesBatchActionForm(ConcatenateAnnexesBatchActionForm):
    """ """

    def __init__(self, context, request):
        super(PMConcatenateAnnexesBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        # super() will check for self.available_permission
        if self.cfg.isManager(self.cfg) and \
           super(ConcatenateAnnexesBatchActionForm, self).available():
            return True

    def _annex_types_vocabulary(self):
        return "Products.PloneMeeting.vocabularies.icon_item_annex_types_vocabulary"

    def _error_obj_title(self, obj):
        """ """
        return obj.Title(withItemNumber=True, withItemReference=True)


class PMDownloadAnnexesBatchActionForm(DownloadAnnexesBatchActionForm):
    """ """

    def __init__(self, context, request):
        super(PMDownloadAnnexesBatchActionForm, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(context)

    def available(self):
        """ """
        return "download-annexes" in self.cfg.getEnabledAnnexesBatchActions()


class PMLabelsBatchActionForm(LabelsBatchActionForm):
    """ """

    def available(self):
        """Only available when labels are enabled."""
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        return 'labels' in cfg.getUsedItemAttributes()

    def _filter_labels_vocabulary(self, jar):
        return filter_access_global_labels(jar, mode='edit')

    def _can_change_labels(self):
        view = None
        for brain in self.brains:
            obj = brain.getObject()
            # only instanciate view one time and change context
            if view is None:
                view = obj.restrictedTraverse('@@labeling')
            view.context = obj
            if not view.can_edit:
                return False
        return True


class PMTransitionBatchActionForm(TransitionBatchActionForm):
    """ """

    def available(self):
        """Only available to users having operational roles in the application.
           This is essentially done to hide this to (restricted)powerobservers
           and to non MeetingManagers on the meeting_view."""
        return is_operational_user(self.context)


#
#
#  Viewlets
#
#
class PMMeetingBatchActionsViewlet(BatchActionsViewlet):
    """ """
    def available(self):
        """Not available on the 'available items' when displayed on a meeting."""
        if displaying_available_items(self.context):
            return False
        return True


class AnnexesBatchActionsViewlet(BatchActionsViewlet):
    """ """

    section = "annexes"

    def available(self):
        """ """
        return True

    @property
    def select_item_name(self):
        """Manage fact that in the annexes, there are 2 tables
          (annexes and decision annexes) that use a different name
          for the checkbox column."""
        value = None
        if self.request.get('categorized_tab').portal_type == 'annexDecision':
            value = "select_item_annex_decision"
        else:
            value = super(AnnexesBatchActionsViewlet, self).select_item_name
        return value
