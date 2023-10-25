# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#


from collective.behavior.talcondition.behavior import TALCondition
from Products.PloneMeeting.utils import _base_extra_expr_ctx


class PMTALCondition(TALCondition):
    """Override TALCondition behavior to add our own TAL expression extra context."""

    def complete_extra_expr_ctx(self, extra_expr_ctx):
        """Return extra_expr_ctx, this is made to be overrided."""
        extra_context = super(PMTALCondition, self).complete_extra_expr_ctx(extra_expr_ctx)
        context = extra_context.get('context', self.context)
        base_extra_expr_ctx = _base_extra_expr_ctx(context)
        extra_context.update(base_extra_expr_ctx)
        return extra_context
