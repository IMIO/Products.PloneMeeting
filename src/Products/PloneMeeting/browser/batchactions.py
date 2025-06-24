# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_all_suffixes
from collective.eeafaceted.batchactions import _ as _CEBA
from collective.eeafaceted.batchactions.browser.viewlets import BatchActionsViewlet
from collective.eeafaceted.batchactions.browser.views import BaseARUOBatchActionForm
from collective.eeafaceted.batchactions.browser.views import BaseBatchActionForm
from collective.eeafaceted.batchactions.browser.views import DeleteBatchActionForm
from collective.eeafaceted.batchactions.browser.views import LabelsBatchActionForm
from collective.eeafaceted.batchactions.browser.views import TransitionBatchActionForm
from collective.eeafaceted.batchactions.utils import listify_uids
from imio.actionspanel.interfaces import IContentDeletable
from imio.annex.browser.views import ConcatenateAnnexesBatchActionForm
from imio.annex.browser.views import DownloadAnnexesBatchActionForm
from plone import api
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import NO_COMMITTEE
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import displaying_available_items
from z3c.form.field import Fields
from zope import schema
from zope.i18n import translate


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
            _is_operational_user(self.context)

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
        return cfg.getEnableLabels()

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


def _is_operational_user(context):
    """Is current user an operationnal user in the application for the given p_context."""
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(context)
    class_name = context.__class__.__name__
    return class_name != 'MeetingItem' and \
        ((class_name == 'Meeting' and
            _checkPermission(ModifyPortalContent, context)) or
         (not class_name == 'Meeting' and
         (tool.isManager(cfg) or
          bool(tool.userIsAmong(
               suffixes=get_all_suffixes(omitted_suffixes=['observers']), cfg=cfg)))))


class PMTransitionBatchActionForm(TransitionBatchActionForm):
    """ """

    def available(self):
        """Only available to users having operational roles in the application.
           This is essentially done to hide this to (restricted)powerobservers
           and to non MeetingManagers on the meeting_view."""
        return _is_operational_user(self.context)


class PMMeetingBatchActionsViewlet(BatchActionsViewlet):
    """ """
    def available(self):
        """Not available on the 'available items' when displayed on a meeting."""
        if displaying_available_items(self.context):
            return False
        return True


#
#
#  Viewlets
#
#
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
