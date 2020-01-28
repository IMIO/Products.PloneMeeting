# -*- coding: utf-8 -*-
#
# File: adapters.py
#
# Copyright (c) 2019 by Imio.be
#
# GNU General Public License (GPL)
#


from collective.behavior.talcondition.behavior import TALCondition
from plone import api
from Products.PageTemplates.Expressions import SecureModuleImporter


class PMTALCondition(TALCondition):
    """Override TALCondition behavior to add our own TAL expression extra context."""

    def complete_extra_expr_ctx(self, extra_expr_ctx):
        """Return extra_expr_ctx, this is made to be overrided."""
        extra_context = super(PMTALCondition, self).complete_extra_expr_ctx(extra_expr_ctx)
        tool = api.portal.get_tool('portal_plonemeeting')
        context = extra_context.get('context', self.context)
        cfg = tool.getMeetingConfig(context)
        extra_context.update({'tool': tool,
                              'pm_utils': SecureModuleImporter['Products.PloneMeeting.utils'],
                              'imio_history_utils': SecureModuleImporter['imio.history.utils'],
                              'cfg': cfg})
        return extra_context
