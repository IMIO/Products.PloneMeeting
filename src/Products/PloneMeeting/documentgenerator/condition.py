# -*- coding: utf-8 -*-

from collective.documentgenerator.content.condition import ConfigurablePODTemplateCondition
from collective.eeafaceted.dashboard.content.pod_template import DashboardPODTemplateCondition
from plone import api


class PMConfigurablePODTemplateCondition(ConfigurablePODTemplateCondition):
    """
    """

    def _extra_expr_ctx(self):
        """ """
        extra_context = super(PMConfigurablePODTemplateCondition, self)._extra_expr_ctx()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        extra_context.update({'tool': tool,
                              'cfg': cfg})
        return extra_context

    def evaluate_allowed_context(self, context):
        """
        Override so we may use a single 'MeetingItemXXX' portal_type
        to work with real MeetingItem, ItemTemplate and RecurringItem item type.
        """
        allowed_types = list(self.pod_template.pod_portal_types)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # add the ItemTemplate and RecurringItem to allowed_types if itemTypeName is allowed
        if cfg and cfg.getItemTypeName() in allowed_types:
            allowed_types.append(cfg.getItemTypeName(configType='MeetingItemTemplate'))
            allowed_types.append(cfg.getItemTypeName(configType='MeetingItemRecurring'))
        return not allowed_types or context.portal_type in allowed_types


class PMDashboardPODTemplateCondition(DashboardPODTemplateCondition):
    """ """

    def _extra_expr_ctx(self):
        """ """
        extra_context = super(PMDashboardPODTemplateCondition, self)._extra_expr_ctx()
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        extra_context.update({'tool': tool,
                              'cfg': cfg})
        return extra_context
