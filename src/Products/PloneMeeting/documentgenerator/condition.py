# -*- coding: utf-8 -*-

from plone import api
from collective.documentgenerator.content.condition import ConfigurablePODTemplateCondition


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
