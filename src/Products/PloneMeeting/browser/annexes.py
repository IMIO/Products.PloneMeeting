# -*- coding: utf-8 -*-

from collective.iconifiedcategory.browser.actionview import BaseView as BaseActionView
from collective.iconifiedcategory.browser.actionview import ConfidentialChangeView
from collective.iconifiedcategory.browser.actionview import PublishableChangeView
from collective.iconifiedcategory.browser.actionview import SignedChangeView
from collective.iconifiedcategory.browser.actionview import ToPrintChangeView
from collective.iconifiedcategory.browser.tabview import CategorizedTable
from collective.iconifiedcategory.browser.tabview import CategorizedTabView
from collective.iconifiedcategory.browser.views import CategorizedChildInfosView
from collective.iconifiedcategory.browser.views import CategorizedChildView
from collective.iconifiedcategory.utils import _categorized_elements
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_vocab
from plone import api
from plone.memoize import ram
from Products.PloneMeeting.browser.overrides import BaseActionsPanelView
from Products.PloneMeeting.config import FACETED_ANNEXES_CRITERION_ID
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_annexes_config


class AnnexActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on an annex.
    """

    def showHistoryForContext(self):
        """
          History on annexes is only shown to Managers.
        """
        if not super(AnnexActionsPanelView, self).showHistoryForContext():
            return False

        # check isManager on parent (item) so caching is used as context is a key
        # used in the caching invalidation
        parent = self.context.aq_inner.aq_parent
        while parent.__class__.__name__ not in ('MeetingItem', 'Meeting'):
            parent = parent.aq_inner.aq_parent
        return self.tool.isManager(realManagers=True)


class CategorizedAnnexesTable(CategorizedTable):
    """ """

    def initColumns(self):
        """Change name of checkbox column for annex decisions,
           because for batchaction, column name must be different than
           checkbox column of normal annexes.
           """
        super(CategorizedAnnexesTable, self).initColumns()
        if self.portal_type == 'annexDecision':
            column = self.columnByName['select_row']
            column.name = "select_item_annex_decision"


class CategorizedAnnexesView(CategorizedTabView):
    """ """

    def __call__(self):
        """ """
        self._update()
        return super(CategorizedAnnexesView, self).__call__()

    def _update(self):
        """ """
        self.portal_url = api.portal.get().absolute_url()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        # compute show annexes here and display a message to the (Meeting)Managers
        # if not able to add annexes because nothing found in annex vocab nor annexDecision vocab
        annex_vocab, self._showAddAnnex = self.showAddAnnex()
        self.annexDecision_vocab, self._showAddAnnexDecision = self.showAddAnnexDecision()
        if not len(annex_vocab) and not len(self.annexDecision_vocab) and self.tool.isManager(self.cfg):
            api.portal.show_message(
                _('The configuration does not let you add annexes.'),
                request=self.request)

    def _check_can_view(self):
        """ """
        return self.context.__class__.__name__ == "Meeting"

    def _config(self):
        """ """
        return get_annexes_config(self.context, self.portal_type)

    def _show_column(self, action_type):
        """Made to be overrided."""
        annex_attr_config = '{0}_display'.format(action_type)
        check = annex_attr_config in self.cfg.getAnnexRestrictShownAndEditableAttributes()
        return not check or self.tool.isManager(self.cfg)

    def showAddAnnex(self):
        """ """
        portal_types = api.portal.get_tool('portal_types')
        annexTypeInfo = portal_types['annex']
        vocab = get_vocab(self.context, 'collective.iconifiedcategory.categories')
        show = annexTypeInfo in self.context.allowedContentTypes() and len(vocab)
        return vocab, show

    def showAddAnnexDecision(self):
        """ """
        portal_types = api.portal.get_tool('portal_types')
        annexTypeInfo = portal_types['annexDecision']
        self.request.set('force_use_item_decision_annexes_group', True)
        vocab = get_vocab(self.context, 'collective.iconifiedcategory.categories')
        self.request.set('force_use_item_decision_annexes_group', False)
        show = annexTypeInfo in self.context.allowedContentTypes() and len(vocab)
        return vocab, show

    def showAnnexesSection(self):
        """Always show this section, a message is displayed in case configuration
           is not correct, this invite Managers to use annexes."""
        return True

    def showDecisionAnnexesSection(self):
        """Check if context contains decisionAnnexes or if there
           are some decisionAnnex annex types available in the configuration."""
        if self.context.__class__.__name__ == 'MeetingItem' and \
            (get_annexes(self.context, portal_types=['annexDecision']) or
             self._showAddAnnexDecision or len(self.annexDecision_vocab)):
            return True
        return False


def _get_filters(request):
    """ """
    # caching
    res = request.get("cached_annexes_filters", None)
    if res is None:
        res = {}
        # in request.form, faceted criterion is like 'c20[]'
        faceted_filter = request.form.get(FACETED_ANNEXES_CRITERION_ID + '[]', None)
        if faceted_filter is not None:
            if not hasattr(faceted_filter, '__iter__'):
                faceted_filter = [faceted_filter]
            for value in faceted_filter:
                if value.startswith('not_'):
                    res[value.replace('not_', '')] = False
                else:
                    res[value] = True
        request["cached_annexes_filters"] = res
    return res


class PMCategorizedChildView(CategorizedChildView):
    """Add caching."""

    def __call___cachekey(method, self, portal_type=None, show_nothing=False, check_can_view=False):
        '''cachekey method for self.__call__.'''
        categorized_elements = _categorized_elements(self.context)
        if not categorized_elements:
            return show_nothing
        # value of the annexes faceted filter
        filters = self._filters
        if filters:
            raise ram.DontCache

        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        # URL to the annex_type can change if server URL changed
        server_url = self.request.get('SERVER_URL', None)
        # use "last_updated" to know when categorized_elements was last updated...
        last_updated = max(
            [info['last_updated'] for info in categorized_elements.values()])
        # this is necessary in case an annex is removed
        len_annexes = len(categorized_elements)
        cfg_modified = cfg.modified()
        # check confidential annexes if not MeetingManager
        isManager = tool.isManager(cfg)
        # manage confidential annexes for non managers
        may_view_confidential_annexes = True
        if not isManager:
            confidential_annexes = [
                elt for elt in self.context.categorized_elements.values()
                if elt["confidential"]]
            may_view_confidential_annexes = not confidential_annexes or \
                set(get_plone_groups_for_user()).intersection(
                    confidential_annexes[0]["visible_for_groups"])
        return (repr(self.context),
                last_updated,
                len_annexes,
                cfg_modified,
                server_url,
                may_view_confidential_annexes,
                portal_type,
                show_nothing,
                check_can_view)

    @property
    def _filters(self):
        """ """
        return _get_filters(self.request)

    @ram.cache(__call___cachekey)
    def __call__(self, portal_type=None, show_nothing=False, check_can_view=False):
        """Override to change show_nothing=False instead
           show_nothing=True and to add caching."""
        return super(PMCategorizedChildView, self).__call__(
            portal_type, show_nothing, check_can_view)


class PMCategorizedChildInfosView(CategorizedChildInfosView):
    """ """

    def __init__(self, context, request):
        """ """
        super(PMCategorizedChildInfosView, self).__init__(context, request)
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    @property
    def _filters(self):
        """ """
        return _get_filters(self.request)

    def show_preview(self, element):
        """Show preview if the auto_convert in collective.documentviewer is enabled."""
        return super(PMCategorizedChildInfosView, self).show_preview(element) or \
            self.tool.auto_convert_annexes()

    def _show_protected_download(self, element):
        """When "show_preview" is "2", trigger advanced check.
           Are allowed to download:
           - proposingGroup members;
           - (Meeting)Managers."""
        return self.tool.isManager(self.cfg) or \
            self.context.getProposingGroup() in self.tool.get_orgs_for_user()

    def show_nothing(self):
        """Do not display the 'Nothing' label."""
        return False

    def categorized_elements_more_infos_url(self):
        """ """
        return "{0}/@@categorized-annexes".format(self.context.absolute_url())

    def _show_detail(self, detail_type):
        """ """
        annex_attr_config = '{0}_display'.format(detail_type)
        check = annex_attr_config in self.cfg.getAnnexRestrictShownAndEditableAttributes()
        return not check or self.tool.isManager(self.cfg)


class PMBaseActionView(BaseActionView):
    """ """

    def _get_config_attributes(self):
        """ """
        category_group_attr_name = getattr(self, 'category_group_attr_name', None)
        # get current type of action
        # turn to_be_printed_activated to to_be_printed_edit/to_be_printed_display
        # if an element is not displayed only to MeetingManagers, we consider it is ony editable as well
        config_attr_display = category_group_attr_name.replace('_activated', '_display')
        config_attr_edit = category_group_attr_name.replace('_activated', '_edit')
        return config_attr_display, config_attr_edit

    def _may_set_values(self, values, ):
        res = super(PMBaseActionView, self)._may_set_values(values)
        if res:
            # get current type of action
            # turn to_be_printed_activated to to_be_printed_edit/to_be_printed_display
            # if an element is not displayed only to MeetingManagers, we consider it is ony editable as well
            config_attr_display, config_attr_edit = self._get_config_attributes()
            # restricted to MeetingManagers?
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self.context)
            annex_attr_config = cfg.getAnnexRestrictShownAndEditableAttributes()
            if config_attr_display in annex_attr_config or config_attr_edit in annex_attr_config:
                res = tool.isManager(cfg)
        return res


class PMConfidentialChangeView(ConfidentialChangeView, PMBaseActionView):
    """Override to use new base klass."""


class PMPublishableChangeView(PublishableChangeView, PMBaseActionView):
    """Override to use new base klass."""


class PMSignedChangeView(SignedChangeView, PMBaseActionView):
    """Override to use new base klass."""


class PMToPrintChangeView(ToPrintChangeView, PMBaseActionView):
    """Override to use new base klass."""
